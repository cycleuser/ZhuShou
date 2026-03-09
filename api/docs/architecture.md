# Flask API Service - Architecture Document

## Overview

Flask API Service is a RESTful web API framework that provides a unified Python interface for building Flask-based services. It implements a standardized `ToolResult` wrapper to ensure consistent error handling and data flow across all components.

---

## File Tree

```
flask_api/
├── __init__.py      # Package init, exports __version__ and ToolResult
├── __main__.py      # 'python -m flask_api' entry point
├── api.py           # Unified Python API with wrapper functions returning ToolResult
├── cli.py           # Command-line interface (argparse)
├── core.py          # Core business logic (data classes, algorithms, processing engine)
├── tools.py         # OpenAI function-calling tool definitions
└── tests/
    ├── __init__.py
    └── conftest.py

docs/
└── architecture.md   # This document
```

---

## Module Descriptions

### `__init__.py` - Package Initialization
- Defines `__version__ = "0.1.0"`
- Exports public API symbols via `__all__`
- Imports and exposes `ToolResult` from `api.py`

### `__main__.py` - Module Entry Point
- Enables running with `python -m flask_api`
- Imports and calls `main()` from `cli.py`

### `api.py` - Unified Python API
- Provides a standardized `ToolResult` dataclass for consistent result handling
- Contains wrapper functions that:
  - Accept clear, typed parameters
  - Call core logic from `core.py`
  - Return `ToolResult(success=True, data=...)` on success
  - Catch exceptions and return `ToolResult(success=False, error=str(e))`

### `cli.py` - Command-Line Interface
- Implements argparse-based CLI with standard flags:
  - `-V, --version`: Show version (action='version')
  - `-v, --verbose`: Verbose output (action='store_true')
  - `--json`: JSON output (dest='json_output', action='store_true')
  - `-q, --quiet`: Suppress non-essential output (action='store_true')
  - `-o, --output`: Output path
- Dispatches to core logic based on arguments

### `core.py` - Core Business Logic
- Contains data classes for request/response models
- Implements the main processing engine
- Handles business rules and algorithms
- Provides utility functions for data transformation

### `tools.py` - Tool Definitions
- Defines tool schemas for OpenAI function calling
- Implements dispatch logic for different tool types
- Maps tool names to their handler functions

---

## Key Data Structures

### `ToolResult` (api.py)

```python
@dataclass
class ToolResult:
    """Standardised result wrapper for all API functions."""
    
    success: bool          # Whether the operation succeeded
    data: Any = None       # Result data on success
    error: Optional[str] = None  # Error message on failure
    metadata: dict = field(default_factory=dict)  # Additional context
```

**Methods:**
- `to_dict() -> dict`: Serializes result for JSON output

---

## Data Flow Diagram

```mermaid
graph TD
    A[CLI Input] --> B{argparse}
    B --> C[Parse Arguments]
    C --> D{Dispatch Logic}
    
    D --> E[API Wrapper Function]
    E --> F[Core Business Logic]
    F --> G{Processing Engine}
    
    G --> H[Success Case]
    G --> I[Error Case]
    
    H --> J[ToolResult(success=True, data=...)]
    I --> K[ToolResult(success=False, error=...)]
    
    J --> L[CLI Output/JSON]
    K --> M[CLI Error Message]
```

---

## CLI Interface Design

### Standard Flags

| Flag | Short | Long | Type | Description |
|------|-------|------|------|-------------|
| `-V` | --version | version | action='version' | Show version and exit |
| `-v` | --verbose | verbose | store_true | Verbose output |
| `--json` | json_output | json_output | store_true | Output results as JSON |
| `-q` | --quiet | quiet | store_true | Suppress non-essential output |
| `-o` | --output | output | string | Output path/file |

### Project-Specific Flags (TODO)
```python
# Example: parser.add_argument("input", help="Input file or value")
# Example: parser.add_argument("--format", choices=["csv","json"], default="json")
```

---

## Design Decisions and Rationale

### 1. `ToolResult` Wrapper Pattern
**Decision**: All API functions return a standardized `ToolResult` dataclass
**Rationale**: 
- Ensures consistent error handling across all components
- Provides clear success/failure indicators
- Enables uniform serialization for JSON output
- Facilitates testing with predictable result structures

### 2. Exception Handling Strategy
**Decision**: Catch exceptions in wrapper functions and convert to `ToolResult(success=False, error=str(e))`
**Rationale**:
- Prevents unhandled exceptions from crashing the CLI
- Provides user-friendly error messages
- Maintains program flow for retry or recovery scenarios

### 3. Core Logic Separation
**Decision**: Business logic lives in `core.py`, API wrappers in `api.py`
**Rationale**:
- Keeps core algorithms testable and reusable
- API layer can be swapped without changing business logic
- Follows separation of concerns principle

### 4. CLI Argument Structure
**Decision**: Standard flags first, project-specific flags second
**Rationale**:
- Provides consistent interface across different projects
- Makes it easy to add new command-line options
- Follows common CLI patterns users expect

### 5. JSON Output Support
**Decision**: `--json` flag enables structured output via `result.to_dict()`
**Rationale**:
- Enables programmatic consumption of API results
- Facilitates integration with other tools and services
- Provides clear data structure for debugging

---

## Usage Examples

### Basic CLI Usage
```bash
# Show version
python -m flask_api --version

# Verbose output
python -m flask_api -v

# JSON output
python -m flask_api --json

# Combined flags
python -m flask_api -v --json
```

### Programmatic API Usage
```python
from flask_api import ToolResult

def my_function(input_text: str) -> ToolResult:
    try:
        from .core import process
        result = process(input_text)
        return ToolResult(success=True, data=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

# Usage
result = my_function("hello")
if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")
```

---

## Future Enhancements

1. **Add project-specific CLI flags** for custom operations
2. **Implement HTTP server** in `core.py` or separate module
3. **Add OpenAI tool integration** via `tools.py` dispatch logic
4. **Create unit tests** for all API wrapper functions
5. **Document each core function** with docstrings and examples

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | Current | Initial scaffold with `ToolResult`, CLI, and TODO placeholders |
