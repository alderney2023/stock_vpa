# Stock VPA — A股量价分析助手

基于通达信行情 + 大模型，对 A 股进行**量价分析**。

## 核心特点

- **量价分析为核心**：计算 OBV、VWAP、MFI、CMF、A/D 等核心量价指标，深度解读资金流向
- **其他指标补充验证**：MA、MACD、RSI、KDJ 等仅做简要交叉验证
- **多模型支持**：可同时配置多个 LLM 模型，运行时灵活切换
- **结构化输出**：将技术指标压缩为结构化摘要，减少 70%+ Token 消耗
- **前复权数据**：自动按分红送股调整历史价格，保证连续可比

## 功能

- 通过通达信网络行情协议获取实时日 K 线数据（自动更新）
- 回退到本地 `.day` 文件（`vipdoc/sh/lday/*.day`、`vipdoc/sz/lday/*.day`）
- 东方财富 API / 通达信行情协议获取全量 A 股代码与名称
- 模糊搜索股票名称
- 运行时切换 LLM 模型
- 调用大模型进行深度量价分析

## 环境要求

- Python >= 3.12
- [UV](https://docs.astral.sh/uv/) 包管理器
- 通达信客户端已安装（日 K 数据文件的兜底）
- LLM API Key（OpenAI 兼容接口，如 DeepSeek、Moonshot、通义千问等）

## 快速开始

### 1. 克隆项目并安装依赖

```bash
cd stock_vpa
uv sync
```

### 2. 配置模型

```bash
# 复制配置模板
cp config.json.example config.json

# 编辑 config.json，填入您的 API 密钥
# Windows
notepad config.json
# Linux/Mac
nano config.json
```

`config.json` 示例：

```json
{
  "models": [
    {
      "name": "deepseek-chat",
      "api_key": "sk-your-api-key",
      "base_url": "https://api.deepseek.com",
      "model": "deepseek-chat",
      "is_default": true
    },
    {
      "name": "moonshot-v1-8k",
      "api_key": "sk-your-moonshot-key",
      "base_url": "https://api.moonshot.cn/v1",
      "model": "moonshot-v1-8k",
      "is_default": false
    }
  ],
  "kline_count": 120,
  "max_analysis_days": 150
}
```

> **提示**: `config.json` 已被 `.gitignore` 忽略，不会提交到 Git。项目使用 `config.json.example` 作为模板。

### 3. 运行

```bash
uv run python -m src
```

## 使用方法

### 交互流程

```
正在初始化股票数据缓存... OK
================================================
  量价分析助手 (输入 exit 退出)
================================================

当前使用的模型: deepseek-chat
可用模型:
  1. deepseek-chat [默认]
  2. moonshot-v1-8k

请输入股票名称 > 皇马科技
请输入分析天数 (回车默认 120): 250
正在从通达信读取 603181 最近 250 条日K数据... OK (250 条)
Prompt length: 739 chars, using 150 days data
正在分析... (共 739 字符，使用流式输出)

... (量价分析报告) ...
```

### 运行时切换模型

分析过程中会询问是否切换模型：

```
是否切换模型? (当前: deepseek-chat) [y/N]: y
可用模型:
  1. deepseek-chat [默认]
  2. moonshot-v1-8k
请选择模型编号: 2
已切换到模型: moonshot-v1-8k
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 同步环境 |
| `uv run python -m src` | 运行程序 |
| `cp config.json.example config.json` | 复制配置模板 |

## 配置项

### 模型配置

`config.json` 支持以下配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `models[name]` | 模型显示名称 | — |
| `models[api_key]` | API 密钥 | — |
| `models[base_url]` | API 基础地址 | — |
| `models[model]` | 实际模型名称 | — |
| `models[is_default]` | 是否为默认模型 | `false` |
| `kline_count` | 默认分析天数 | `120` |
| `max_analysis_days` | 最大分析天数限制 | `150` |

> 💡 **调整天数限制**: 如需分析超过 150 天的数据，修改 `max_analysis_days`。注意数据量过大可能导致 API 超时。

### 常见模型配置

#### DeepSeek
```json
{
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

#### Moonshot AI
```json
{
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://api.moonshot.cn/v1",
  "model": "moonshot-v1-8k"
}
```

#### 通义千问
```json
{
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model": "qwen-plus"
}
```

#### OpenAI
```json
{
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-3.5-turbo"
}
```

### 多模型配置示例

```json
{
  "models": [
    {
      "name": "deepseek-chat",
      "api_key": "sk-deepseek-key",
      "base_url": "https://api.deepseek.com",
      "model": "deepseek-chat",
      "is_default": true
    },
    {
      "name": "moonshot-v1-8k",
      "api_key": "sk-moonshot-key",
      "base_url": "https://api.moonshot.cn/v1",
      "model": "moonshot-v1-8k",
      "is_default": false
    },
    {
      "name": "qwen-plus",
      "api_key": "sk-qwen-key",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-plus",
      "is_default": false
    }
  ],
  "kline_count": 120,
  "max_analysis_days": 150
}
```

## 量价分析架构

### 核心量价指标（深度计算）

| 指标 | 说明 |
|------|------|
| **OBV** | 能量潮，判断资金流向 |
| **VWAP** | 成交量加权均价，判断价格公允位置 |
| **A/D** | 积累/分布线，判断主力吸筹/出货 |
| **MFI** | 资金流量指数，判断买卖力度 |
| **CMF** | 蔡金资金流，判断资金流入/流出 |
| **VPT** | 量价趋势 |
| **Force Index** | 强力指数 |
| **PVI / NVI** | 正/负成交量指数 |

### 补充指标（简要验证）

| 指标 | 用途 |
|------|------|
| MA(5,10,20) | 趋势方向验证 |
| MACD | 趋势强度确认 |
| RSI(14) | 超买超卖 |
| KDJ | 转折点验证 |
| ATR + Bollinger | 波动率背景 |

### 特征提取流程

从原始 K 线到结构化摘要的数据流：

```
原始K线 (250行 × 7列)
    ↓ VPIndicators
技术指标 (250行 × 40列)
    ↓ VPAExtractor
结构化特征 (~800-1500字符)
    ↓ LLM Prompt (~1200字符)
    ↓
  量价分析报告
```

## 项目结构

```
stock_vpa/
├── src/
│   ├── __init__.py         # 包初始化
│   ├── __main__.py         # CLI 交互入口
│   ├── config.py           # 配置加载（JSON 多模型）
│   ├── stock_map.py        # 股票名称↔代码映射
│   ├── stock_reader.py     # 日 K 数据读取（网络 > 本地文件）
│   ├── vpa_indicators.py   # 🆕 量价指标计算引擎
│   ├── vpa_features.py     # 🆕 量价特征提取与压缩
│   ├── vpa_analyzer.py     # 🆕 量价分析 LLM 分析器
│   └── analyzer.py         # 旧版分析器（保留兼容）
├── data/
│   └── stocks.csv          # 全量 A 股缓存
├── config.json.example     # 📋 配置模板（提交到 Git）
├── config.json             # 🚫 用户配置（.gitignore 忽略）
├── README.md               # 项目说明
├── .gitignore              # Git 忽略规则
├── pyproject.toml          # 项目依赖定义
└── uv.lock                 # 依赖锁定文件
```

## 数据流说明

### 日 K 线数据

1. **通达信网络行情协议**（首选）— 通过 `mootdx.Quotes.bars()` 实时获取
2. **本地 `.day` 文件**（兜底）— 读取 `C:\new_tdx64\vipdoc\{sh,sz}\lday\*.day`

### 股票名称↔代码映射

首次运行自动缓存到 `data/stocks.csv`，按以下优先级获取：

1. **东方财富 API**（首选，自动绕过系统代理）
2. **通达信行情协议**（通过 mootdx 连接 TDX 行情服务器）
3. **本地 `.day` 文件扫描**（最终兜底，仅包含代码）

## 依赖

| 包 | 用途 |
|---|---|
| `mootdx` | 通达信数据读取（本地文件 + 网络行情协议） |
| `openai` | 大模型 API 调用 |
| `pandas-ta` | 技术指标计算 |
| `python-dotenv` | 环境变量管理 |
| `httpx` | HTTP 请求（东方财富 API） |
| `pandas` | 数据处理 |
| `numpy` | 数值计算 |

## 常用 UV 命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 根据 `pyproject.toml` / `uv.lock` 同步环境 |
| `uv add <包名>` | 安装依赖并写入 `pyproject.toml` |
| `uv remove <包名>` | 移除依赖 |
| `uv run <脚本>` | 在虚拟环境中运行脚本 |
| `uv run python -m src` | 以模块方式运行 |

## 故障排除

### 配置文件不存在

```
错误: 配置文件不存在
请复制示例配置文件:
  config.json.example
  → 重命名为: config.json
```

**解决方案**:
```bash
cp config.json.example config.json
# 编辑 config.json，填入您的 API 密钥
```

### 配置格式错误

```
错误: 配置文件格式错误
请检查 config.json 的 JSON 格式是否正确
```

**解决方案**: 使用 JSON 验证工具检查格式，或对照 `config.json.example` 模板。

### API 超时

```
分析失败: EngineCore encountered an issue
```

**解决方案** Decoction:
- 减少 `max_analysis_days`（如设置为 120）
- 检查网络连接
- 切换到其他模型

## Git 注意事项

**永远不要提交 `config.json`**！它包含您的 API 密钥。

```bash
# 正确操作
git add config.json.example  # ✅ 提交模板
git add src/                 # ✅ 提交代码
git commit -m "更新功能"

# 错误操作
git add config.json          # ❌ 不要提交！
```

`.gitignore` 已自动忽略 `config.json`。

## 版本更新

- **v2.0** — 量价分析重构、JSON 多模型配置、结构化特征提取
- **v1.0** — 初始版本，直接喂原始 K 线数据给 LLM

---

**更新时间**: 2026年
**版本**: 2.0.0