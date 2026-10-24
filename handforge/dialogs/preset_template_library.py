"""Browse and apply curated preset templates."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ..core.presets import (
    apply_template,
    list_template_categories,
    list_templates,
)


class PresetTemplateLibraryDialog(QDialog):
    """Dialog for browsing the packaged preset template library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applied_names: Set[str] = set()
        self._templates: List[Dict] = []
        self.init_ui()
        self.reload_templates()

    def init_ui(self) -> None:
        self.setWindowTitle("Preset Template Library")
        self.setMinimumSize(720, 480)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Curated templates based on platform guidance "
            "(Apple Podcasts, YouTube) and common delivery workflows. "
            "Apply a template to add it to your custom presets."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All", None)
        for cat in list_template_categories():
            self.category_combo.addItem(cat, cat)
        self.category_combo.currentIndexChanged.connect(self.reload_templates)
        filter_row.addWidget(self.category_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Category", "Format", "Id"]
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 2)

        self.description = QTextEdit()
        self.description.setReadOnly(True)
        self.description.setMaximumHeight(120)
        self.description.setPlaceholderText("Select a template to see details.")
        layout.addWidget(self.description)

        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton("Apply to My Presets")
        self.btn_apply.clicked.connect(self.apply_selected)
        btn_row.addWidget(self.btn_apply)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            Qt.Orientation.Horizontal,
            self,
        )
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def reload_templates(self) -> None:
        category = self.category_combo.currentData()
        self._templates = list_templates(category=category)
        self.table.setRowCount(len(self._templates))
        for row, template in enumerate(self._templates):
            opts = template.get("options") or {}
            self.table.setItem(
                row, 0, QTableWidgetItem(str(template.get("name", "")))
            )
            self.table.setItem(
                row, 1, QTableWidgetItem(str(template.get("category", "")))
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(str(opts.get("format", "")))
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(str(template.get("id", "")))
            )
        if self._templates:
            self.table.selectRow(0)
        else:
            self.description.clear()

    def _selected_template(self) -> Optional[Dict]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._templates):
            return None
        return self._templates[row]

    def _on_selection_changed(self) -> None:
        template = self._selected_template()
        if not template:
            self.description.clear()
            return
        opts = template.get("options") or {}
        bits = [
            str(template.get("description") or "").strip(),
            "",
            f"Id: {template.get('id')}",
            f"Options: {opts}",
        ]
        source = template.get("source")
        if source:
            bits.append(f"Source: {source}")
        self.description.setPlainText("\n".join(bits).strip())

    def apply_selected(self) -> None:
        template = self._selected_template()
        if not template:
            QMessageBox.warning(
                self, "No Selection", "Please select a template to apply."
            )
            return
        tid = str(template.get("id") or template.get("name"))
        try:
            saved_name, _options = apply_template(tid, overwrite=False)
        except FileExistsError:
            reply = QMessageBox.question(
                self,
                "Preset Exists",
                f"A custom preset named '{template.get('name')}' already exists.\n"
                "Overwrite it with this template?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                saved_name, _options = apply_template(tid, overwrite=True)
            except (KeyError, ValueError, OSError) as exc:
                QMessageBox.critical(self, "Apply Failed", str(exc))
                return
        except (KeyError, ValueError, OSError) as exc:
            QMessageBox.critical(self, "Apply Failed", str(exc))
            return

        self._applied_names.add(saved_name)
        QMessageBox.information(
            self,
            "Template Applied",
            f"Saved as custom preset '{saved_name}'.",
        )

    def applied_preset_names(self) -> List[str]:
        """Names of custom presets installed during this dialog session."""
        return sorted(self._applied_names)
