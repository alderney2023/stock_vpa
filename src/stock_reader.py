from mootdx.quotes import Quotes
from mootdx.reader import Reader

from src.config import TDX_DIR


def read_daily(code: str, count: int = 120):
    try:
        client = Quotes.factory(market="std")
        raw = client.bars(symbol=code, frequency=9, start=0, offset=count)
        if raw is not None and not raw.empty:
            df = raw.tail(count).copy()
            df = df.rename(columns={"vol": "volume"})
            df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")
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
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df
