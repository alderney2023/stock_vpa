import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_config():
    """从 config.json 加载配置"""
    config_file = PROJECT_ROOT / "config.json"
    example_file = PROJECT_ROOT / "config.json.example"

    if not config_file.exists():
        print("\n" + "=" * 60)
        print("错误: 配置文件不存在")
        print("=" * 60)
        print(f"请复制示例配置文件:")
        print(f"  {example_file}")
        print(f"  → 重命名为: config.json")
        print(f"\n示例配置内容:")
        try:
            with open(example_file, 'r', encoding='utf-8') as f:
                example_content = f.read()
                # 只显示前300个字符
                print(example_content[:300] + "...")
        except Exception as e:
            print(f"无法读取示例文件: {e}")
        print("\n提示:")
        print("1. 复制 config.json.example 到 config.json")
        print("2. 编辑 config.json，填入您的 API 密钥")
        print("3. 可以添加多个模型，设置 is_default: true 来指定默认模型")
        print("=" * 60 + "\n")
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n错误: 配置文件格式错误: {e}")
        print(f"请检查 {config_file} 的 JSON 格式是否正确\n")
        raise

    models_config = config.get('models', [])
    if not models_config:
        raise ValueError("配置文件中没有定义任何模型")

    default_model_name = None
    model_configs = {}

    for model_config in models_config:
        name = model_config.get('name')
        if name:
            model_configs[name] = {
                'api_key': model_config.get('api_key', ''),
                'base_url': model_config.get('base_url', 'https://api.openai.com/v1'),
                'model': model_config.get('model', name),
                'is_default': model_config.get('is_default', False)
            }
            if model_config.get('is_default', False):
                default_model_name = name

    if not default_model_name:
        default_model_name = list(model_configs.keys())[0]
        print(f"注意: 未设置默认模型，使用第一个模型: {default_model_name}")

    return {
        'default_model': default_model_name,
        'models': model_configs,
        'kline_count': config.get('kline_count', 120),
        'max_analysis_days': config.get('max_analysis_days', 150)
    }

# 加载配置
config = load_config()

LLM_API_KEY = config['models'][config['default_model']]['api_key']
LLM_BASE_URL = config['models'][config['default_model']]['base_url']
LLM_MODEL = config['models'][config['default_model']]['model']
KLINE_COUNT = config['kline_count']
MAX_ANALYSIS_DAYS = config['max_analysis_days']
DEFAULT_MODEL = config['default_model']
ALL_MODELS = config['models']

TDX_DIR = "C:/new_tdx64"
DATA_DIR = PROJECT_ROOT / "data"
STOCKS_CSV = DATA_DIR / "stocks.csv"
