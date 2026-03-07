"""Document source registry — URLs for official framework documentation.

Structure mirrors GangDan's DOC_SOURCES for format compatibility.
Each entry maps a short name to ``{"name": display_name, "urls": [...]}``.
"""

from __future__ import annotations

DOC_SOURCES: dict[str, dict] = {
    "numpy": {
        "name": "NumPy",
        "urls": [
            "https://raw.githubusercontent.com/numpy/numpy/main/doc/source/user/absolute_beginners.rst",
            "https://raw.githubusercontent.com/numpy/numpy/main/doc/source/user/basics.creation.rst",
            "https://raw.githubusercontent.com/numpy/numpy/main/doc/source/user/basics.indexing.rst",
        ],
    },
    "pandas": {
        "name": "Pandas",
        "urls": [
            "https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/user_guide/10min.rst",
            "https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/user_guide/indexing.rst",
        ],
    },
    "matplotlib": {
        "name": "Matplotlib",
        "urls": [
            "https://raw.githubusercontent.com/matplotlib/matplotlib/main/README.md",
            "https://raw.githubusercontent.com/matplotlib/matplotlib/main/doc/users/getting_started/index.rst",
        ],
    },
    "scipy": {
        "name": "SciPy",
        "urls": [
            "https://raw.githubusercontent.com/scipy/scipy/main/doc/source/tutorial/index.rst",
            "https://raw.githubusercontent.com/scipy/scipy/main/doc/source/tutorial/optimize.rst",
            "https://raw.githubusercontent.com/scipy/scipy/main/doc/source/tutorial/interpolate.rst",
            "https://raw.githubusercontent.com/scipy/scipy/main/doc/source/tutorial/linalg.rst",
        ],
    },
    "sympy": {
        "name": "SymPy",
        "urls": [
            "https://raw.githubusercontent.com/sympy/sympy/master/README.md",
            "https://raw.githubusercontent.com/sympy/sympy/master/doc/src/tutorials/intro-tutorial/intro.rst",
            "https://raw.githubusercontent.com/sympy/sympy/master/doc/src/tutorials/intro-tutorial/basic_operations.rst",
        ],
    },
    "torch": {
        "name": "PyTorch",
        "urls": [
            "https://raw.githubusercontent.com/pytorch/pytorch/main/README.md",
            "https://raw.githubusercontent.com/pytorch/tutorials/main/beginner_source/basics/intro.py",
        ],
    },
    "pyside6": {
        "name": "PySide6/Qt",
        "urls": [
            "https://raw.githubusercontent.com/pyside/pyside-setup/dev/README.md",
            "https://raw.githubusercontent.com/qt/qtbase/dev/README.md",
        ],
    },
    "pyqtgraph": {
        "name": "PyQtGraph",
        "urls": [
            "https://raw.githubusercontent.com/pyqtgraph/pyqtgraph/master/README.md",
        ],
    },
    "flask": {
        "name": "Flask",
        "urls": [
            "https://raw.githubusercontent.com/pallets/flask/main/README.md",
            "https://raw.githubusercontent.com/pallets/flask/main/docs/quickstart.rst",
        ],
    },
    # ── Additional sources for forward compatibility ──────────────
    "sklearn": {
        "name": "scikit-learn",
        "urls": [
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/README.rst",
        ],
    },
    "tensorflow": {
        "name": "TensorFlow",
        "urls": [
            "https://raw.githubusercontent.com/tensorflow/tensorflow/master/README.md",
        ],
    },
}


def list_available_sources() -> list[dict]:
    """Return a list of ``{"key": ..., "name": ...}`` for every registered source."""
    return [
        {"key": key, "name": info["name"]}
        for key, info in DOC_SOURCES.items()
    ]


def get_source(name: str) -> dict | None:
    """Look up a single source by key.  Returns ``None`` if not found."""
    return DOC_SOURCES.get(name)
