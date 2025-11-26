"""Presets manager dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any


class PresetsDialog(QDialog):
    """Dialog for managing conversion presets."""
    
    def __init__(self, presets: Dict[str, Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.presets = presets.copy()
        self.init_ui()
        self.update_table()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Manage Presets")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Format", "Mode", "Bitrate/VBR"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_preset)
        btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(self.edit_preset)
        btn_layout.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_preset)
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
    
    def update_table(self):
        """Update the presets table."""
        self.table.setRowCount(len(self.presets))
        for row, (name, preset) in enumerate(self.presets.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(preset.get("format", "")))
            self.table.setItem(row, 2, QTableWidgetItem(preset.get("mode", "")))
            bitrate = preset.get("bitrate") or preset.get("vbrq") or "-"
            self.table.setItem(row, 3, QTableWidgetItem(str(bitrate)))
    
    def add_preset(self):
        """Add a new preset."""
        dialog = PresetEditDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, preset = dialog.get_preset()
            if name in self.presets:
                QMessageBox.warning(self, "Duplicate", f"Preset '{name}' already exists.")
                return
            self.presets[name] = preset
            self.update_table()
    
    def edit_preset(self):
        """Edit selected preset."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a preset to edit.")
            return
        
        name = self.table.item(row, 0).text()
        preset = self.presets[name]
        
        dialog = PresetEditDialog((name, preset), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_preset = dialog.get_preset()
            if new_name != name and new_name in self.presets:
                QMessageBox.warning(self, "Duplicate", f"Preset '{new_name}' already exists.")
                return
            del self.presets[name]
            self.presets[new_name] = new_preset
            self.update_table()
    
    def delete_preset(self):
        """Delete selected preset."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a preset to delete.")
            return
        
        name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.presets[name]
            self.update_table()
    
    def get_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get all presets."""
        return self.presets


class PresetEditDialog(QDialog):
    """Dialog for editing a single preset."""
    
    def __init__(self, preset_data, parent=None):
        super().__init__(parent)
        self.preset_data = preset_data
        self.init_ui()
        if preset_data:
            self.load_preset()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Edit Preset")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Name
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # Format
        layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp3", "aac", "m4a", "flac", "wav", "ogg", "opus"])
        layout.addWidget(self.format_combo)
        
        # Mode
        layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["CBR", "VBR", "Lossless"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        # Bitrate
        layout.addWidget(QLabel("Bitrate (kbps):"))
        self.bitrate_edit = QLineEdit()
        layout.addWidget(self.bitrate_edit)
        
        # VBR Quality
        layout.addWidget(QLabel("VBR Quality (0-9):"))
        self.vbrq_edit = QLineEdit()
        layout.addWidget(self.vbrq_edit)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.on_mode_changed()
    
    def on_mode_changed(self):
        """Handle mode change."""
        mode = self.mode_combo.currentText()
        if mode == "CBR":
            self.bitrate_edit.setEnabled(True)
            self.vbrq_edit.setEnabled(False)
        elif mode == "VBR":
            self.bitrate_edit.setEnabled(False)
            self.vbrq_edit.setEnabled(True)
        else:  # Lossless
            self.bitrate_edit.setEnabled(False)
            self.vbrq_edit.setEnabled(False)
    
    def load_preset(self):
        """Load preset data."""
        name, preset = self.preset_data
        self.name_edit.setText(name)
        self.format_combo.setCurrentText(preset.get("format", "mp3"))
        self.mode_combo.setCurrentText(preset.get("mode", "CBR"))
        self.bitrate_edit.setText(str(preset.get("bitrate", "")))
        self.vbrq_edit.setText(str(preset.get("vbrq", "")))
    
    def get_preset(self):
        """Get preset data."""
        name = self.name_edit.text()
        if not name:
            raise ValueError("Preset name cannot be empty")
        
        preset = {
            "format": self.format_combo.currentText(),
            "mode": self.mode_combo.currentText(),
        }
        
        if preset["mode"] == "CBR":
            bitrate = self.bitrate_edit.text()
            if bitrate:
                preset["bitrate"] = bitrate
            preset["vbrq"] = "-"
        elif preset["mode"] == "VBR":
            vbrq = self.vbrq_edit.text()
            if vbrq:
                preset["vbrq"] = vbrq
            preset["bitrate"] = "-"
        else:  # Lossless
            preset["bitrate"] = "-"
            preset["vbrq"] = "-"
        
        return name, preset

