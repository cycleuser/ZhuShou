"""Application entry point for the ZhuShou PySide6 GUI.

Creates the QApplication, applies the dark theme, optionally runs
the first-run wizard, then shows the main window.
"""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtWidgets import QApplication

from zhushou.config.manager import ZhuShouConfig
from zhushou.gui.main_window import MainWindow
from zhushou.gui.styles import STYLESHEET


def launch_gui(config: Any | None = None) -> None:
    """Launch the ZhuShou desktop GUI.

    Called from ``zhushou.cli._cmd_gui()`` or directly.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ZhuShou")
    app.setOrganizationName("ZhuShou")
    app.setStyleSheet(STYLESHEET)

    # Load config if not provided
    if config is None or not isinstance(config, ZhuShouConfig):
        config = ZhuShouConfig.load()

    # First-run wizard in GUI mode
    if config.is_first_run:
        from zhushou.gui.wizard_dialog import SetupWizardDialog

        dialog = SetupWizardDialog(config)
        if dialog.exec():
            config = dialog.get_config()
            config.first_run_complete = True
            config.save()
        else:
            # User cancelled — use defaults
            pass

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())
