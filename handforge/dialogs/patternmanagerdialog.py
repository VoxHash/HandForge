"""Pattern manager dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QListWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import List


class PatternManagerDialog(QDialog):
    """Dialog for managing filename patterns."""
    
    def __init__(self, patterns: List[str], parent=None):
        super().__init__(parent)
        self.patterns = patterns.copy()
        self.init_ui()
        self.update_list()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Manage Filename Patterns")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel("Patterns use variables: {artist}, {title}, {album}, {track}, {year}")
        layout.addWidget(info)
        
        # Pattern input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("{artist} - {title}")
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
    
    def update_list(self):
        """Update the patterns list."""
        self.list_widget.clear()
        for pattern in self.patterns:
            self.list_widget.addItem(pattern)
    
    def add_pattern(self):
        """Add a new pattern."""
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Empty Pattern", "Please enter a pattern.")
            return
        
        if pattern in self.patterns:
            QMessageBox.warning(self, "Duplicate", "This pattern already exists.")
            return
        
        self.patterns.append(pattern)
        self.pattern_edit.clear()
        self.update_list()
    
    def delete_pattern(self):
        """Delete selected pattern."""
        row = self.list_widget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a pattern to delete.")
            return
        
        del self.patterns[row]
        self.update_list()
    
    def get_patterns(self) -> List[str]:
        """Get all patterns."""
        return self.patterns

