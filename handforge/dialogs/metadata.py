"""Metadata editor dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QFileDialog
)
from PyQt6.QtCore import Qt
from typing import Optional, Dict, Any


class MetadataDialog(QDialog):
    """Dialog for editing file metadata."""
    
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self.init_ui()
        self.load_metadata()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Edit Metadata")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Title
        layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)
        
        # Artist
        layout.addWidget(QLabel("Artist:"))
        self.artist_edit = QLineEdit()
        layout.addWidget(self.artist_edit)
        
        # Album
        layout.addWidget(QLabel("Album:"))
        self.album_edit = QLineEdit()
        layout.addWidget(self.album_edit)
        
        # Year
        layout.addWidget(QLabel("Year:"))
        self.year_edit = QLineEdit()
        layout.addWidget(self.year_edit)
        
        # Genre
        layout.addWidget(QLabel("Genre:"))
        self.genre_edit = QLineEdit()
        layout.addWidget(self.genre_edit)
        
        # Track
        layout.addWidget(QLabel("Track:"))
        self.track_edit = QLineEdit()
        layout.addWidget(self.track_edit)
        
        # Cover art
        cover_layout = QHBoxLayout()
        cover_layout.addWidget(QLabel("Cover Art:"))
        self.cover_edit = QLineEdit()
        self.cover_edit.setReadOnly(True)
        cover_layout.addWidget(self.cover_edit)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_cover)
        cover_layout.addWidget(btn_browse)
        layout.addLayout(cover_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_metadata(self):
        """Load metadata from job."""
        self.title_edit.setText(self.job.meta_title or "")
        self.artist_edit.setText(self.job.meta_artist or "")
        self.album_edit.setText(self.job.meta_album or "")
        self.year_edit.setText(self.job.meta_year or "")
        self.genre_edit.setText(self.job.meta_genre or "")
        self.track_edit.setText(self.job.meta_track or "")
    
    def browse_cover(self):
        """Browse for cover art file."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Art", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp);;All Files (*)"
        )
        if file:
            self.cover_edit.setText(file)
    
    def get_metadata(self) -> Dict[str, Optional[str]]:
        """Get metadata from dialog."""
        return {
            "title": self.title_edit.text() or None,
            "artist": self.artist_edit.text() or None,
            "album": self.album_edit.text() or None,
            "year": self.year_edit.text() or None,
            "genre": self.genre_edit.text() or None,
            "track": self.track_edit.text() or None,
            "cover": self.cover_edit.text() or None,
        }

