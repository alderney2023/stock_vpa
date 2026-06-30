"""量价分析为核心的 LLM 分析器（支持周线锚定）"""
from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from src.vpa_indicators import VPIndicators
from src.vpa_features import VPAExtractor

_WEEKLY_PROMPT = """你是一位资深机构交易员，专注量价关系分析。请基于以下数据，对 {name} ({code}) 进行深度量价分析。

## 【第一步】周线趋势判断（定大方向）
以下是最低52周完整周的原始数据，请自行判断当前中期趋势：

| 周起始 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |
|--------|------|------|------|------|--------|
{weekly_rows}

请基于以上周线数据，判断并输出：
- 中期趋势方向：（如：上升、下降、震荡）
- 趋势强度：（如：强、中、弱）
- 关键周线支撑/阻力价位
- 近4-8周量价配合概况

---

## 【第二步】日线量价分析（找入场点）

### 日线头版摘要
{headlines}

### 阶段划分
{phases}

### 关键价位
{levels}

### 量价异动
{events}

### 补充验证
{supp}

---

## 分析要求（严格按照此步骤）

### 一、趋势一致性检验（重要！）
1. 先看周线：中期趋势是什么？
2. 再看日线：当前处于该趋势的什么位置？

对照规则：
- 若周线上升 + 日线回调 = "上升途中的正常回调，关注支撑位是否有效"
- 若周线上升 + 日线突破 = "趋势确认，可考虑跟进"
- 若周线下降 + 日线反弹 = "下降途中的反弹，警惕假突破"
- 若周线震荡 + 日线异动 = "震荡区间内的波动，关注区间突破"

### 二、量价关系核心解读（重点，需占 60% 篇幅）
- 结合 OBV / CMF / VWAP 判断资金真实意图
- 判断量价是否配合（放量涨/缩量跌 为健康）
- 解读天量 / 地量 出现的位置及含义
- 结合 A/D 线判断积累或分布
- 综合 MFI 和 Force Index 判断买卖力量

### 三、关键价位分析
- 日线关键支撑/阻力
- 这些价位与周线支撑/阻力的关系
- 若日线价位接近周线关键位，需特别关注

### 四、补充指标简要验证（占 20% 篇幅）
- 均线 / MACD 验证
- RSI / KDJ 验证
- ATR / Bollinger 提供波动率背景

### 五、结论（必须包含以下格式）
1. 【中期趋势评分】(0-10分，基于周线) + 简述理由
2. 【短期状态】(吸筹/拉升/洗盘/出货/回调/反弹)
3. 【趋势一致性】日线与周线是否一致？不一致时如何判断？
4. 【入场点建议】若趋势一致，给出具体建议
5. 【风险提示】关键观察点
"""


class VpaAnalyzer:
    MAX_DAYS = 150  # 限制最大分析天数

    def __init__(self):
        self._client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    def analyze(self, name: str, code: str, df_daily, df_weekly):
        n = len(df_daily)

        # 限制天数
        if n > self.MAX_DAYS:
            print(f"数据量 {n} 天超过限制 {self.MAX_DAYS} 天，将使用最后 {self.MAX_DAYS} 天数据")
            df_daily = df_daily.tail(self.MAX_DAYS)
            n = self.MAX_DAYS

        # 计算日线指标
        ind = VPIndicators(df_daily)
        df_ind = ind.df

        ext = VPAExtractor(df_ind)
        feat = ext.extract()

        headlines = self._fmt_headlines(feat["vpa_headers"])
        phases = self._fmt_phases(feat["vpa_phases"])
        levels = self._fmt_levels(feat["key_levels"])
        events = self._fmt_events(feat["volume_events"])
        supp = self._fmt_supp(feat["supp_verify"])

        # 格式化周K数据
        weekly_rows = self._fmt_weekly(df_weekly)

        prompt = _WEEKLY_PROMPT.format(
            name=name,
            code=code,
            weekly_rows=weekly_rows,
            headlines=headlines,
            phases=phases,
            levels=levels,
            events=events,
            supp=supp,
        )

        print(f"Prompt length: {len(prompt)} chars, using {n} days data, {len(df_weekly)} weeks data")
        return self._stream(prompt)

    @staticmethod
    def _fmt_weekly(df_weekly) -> str:
        """格式化周K数据为表格行"""
        lines = []
        for _, r in df_weekly.iterrows():
            v = r['volume']
            # 成交量格式化为 万/亿
            if v >= 1e8:
                vol_str = f"{v/1e8:.2f}亿"
            elif v >= 1e4:
                vol_str = f"{v/1e4:.2f}万"
            else:
                vol_str = f"{v:.0f}"
            lines.append(
                f"| {r['week_start']} | {r['open']:.2f} | {r['high']:.2f} | {r['low']:.2f} | {r['close']:.2f} | {vol_str} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _fmt_headlines(d) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _fmt_phases(phases: list) -> str:
        if not phases:
            return "(数据不足，无法划分阶段)"
        lines = []
        for i, p in enumerate(phases, 1):
            lines.append(f"  {i}. {p['时间']} ({p['天数']}天) | {p['区间涨跌']} | 均量 {p['均量倍数']} | {p['量价标签']}")
        return "\n".join(lines)

    @staticmethod
    def _fmt_levels(lvls: dict) -> str:
        sup = lvls.get("支撑位", [])
        res = lvls.get("阻力位", [])
        lines = ["支撑位:"]
        for s in sup:
            lines.append(f"  - {s['价格']:.2f}  ({s['类型']})")
        lines.append("阻力位:")
        for r in res:
            lines.append(f"  - {r['价格']:.2f}  ({r['类型']})")
        return "\n".join(lines) if (sup or res) else "(暂无明确关键价位)"

    @staticmethod
    def _fmt_events(events: list) -> str:
        if not events:
            return "(近20日无明显异动)"
        return "\n".join(f"- {e}" for e in events)

    @staticmethod
    def _fmt_supp(d: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    def _stream(self, prompt: str):
        try:
            print(f"正在分析... (共 {len(prompt)} 字符，使用流式输出)")
            resp = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                stream=True,
            )
            chunks = []
            for chunk in resp:
                if not chunk.choices:
                    continue
                c = chunk.choices[0].delta.content or ""
                print(c, end="", flush=True)
                chunks.append(c)
            print()
            return "".join(chunks)
        except Exception as e:
            print(f"\n分析失败: {e}")
            print("请检查：")
            print("1. API密钥是否正确配置")
            print("2. 网络连接是否正常")
            print("3. API服务是否可用")
            return None


def analyze(name: str, code: str, df_daily, df_weekly):
    return VpaAnalyzer().analyze(name, code, df_daily, df_weekly)
