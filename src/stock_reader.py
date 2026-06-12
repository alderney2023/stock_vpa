from mootdx.quotes import Quotes
from mootdx.reader import Reader

from src.config import TDX_DIR


def _adjust(df, code):
    try:
        from mootdx.utils.factor import fq_factor as _fq_factor
        factor = _fq_factor(code, "qfq")
        if factor is not None and not factor.empty:
            df = df.sort_index(ascending=True)
            factor = factor.sort_index(ascending=True)
            df.index = df.index.normalize()
            data = df.join(factor, how="left")
            data["factor"] = data["factor"].bfill().fillna(1.0).astype(float)
            for col in ["open", "high", "low", "close"]:
                data[col] = data[col] / data["factor"]
            return data
    except Exception:
        pass
    return df

def read_daily(code: str, count: int = 120):
    try:
        client = Quotes.factory(market="std")
        raw = client.bars(symbol=code, frequency=9, start=0, offset=count)
        if raw is not None and not raw.empty:
            df = raw.tail(count).copy()
            df = _adjust(df, code)
            df["date"] = df.index.strftime("%Y-%m-%d")
            df = df[["date", "open", "high", "low", "close", "amount", "volume"]]
            df = df.reset_index(drop=True)
            return df
    except Exception:
        pass

    reader = Reader.factory(market="std", tdxdir=TDX_DIR)
    df = reader.daily(symbol=code)
    if df is None or df.empty:
        msg = f"股票 {code} 的日K线数据未找到，请确认：1) 股票代码是否正确；2) 通达信数据目录 {TDX_DIR} 下是否有对应 .day 文件"
        raise FileNotFoundError(msg)
    df = df.tail(count).reset_index()
    df = _adjust(df, code)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df
