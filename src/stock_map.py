import os
import time
from pathlib import Path

import pandas as pd
import httpx

from src.config import STOCKS_CSV, DATA_DIR, TDX_DIR

_EASTMONEY_URLS = [
    "http://push2.eastmoney.com/api/qt/clist/get",
    "https://push2.eastmoney.com/api/qt/clist/get",
]
_EASTMONEY_PARAMS = {
    "pn": "1",
    "pz": "50000",
    "po": "1",
    "np": "1",
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": "2",
    "invt": "2",
    "fid": "f3",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
    "fields": "f12,f14",
}


def _market_from_code(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return ""


def _fetch_from_eastmoney() -> pd.DataFrame | None:
    saved = {k: os.environ.pop(k, None) for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")}
    try:
        for url in _EASTMONEY_URLS:
            try:
                resp = httpx.get(url, params=_EASTMONEY_PARAMS, timeout=20,
                                 headers={"User-Agent": "Mozilla/5.0"})
                data = resp.json()
                rows = data["data"]["diff"]
                df = pd.DataFrame(rows)[["f12", "f14"]]
                df.columns = ["code", "name"]
                df["market"] = df["code"].apply(_market_from_code)
                return df
            except Exception:
                time.sleep(1)
        return None
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def _fetch_from_tdx_quotes() -> pd.DataFrame | None:
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std")
        sh = client.stocks(market=1)
        sz = client.stocks(market=0)
        df = pd.concat([sh, sz], ignore_index=True)
        df = df[["code", "name"]].copy()
        df["market"] = df["code"].apply(_market_from_code)
        df["code"] = df["code"].astype(str)
        return df
    except Exception:
        return None


def _scan_local_day_files() -> pd.DataFrame:
    codes = []
    for market_dir, prefix in [(Path(TDX_DIR) / "vipdoc" / "sh" / "lday", "sh"),
                                (Path(TDX_DIR) / "vipdoc" / "sz" / "lday", "sz")]:
        if market_dir.exists():
            for f in market_dir.glob("*.day"):
                code = f.stem.replace(prefix, "")
                if code.isdigit():
                    codes.append({"code": code, "name": code, "market": _market_from_code(code)})
    df = pd.DataFrame(codes)
    return df.drop_duplicates(subset="code").reset_index(drop=True)


def fetch_all_stocks() -> pd.DataFrame:
    df = _fetch_from_eastmoney()
    if df is not None and not df.empty:
        return df
    df = _fetch_from_tdx_quotes()
    if df is not None and not df.empty:
        return df
    df = _scan_local_day_files()
    if df is not None and not df.empty:
        return df
    raise ConnectionError("无法获取股票列表（东方财富API、通达信行情、本地文件均失败）")


def load_stocks() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if STOCKS_CSV.exists():
        return pd.read_csv(STOCKS_CSV, dtype=str)
    df = fetch_all_stocks()
    df.to_csv(STOCKS_CSV, index=False, encoding="utf-8")
    return df


def search(keyword: str) -> pd.DataFrame:
    df = load_stocks()
    mask = df["name"].str.contains(keyword, na=False)
    return df[mask]
