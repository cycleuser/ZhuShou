"""Main window for the ZhuShou desktop GUI.

Top bar: request input + Run button + settings.
Central area: PipelineView (sidebar + code/thinking split).
Status bar: provider, model, elapsed time.
"""

from __future__ import annotations

import os
import time
from typing import Any

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from zhushou.config.manager import ZhuShouConfig
from zhushou.events.bus import PipelineEventBus
from zhushou.gui.pipeline_view import PipelineView
from zhushou.gui.styles import Colors, Fonts
from zhushou.gui.workers import EventBridge, PipelineWorker


class MainWindow(QMainWindow):
    """ZhuShou main application window."""

    def __init__(self, config: ZhuShouConfig | None = None) -> None:
        super().__init__()
        self._config = config or ZhuShouConfig.load()
        self._worker: PipelineWorker | None = None
        self._start_time: float = 0.0

        self.setWindowTitle("ZhuShou - AI Development Assistant")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)

        self._setup_menu()
        self._setup_ui()
        self._setup_status_bar()
        self._setup_timer()

    def _setup_menu(self) -> None:
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")

        setup_action = QAction("&Setup Wizard...", self)
        setup_action.triggered.connect(self._open_setup_wizard)
        file_menu.addAction(setup_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menu.addMenu("&View")

        clear_action = QAction("&Clear Output", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self._clear_output)
        view_menu.addAction(clear_action)

        # Knowledge Base menu
        kb_menu = menu.addMenu("&Knowledge Base")

        crawl_action = QAction("Crawl &Website...", self)
        crawl_action.triggered.connect(self._on_crawl_website)
        kb_menu.addAction(crawl_action)

        upload_action = QAction("&Upload Files...", self)
        upload_action.triggered.connect(self._on_upload_files)
        kb_menu.addAction(upload_action)

        import_action = QAction("&Import Directory...", self)
        import_action.triggered.connect(self._on_import_directory)
        kb_menu.addAction(import_action)

        kb_menu.addSeparator()

        delete_action = QAction("&Delete User KB...", self)
        delete_action.triggered.connect(self._on_delete_user_kb)
        kb_menu.addAction(delete_action)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar: request input ──
        top_bar = QWidget()
        top_bar.setStyleSheet(
            f"background-color: {Colors.BG_SECONDARY}; "
            f"border-bottom: 1px solid {Colors.BORDER};"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(8)

        prompt_label = QLabel("Request:")
        prompt_label.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_NORMAL))
        prompt_label.setStyleSheet(
            f"color: {Colors.FG_SECONDARY}; background: transparent;"
        )
        top_layout.addWidget(prompt_label)

        self._request_input = QLineEdit()
        self._request_input.setPlaceholderText(
            "Describe the project you want to build..."
        )
        self._request_input.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_LARGE))
        self._request_input.returnPressed.connect(self._on_run)
        top_layout.addWidget(self._request_input, 1)

        self._run_btn = QPushButton("Run Pipeline")
        self._run_btn.setObjectName("primaryButton")
        self._run_btn.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_NORMAL))
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(self._on_run)
        top_layout.addWidget(self._run_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet(
            f"background-color: {Colors.ERROR}; "
            f"color: {Colors.BG_PRIMARY}; "
            f"border: none; border-radius: 6px; "
            f"padding: 6px 16px; font-weight: bold;"
        )
        self._stop_btn.setFixedHeight(36)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.hide()
        top_layout.addWidget(self._stop_btn)

        layout.addWidget(top_bar)

        # ── Central: pipeline view ──
        self._pipeline_view = PipelineView()
        layout.addWidget(self._pipeline_view, 1)

    def _setup_status_bar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)

        self._provider_label = QLabel(
            f"Provider: {self._config.provider}"
        )
        bar.addWidget(self._provider_label)

        self._model_label = QLabel(
            f"Model: {self._config.model or '(auto)'}"
        )
        bar.addWidget(self._model_label)

        self._time_label = QLabel("Elapsed: --")
        bar.addPermanentWidget(self._time_label)

        # World context indicator
        self._world_label = QLabel("")
        bar.addPermanentWidget(self._world_label)
        self._update_world_label()

    def _setup_timer(self) -> None:
        """Timer to update elapsed time during pipeline runs."""
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_elapsed)

    # ── Actions ────────────────────────────────────────────────────

    @Slot()
    def _on_run(self) -> None:
        request = self._request_input.text().strip()
        if not request:
            return

        if self._worker and self._worker.isRunning():
            return

        # Reset UI
        self._pipeline_view.clear()
        self._run_btn.hide()
        self._stop_btn.show()
        self._request_input.setReadOnly(True)
        self._start_time = time.time()
        self._timer.start()

        output_dir = os.path.join(".", "output")

        # Create event bus + bridge
        bus = PipelineEventBus()
        bridge = EventBridge(self)
        bus.subscribe(bridge.on_event)

        # Connect bridge to pipeline view
        self._pipeline_view.connect_bridge(bridge)
        self._pipeline_view.set_work_dir(os.path.abspath(output_dir))

        # Connect completion signals
        bridge.pipeline_complete.connect(self._on_pipeline_done)

        # Create and start worker
        self._worker = PipelineWorker(
            request=request,
            provider=self._config.provider,
            model=self._config.model,
            event_bus=bus,
            output_dir=output_dir,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            proxy=self._config.proxy,
            timeout=self._config.timeout,
            python_path=self._config.python_path,
            world_sense=self._config.world_sense,
            parent=self,
        )
        self._worker.error_occurred.connect(self._on_pipeline_error)
        self._worker.start()

    @Slot()
    def _on_stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
        self._reset_run_ui()

    @Slot(dict)
    def _on_pipeline_done(self, stats: dict) -> None:
        self._reset_run_ui()
        tests = stats.get("tests_passed", "N/A")
        total_time = stats.get("total_time", "")
        self.statusBar().showMessage(
            f"Pipeline complete | Tests: {tests} | Time: {total_time}",
            10000,
        )

    @Slot(str)
    def _on_pipeline_error(self, error: str) -> None:
        self._reset_run_ui()
        QMessageBox.critical(self, "Pipeline Error", error)

    def _reset_run_ui(self) -> None:
        self._timer.stop()
        self._run_btn.show()
        self._stop_btn.hide()
        self._request_input.setReadOnly(False)

    @Slot()
    def _update_elapsed(self) -> None:
        elapsed = int(time.time() - self._start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self._time_label.setText(f"Elapsed: {minutes}m {seconds:02d}s")

    @Slot()
    def _open_setup_wizard(self) -> None:
        from zhushou.gui.wizard_dialog import SetupWizardDialog

        dialog = SetupWizardDialog(self._config, parent=self)
        if dialog.exec():
            self._config = dialog.get_config()
            self._config.first_run_complete = True
            self._config.save()
            self._provider_label.setText(f"Provider: {self._config.provider}")
            self._model_label.setText(
                f"Model: {self._config.model or '(auto)'}"
            )

    @Slot()
    def _clear_output(self) -> None:
        self._pipeline_view.clear()

    def _update_world_label(self) -> None:
        """Update the status bar world-context indicator."""
        try:
            from zhushou.utils.world_context import get_world_context

            ctx = get_world_context(self._config.world_sense)
            if ctx:
                # Extract just the date line for brevity
                for line in ctx.splitlines():
                    if line.startswith("Current date"):
                        self._world_label.setText(line)
                        return
                self._world_label.setText("World: active")
            else:
                self._world_label.setText("World: off")
        except Exception:
            self._world_label.setText("")

    @Slot()
    def _on_crawl_website(self) -> None:
        """Prompt user for a URL and start a KB crawl worker."""
        url, ok = QInputDialog.getText(
            self, "Crawl Website",
            "Enter the URL to crawl into knowledge base:",
        )
        if not ok or not url.strip():
            return

        from zhushou.gui.workers import KBCrawlWorker

        self._crawl_worker = KBCrawlWorker(url.strip(), parent=self)
        self._crawl_worker.crawl_finished.connect(self._on_crawl_finished)
        self._crawl_worker.crawl_error.connect(self._on_crawl_error)
        self._crawl_worker.start()
        self.statusBar().showMessage(f"Crawling {url.strip()}...")

    @Slot(int, str)
    def _on_crawl_finished(self, pages: int, output_dir: str) -> None:
        self.statusBar().showMessage(
            f"Crawl complete: {pages} pages saved to {output_dir}", 10000,
        )

    @Slot(str)
    def _on_crawl_error(self, error: str) -> None:
        QMessageBox.warning(self, "Crawl Error", error)

    @Slot()
    def _on_upload_files(self) -> None:
        """Prompt user to select files and a KB name, then upload."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Upload",
            "",
            "Markdown & Text (*.md *.txt);;All Files (*)",
        )
        if not file_paths:
            return

        name, ok = QInputDialog.getText(
            self, "Knowledge Base Name",
            "Enter a display name for the knowledge base:",
        )
        if not ok or not name.strip():
            return

        from zhushou.gui.workers import KBUploadWorker

        self._upload_worker = KBUploadWorker(
            name.strip(), file_paths, parent=self,
        )
        self._upload_worker.upload_finished.connect(self._on_upload_finished)
        self._upload_worker.upload_error.connect(self._on_upload_error)
        self._upload_worker.start()
        self.statusBar().showMessage(f"Uploading {len(file_paths)} file(s)...")

    @Slot(dict)
    def _on_upload_finished(self, result: dict) -> None:
        saved = result.get("saved", 0)
        skipped = result.get("skipped", 0)
        self.statusBar().showMessage(
            f"Upload complete: {saved} saved, {skipped} skipped", 10000,
        )

    @Slot(str)
    def _on_upload_error(self, error: str) -> None:
        QMessageBox.warning(self, "Upload Error", error)

    @Slot()
    def _on_import_directory(self) -> None:
        """Prompt user to select a directory and KB name, then import."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Import",
        )
        if not dir_path:
            return

        name, ok = QInputDialog.getText(
            self, "Knowledge Base Name",
            "Enter a display name for the knowledge base:",
        )
        if not ok or not name.strip():
            return

        from zhushou.gui.workers import KBImportDirWorker

        self._import_worker = KBImportDirWorker(
            name.strip(), dir_path, parent=self,
        )
        self._import_worker.import_finished.connect(self._on_import_finished)
        self._import_worker.import_error.connect(self._on_import_error)
        self._import_worker.start()
        self.statusBar().showMessage(f"Importing from {dir_path}...")

    @Slot(dict)
    def _on_import_finished(self, result: dict) -> None:
        saved = result.get("saved", 0)
        self.statusBar().showMessage(
            f"Import complete: {saved} file(s) imported", 10000,
        )

    @Slot(str)
    def _on_import_error(self, error: str) -> None:
        QMessageBox.warning(self, "Import Error", error)

    @Slot()
    def _on_delete_user_kb(self) -> None:
        """Prompt user to select a user KB and delete it."""
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig

        mgr = KBManager(KBConfig())
        user_kbs = mgr.list_user_kbs()

        if not user_kbs:
            QMessageBox.information(
                self, "Delete User KB",
                "No user-created knowledge bases found.",
            )
            return

        items = [f"{kb['display_name']} ({kb['key']})" for kb in user_kbs]
        item, ok = QInputDialog.getItem(
            self, "Delete User KB",
            "Select the knowledge base to delete:",
            items, 0, False,
        )
        if not ok:
            return

        idx = items.index(item)
        internal_name = user_kbs[idx]["key"]
        display_name = user_kbs[idx]["display_name"]

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete KB '{display_name}' ({internal_name})?\n"
            "This will remove all documents and the index.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        deleted = mgr.delete_user_kb(internal_name)
        if deleted:
            self.statusBar().showMessage(
                f"Deleted KB '{display_name}'", 10000,
            )
        else:
            QMessageBox.warning(
                self, "Delete Error",
                f"Failed to delete KB '{display_name}'.",
            )
