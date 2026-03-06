# ZhuShou (助手) - AI-Powered Development Assistant

An AI-powered development assistant with multi-model LLM support, three-tier memory, tool execution, and an autonomous 7-stage coding pipeline.

## Features

- **Multi-provider LLM support** - Ollama, OpenAI, Anthropic, DeepSeek, Gemini, LM Studio, vLLM
- **Interactive REPL** with streaming responses and slash commands
- **11 built-in tools** - file read/write/edit, shell commands, glob, grep, search, git operations
- **7-stage autonomous coding pipeline** - Requirements, Architecture, Tasks, Implementation, Testing, Debugging, Verification
- **Three-tier memory system** - persistent JSON KV store, JSONL conversation logs, ChromaDB vector search
- **Context window management** - automatic compaction when 80% of context budget is used
- **Token tracking and cost estimation** per provider/model
- **Persona configuration** via Markdown files
- **Sibling tool discovery** - integrates tools from Chou, GangDan, Huan, Liao, NuoYi, CopyTalker, LaPian
- **.git directory protection** - refuses to modify git internals

## Requirements

- Python >= 3.10
- httpx (required)
- rich (required)

## Installation

### From PyPI

```bash
pip install zhushou
```

### From Source

```bash
git clone https://github.com/cycleuser/ZhuShou.git
cd ZhuShou
pip install -e .
```

### With Optional Dependencies

```bash
# Install with vector search support
pip install zhushou[vector]

# Install with specific LLM providers
pip install zhushou[openai]
pip install zhushou[anthropic]
pip install zhushou[gemini]

# Install everything
pip install zhushou[all]
```

## Quick Start

After installation, the `zhushou` command is available:

```bash
# Launch interactive REPL
zhushou

# Single-turn chat
zhushou chat "Explain Python decorators"

# Run the 7-stage autonomous pipeline
zhushou pipeline "Build a Gomoku game" -o ./output

# List available models
zhushou models

# Show configuration
zhushou config

# Show version
zhushou -V
```

## Usage

```bash
zhushou [options] [command]
```

### Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-V` | Show version |
| `--verbose` | `-v` | Verbose output |
| `--json` | | Output results as JSON |
| `--quiet` | `-q` | Suppress non-essential output |
| `--output DIR` | `-o` | Working / output directory |
| `--provider` | | LLM provider (default: ollama) |
| `--model` | `-m` | Model name |
| `--api-key` | | API key for cloud providers |
| `--base-url` | | Custom API endpoint URL |

### Subcommands

| Command | Description |
|---------|-------------|
| `chat` | Send a message to the assistant |
| `pipeline` | Run the 7-stage autonomous coding pipeline |
| `models` | List available models across providers |
| `config` | Show or edit configuration |

### Interactive REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/quit` or `/exit` | Exit the REPL |
| `/clear` | Clear conversation history |
| `/stats` | Show token usage statistics |

## LLM Providers

| Provider | Key | Notes |
|----------|-----|-------|
| Ollama | `ollama` | Local, free, default |
| OpenAI | `openai` | Requires API key |
| Anthropic | `anthropic` | Requires API key |
| DeepSeek | `deepseek` | Requires API key |
| Gemini | `gemini` | Requires API key |
| LM Studio | `lmstudio` | Local, OpenAI-compatible |
| vLLM | `vllm` | Local, OpenAI-compatible |

```bash
# Use with Ollama (default)
zhushou --provider ollama --model llama3

# Use with OpenAI
zhushou --provider openai --api-key sk-... --model gpt-4o

# Use with DeepSeek
zhushou --provider deepseek --api-key sk-...

# Use with a custom endpoint
zhushou --provider openai --base-url http://localhost:8080/v1
```

## Autonomous Pipeline

The 7-stage pipeline generates a complete project from a text description:

1. **Requirements** - Analyse the request and produce a specification
2. **Architecture** - Design file structure and module layout
3. **Task Breakdown** - Create ordered implementation tasks
4. **Implementation** - Write code file by file
5. **Testing** - Generate and run tests
6. **Debugging** - Fix any failing tests (up to 5 retries)
7. **Verification** - Final check and summary

```bash
zhushou pipeline "Build a REST API with Flask" -o ./my_api
```

## Memory System

ZhuShou provides three tiers of persistent memory:

| Tier | Storage | Purpose |
|------|---------|---------|
| Persistent KV | `~/.zhushou/memory.json` | Facts, preferences, project metadata |
| Conversation Log | `~/.zhushou/logs/{date}.jsonl` | Full message history per day |
| Vector Search | ChromaDB (optional) | Semantic search over past conversations |

## Persona Configuration

Customise the assistant's behaviour by creating a persona file:

```bash
# Project-local persona
mkdir -p .zhushou
cat > .zhushou/persona.md << 'EOF'
# Identity
You are a senior Python developer specialising in data science.

# Rules
- Always use type hints
- Prefer pandas over raw loops

# Tools
- Use python_exec for quick calculations
EOF
```

Search order: `.zhushou/persona.md` -> `~/.zhushou/persona.md` -> built-in default.

## Project Structure

```
ZhuShou/
├── zhushou/                # Main package
│   ├── llm/               # LLM provider abstraction
│   │   ├── base.py             # BaseLLMClient ABC + dataclasses
│   │   ├── ollama_client.py    # Ollama provider
│   │   ├── openai_client.py    # OpenAI / DeepSeek / LM Studio
│   │   ├── anthropic_client.py # Anthropic
│   │   ├── gemini_client.py    # Google Gemini
│   │   ├── factory.py          # LLMClientFactory
│   │   └── model_registry.py   # Context windows & pricing
│   ├── executor/          # Tool execution
│   │   ├── tool_executor.py    # Sandboxed dispatcher
│   │   ├── builtin_tools.py    # 11 built-in tools
│   │   └── sibling_tools.py    # Sibling package discovery
│   ├── agent/             # Core agent loop
│   │   ├── loop.py             # Interactive REPL + tool loop
│   │   ├── context.py          # Context window management
│   │   └── conversation.py     # Conversation buffer
│   ├── memory/            # Three-tier memory
│   │   ├── persistent.py       # JSON KV store
│   │   ├── conversation_log.py # JSONL logger
│   │   └── vector_store.py     # ChromaDB / numpy fallback
│   ├── pipeline/          # Autonomous pipeline
│   │   ├── stages.py           # 7 stage definitions
│   │   └── orchestrator.py     # Pipeline runner
│   ├── display/           # Rich console output
│   ├── persona/           # Persona loader
│   ├── tracking/          # Token usage tracker
│   ├── git/               # Git operations
│   ├── utils/             # Constants, python finder
│   ├── api.py             # Unified Python API
│   ├── tools.py           # OpenAI function-calling schemas
│   └── cli.py             # CLI entry point
├── tests/                 # pytest tests
├── old/                   # Original prototype
├── pyproject.toml         # Package configuration
├── README.md              # This file
└── README_CN.md           # Chinese documentation
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with verbose output
pytest -v
```

## Python API

```python
from zhushou import chat, run_pipeline, search_pypi

# Single-turn chat
result = chat("Explain list comprehensions", provider="ollama", model="llama3")
print(result.success)   # True / False
print(result.data)      # Assistant response text

# Run the autonomous pipeline
result = run_pipeline("Build a calculator app", output_dir="./calc")
print(result.data)      # Pipeline stats

# Search PyPI
result = search_pypi("requests")
print(result.data)      # List of package info dicts
```

## Agent Integration (OpenAI Function Calling)

ZhuShou exposes OpenAI-compatible tools for LLM agents:

```python
from zhushou.tools import TOOLS, dispatch

# Pass TOOLS to the OpenAI chat completion API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,
)

# Dispatch the tool call
result = dispatch(
    tool_call.function.name,
    tool_call.function.arguments,
)
```

## CLI Help

![CLI Help](images/zhushou_help.png)

## License

MIT License
