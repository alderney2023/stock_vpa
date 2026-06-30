import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.config import (
    LLM_API_KEY, KLINE_COUNT, LLM_MODEL,
    DEFAULT_MODEL, ALL_MODELS
)
from src.stock_map import search, load_stocks
from src.stock_reader import read_daily
from src.weekly_reader import calc_weekly
from src.vpa_analyzer import analyze


def _normalize_code(keyword: str) -> str | None:
    raw = keyword.strip().upper().replace(".NAN", "").replace(".BJ", "").replace(".SH", "").replace(".SZ", "")
    if raw.isdigit() and len(raw) == 6:
        return raw
    return None


def _lookup_by_code(keyword: str):
    code = _normalize_code(keyword)
    if code is None:
        return None
    df = load_stocks()
    match = df[df["code"] == code]
    if match.empty:
        return None
    stock = match[match["market"].isin(["SH", "SZ", "BJ"])]
    if not stock.empty:
        return stock.iloc[0]
    return match.iloc[0]


def _pick_stock(keyword: str):
    results = search(keyword)
    if results.empty:
        stock = _lookup_by_code(keyword)
        if stock is not None:
            return stock
        print(f"未找到匹配 \"{keyword}\" 的股票，请尝试输入股票代码")
        return None
    if len(results) == 1:
        return results.iloc[0]
    print(f"匹配到以下股票:")
    for i, (_, row) in enumerate(results.iterrows(), 1):
        print(f"  {i}. {row['code']}.{row['market']}  {row['name']}")
    print("(输入股票代码直接匹配，回车返回搜索)")
    while True:
        choice = input("请选择 (输入编号或代码): ").strip()
        if not choice:
            return None
        if choice.lower() in ("exit", "quit", "cancel", "back"):
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                return results.iloc[idx]
        except ValueError:
            pass
        stock = _lookup_by_code(choice)
        if stock is not None:
            return stock
        print("未匹配到股票代码，请重新输入")


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
        print("警告: 未配置模型API密钥")
        print("请在 config.json 文件中配置模型的 API Key")
        print("=" * 50)
        print()
        return

    print("=" * 48)
    print("  量价分析助手 (输入 exit 退出)")
    print("=" * 48)

    # 显示可用模型
    print(f"\n当前使用的模型: {DEFAULT_MODEL}")
    print("可用模型:")
    for i, (name, model_cfg) in enumerate(ALL_MODELS.items(), 1):
        marker = " [默认]" if name == DEFAULT_MODEL else ""
        print(f"  {i}. {name}{marker}")
        print(f"     API: {model_cfg['base_url']}")
        print()

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

        # 提示数据量限制
        if count > 150:
            print(f"注意：分析天数 {count} 超过推荐上限 150 天，将自动限制为 150 天")
            count = 150

        print(f"正在从通达信读取 {code} 最近 {count} 条日K数据...", end=" ", flush=True)
        try:
            df = read_daily(code, count)
            print(f"OK ({len(df)} 条)")
            # 基于日K计算周K
            print("正在计算周K数据...", end=" ", flush=True)
            df_weekly = calc_weekly(df, weeks=52)
            print(f"OK ({len(df_weekly)} 周)")
        except FileNotFoundError as e:
            print()
            print(e)
            continue
        except Exception as e:
            print()
            print(f"读取失败: {e}")
            continue

        # 询问是否切换模型（默认N=不切换，输入Y/y切换）
        while True:
            model_choice = input(f"是否切换模型? (当前: {DEFAULT_MODEL}, 按回车保持当前) [Y/N]: ").strip().lower()
            if model_choice == 'y':
                print("可用模型:")
                for i, name in enumerate(ALL_MODELS.keys(), 1):
                    marker = " [默认]" if name == DEFAULT_MODEL else ""
                    print(f"  {i}. {name}{marker}")
                choice = input("请选择模型编号: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(ALL_MODELS):
                        selected_model = list(ALL_MODELS.keys())[idx]
                        print(f"已切换到模型: {selected_model}")
                        break
                    else:
                        print("无效编号，保持使用当前模型")
                        break
                except ValueError:
                    print("请输入数字编号")
            else:
                break

        print(f"正在调用 {LLM_MODEL} 进行分析...")
        print()
        try:
            analyze(name, code, df, df_weekly)
        except Exception as e:
            print(f"分析失败: {e}")
        print()

    print("再见!")


if __name__ == "__main__":
    main()
