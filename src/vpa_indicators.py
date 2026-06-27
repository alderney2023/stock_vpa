"""量价分析核心指标计算引擎"""
import numpy as np
import pandas as pd
import pandas_ta as ta


class VPIndicators:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._prepare()
        self._core_vpa()
        self._supplement()

    def _prepare(self):
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in self.df.columns:
                raise ValueError(f"缺少列: {col}")
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce").fillna(0)
        for col in ["open", "high", "low", "close"]:
            self.df[col] = self.df[col].clip(lower=0)
        self.df["volume"] = self.df["volume"].clip(lower=0)
        return self

    # ============================================================
    #  核心量价指标 — 深度分析的重点
    # ============================================================
    def _core_vpa(self):
        df = self.df
        cl = df["close"]
        vo = df["volume"]
        hi = df["high"]
        lo = df["low"]

        # OBV
        obv = ta.obv(cl, vo)
        df["obv"] = obv if obv is not None and not obv.empty else 0
        df["obv_ma5"] = df["obv"].rolling(5, min_periods=1).mean()
        df["obv_ma10"] = df["obv"].rolling(10, min_periods=1).mean()
        df["obv_signal"] = np.where(df["obv"] > df["obv_ma5"], 1, -1)

        # VWAP
        vwap = ta.vwap(hi, lo, cl, vo)
        df["vwap"] = vwap if vwap is not None and not vwap.empty else cl
        df["price_vs_vwap"] = (cl - df["vwap"]) / df["vwap"].replace(0, np.nan) * 100

        # A/D
        ad = ta.ad(hi, lo, cl, vo)
        df["ad"] = ad if ad is not None and not ad.empty else 0
        df["ad_ma5"] = df["ad"].rolling(5, min_periods=1).mean()
        df["ad_ma10"] = df["ad"].rolling(10, min_periods=1).mean()

        # MFI
        mfi = ta.mfi(hi, lo, cl, vo, length=14)
        df["mfi"] = mfi if mfi is not None and not mfi.empty else 50

        # CMF
        cmf = ta.cmf(hi, lo, cl, vo, length=20)
        df["cmf"] = cmf if cmf is not None and not cmf.empty else 0

        # VP (Volume Price Trend) - Skip if fails
        try:
            vp = ta.vp(cl, vo)
            df["vpt"] = vp if vp is not None and not vp.empty else 0
            df["vpt_ma5"] = df["vpt"].rolling(5, min_periods=1).mean()
        except Exception as e:
            df["vpt"] = 0.0
            df["vpt_ma5"] = 0.0

        # Force Index (use efi instead)
        try:
            fi = ta.efi(cl, vo, length=13)
            df["force_index"] = fi if fi is not None and not fi.empty else 0
        except Exception as e:
            df["force_index"] = 0.0

        # PVI / NVI - Skip if fails
        try:
            pvi = ta.pvi(cl, vo)
            if pvi is not None and not pvi.empty:
                if isinstance(pvi, pd.DataFrame):
                    df["pvi"] = pvi.iloc[:, 0] if pvi.shape[1] > 0 else 0
                    df["nvi"] = pvi.iloc[:, 1] if pvi.shape[1] > 1 else 0
                else:
                    df["pvi"] = pvi
                    df["nvi"] = 0
            else:
                df["pvi"] = 0
                df["nvi"] = 0
            df["pvi_ma5"] = df["pvi"].rolling(5, min_periods=1).mean()
            df["nvi_ma5"] = df["nvi"].rolling(5, min_periods=1).mean()
        except Exception as e:
            df["pvi"] = 0
            df["nvi"] = 0
            df["pvi_ma5"] = 0
            df["nvi_ma5"] = 0

    # ============================================================
    #  补充指标 — 简要验证量价结论
    # ============================================================
    def _supplement(self):
        df = self.df
        cl, hi, lo = df["close"], df["high"], df["low"]

        # MA
        df["ma5"] = cl.rolling(5, min_periods=1).mean()
        df["ma10"] = cl.rolling(10, min_periods=1).mean()
        df["ma20"] = cl.rolling(20, min_periods=1).mean()

        # MACD
        macd = ta.macd(cl, fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            cols = macd.columns
            for c in cols:
                if "MACDh" in c:
                    df["macd_hist"] = macd[c]
                elif "MACDs" in c:
                    df["macd_signal"] = macd[c]
                elif "MACD_" in c:
                    df["macd"] = macd[c]
        for c in ["macd", "macd_signal", "macd_hist"]:
            if c not in df.columns:
                df[c] = 0

        # RSI
        rsi = ta.rsi(cl, length=14)
        df["rsi"] = rsi if rsi is not None and not rsi.empty else 50

        # KDJ
        kdj = ta.stoch(hi, lo, cl, k=14, d=3, smooth_k=3)
        if kdj is not None and not kdj.empty:
            df["kdj_k"] = kdj.iloc[:, 0]
            df["kdj_d"] = kdj.iloc[:, 1]
        else:
            df["kdj_k"] = 50
            df["kdj_d"] = 50
        df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]

        # ATR
        atr = ta.atr(hi, lo, cl, length=14)
        df["atr"] = atr if atr is not None and not atr.empty else 0

        # Bollinger
        bb = ta.bbands(cl, length=20, std=2)
        if bb is not None and not bb.empty:
            for c in bb.columns:
                if "BBU" in c:
                    df["bb_upper"] = bb[c]
                elif "BBM" in c:
                    df["bb_middle"] = bb[c]
                elif "BBL" in c:
                    df["bb_lower"] = bb[c]
        for c in ["bb_upper", "bb_middle", "bb_lower"]:
            if c not in df.columns:
                df[c] = 0

        # ROC
        roc = ta.roc(cl, length=10)
        df["roc"] = roc if roc is not None and not roc.empty else 0


def calc(df: pd.DataFrame) -> pd.DataFrame:
    return VPIndicators(df).df