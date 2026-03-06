"""ZhuShou persona loader.

Searches for persona configuration in:
1. ``{work_dir}/.zhushou/persona.md``
2. ``~/.zhushou/persona.md``
3. Built-in default persona
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_DEFAULT_PERSONA = """\
You are ZhuShou (助手), an AI-powered development assistant.

# Identity
- You help developers write, debug, and maintain code.
- You are precise, concise, and respectful.
- You always explain your reasoning before making changes.

# Rules
- Follow existing code conventions in the project.
- Never delete or overwrite files without confirmation.
- Prefer small, incremental changes over large rewrites.
- Always validate your changes by running tests when available.
- Protect .git directories: never modify their contents.

# Tools
- You have access to file read/write, shell commands, search, and git tools.
- Use the right tool for the job: read before edit, list before write.
- Report tool failures clearly and suggest alternatives.
"""


class PersonaLoader:
    """Load persona configuration from markdown files.

    The persona file uses markdown sections (``# Identity``,
    ``# Rules``, ``# Tools``) to structure the system prompt.
    """

    @staticmethod
    def load(work_dir: str = ".") -> str:
        """Search for a persona file and return the combined system prompt.

        Search order:
        1. ``{work_dir}/.zhushou/persona.md``
        2. ``~/.zhushou/persona.md``
        3. Built-in default persona

        Parameters
        ----------
        work_dir : str
            Project working directory to search first.

        Returns
        -------
        str
            The system prompt string.
        """
        # 1. Project-local persona
        local_path = Path(work_dir) / ".zhushou" / "persona.md"
        content = PersonaLoader._try_read(local_path)
        if content:
            return PersonaLoader._parse(content)

        # 2. User-global persona
        global_path = Path.home() / ".zhushou" / "persona.md"
        content = PersonaLoader._try_read(global_path)
        if content:
            return PersonaLoader._parse(content)

        # 3. Built-in default
        return _DEFAULT_PERSONA.strip()

    @staticmethod
    def _try_read(path: Path) -> Optional[str]:
        """Read a file if it exists and is non-empty."""
        try:
            if path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                return text if text else None
        except OSError:
            pass
        return None

    @staticmethod
    def _parse(content: str) -> str:
        """Parse a persona markdown file and return the combined prompt.

        Currently returns the full content as-is.  Section headers
        (``# Identity``, ``# Rules``, ``# Tools``) are preserved in
        the output so the LLM can see the structure.
        """
        # Strip any leading/trailing whitespace
        return content.strip()
