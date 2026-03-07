# ZhuShou (助手) - AI-Powered Development Assistant

An AI-powered development assistant with multi-model LLM support, three interfaces (CLI, desktop GUI, web), an autonomous 8-stage coding pipeline, three-tier memory, world-context awareness, web doc crawling, and persistent configuration.

## Features

- **Multi-provider LLM support** - Ollama, OpenAI, Anthropic, DeepSeek, Gemini, LM Studio, vLLM
- **Interactive REPL** with streaming responses and slash commands
- **11 built-in tools** - file read/write/edit, shell commands, glob, grep, search, git operations
- **8-stage autonomous coding pipeline** - Requirements, Architecture, Tasks, Function Design, Implementation, Testing, Debugging, Verification (10 stages with `--full`)
- **Desktop GUI** - PySide6-based with real-time pipeline visualization, syntax-highlighted code viewer, and Catppuccin Mocha dark theme
- **Web Interface** - FastAPI + vanilla JS at `http://127.0.0.1:8765`, real-time WebSocket event streaming, no build step required
- **First-run Setup Wizard** - auto-discovers Python interpreters, guides provider/model selection (CLI and GUI modes)
- **Persistent Configuration** - settings stored in `~/.zhushou/config.json`, CLI args always override stored values
- **Event-driven Architecture** - thread-safe pub/sub event bus with 13 event types powering real-time UI updates
- **Knowledge Base** - download, index, and search framework documentation; built-in cheatsheets; pipeline context injection via `--kb`
- **World-Context Awareness** - injects real-time date/time/timezone into LLM prompts via ModelSensor (configurable, disable with `--no-world`)
- **Web Doc Crawler** - crawl any website into the knowledge base using Huan (`zhushou kb crawl <url>`)
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
- modelsensor (required, world-context awareness)
- huan (required, web doc crawling)

Optional:
- PySide6 (for desktop GUI)
- FastAPI + uvicorn (for web interface)
- ChromaDB (for vector search)

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

# Install desktop GUI (PySide6)
pip install zhushou[gui]

# Install web interface (FastAPI + uvicorn)
pip install zhushou[web]

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

# Run the 8-stage autonomous pipeline
zhushou pipeline "Build a Gomoku game" -o ./output

# Run the full 10-stage pipeline (adds documentation + packaging)
zhushou pipeline "Build a Flask API" --full -o ./api

# Run pipeline with knowledge base context
zhushou pipeline "Build a Flask API" --kb flask -o ./api

# Launch desktop GUI
zhushou gui

# Launch web interface
zhushou web

# List available models
zhushou models

# Show configuration
zhushou config

# Re-run setup wizard
zhushou config --setup

# Knowledge base management
zhushou kb list

# Download framework docs
zhushou kb download numpy

# Crawl a website into KB
zhushou kb crawl https://docs.example.com --max-pages 100

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
| `--proxy` | | HTTP/HTTPS proxy URL (default: disabled) |
| `--timeout` | | LLM request timeout in seconds (default: 300) |
| `--no-setup` | | Skip first-run setup wizard |
| `--no-world` | | Disable world-context injection (date/time awareness) |

### Subcommands

| Command | Description |
|---------|-------------|
| `chat` | Send a message to the assistant |
| `pipeline` | Run the 8-stage autonomous coding pipeline (10 with `--full`) |
| `models` | List available models across providers |
| `config` | Show configuration; `--setup` to re-run wizard |
| `gui` | Launch PySide6 desktop GUI |
| `web` | Launch web interface (`--port`, `--host`) |
| `kb` | Knowledge base management (list, download, index, search, crawl) |

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

## Desktop GUI

Launch the PySide6 desktop GUI for a graphical pipeline experience:

```bash
pip install zhushou[gui]
zhushou gui
```

The GUI provides a real-time view of the coding pipeline with a Catppuccin Mocha dark theme:

- **Top bar** - Request text input field, Run / Stop buttons, provider and model status
- **Stage sidebar** (left, 200-280px) - Pipeline stage progress with status indicators:
  - ○ pending  ● running  ✓ complete  ✗ error
- **Code panel** (top-right, ~60%) - File list with syntax-highlighted Python code viewer
- **Thinking panel** (bottom-right, ~40%) - Real-time LLM reasoning, tool calls, test results
- **Status bar** - Provider, model, elapsed time

On first launch, a **setup wizard dialog** guides you through 4 steps: Python interpreter selection, LLM provider selection, API key entry (skipped for local providers like Ollama), and model selection.

## Web Interface

Launch the FastAPI web interface for browser-based access:

```bash
pip install zhushou[web]
zhushou web [--port PORT] [--host HOST]
```

Default URL: `http://127.0.0.1:8765`

The web interface provides the same split-panel layout as the desktop GUI (sidebar + code panel + thinking panel) with the same Catppuccin Mocha dark theme. Updates stream in real-time via WebSocket. No build step is required — the frontend is vanilla HTML/CSS/JS served directly by FastAPI.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Current configuration (API keys masked) |
| `/api/providers` | GET | Available LLM providers |
| `/api/models` | GET | Models for current provider |
| `/api/world` | GET | World context info (date/time from ModelSensor) |
| `/api/pipeline` | POST | Start a pipeline run (`{"request": "..."}`) |
| `/api/kb/crawl` | POST | Crawl a website into KB (`{"url": "..."}`) |
| `/ws` | WebSocket | Real-time event stream |

## Configuration & Setup Wizard

ZhuShou stores configuration in `~/.zhushou/config.json`. On first launch, the setup wizard runs automatically to configure:

1. **Python interpreter** - auto-discovers interpreters from PATH, pyenv, and conda environments
2. **LLM provider** - select from available providers (Ollama, OpenAI, Anthropic, etc.)
3. **API key** - enter the API key for cloud providers (skipped for local providers)
4. **Model** - select from the provider's available models

To re-run the wizard: `zhushou config --setup`

To skip the wizard: `zhushou --no-setup`

CLI arguments always override stored configuration values.

| Field | Description | Default |
|-------|-------------|---------|
| `python_path` | Python interpreter path | (auto-detected) |
| `provider` | LLM provider | `ollama` |
| `model` | Model name | (selected during setup) |
| `api_key` | Cloud provider API key | (empty) |
| `base_url` | Custom API endpoint | (empty) |
| `proxy` | HTTP proxy URL | (empty) |
| `timeout` | Request timeout in seconds | `300` |
| `world_sense` | Enable world-context injection | `true` |

## Autonomous Pipeline

The 8-stage pipeline generates a complete project from a text description:

1. **Requirements** - Analyse the request and produce a specification
2. **Architecture** - Design file structure, module layout, and scaffold the project
3. **Task Breakdown** - Create ordered implementation tasks
4. **Function Design** - Detailed function-level signatures and dependencies
5. **Implementation** - Write code file by file
6. **Testing** - Generate and run tests
7. **Debugging** - Fix any failing tests (up to 5 retries with verify-debug feedback loop)
8. **Verification** - Final check, import validation, and summary report

With `--full`, two additional stages are added:

9. **Documentation** - Generate README.md, README_CN.md, requirements.txt
10. **Packaging** - Generate pyproject.toml, upload scripts, help screenshot generator

```bash
# Standard 8-stage pipeline
zhushou pipeline "Build a REST API with Flask" -o ./my_api

# Full 10-stage pipeline
zhushou pipeline "Build a Gomoku game" --full -o ./game

# Pipeline with knowledge base context
zhushou pipeline "Build a Flask app" --kb flask -o ./app
```

## Knowledge Base

Download, index, and search official framework documentation for use as pipeline context:

| Command | Description |
|---------|-------------|
| `zhushou kb list` | List available sources with download/index status |
| `zhushou kb download <source>` | Download official docs for a framework |
| `zhushou kb index <source>` | Index downloaded docs into vector DB |
| `zhushou kb search <query>` | Search indexed knowledge base |
| `zhushou kb cheatsheet <name>` | Display built-in cheatsheet |
| `zhushou kb crawl <url>` | Crawl a website into knowledge base (via Huan) |

Inject knowledge base context into pipeline runs with the `--kb` flag:

```bash
zhushou pipeline "Build a data viz app" --kb numpy matplotlib -o ./viz
```

### Web Doc Crawling

Crawl any website into the knowledge base using Huan:

```bash
# Crawl a documentation site
zhushou kb crawl https://docs.flask.palletsprojects.com --name flask-docs

# Limit pages and restrict to a path prefix
zhushou kb crawl https://docs.python.org --max-pages 50 --prefix /3/library/

# Crawled content is auto-indexed and available via --kb or kb search
zhushou kb search "Flask routing"
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
│   ├── config/            # Persistent configuration
│   │   ├── manager.py         # ZhuShouConfig dataclass + JSON I/O
│   │   └── wizard.py          # First-run setup wizard (CLI + GUI)
│   ├── events/            # Event system
│   │   ├── types.py           # 13 frozen event dataclasses
│   │   └── bus.py             # Thread-safe PipelineEventBus
│   ├── gui/               # Desktop GUI (PySide6)
│   │   ├── app.py             # Application entry point
│   │   ├── main_window.py     # MainWindow (1400x850)
│   │   ├── pipeline_view.py   # Split-view container
│   │   ├── stage_sidebar.py   # Stage progress sidebar
│   │   ├── code_panel.py      # File list + syntax-highlighted viewer
│   │   ├── thinking_panel.py  # LLM reasoning display
│   │   ├── wizard_dialog.py   # Setup wizard dialog (4 pages)
│   │   ├── workers.py         # QThread pipeline worker + EventBridge
│   │   └── styles.py          # Catppuccin Mocha theme + QSS
│   ├── web/               # Web interface (FastAPI)
│   │   ├── app.py             # FastAPI factory + uvicorn launcher
│   │   ├── routes.py          # REST + WebSocket endpoints
│   │   ├── bridge.py          # Event bus -> WebSocket bridge
│   │   └── static/            # Vanilla JS frontend
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
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
│   ├── knowledge/         # Knowledge base subsystem
│   │   ├── kb_manager.py       # High-level facade
│   │   ├── kb_config.py        # KB configuration
│   │   ├── doc_sources.py      # Official doc source definitions
│   │   ├── doc_manager.py      # Doc downloader
│   │   ├── indexer.py          # Vector DB indexer
│   │   ├── retriever.py        # RAG search
│   │   └── cheatsheets.py      # Built-in cheatsheets
│   ├── pipeline/          # Autonomous pipeline
│   │   ├── stages.py           # 8 core + 2 full-mode stages
│   │   ├── orchestrator.py     # Pipeline runner with event emission
│   │   └── function_design.py  # Function-level design parser
│   ├── display/           # Rich console output
│   ├── persona/           # Persona loader
│   ├── tracking/          # Token usage tracker
│   ├── git/               # Git operations
│   ├── utils/             # Utilities
│   │   ├── constants.py        # Project constants
│   │   ├── python_finder.py    # Multi-source Python discovery
│   │   └── world_context.py    # ModelSensor world-context helper
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

GPLv3 License
