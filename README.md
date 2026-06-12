# Stock VPA — A股量价分析助手

基于通达信行情 + 大模型，对 A 股进行量价分析。

## 功能

- 通过通达信网络行情协议获取实时日 K 线数据（自动更新，无需手动下载）
- 回退到本地 `.day` 文件（`vipdoc/sh/lday/*.day`、`vipdoc/sz/lday/*.day`）
- 数据自动进行**前复权**处理，历史价格已按分红送股调整，保证连续可比
- 通过东方财富 API / 通达信行情协议获取全量 A 股代码与名称
- 支持模糊搜索股票名称
- 可配置分析天数
- 调用大模型（OpenAI 兼容接口）进行量价分析：
  - 量价配合关系
  - 关键支撑/阻力位识别
  - 趋势判断
  - 异常信号检测
  - 综合结论

## 环境要求

- Python >= 3.12
- [UV](https://docs.astral.sh/uv/) 包管理器
- 通达信客户端已安装（日 K 数据文件作为网络不可用时的兜底）
- 大模型 API Key（支持 OpenAI 兼容接口，如 DeepSeek、智谱 GLM 等）

## UV 配置环境

### 方式一：使用已有项目（推荐）

```bash
# 1. 进入项目目录
cd stock_vpa

# 2. UV 自动创建虚拟环境并安装所有依赖
uv sync

# 3. 创建配置文件
copy .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 运行
uv run python -m src
```

### 方式二：从头搭建

```bash
# 1. 初始化项目
mkdir stock_vpa && cd stock_vpa
uv init --python 3.12

# 2. 添加依赖
uv add mootdx openai python-dotenv httpx pandas

# 3. 创建配置文件
copy .env.example .env

# 4. 运行
uv run python -m src
```

### 常用 UV 命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 根据 `pyproject.toml` / `uv.lock` 同步环境 |
| `uv add <包名>` | 安装依赖并写入 `pyproject.toml` |
| `uv remove <包名>` | 移除依赖 |
| `uv run <脚本>` | 在虚拟环境中运行脚本 |
| `uv run python -m src` | 以模块方式运行 |

## 配置项

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | 大模型 API Key（必填） | — |
| `LLM_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
| `KLINE_COUNT` | 默认分析天数 | `120` |

## 使用示例

```
> uv run python -m src
正在初始化股票数据缓存... OK

================================================
  量价分析助手 (输入 exit 退出)
================================================

请输入股票名称 > 吉祥航空
匹配到以下股票:
  1. 603885.SH  吉祥航空
请选择 (输入编号): 1
请输入分析天数 (回车默认 120): 180
正在从通达信读取 603885 最近 180 条日K数据... OK (180 条)
正在调用 deepseek-chat 进行分析...

... (量价分析报告) ...

请输入股票名称 >
```

## 数据源

### 日 K 线数据

1. **通达信网络行情协议**（首选）— 通过 `mootdx.Quotes.bars()` 实时获取，自动包含最新交易日数据
2. **本地 `.day` 文件**（兜底）— 读取 `C:\new_tdx64\vipdoc\{sh,sz}\lday\*.day`

### 股票名称↔代码映射

首次运行自动缓存到 `data/stocks.csv`，按以下优先级获取：

1. **东方财富 API**（首选，自动绕过系统代理）
2. **通达信行情协议**（通过 mootdx 连接 TDX 行情服务器）
3. **本地 .day 文件扫描**（最终兜底，仅包含代码）

## 项目结构

```
stock_vpa/
├── src/
│   ├── __init__.py      # 包初始化
│   ├── __main__.py      # CLI 循环交互入口
│   ├── config.py        # .env 配置加载
│   ├── stock_map.py     # 股票名称↔代码映射
│   ├── stock_reader.py  # 日 K 数据读取（网络 > 本地文件）
│   └── analyzer.py      # 大模型量价分析
├── data/
│   └── stocks.csv       # 全量 A 股缓存
├── .env.example         # 配置模板
├── pyproject.toml       # 项目依赖定义
├── uv.lock              # 依赖锁定文件
└── README.md
```

## 依赖

| 包 | 用途 |
|---|---|
| `mootdx` | 通达信数据读取（本地文件 + 网络行情协议） |
| `openai` | 大模型 API 调用 |
| `python-dotenv` | 环境变量管理 |
| `httpx` | HTTP 请求（东方财富 API） |
| `pandas` | 数据处理 |
