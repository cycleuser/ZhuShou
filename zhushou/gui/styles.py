"""Dark theme and styling constants for the ZhuShou GUI.

Defines a cohesive dark color palette, font settings, and a complete
QSS stylesheet.  All GUI modules import from here to stay consistent.
"""

from __future__ import annotations


# ── Color palette ──────────────────────────────────────────────────

class Colors:
    """Centralized color constants."""

    BG_PRIMARY = "#1e1e2e"       # main background
    BG_SECONDARY = "#181825"     # sidebar / panels
    BG_TERTIARY = "#11111b"      # deepest layer (editors)
    BG_HOVER = "#313244"         # hover / selection highlight
    BG_ACTIVE = "#45475a"        # active item

    FG_PRIMARY = "#cdd6f4"       # main text
    FG_SECONDARY = "#a6adc8"     # muted text
    FG_DIM = "#6c7086"           # very dim / placeholders

    ACCENT = "#89b4fa"           # primary accent (blue)
    ACCENT_HOVER = "#74c7ec"     # accent hover
    SUCCESS = "#a6e3a1"          # green
    WARNING = "#f9e2af"          # yellow
    ERROR = "#f38ba8"            # red/pink
    INFO = "#89dceb"             # teal

    BORDER = "#313244"           # border color
    BORDER_FOCUS = "#89b4fa"     # focused border

    # Stage status colors
    STAGE_PENDING = "#6c7086"
    STAGE_RUNNING = "#89b4fa"
    STAGE_COMPLETE = "#a6e3a1"
    STAGE_ERROR = "#f38ba8"

    # Syntax / code highlights
    CODE_BG = "#11111b"
    CODE_KEYWORD = "#cba6f7"     # purple
    CODE_STRING = "#a6e3a1"      # green
    CODE_COMMENT = "#6c7086"     # dim
    CODE_FUNCTION = "#89b4fa"    # blue
    CODE_NUMBER = "#fab387"      # peach


# ── Font settings ──────────────────────────────────────────────────

class Fonts:
    """Font family and size constants."""

    FAMILY_MONO = "Cascadia Code, JetBrains Mono, Fira Code, Consolas, monospace"
    FAMILY_UI = "Inter, Segoe UI, Noto Sans, sans-serif"

    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 15
    SIZE_HEADER = 18
    SIZE_TITLE = 22


# ── QSS Stylesheet ────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Global ────────────────────────────────────────── */

QWidget {{
    background-color: {Colors.BG_PRIMARY};
    color: {Colors.FG_PRIMARY};
    font-family: {Fonts.FAMILY_UI};
    font-size: {Fonts.SIZE_NORMAL}px;
}}

/* ── Main Window ───────────────────────────────────── */

QMainWindow {{
    background-color: {Colors.BG_PRIMARY};
}}

QMenuBar {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_PRIMARY};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 2px 0;
}}

QMenuBar::item:selected {{
    background-color: {Colors.BG_HOVER};
    border-radius: 4px;
}}

QMenu {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item:selected {{
    background-color: {Colors.BG_HOVER};
    border-radius: 4px;
}}

/* ── Buttons ───────────────────────────────────────── */

QPushButton {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {Colors.BG_ACTIVE};
    border-color: {Colors.ACCENT};
}}

QPushButton:pressed {{
    background-color: {Colors.ACCENT};
    color: {Colors.BG_PRIMARY};
}}

QPushButton#primaryButton {{
    background-color: {Colors.ACCENT};
    color: {Colors.BG_PRIMARY};
    border: none;
}}

QPushButton#primaryButton:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

/* ── Input fields ──────────────────────────────────── */

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_TERTIARY};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {Colors.ACCENT};
    selection-color: {Colors.BG_PRIMARY};
    font-family: {Fonts.FAMILY_MONO};
    font-size: {Fonts.SIZE_NORMAL}px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {Colors.BORDER_FOCUS};
}}

/* ── Scrollbars ────────────────────────────────────── */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {Colors.BG_ACTIVE};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.FG_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.BG_ACTIVE};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {Colors.FG_DIM};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Splitter ──────────────────────────────────────── */

QSplitter::handle {{
    background-color: {Colors.BORDER};
    margin: 1px;
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* ── Tab widget ────────────────────────────────────── */

QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    background-color: {Colors.BG_PRIMARY};
}}

QTabBar::tab {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {Colors.BG_PRIMARY};
    color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
}}

QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.FG_PRIMARY};
}}

/* ── Labels ────────────────────────────────────────── */

QLabel {{
    background-color: transparent;
    color: {Colors.FG_PRIMARY};
}}

QLabel#headerLabel {{
    font-size: {Fonts.SIZE_HEADER}px;
    font-weight: bold;
    color: {Colors.ACCENT};
}}

QLabel#dimLabel {{
    color: {Colors.FG_DIM};
    font-size: {Fonts.SIZE_SMALL}px;
}}

/* ── Combo box ─────────────────────────────────────── */

QComboBox {{
    background-color: {Colors.BG_TERTIARY};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
}}

QComboBox:hover {{
    border-color: {Colors.ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    selection-background-color: {Colors.BG_HOVER};
}}

/* ── Progress bar ──────────────────────────────────── */

QProgressBar {{
    background-color: {Colors.BG_TERTIARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    text-align: center;
    color: {Colors.FG_PRIMARY};
    height: 8px;
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 3px;
}}

/* ── Status bar ────────────────────────────────────── */

QStatusBar {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_SECONDARY};
    border-top: 1px solid {Colors.BORDER};
    font-size: {Fonts.SIZE_SMALL}px;
}}

/* ── Group box ─────────────────────────────────────── */

QGroupBox {{
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {Colors.ACCENT};
}}

/* ── Tool tips ─────────────────────────────────────── */

QToolTip {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""
