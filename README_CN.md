# ZhuShou (助手) - AI 驱动的开发助手

一个 AI 驱动的开发助手，支持多模型 LLM、三层记忆系统、工具执行和自主 7 阶段编程流水线。

## 功能特点

- **多提供商 LLM 支持** - Ollama、OpenAI、Anthropic、DeepSeek、Gemini、LM Studio、vLLM
- **交互式 REPL** - 流式响应和斜杠命令
- **11 个内置工具** - 文件读写编辑、Shell 命令、glob、grep、搜索、git 操作
- **7 阶段自主编程流水线** - 需求、架构、任务、实现、测试、调试、验证
- **三层记忆系统** - 持久化 JSON 键值存储、JSONL 对话日志、ChromaDB 向量搜索
- **上下文窗口管理** - 使用超过 80% 预算时自动压缩
- **Token 追踪和成本估算** - 按提供商/模型计算
- **Persona 配置** - 通过 Markdown 文件自定义
- **兄弟工具发现** - 集成 Chou、GangDan、Huan、Liao、NuoYi、CopyTalker、LaPian 的工具
- **.git 目录保护** - 拒绝修改 git 内部文件

## 环境要求

- Python >= 3.10
- httpx（必需）
- rich（必需）

## 安装

### 从 PyPI 安装

```bash
pip install zhushou
```

### 从源码安装

```bash
git clone https://github.com/cycleuser/ZhuShou.git
cd ZhuShou
pip install -e .
```

### 安装可选依赖

```bash
# 安装向量搜索支持
pip install zhushou[vector]

# 安装特定 LLM 提供商
pip install zhushou[openai]
pip install zhushou[anthropic]
pip install zhushou[gemini]

# 安装全部依赖
pip install zhushou[all]
```

## 快速开始

安装后，`zhushou` 命令即可使用：

```bash
# 启动交互式 REPL
zhushou

# 单轮对话
zhushou chat "解释 Python 装饰器"

# 运行 7 阶段自主流水线
zhushou pipeline "开发一个五子棋游戏" -o ./output

# 列出可用模型
zhushou models

# 显示配置
zhushou config

# 显示版本
zhushou -V
```

## 使用方法

```bash
zhushou [选项] [命令]
```

### 全局选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--version` | `-V` | 显示版本 |
| `--verbose` | `-v` | 详细输出 |
| `--json` | | 以 JSON 格式输出结果 |
| `--quiet` | `-q` | 静默模式 |
| `--output DIR` | `-o` | 工作/输出目录 |
| `--provider` | | LLM 提供商（默认：ollama） |
| `--model` | `-m` | 模型名称 |
| `--api-key` | | 云服务 API 密钥 |
| `--base-url` | | 自定义 API 端点 URL |
| `--proxy` | | HTTP/HTTPS 代理 URL（默认：禁用） |

### 子命令

| 命令 | 说明 |
|------|------|
| `chat` | 向助手发送消息 |
| `pipeline` | 运行 7 阶段自主编程流水线 |
| `models` | 列出各提供商的可用模型 |
| `config` | 显示或编辑配置 |

### 交互式 REPL 命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示可用命令 |
| `/quit` 或 `/exit` | 退出 REPL |
| `/clear` | 清除对话历史 |
| `/stats` | 显示 Token 使用统计 |

## LLM 提供商

| 提供商 | 键名 | 说明 |
|--------|------|------|
| Ollama | `ollama` | 本地运行，免费，默认 |
| OpenAI | `openai` | 需要 API 密钥 |
| Anthropic | `anthropic` | 需要 API 密钥 |
| DeepSeek | `deepseek` | 需要 API 密钥 |
| Gemini | `gemini` | 需要 API 密钥 |
| LM Studio | `lmstudio` | 本地运行，OpenAI 兼容 |
| vLLM | `vllm` | 本地运行，OpenAI 兼容 |

```bash
# 使用 Ollama（默认）
zhushou --provider ollama --model llama3

# 使用 OpenAI
zhushou --provider openai --api-key sk-... --model gpt-4o

# 使用 DeepSeek
zhushou --provider deepseek --api-key sk-...

# 使用自定义端点
zhushou --provider openai --base-url http://localhost:8080/v1
```

## 自主编程流水线

7 阶段流水线从文本描述生成完整项目：

1. **需求分析** - 分析请求，生成规格说明
2. **架构设计** - 设计文件结构和模块布局
3. **任务拆解** - 创建有序的实现任务列表
4. **代码实现** - 逐文件编写代码
5. **测试生成** - 生成并运行测试
6. **调试修复** - 修复失败的测试（最多 5 次重试）
7. **最终验证** - 最后检查和总结

```bash
zhushou pipeline "用 Flask 开发一个 REST API" -o ./my_api
```

## 记忆系统

ZhuShou 提供三层持久化记忆：

| 层级 | 存储 | 用途 |
|------|------|------|
| 持久化 KV | `~/.zhushou/memory.json` | 事实、偏好、项目元数据 |
| 对话日志 | `~/.zhushou/logs/{日期}.jsonl` | 每日完整消息历史 |
| 向量搜索 | ChromaDB（可选） | 过往对话的语义搜索 |

## Persona 配置

通过创建 persona 文件自定义助手行为：

```bash
# 项目本地 persona
mkdir -p .zhushou
cat > .zhushou/persona.md << 'EOF'
# Identity
你是一位资深 Python 开发者，专注于数据科学。

# Rules
- 始终使用类型提示
- 优先使用 pandas 而非原始循环

# Tools
- 使用 python_exec 进行快速计算
EOF
```

搜索顺序：`.zhushou/persona.md` -> `~/.zhushou/persona.md` -> 内置默认值。

## 项目结构

```
ZhuShou/
├── zhushou/                # 主包
│   ├── llm/               # LLM 提供商抽象层
│   │   ├── base.py             # BaseLLMClient 抽象类 + 数据类
│   │   ├── ollama_client.py    # Ollama 提供商
│   │   ├── openai_client.py    # OpenAI / DeepSeek / LM Studio
│   │   ├── anthropic_client.py # Anthropic
│   │   ├── gemini_client.py    # Google Gemini
│   │   ├── factory.py          # LLMClientFactory
│   │   └── model_registry.py   # 上下文窗口和定价信息
│   ├── executor/          # 工具执行器
│   │   ├── tool_executor.py    # 沙箱化调度器
│   │   ├── builtin_tools.py    # 11 个内置工具
│   │   └── sibling_tools.py    # 兄弟包发现
│   ├── agent/             # 核心代理循环
│   │   ├── loop.py             # 交互式 REPL + 工具循环
│   │   ├── context.py          # 上下文窗口管理
│   │   └── conversation.py     # 对话缓冲区
│   ├── memory/            # 三层记忆
│   │   ├── persistent.py       # JSON 键值存储
│   │   ├── conversation_log.py # JSONL 日志
│   │   └── vector_store.py     # ChromaDB / numpy 回退
│   ├── pipeline/          # 自主流水线
│   │   ├── stages.py           # 7 个阶段定义
│   │   └── orchestrator.py     # 流水线运行器
│   ├── display/           # Rich 控制台输出
│   ├── persona/           # Persona 加载器
│   ├── tracking/          # Token 使用追踪
│   ├── git/               # Git 操作
│   ├── utils/             # 常量、Python 查找
│   ├── api.py             # 统一 Python API
│   ├── tools.py           # OpenAI 函数调用格式
│   └── cli.py             # CLI 入口
├── tests/                 # pytest 测试
├── old/                   # 原始原型
├── pyproject.toml         # 包配置
├── README.md              # 英文文档
└── README_CN.md           # 本文件
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 详细输出
pytest -v
```

## Python API

```python
from zhushou import chat, run_pipeline, search_pypi

# 单轮对话
result = chat("解释列表推导式", provider="ollama", model="llama3")
print(result.success)   # True / False
print(result.data)      # 助手回复文本

# 运行自主流水线
result = run_pipeline("开发一个计算器应用", output_dir="./calc")
print(result.data)      # 流水线统计信息

# 搜索 PyPI
result = search_pypi("requests")
print(result.data)      # 包信息列表
```

## Agent 集成（OpenAI Function Calling）

ZhuShou 提供 OpenAI 兼容的工具定义，可供 LLM Agent 调用：

```python
from zhushou.tools import TOOLS, dispatch

# 将 TOOLS 传入 OpenAI chat completion API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,
)

# 分发工具调用
result = dispatch(
    tool_call.function.name,
    tool_call.function.arguments,
)
```

## CLI 帮助

![CLI 帮助](images/zhushou_help.png)

## 许可证

MIT License
