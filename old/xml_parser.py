"""Parse <use_tool> XML blocks from LLM text output.

NOTE: We use <use_tool> instead of <tool_call> to avoid conflicts with
Ollama's built-in tool call parsers (e.g. qwen3-coder's parser intercepts
<tool_call> tags and crashes with EOF errors).
"""

import re
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


# Regex to match entire <use_tool>...</use_tool> blocks (DOTALL for multiline)
_TOOL_CALL_RE = re.compile(
    r"<use_tool>\s*(.*?)\s*</use_tool>", re.DOTALL
)
_TOOL_NAME_RE = re.compile(r"<tool_name>\s*(.*?)\s*</tool_name>", re.DOTALL)

# Known argument tags and their names
_ARG_TAGS = ["path", "content", "command", "dir"]


def _extract_tag(text: str, tag: str) -> str | None:
    """Extract content between <tag>...</tag>. Returns None if not found."""
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    m = pattern.search(text)
    if m:
        return m.group(1)
    return None


def _extract_content_tag(text: str) -> str | None:
    """Special extraction for <content> tag - preserves internal formatting.

    Handles the case where code inside <content> may contain XML-like strings.
    We find the FIRST <content> and LAST </content> to be safe.
    """
    start_marker = "<content>"
    end_marker = "</content>"
    start = text.find(start_marker)
    if start == -1:
        return None
    end = text.rfind(end_marker)
    if end == -1 or end <= start:
        return None
    inner = text[start + len(start_marker) : end]
    # Strip exactly one leading and one trailing newline if present
    if inner.startswith("\n"):
        inner = inner[1:]
    if inner.endswith("\n"):
        inner = inner[:-1]
    return inner


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Parse all <tool_call> blocks from LLM output text.

    Returns a list of ToolCall objects with name and args dict.
    """
    results = []
    for match in _TOOL_CALL_RE.finditer(text):
        block = match.group(1)

        # Extract tool name
        name_match = _TOOL_NAME_RE.search(block)
        if not name_match:
            continue
        name = name_match.group(1).strip()

        # Extract arguments
        args: dict[str, str] = {}

        # Handle <content> specially (may contain code with < > chars)
        content_val = _extract_content_tag(block)
        if content_val is not None:
            args["content"] = content_val

        # Extract other simple tags
        for tag in _ARG_TAGS:
            if tag == "content":
                continue  # already handled
            val = _extract_tag(block, tag)
            if val is not None:
                args[tag] = val.strip()

        results.append(ToolCall(name=name, args=args))
    return results


def extract_reasoning(text: str) -> str:
    """Extract non-tool-call text (LLM reasoning/explanations)."""
    cleaned = _TOOL_CALL_RE.sub("", text)
    # Collapse multiple blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
