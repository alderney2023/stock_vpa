import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.config import LLM_API_KEY, KLINE_COUNT, LLM_MODEL
from src.stock_map import search, load_stocks
from src.stock_reader import read_daily
from src.analyzer import analyze


def _pick_stock(keyword: str):
    results = search(keyword)
    if results.empty:
        print(f"未找到匹配 \"{keyword}\" 的股票")
        return None
    if len(results) == 1:
        return results.iloc[0]
    print(f"匹配到以下股票:")
    for i, (_, row) in enumerate(results.iterrows(), 1):
        print(f"  {i}. {row['code']}.{row['market']}  {row['name']}")
    while True:
        try:
            choice = input("请选择 (输入编号): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                return results.iloc[idx]
            print(f"请输入 1-{len(results)} 之间的编号")
        except ValueError:
            print("请输入有效数字")


def main():
    print("正在初始化股票数据缓存...", end=" ", flush=True)
    try:
        load_stocks()
        print("OK")
    except Exception as e:
        print(f"失败: {e}")
        print("请检查网络连接后重试")
        return

    if not LLM_API_KEY:
        print("=" * 50)
        print("警告: 未配置 LLM_API_KEY")
        print("请在 .env 文件中设置以下配置项:")
        print("  LLM_API_KEY=your_api_key")
        print("  LLM_BASE_URL=https://api.deepseek.com  (可选)")
        print("  LLM_MODEL=deepseek-chat  (可选)")
        print("  KLINE_COUNT=120  (可选)")
        print("=" * 50)
        print()

    print("=" * 48)
    print("  量价分析助手 (输入 exit 退出)")
    print("=" * 48)
    print()

    while True:
        try:
            raw = input("请输入股票名称 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            break

        stock = _pick_stock(raw)
        if stock is None:
            continue

        code = stock["code"]
        name = stock["name"]
        market = stock["market"]

        raw_count = input(f"请输入分析天数 (回车默认 {KLINE_COUNT}): ").strip()
        count = int(raw_count) if raw_count else KLINE_COUNT

        print(f"正在从通达信读取 {code} 最近 {count} 条日K数据...", end=" ", flush=True)
        try:
            df = read_daily(code, count)
            print(f"OK ({len(df)} 条)")
        except FileNotFoundError as e:
            print()
            print(e)
            continue
        except Exception as e:
            print()
            print(f"读取失败: {e}")
            continue

        print(f"正在调用 {LLM_MODEL} 进行分析...")
        print()
        try:
            analyze(name, code, df)
        except Exception as e:
            print(f"分析失败: {e}")
        print()

    print("再见!")


if __name__ == "__main__":
    main()
