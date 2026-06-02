import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
KLINE_COUNT = int(os.getenv("KLINE_COUNT", "120"))

TDX_DIR = "C:/new_tdx64"
DATA_DIR = PROJECT_ROOT / "data"
STOCKS_CSV = DATA_DIR / "stocks.csv"
