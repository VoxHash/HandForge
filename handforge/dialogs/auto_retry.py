"""Auto-retry dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QCheckBox, QListWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, List


class AutoRetryDialog(QDialog):
    """Dialog for managing auto-retry rules."""
    
    def __init__(self, settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Auto-Retry Settings")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable Auto-Retry")
        layout.addWidget(self.enable_checkbox)
        
        # Info label
        info = QLabel("Add error patterns to automatically retry when these errors occur:")
        layout.addWidget(info)
        
        # Pattern input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Error Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("Error while decoding")
        input_layout.addWidget(self.pattern_edit)
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_pattern)
        input_layout.addWidget(btn_add)
        layout.addLayout(input_layout)
        
        # List
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_pattern)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_settings(self):
        """Load settings into UI."""
        enabled = self.settings.get("auto_retry_enabled", True)
        self.enable_checkbox.setChecked(enabled)
        
        patterns = self.settings.get("auto_retry_patterns", [])
        self.list_widget.clear()
        for pattern in patterns:
            self.list_widget.addItem(pattern)
    
    def add_pattern(self):
        """Add a new error pattern."""
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Empty Pattern", "Please enter an error pattern.")
            return
        
        # Check for duplicates
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text() == pattern:
                QMessageBox.warning(self, "Duplicate", "This pattern already exists.")
                return
        
        self.list_widget.addItem(pattern)
        self.pattern_edit.clear()
    
    def delete_pattern(self):
        """Delete selected pattern."""
        row = self.list_widget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a pattern to delete.")
            return
        
        self.list_widget.takeItem(row)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from dialog."""
        patterns = []
        for i in range(self.list_widget.count()):
            patterns.append(self.list_widget.item(i).text())
        
        return {
            "auto_retry_enabled": self.enable_checkbox.isChecked(),
            "auto_retry_patterns": patterns,
        }

