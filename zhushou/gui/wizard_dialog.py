"""PySide6 setup wizard dialog.

A multi-page QDialog that mirrors the CLI wizard: select Python,
provider, API key, and model.  Used both from the GUI main window
and from ``SetupWizard.run_gui()``.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from zhushou.config.manager import ZhuShouConfig
from zhushou.gui.styles import Colors, Fonts
from zhushou.utils.python_finder import discover_all_pythons

logger = logging.getLogger(__name__)


class SetupWizardDialog(QDialog):
    """Multi-step setup wizard dialog."""

    def __init__(
        self,
        config: ZhuShouConfig | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or ZhuShouConfig()
        self.setWindowTitle("ZhuShou Setup")
        self.setMinimumSize(600, 450)
        self.setModal(True)

        self._setup_ui()
        self._populate_python_list()
        self._populate_provider_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("ZhuShou Setup Wizard")
        title.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_TITLE))
        title.setStyleSheet(f"color: {Colors.ACCENT};")
        layout.addWidget(title)

        subtitle = QLabel("Configure your Python interpreter and LLM provider")
        subtitle.setObjectName("dimLabel")
        layout.addWidget(subtitle)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_python_page())
        self._stack.addWidget(self._make_provider_page())
        self._stack.addWidget(self._make_api_key_page())
        self._stack.addWidget(self._make_model_page())
        layout.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.addStretch()

        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setEnabled(False)
        nav.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("primaryButton")
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn)

        layout.addLayout(nav)

    # ── Pages ──────────────────────────────────────────────────────

    def _make_python_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Step 1/4: Select Python Interpreter"))

        self._python_list = QListWidget()
        layout.addWidget(self._python_list)
        return page

    def _make_provider_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Step 2/4: Select LLM Provider"))

        self._provider_combo = QComboBox()
        layout.addWidget(self._provider_combo)
        layout.addStretch()
        return page

    def _make_api_key_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Step 3/4: Enter API Key (if required)"))

        self._api_key_label = QLabel(
            "Your selected provider may require an API key."
        )
        self._api_key_label.setObjectName("dimLabel")
        layout.addWidget(self._api_key_label)

        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("sk-...")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._api_key_input)
        layout.addStretch()
        return page

    def _make_model_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Step 4/4: Select Model"))

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText(
            "Enter model name (e.g. qwen2.5-coder:7b)"
        )
        layout.addWidget(self._model_input)

        self._model_list = QListWidget()
        self._model_list.itemClicked.connect(self._on_model_clicked)
        layout.addWidget(self._model_list)

        self._model_status = QLabel("")
        self._model_status.setObjectName("dimLabel")
        layout.addWidget(self._model_status)
        return page

    # ── Population ────────────────────────────────────────────────

    def _populate_python_list(self) -> None:
        interpreters = discover_all_pythons()
        for p in interpreters:
            parts = [p.path, f"({p.version})"]
            if p.is_current:
                parts.append("[current]")
            if p.is_venv:
                parts.append("[venv]")
            item = QListWidgetItem(" ".join(parts))
            item.setData(Qt.ItemDataRole.UserRole, p.path)
            self._python_list.addItem(item)

        if interpreters:
            self._python_list.setCurrentRow(0)

    def _populate_provider_list(self) -> None:
        try:
            from zhushou.llm.factory import LLMClientFactory
            providers = LLMClientFactory.list_providers()
        except Exception:
            providers = ["ollama", "openai", "anthropic", "deepseek", "gemini"]
        for p in providers:
            self._provider_combo.addItem(p)

    def _try_load_models(self) -> None:
        """Attempt to list models from the selected provider."""
        self._model_list.clear()
        self._model_status.setText("Connecting...")

        provider = self._provider_combo.currentText()
        try:
            from zhushou.llm.factory import LLMClientFactory

            kwargs: dict[str, Any] = {}
            if self._config.base_url:
                kwargs["base_url"] = self._config.base_url
            api_key = self._api_key_input.text().strip()
            if api_key:
                kwargs["api_key"] = api_key

            client = LLMClientFactory.create_client(provider, **kwargs)
            if client.is_available():
                models = client.list_models()
                for m in models:
                    name = m if isinstance(m, str) else getattr(m, "name", str(m))
                    self._model_list.addItem(name)
                self._model_status.setText(f"{len(models)} models found")
            else:
                self._model_status.setText(
                    f"Cannot connect to {provider}. Enter model name manually."
                )
        except Exception as e:
            logger.debug("Model listing failed: %s", e)
            self._model_status.setText("Could not list models. Enter name manually.")

    # ── Navigation ────────────────────────────────────────────────

    @Slot()
    def _go_next(self) -> None:
        current = self._stack.currentIndex()

        # Save current page data
        if current == 0:
            item = self._python_list.currentItem()
            if item:
                self._config.python_path = item.data(Qt.ItemDataRole.UserRole)
        elif current == 1:
            self._config.provider = self._provider_combo.currentText()
        elif current == 2:
            key = self._api_key_input.text().strip()
            if key:
                self._config.api_key = key

        # Last page -> accept
        if current == self._stack.count() - 1:
            model = self._model_input.text().strip()
            if model:
                self._config.model = model
            self.accept()
            return

        # Move to next page
        next_idx = current + 1

        # Skip API key page for local providers
        if next_idx == 2:
            provider = self._provider_combo.currentText()
            local = {"ollama", "lmstudio", "vllm"}
            if provider in local:
                next_idx = 3

        # Load models when reaching model page
        if next_idx == 3:
            self._try_load_models()

        self._stack.setCurrentIndex(next_idx)
        self._back_btn.setEnabled(True)
        if next_idx == self._stack.count() - 1:
            self._next_btn.setText("Finish")

    @Slot()
    def _go_back(self) -> None:
        current = self._stack.currentIndex()
        prev_idx = current - 1

        # Skip API key page for local providers
        if prev_idx == 2:
            provider = self._provider_combo.currentText()
            local = {"ollama", "lmstudio", "vllm"}
            if provider in local:
                prev_idx = 1

        self._stack.setCurrentIndex(max(0, prev_idx))
        self._back_btn.setEnabled(prev_idx > 0)
        self._next_btn.setText("Next")

    @Slot(QListWidgetItem)
    def _on_model_clicked(self, item: QListWidgetItem) -> None:
        self._model_input.setText(item.text())

    # ── Public API ────────────────────────────────────────────────

    def get_config(self) -> ZhuShouConfig:
        """Return the configured result."""
        return self._config
