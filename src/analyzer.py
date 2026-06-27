from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


_PROMPT_TEMPLATE = """你是一位擅长量价时空分析的A股职业交易员，拥有10年以上实战经验。请基于以下日K线数据，对 {name} ({code}) 进行深度量价分析。

## 分析目标
- 透过量价关系，识别主力资金行为（吸筹、洗盘、拉升、出货）
- 判断当前趋势的健康程度与可持续性
- 发现潜在转折信号或异常波动

## 输入数据
最近 {count} 个交易日数据（按时间倒序/正序排列，请自行判断）：

| 日期 | 开盘 | 最高 | 最低 | 收盘 | 成交额 | 成交量 |
|------|------|------|------|------|--------|--------|
{kline_rows}

## 分析步骤与输出要求（请严格按以下结构作答）

### 一、量价阶段特征（逐日或分段）
- 将数据划分为3~5个阶段（如上涨初期、主升、高位震荡等），对每个阶段描述：
  - 价格走势（涨跌幅、斜率）
  - 成交量变化（放量/缩量/平量，对比前5日均量）
  - 量价配合类型（列举：放量上涨、缩量上涨、放量下跌、缩量下跌、量价背离、放量滞涨、缩量止跌等）
  - 该阶段反映的市场情绪与资金意图

### 二、关键价格区间验证
- 计算并标识：
  - 近期明显支撑位（价格+触碰次数+对应量能）
  - 近期明显阻力位（价格+触碰次数+对应量能）
  - 用成交量验证这些位置的有效性（如：支撑位缩量不破，阻力位放量突破等）
- 若有突破或跌破，说明是真突破还是假突破（结合量能）

### 三、趋势质量评估
- 判断当前主要趋势（上升/下降/横盘），并用以下指标佐证：
  - 均线排列（若可推算大致MA5/MA10/MA20方向）
  - 趋势线斜率与角度
  - 成交量是否与趋势方向共振（趋势上行需温和放量，趋势下行需缩量或恐慌放量）
- 评估趋势的持续性（如：上升趋势是否出现量价背离，下降趋势是否出现底部放量）

### 四、异常信号与警示
- 识别并重点解释以下信号（如有）：
  - 天量天价（阶段性最大量伴随最高价，可能见顶）
  - 地量地价（阶段性最小量伴随最低价，可能见底）
  - 放量滞涨（成交量放大但价格涨幅缩小或走平）
  - 缩量深跌（价格大跌但成交量萎缩，可能非理性杀跌）
  - 尾盘异动、大单对倒等（从量价形态推断）
- 若无明显异常，请说明“当前量价结构较为常规”

### 五、综合结论与操作参考
- 给出总体量价健康度评分（满分10分）及理由
- 明确当前处于趋势的哪个阶段（早期/中期/末期）
- 给出短期（1~3日）和中期（1~2周）的量价预判
- 提供风险提示（如：关键支撑跌破则趋势转弱，阻力位突破需补量确认等）
- 若需制定策略，建议关注哪些量价触发条件（如：收盘站上XX量且放量则加仓，缩量破XX则减仓）

## 重要注意事项
- 分析必须基于数据内在逻辑，不得凭空猜测基本面
- 每个结论必须有量价证据支撑（引用具体日期或数值）
- 避免模糊表述（如“可能”“或许”），尽量用“数据显示”“量能表明”等客观措辞
- 若数据不足或信号矛盾，请明确指出不确定性

请开始你的专业分析：
"""


def analyze(name: str, code: str, kline_df) -> str:
    count = len(kline_df)
    rows = "\n".join(
        f"| {r['date']} | {r['open']} | {r['high']} | {r['low']} | {r['close']} | {r['amount']:.0f} | {r['volume']:.0f} |"
        for _, r in kline_df.iterrows()
    )
    prompt = _PROMPT_TEMPLATE.format(
        name=name, code=code, count=count, kline_rows=rows
    )

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        stream=True,
    )

    chunks = []
    for chunk in resp:
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
        chunks.append(content)
    print()
    return "".join(chunks)
