"""量价特征深度提取器"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class VPAExtractor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._n = len(df)

    # ============================================================
    #  全部特征 (供 LLM 消费)
    # ============================================================
    def extract(self) -> Dict[str, Any]:
        # 确保索引是日期
        if not isinstance(self.df.index, pd.DatetimeIndex):
            if self.df.index.name == "date":
                try:
                    self.df.index = pd.to_datetime(self.df.index)
                except Exception:
                    pass
        return {
            "vpa_headers": self._vpa_headlines(),
            "vpa_phases": self._vpa_phases(),
            "key_levels": self._key_levels(),
            "volume_events": self._volume_events(),
            "supp_verify": self._supp_check(),
        }

    # ============================================================
    #  一、量价头版结论 — 最核心摘要
    # ============================================================
    def _vpa_headlines(self) -> Dict[str, Any]:
        latest = self.df.iloc[-1]
        prev5 = self.df.tail(5)

        mfi = latest["mfi"]
        mfi_desc = "超买" if mfi > 80 else ("超卖" if mfi < 20 else "正常")
        cmf = latest["cmf"]
        cmf_desc = "资金流入" if cmf > 0.05 else ("资金流出" if cmf < -0.05 else "中性")

        avg_vol_5 = prev5["volume"].mean()
        avg_vol_20 = self.df.tail(20)["volume"].mean() if self._n >= 20 else avg_vol_5
        vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1.0

        price_5d = (latest["close"] - self.df.iloc[-5]["close"]) / abs(self.df.iloc[-5]["close"]) * 100 if self._n >= 5 else 0

        obv_dir = "上升" if latest["obv"] > latest["obv_ma5"] else "下降"
        ad_dir = "积累" if latest["ad"] > latest["ad_ma5"] else "分布"

        close = latest["close"]
        bb_upper = latest["bb_upper"]
        bb_lower = latest["bb_lower"]
        bb_pos = "上轨以上" if close > bb_upper else ("下轨以下" if close < bb_lower else "轨道内")

        atr_pct = latest["atr"] / close * 100 if close > 0 else 0

        return {
            "收盘价": round(float(close), 2),
            "近5日涨跌幅": f"{price_5d:+.2f}%",
            "成交量活跃度": f"{vol_ratio:.2f}x 近20日均量",
            "OBV趋势": obv_dir,
            "资金流量MFI": f"{mfi:.1f} ({mfi_desc})",
            "蔡金资金流CMF": f"{cmf:.3f} ({cmf_desc})",
            "A/D 积累分布": ad_dir,
            "布林带位置": bb_pos,
            "波动率ATR/Price": f"{atr_pct:.2f}%",
        }

    # ============================================================
    #  二、量价阶段划分
    # ============================================================
    def _vpa_phases(self) -> List[Dict[str, Any]]:
        if self._n < 10:
            return []
        phases = []
        df = self.df.copy()
        df["pct"] = df["close"].pct_change()
        df["vol_factor"] = df["volume"] / df["volume"].rolling(5, min_periods=1).mean()

        segments = self._simple_segment(5)
        for seg in segments:
            sub = df.iloc[seg[0]: seg[1] + 1]
            if len(sub) < 2:
                continue
            start_date = self._date_str(sub.index[0])
            end_date = self._date_str(sub.index[-1])
            price_chg = (sub["close"].iloc[-1] - sub["close"].iloc[0]) / abs(sub["close"].iloc[0]) * 100
            avg_vol_vs_20 = sub["volume"].mean() / df["volume"].tail(20).mean() if self._n >= 20 else 1.0
            if price_chg > 3 and avg_vol_vs_20 > 1.2:
                label = "放量上涨"
            elif price_chg > 3 and avg_vol_vs_20 < 0.8:
                label = "缩量上涨"
            elif price_chg < -3 and avg_vol_vs_20 > 1.2:
                label = "放量下跌"
            elif price_chg < -3 and avg_vol_vs_20 < 0.8:
                label = "缩量下跌"
            elif abs(price_chg) <= 3 and avg_vol_vs_20 > 1.2:
                label = "放量横盘"
            elif abs(price_chg) <= 3 and avg_vol_vs_20 < 0.8:
                label = "缩量横盘"
            else:
                label = "正常波动"
            phases.append({
                "时间": f"{start_date} → {end_date}",
                "天数": len(sub),
                "区间涨跌": f"{price_chg:+.1f}%",
                "均量倍数": f"{avg_vol_vs_20:.2f}x",
                "量价标签": label,
            })
        return phases

    # ============================================================
    #  三、关键价位 (支撑 / 阻力)
    # ============================================================
    def _key_levels(self) -> Dict[str, Any]:
        latest = self.df.iloc[-1]
        close = latest["close"]
        supports, resistances = [], []

        if self._n >= 20:
            for d in [5, 10, 20]:
                row = self.df.iloc[-d]
                lo, hi = row["low"], row["high"]
                if lo < close:
                    supports.append({"价格": round(float(lo), 2), "类型": f"{d}日前低点"})
                if hi > close:
                    resistances.append({"价格": round(float(hi), 2), "类型": f"{d}日前高点"})
        for label, val in [("MA20", latest["ma20"]), ("MA10", latest["ma10"]), ("MA5", latest["ma5"]), ("VWAP", latest["vwap"])]:
            if val < close:
                supports.append({"价格": round(float(val), 2), "类型": label})
            elif val > close:
                resistances.append({"价格": round(float(val), 2), "类型": label})

        supports = sorted(supports, key=lambda x: x["价格"], reverse=True)[:4]
        resistances = sorted(resistances, key=lambda x: x["价格"])[:4]

        return {
            "支撑位": supports,
            "阻力位": resistances,
        }

    # ============================================================
    #  四、成交量异常事件
    # ============================================================
    def _volume_events(self) -> List[str]:
        events = []
        df = self.df
        if self._n < 20:
            return events

        vol_ma20 = df["volume"].tail(20).mean()
        latest = df.iloc[-1]
        close, vol = latest["close"], latest["volume"]
        if vol > vol_ma20 * 2.5:
            events.append(f"天量警报：最近交易日成交量是20日均量的 {vol/vol_ma20:.1f} 倍")
        elif vol < vol_ma20 * 0.3:
            events.append(f"地量信号：最近交易日成交量仅为20日均量的 {vol/vol_ma20:.1f} 倍")
        if self._n >= 5:
            prev5 = df.iloc[-5]
            price_chg_5d = (close - prev5["close"]) / abs(prev5["close"]) * 100
            if price_chg_5d > 10 and vol < vol_ma20 * 0.8:
                events.append(f"缩量暴涨：近5日涨幅 {price_chg_5d:+.1f}% 但量能萎缩，警惕诱多")
            elif price_chg_5d > 10 and vol > vol_ma20 * 1.5:
                events.append(f"放量暴涨：近5日涨幅 {price_chg_5d:+.1f}% 量价配合良好，但需关注是否天量见顶")
            elif price_chg_5d < -10 and vol < vol_ma20 * 0.8:
                events.append(f"缩量暴跌：近5日跌幅 {price_chg_5d:+.1f}% 但量能萎缩，卖压衰竭可能")
            elif price_chg_5d < -10 and vol > vol_ma20 * 1.5:
                events.append(f"放量暴跌：近5日跌幅 {price_chg_5d:+.1f}% 恐慌盘涌出，关注是否超跌")

        # 量价背离
        if self._n >= 10:
            price_up = close > df.iloc[-10]["close"]
            vol_down = df.tail(5)["volume"].mean() < df.iloc[-10:-5]["volume"].mean()
            if price_up and vol_down:
                events.append("量价背离：价格创新高但成交量萎缩，上升动能减弱")
            price_down = close < df.iloc[-10]["close"]
            vol_up = df.tail(5)["volume"].mean() > df.iloc[-10:-5]["volume"].mean()
            if price_down and vol_up:
                events.append("量价背离：价格下跌但成交量放大，关注抄底资金介入")
        return events

    # ============================================================
    #  五、补充指标简要验证
    # ============================================================
    def _supp_check(self) -> Dict[str, Any]:
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if self._n > 1 else latest

        macd_kind = ""
        if latest["macd"] > latest["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
            macd_kind = "MACD 金叉 → 趋势转强"
        elif latest["macd"] < latest["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
            macd_kind = "MACD 死叉 → 趋势转弱"
        elif latest["macd"] > latest["macd_signal"]:
            macd_kind = "MACD 多头运行"
        else:
            macd_kind = "MACD 空头运行"

        kdj_kind = ""
        if latest["kdj_k"] > latest["kdj_d"] and prev["kdj_k"] <= prev["kdj_d"]:
            kdj_kind = "KDJ 金叉 → 短线转强"
        elif latest["kdj_k"] < latest["kdj_d"] and prev["kdj_k"] >= prev["kdj_d"]:
            kdj_kind = "KDJ 死叉 → 短线转弱"
        elif latest["kdj_k"] > latest["kdj_d"]:
            kdj_kind = "KDJ 多头运行"
        else:
            kdj_kind = "KDJ 空头运行"

        rsi_val = latest["rsi"]
        rsi_desc = "超买" if rsi_val > 70 else ("超卖" if rsi_val < 30 else "中性")

        ma_desc = ""
        if latest["ma5"] > latest["ma10"] > latest["ma20"]:
            ma_desc = "多头排列 → 上升趋势确认"
        elif latest["ma5"] < latest["ma10"] < latest["ma20"]:
            ma_desc = "空头排列 → 下降趋势确认"
        else:
            ma_desc = "均线缠绕 → 震荡整理"

        roc_val = latest["roc"]

        return {
            "MACD": f"DIF {latest['macd']:.3f} DEA {latest['macd_signal']:.3f} | {macd_kind}",
            "RSI(14)": f"{rsi_val:.1f} ({rsi_desc})",
            "KDJ": f"K {latest['kdj_k']:.1f} D {latest['kdj_d']:.1f} J {latest['kdj_j']:.1f} | {kdj_kind}",
            "均线": ma_desc,
            "ROC(10)": f"{roc_val:.2f}",
        }

    # ============================================================
    #  辅助方法
    # ============================================================
    def _simple_segment(self, k: int) -> List[tuple]:
        n = self._n
        if n <= k:
            return [(0, n - 1)]
        step = n // k
        segs = []
        for i in range(k):
            start = i * step
            end = start + step - 1 if i < k - 1 else n - 1
            if start < n and end >= start:
                segs.append((start, end))
        return segs

    def _date_str(self, row) -> str:
        try:
            val = row.get("date", row.name)
            if hasattr(val, "strftime"):
                return val.strftime("%Y-%m-%d")
            if isinstance(val, (int, float)):
                try:
                    return pd.to_datetime(val).strftime("%Y-%m-%d")
                except Exception:
                    pass
            if val is not None:
                return str(val)[:10]
            return "未知日期"
        except Exception:
            try:
                return str(row.name)[:10] if row.name is not None else "未知日期"
            except Exception:
                return "未知日期"


def extract(df: pd.DataFrame) -> Dict[str, Any]:
    return VPAExtractor(df).extract()