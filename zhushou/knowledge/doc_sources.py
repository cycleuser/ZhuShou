"""Document source registry — URLs for official framework documentation.

Structure mirrors GangDan's DOC_SOURCES for format compatibility.
Each entry maps a short name to ``{"name": display_name, "urls": [...]}``.
"""

from __future__ import annotations

DOC_SOURCES: dict[str, dict] = {
    # ── Python Libraries ───────────────────────────────────────────
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
    "pytorch": {
        "name": "PyTorch",
        "urls": [
            "https://raw.githubusercontent.com/pytorch/pytorch/main/README.md",
            "https://raw.githubusercontent.com/pytorch/tutorials/main/beginner_source/basics/intro.py",
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
    "sklearn": {
        "name": "Scikit-learn",
        "urls": [
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/README.rst",
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/doc/getting_started.rst",
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/doc/modules/clustering.rst",
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/doc/modules/tree.rst",
        ],
    },
    "skimage": {
        "name": "Scikit-image",
        "urls": [
            "https://raw.githubusercontent.com/scikit-image/scikit-image/main/README.md",
            "https://raw.githubusercontent.com/scikit-image/scikit-image/main/doc/source/user_guide/getting_started.rst",
            "https://raw.githubusercontent.com/scikit-image/scikit-image/main/doc/source/user_guide/tutorial_segmentation.rst",
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
    "chempy": {
        "name": "ChemPy",
        "urls": [
            "https://raw.githubusercontent.com/bjodah/chempy/master/README.rst",
            "https://raw.githubusercontent.com/bjodah/chempy/master/CHANGES.rst",
        ],
    },
    "jupyter": {
        "name": "Jupyter",
        "urls": [
            "https://raw.githubusercontent.com/jupyter/notebook/main/README.md",
            "https://raw.githubusercontent.com/jupyterlab/jupyterlab/main/README.md",
            "https://raw.githubusercontent.com/ipython/ipython/main/README.rst",
        ],
    },
    "matplotlib": {
        "name": "Matplotlib",
        "urls": [
            "https://raw.githubusercontent.com/matplotlib/matplotlib/main/README.md",
            "https://raw.githubusercontent.com/matplotlib/matplotlib/main/doc/users/getting_started/index.rst",
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
            "https://raw.githubusercontent.com/pyqtgraph/pyqtgraph/master/doc/source/index.rst",
        ],
    },
    "tensorflow": {
        "name": "TensorFlow",
        "urls": [
            "https://raw.githubusercontent.com/tensorflow/tensorflow/master/README.md",
            "https://raw.githubusercontent.com/tensorflow/docs/master/site/en/guide/basics.ipynb",
        ],
    },
    "flask": {
        "name": "Flask",
        "urls": [
            "https://raw.githubusercontent.com/pallets/flask/main/README.md",
            "https://raw.githubusercontent.com/pallets/flask/main/docs/quickstart.rst",
        ],
    },
    # ── GPU Computing ──────────────────────────────────────────────
    "cuda": {
        "name": "CUDA/PyCUDA",
        "urls": [
            "https://raw.githubusercontent.com/inducer/pycuda/main/README.rst",
            "https://raw.githubusercontent.com/inducer/pycuda/main/doc/source/tutorial.rst",
        ],
    },
    "opencl": {
        "name": "OpenCL/PyOpenCL",
        "urls": [
            "https://raw.githubusercontent.com/inducer/pyopencl/main/README.rst",
            "https://raw.githubusercontent.com/inducer/pyopencl/main/doc/source/index.rst",
        ],
    },
    # ── Programming Languages ──────────────────────────────────────
    "rust": {
        "name": "Rust",
        "urls": [
            "https://raw.githubusercontent.com/rust-lang/book/main/src/ch01-00-getting-started.md",
            "https://raw.githubusercontent.com/rust-lang/book/main/src/ch03-00-common-programming-concepts.md",
            "https://raw.githubusercontent.com/rust-lang/book/main/src/ch04-00-understanding-ownership.md",
        ],
    },
    "javascript": {
        "name": "JavaScript",
        "urls": [
            "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/javascript/guide/introduction/index.md",
            "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/javascript/guide/grammar_and_types/index.md",
        ],
    },
    "typescript": {
        "name": "TypeScript",
        "urls": [
            "https://raw.githubusercontent.com/microsoft/TypeScript/main/README.md",
            "https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/Basics.md",
        ],
    },
    "c_lang": {
        "name": "C Language",
        "urls": [
            "https://raw.githubusercontent.com/torvalds/linux/master/Documentation/process/coding-style.rst",
        ],
    },
    "cpp": {
        "name": "C++",
        "urls": [
            "https://raw.githubusercontent.com/isocpp/CppCoreGuidelines/master/CppCoreGuidelines.md",
        ],
    },
    "go": {
        "name": "Go/Golang",
        "urls": [
            "https://raw.githubusercontent.com/golang/go/master/README.md",
            "https://raw.githubusercontent.com/golang/go/master/doc/effective_go.html",
        ],
    },
    "html_css": {
        "name": "HTML/CSS",
        "urls": [
            "https://raw.githubusercontent.com/mdn/content/main/files/en-us/learn/html/introduction_to_html/index.md",
            "https://raw.githubusercontent.com/mdn/content/main/files/en-us/learn/css/first_steps/index.md",
        ],
    },
    # ── Shell & Command Line ───────────────────────────────────────
    "bash": {
        "name": "Bash Shell",
        "urls": [
            "https://raw.githubusercontent.com/dylanaraps/pure-bash-bible/master/README.md",
            "https://raw.githubusercontent.com/jlevy/the-art-of-command-line/master/README.md",
            "https://raw.githubusercontent.com/awesome-lists/awesome-bash/master/README.md",
        ],
    },
    "zsh": {
        "name": "Zsh Shell",
        "urls": [
            "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/README.md",
            "https://raw.githubusercontent.com/unixorn/awesome-zsh-plugins/main/README.md",
        ],
    },
    "powershell": {
        "name": "PowerShell",
        "urls": [
            "https://raw.githubusercontent.com/PowerShell/PowerShell/master/README.md",
            "https://raw.githubusercontent.com/janikvonrotz/awesome-powershell/master/readme.md",
        ],
    },
    "fish": {
        "name": "Fish Shell",
        "urls": [
            "https://raw.githubusercontent.com/fish-shell/fish-shell/master/README.md",
            "https://raw.githubusercontent.com/jorgebucaran/awsm.fish/main/README.md",
        ],
    },
    "linux_commands": {
        "name": "Linux Commands",
        "urls": [
            "https://raw.githubusercontent.com/jlevy/the-art-of-command-line/master/README.md",
            "https://raw.githubusercontent.com/tldr-pages/tldr/main/README.md",
            "https://raw.githubusercontent.com/chubin/cheat.sh/master/README.md",
        ],
    },
    "git": {
        "name": "Git Commands",
        "urls": [
            "https://raw.githubusercontent.com/git/git/master/README.md",
            "https://raw.githubusercontent.com/git-tips/tips/master/README.md",
            "https://raw.githubusercontent.com/arslanbilal/git-cheat-sheet/master/README.md",
        ],
    },
    "docker": {
        "name": "Docker Commands",
        "urls": [
            "https://raw.githubusercontent.com/docker/docker.github.io/master/README.md",
            "https://raw.githubusercontent.com/wsargent/docker-cheat-sheet/master/README.md",
        ],
    },
    "kubectl": {
        "name": "Kubernetes/kubectl",
        "urls": [
            "https://raw.githubusercontent.com/kubernetes/kubectl/master/README.md",
            "https://raw.githubusercontent.com/dennyzhang/cheatsheet-kubernetes-A4/master/README.org",
        ],
    },
}

# Backward-compat alias: "torch" -> "pytorch"
DOC_SOURCES["torch"] = DOC_SOURCES["pytorch"]


def list_available_sources() -> list[dict]:
    """Return a list of ``{"key": ..., "name": ...}`` for every registered source."""
    return [
        {"key": key, "name": info["name"]}
        for key, info in DOC_SOURCES.items()
    ]


def get_source(name: str) -> dict | None:
    """Look up a single source by key.  Returns ``None`` if not found."""
    return DOC_SOURCES.get(name)
