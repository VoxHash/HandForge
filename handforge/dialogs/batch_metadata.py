"""Batch metadata editor dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QCheckBox, QGroupBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from typing import List, Dict, Any, Optional
from ..core.models import Job


class BatchMetadataDialog(QDialog):
    """Dialog for batch editing metadata across multiple files."""
    
    def __init__(self, jobs: List[Job], parent=None):
        super().__init__(parent)
        self.jobs = jobs
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle(f"Batch Metadata Editor - {len(self.jobs)} files")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Editing metadata for {len(self.jobs)} file(s).\n"
                           "Leave fields empty to keep existing values.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Metadata fields with checkboxes
        fields_group = QGroupBox("Metadata Fields")
        fields_layout = QFormLayout(fields_group)
        
        # Title
        title_layout = QHBoxLayout()
        self.title_check = QCheckBox()
        self.title_check.setToolTip("Apply to all selected files")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Leave empty to keep existing")
        title_layout.addWidget(self.title_check)
        title_layout.addWidget(self.title_edit)
        fields_layout.addRow("Title:", title_layout)
        
        # Artist
        artist_layout = QHBoxLayout()
        self.artist_check = QCheckBox()
        self.artist_check.setToolTip("Apply to all selected files")
        self.artist_edit = QLineEdit()
        self.artist_edit.setPlaceholderText("Leave empty to keep existing")
        artist_layout.addWidget(self.artist_check)
        artist_layout.addWidget(self.artist_edit)
        fields_layout.addRow("Artist:", artist_layout)
        
        # Album
        album_layout = QHBoxLayout()
        self.album_check = QCheckBox()
        self.album_check.setToolTip("Apply to all selected files")
        self.album_edit = QLineEdit()
        self.album_edit.setPlaceholderText("Leave empty to keep existing")
        album_layout.addWidget(self.album_check)
        album_layout.addWidget(self.album_edit)
        fields_layout.addRow("Album:", album_layout)
        
        # Year
        year_layout = QHBoxLayout()
        self.year_check = QCheckBox()
        self.year_check.setToolTip("Apply to all selected files")
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("Leave empty to keep existing")
        year_layout.addWidget(self.year_check)
        year_layout.addWidget(self.year_edit)
        fields_layout.addRow("Year:", year_layout)
        
        # Genre
        genre_layout = QHBoxLayout()
        self.genre_check = QCheckBox()
        self.genre_check.setToolTip("Apply to all selected files")
        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Leave empty to keep existing")
        genre_layout.addWidget(self.genre_check)
        genre_layout.addWidget(self.genre_edit)
        fields_layout.addRow("Genre:", genre_layout)
        
        # Track
        track_layout = QHBoxLayout()
        self.track_check = QCheckBox()
        self.track_check.setToolTip("Apply to all selected files")
        self.track_edit = QLineEdit()
        self.track_edit.setPlaceholderText("Leave empty to keep existing")
        track_layout.addWidget(self.track_check)
        track_layout.addWidget(self.track_edit)
        fields_layout.addRow("Track:", track_layout)
        
        layout.addWidget(fields_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_metadata(self) -> Dict[str, Optional[str]]:
        """Get metadata values that should be applied."""
        metadata = {}
        
        if self.title_check.isChecked():
            metadata["title"] = self.title_edit.text() or None
        if self.artist_check.isChecked():
            metadata["artist"] = self.artist_edit.text() or None
        if self.album_check.isChecked():
            metadata["album"] = self.album_edit.text() or None
        if self.year_check.isChecked():
            metadata["year"] = self.year_edit.text() or None
        if self.genre_check.isChecked():
            metadata["genre"] = self.genre_edit.text() or None
        if self.track_check.isChecked():
            metadata["track"] = self.track_edit.text() or None
        
        return metadata
    
    def accept(self):
        """Apply metadata to all jobs."""
        metadata = self.get_metadata()
        
        if not any(metadata.values()):
            QMessageBox.warning(
                self, "No Changes",
                "Please check at least one field and enter a value to apply."
            )
            return
        
        # Apply metadata to all jobs
        for job in self.jobs:
            if "title" in metadata and metadata["title"] is not None:
                job.meta_title = metadata["title"]
            if "artist" in metadata and metadata["artist"] is not None:
                job.meta_artist = metadata["artist"]
            if "album" in metadata and metadata["album"] is not None:
                job.meta_album = metadata["album"]
            if "year" in metadata and metadata["year"] is not None:
                job.meta_year = metadata["year"]
            if "genre" in metadata and metadata["genre"] is not None:
                job.meta_genre = metadata["genre"]
            if "track" in metadata and metadata["track"] is not None:
                job.meta_track = metadata["track"]
        
        super().accept()

