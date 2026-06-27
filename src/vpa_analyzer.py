"""量价分析为核心的 LLM 分析器"""
import json
from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from src.vpa_indicators import VPIndicators
from src.vpa_features import VPAExtractor

_VPA_PROMPT = """你是一位资深机构交易员，专注量价关系分析。请基于以下数据，对 {name} ({code}) 进行深度量价分析。

## 量价头版摘要
{headlines}

## 量价阶段划分
{phases}

## 关键价位
{levels}

## 量价异动事件
{events}

## 补充指标交叉验证
{supp}


## 分析要求

### 一、量价关系核心解读（重点，需占 80% 篇幅）
- 结合 OBV / CMF / VWAP 判断资金真实意图：吸筹、洗盘、拉升、出货
- 判断量价是否配合（放量涨/缩量跌 为健康）
- 解读天量 / 地量 出现的位置及含义
- 结合 A/D 线判断积累或分布
- 综合 MFI 和 Force Index 判断买卖力量的强度

### 二、补充指标简要验证（简要，占 20% 篇幅）
- 均线 / MACD 验证趋势方向
- RSI / KDJ 验证超买超卖
- ATR / Bollinger 提供波动率背景

### 三、结论
1. 量价健康度 (0-10分，简述理由)
2. 所处阶段 (吸筹/拉升/出货/下跌)
3. 后市预判 (未来3-5日量价走势)
4. 关键观察点与风险提示
5. 操作建议 (仅参考)
"""


class VpaAnalyzer:
    MAX_DAYS = 150  # 限制最大分析天数

    def __init__(self):
        self._client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    def analyze(self, name: str, code: str, df):
        n = len(df)

        # 限制天数
        if n > self.MAX_DAYS:
            print(f"数据量 {n} 天超过限制 {self.MAX_DAYS} 天，将使用最后 {self.MAX_DAYS} 天数据")
            df = df.tail(self.MAX_DAYS)
            n = self.MAX_DAYS

        ind = VPIndicators(df)
        df_ind = ind.df

        ext = VPAExtractor(df_ind)
        feat = ext.extract()

        headlines = self._fmt_headlines(feat["vpa_headers"])
        phases = self._fmt_phases(feat["vpa_phases"])
        levels = self._fmt_levels(feat["key_levels"])
        events = self._fmt_events(feat["volume_events"])
        supp = self._fmt_supp(feat["supp_verify"])

        prompt = _VPA_PROMPT.format(
            name=name,
            code=code,
            headlines=headlines,
            phases=phases,
            levels=levels,
            events=events,
            supp=supp,
        )

        print(f"Prompt length: {len(prompt)} chars, using {n} days data")
        return self._stream(prompt)

    # ---------- 格式化辅助 ----------
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


def analyze(name: str, code: str, df):
    return VpaAnalyzer().analyze(name, code, df)