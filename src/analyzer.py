from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


_PROMPT_TEMPLATE = """你是一位专业的A股量价分析分析师。请根据以下日K线数据，进行量价分析。

分析要求：
1. **量价配合关系**：分析每个时间段内价格与成交量的配合情况（放量上涨、缩量上涨、放量下跌、缩量下跌、量价背离等）
2. **关键位置识别**：识别重要的支撑位和阻力位，并结合成交量验证其有效性
3. **趋势判断**：判断当前处于什么趋势（上升/下降/横盘），成交量是否支持该趋势
4. **异常信号**：指出是否有异常的量价信号（如天量天价、地量地价、放量滞涨等）
5. **总结观点**：给出综合性的量价分析结论

以下是 {name} ({code}) 最近 {count} 个交易日的日K线数据：

| 日期 | 开盘价 | 最高价 | 最低价 | 收盘价 | 成交额 | 成交量 |
|------|--------|--------|--------|--------|--------|--------|
{kline_rows}

请给出详细分析："""


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
