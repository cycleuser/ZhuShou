"""Function-level design and implementation tracking.

Provides data structures and parsing logic for the Function Design stage
(Stage 3.5) which produces fine-grained function/class specifications
before implementation begins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionSpec:
    """Specification for a single function or class definition."""

    name: str
    """Fully qualified name (e.g. ``calculator.core.Calculator.add``)."""

    file_path: str
    """Relative file path (e.g. ``calculator/core.py``)."""

    signature: str
    """Function signature (e.g. ``add(self, a: float, b: float) -> float``)."""

    docstring: str
    """One-line purpose description."""

    dependencies: list[str] = field(default_factory=list)
    """Names of other FunctionSpecs this depends on."""

    is_class_def: bool = False
    """True if this represents a class skeleton (class line + __init__)."""

    implemented: bool = False
    """Whether this function has been implemented."""


class FunctionRegistry:
    """Tracks function design specs and implementation progress.

    Used by the orchestrator to:
    - Know what needs to be implemented
    - Provide context about already-implemented functions
    - Prevent duplicate implementations
    """

    def __init__(self) -> None:
        self.functions: list[FunctionSpec] = []
        self._by_name: dict[str, FunctionSpec] = {}

    def register(self, specs: list[FunctionSpec]) -> None:
        """Populate from parsed design specs.  Deduplicates by name."""
        for spec in specs:
            if spec.name not in self._by_name:
                self.functions.append(spec)
                self._by_name[spec.name] = spec

    def mark_implemented(self, name: str) -> None:
        """Mark a function as implemented."""
        spec = self._by_name.get(name)
        if spec:
            spec.implemented = True

    def get_unimplemented_for_file(self, file_path: str) -> list[FunctionSpec]:
        """Return unimplemented functions belonging to *file_path*, in order."""
        return [
            f for f in self.functions
            if f.file_path == file_path and not f.implemented
        ]

    def get_implemented_signatures(self, file_path: str) -> str:
        """Return signatures of already-implemented functions in *file_path*.

        Used as context for the LLM so it knows what's already written.
        """
        lines: list[str] = []
        for f in self.functions:
            if f.file_path == file_path and f.implemented:
                prefix = "class " if f.is_class_def else "def "
                lines.append(f"{prefix}{f.signature}  # {f.docstring}")
        return "\n".join(lines)

    def get_dependency_signatures(self, name: str) -> str:
        """Return signatures of dependencies for function *name*."""
        spec = self._by_name.get(name)
        if not spec:
            return ""
        lines: list[str] = []
        for dep_name in spec.dependencies:
            dep = self._by_name.get(dep_name)
            if dep:
                prefix = "class " if dep.is_class_def else "def "
                lines.append(f"{prefix}{dep.signature}  # {dep.docstring}")
        return "\n".join(lines)

    def all_implemented(self) -> bool:
        """Check if all registered functions are implemented."""
        return all(f.implemented for f in self.functions)

    def summary(self) -> str:
        """Return a progress summary string."""
        done = sum(1 for f in self.functions if f.implemented)
        total = len(self.functions)
        return f"{done}/{total} functions implemented"

    def file_paths(self) -> list[str]:
        """Return deduplicated, order-preserving list of file paths."""
        seen: set[str] = set()
        paths: list[str] = []
        for f in self.functions:
            if f.file_path not in seen:
                seen.add(f.file_path)
                paths.append(f.file_path)
        return paths

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage in pipeline context."""
        return {
            "functions": [
                {
                    "name": f.name,
                    "file_path": f.file_path,
                    "signature": f.signature,
                    "docstring": f.docstring,
                    "dependencies": f.dependencies,
                    "is_class_def": f.is_class_def,
                    "implemented": f.implemented,
                }
                for f in self.functions
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FunctionRegistry:
        """Deserialize from dict."""
        registry = cls()
        for item in data.get("functions", []):
            spec = FunctionSpec(
                name=item["name"],
                file_path=item["file_path"],
                signature=item["signature"],
                docstring=item.get("docstring", ""),
                dependencies=item.get("dependencies", []),
                is_class_def=item.get("is_class_def", False),
                implemented=item.get("implemented", False),
            )
            registry.functions.append(spec)
            registry._by_name[spec.name] = spec
        return registry


def parse_function_design(markdown: str) -> list[FunctionSpec]:
    """Parse ``docs/function_design.md`` into a list of FunctionSpecs.

    Expected format::

        ## File: calculator/core.py

        ### class Calculator
        - `__init__(self, precision: int = 10)` -- Initialize with precision
        - `add(self, a: float, b: float) -> float` -- Add two numbers
          - depends_on: validate_input

        ### function validate_input
        - `validate_input(value: Any) -> float` -- Validate and convert input

    Returns an ordered list of FunctionSpec objects.
    """
    specs: list[FunctionSpec] = []
    current_file: str = ""
    current_class: str = ""

    # Pattern: ## File: path/to/file.py
    file_pat = re.compile(r"^##\s+File:\s*(\S+\.py)", re.MULTILINE)
    # Pattern: ### class ClassName or ### function func_name
    heading_pat = re.compile(r"^###\s+(class|function)\s+(\w+)", re.MULTILINE)
    # Pattern: - `signature` -- description
    sig_pat = re.compile(
        r"^-\s+`([^`]+)`\s*(?:--|—|:)\s*(.+)",
        re.MULTILINE,
    )
    # Pattern:   - depends_on: name1, name2
    dep_pat = re.compile(
        r"^\s+-\s*depends_on:\s*(.+)",
        re.MULTILINE,
    )

    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Match file heading
        file_m = file_pat.match(line)
        if file_m:
            current_file = file_m.group(1)
            current_class = ""
            i += 1
            continue

        # Match class/function heading
        heading_m = heading_pat.match(line)
        if heading_m:
            kind = heading_m.group(1)  # "class" or "function"
            name = heading_m.group(2)
            if kind == "class":
                current_class = name
            else:
                current_class = ""
            i += 1
            continue

        # Match signature line
        sig_m = sig_pat.match(line)
        if sig_m and current_file:
            signature = sig_m.group(1).strip()
            docstring = sig_m.group(2).strip()

            # Determine fully qualified name
            func_name = signature.split("(")[0].strip()
            if current_class:
                fq_name = f"{current_file.replace('/', '.').replace('.py', '')}.{current_class}.{func_name}"
            else:
                fq_name = f"{current_file.replace('/', '.').replace('.py', '')}.{func_name}"

            is_class_def = func_name == "__init__" or (
                current_class != "" and func_name == current_class
            )

            # Check next line for depends_on
            dependencies: list[str] = []
            if i + 1 < len(lines):
                dep_m = dep_pat.match(lines[i + 1])
                if dep_m:
                    deps_str = dep_m.group(1).strip()
                    dependencies = [
                        d.strip() for d in deps_str.split(",") if d.strip()
                    ]
                    i += 1  # skip the depends_on line

            specs.append(FunctionSpec(
                name=fq_name,
                file_path=current_file,
                signature=signature,
                docstring=docstring,
                dependencies=dependencies,
                is_class_def=is_class_def,
            ))

            i += 1
            continue

        i += 1

    return specs
