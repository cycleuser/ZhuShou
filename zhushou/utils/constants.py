"""ZhuShou constants and default configuration."""

from pathlib import Path

DATA_DIR = Path.home() / ".zhushou"
CONFIG_FILE = DATA_DIR / "config.json"
MEMORY_FILE = DATA_DIR / "memory.json"
USAGE_FILE = DATA_DIR / "usage.json"
LOGS_DIR = DATA_DIR / "logs"
CHROMA_DIR = DATA_DIR / "chroma"

# Knowledge base
KB_DIR = DATA_DIR / "kb"
KB_DOCS_DIR = KB_DIR / "docs"
KB_CHROMA_DIR = KB_DIR / "chroma"
KB_CONFIG_FILE = KB_DIR / "config.json"

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com"

MAX_TOOL_TURNS = 25
MAX_DEBUG_RETRIES = 5
COMMAND_TIMEOUT = 120

# Context window defaults (tokens)
DEFAULT_CONTEXT_WINDOW = 32768
COMPACTION_THRESHOLD = 0.8  # Compact when 80% used
