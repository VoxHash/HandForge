"""Audio quality analysis dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QFileDialog,
    QGroupBox, QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt
from typing import Optional, Dict, Any
from ..util.ffmpeg import analyze_audio_quality, get_media_info, is_audio_file, is_video_file


class AudioQualityDialog(QDialog):
    """Dialog for analyzing audio quality."""
    
    def __init__(self, file_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()
        if file_path:
            self.analyze_file(file_path)
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Audio Quality Analysis")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QHBoxLayout(file_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Quality metrics
        metrics_group = QGroupBox("Quality Metrics")
        metrics_layout = QFormLayout(metrics_group)
        
        self.codec_label = QLabel("-")
        metrics_layout.addRow("Codec:", self.codec_label)
        
        self.bitrate_label = QLabel("-")
        metrics_layout.addRow("Bitrate:", self.bitrate_label)
        
        self.sample_rate_label = QLabel("-")
        metrics_layout.addRow("Sample Rate:", self.sample_rate_label)
        
        self.channels_label = QLabel("-")
        metrics_layout.addRow("Channels:", self.channels_label)
        
        self.codec_long_label = QLabel("-")
        self.codec_long_label.setWordWrap(True)
        metrics_layout.addRow("Codec Details:", self.codec_long_label)
        
        layout.addWidget(metrics_group)
        
        # Media information
        info_group = QGroupBox("Media Information")
        info_layout = QFormLayout(info_group)
        
        self.duration_label = QLabel("-")
        info_layout.addRow("Duration:", self.duration_label)
        
        self.size_label = QLabel("-")
        info_layout.addRow("File Size:", self.size_label)
        
        self.overall_bitrate_label = QLabel("-")
        info_layout.addRow("Overall Bitrate:", self.overall_bitrate_label)
        
        layout.addWidget(info_group)
        
        # Raw data
        raw_group = QGroupBox("Raw Analysis Data")
        raw_layout = QVBoxLayout(raw_group)
        
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setMaximumHeight(150)
        raw_layout.addWidget(self.raw_text)
        
        layout.addWidget(raw_group)
        
        layout.addStretch()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def browse_file(self):
        """Browse for audio/video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio/Video File", "",
            "Media Files (*.mp3 *.aac *.m4a *.flac *.wav *.ogg *.opus *.mp4 *.mkv *.avi *.mov);;All Files (*)"
        )
        if file_path:
            self.analyze_file(file_path)
    
    def analyze_file(self, file_path: str):
        """Analyze audio quality of file."""
        self.file_path = file_path
        self.file_label.setText(file_path)
        
        # Check if file is audio or video
        if not (is_audio_file(file_path) or is_video_file(file_path)):
            QMessageBox.warning(
                self, "Invalid File",
                "Please select an audio or video file."
            )
            return
        
        # Get quality analysis
        quality_info = analyze_audio_quality(file_path)
        
        # Get media info
        media_info = get_media_info(file_path)
        
        # Update UI
        if quality_info:
            self.codec_label.setText(quality_info.get("codec", "unknown").upper())
            bitrate = quality_info.get("bitrate")
            if bitrate:
                self.bitrate_label.setText(f"{bitrate} kbps")
            else:
                self.bitrate_label.setText("Unknown")
            
            sample_rate = quality_info.get("sample_rate")
            if sample_rate:
                self.sample_rate_label.setText(f"{sample_rate} Hz")
            else:
                self.sample_rate_label.setText("Unknown")
            
            channels = quality_info.get("channels")
            if channels:
                channel_names = {1: "Mono", 2: "Stereo", 6: "5.1", 8: "7.1"}
                channel_name = channel_names.get(channels, f"{channels} channels")
                self.channels_label.setText(f"{channels} ({channel_name})")
            else:
                self.channels_label.setText("Unknown")
            
            codec_long = quality_info.get("codec_long_name", "")
            self.codec_long_label.setText(codec_long if codec_long else "Unknown")
        else:
            self.codec_label.setText("Error")
            self.bitrate_label.setText("Error analyzing file")
            self.sample_rate_label.setText("Error")
            self.channels_label.setText("Error")
            self.codec_long_label.setText("Could not analyze file. Ensure FFprobe is installed.")
        
        # Media info
        duration = media_info.get("duration")
        if duration:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            if hours > 0:
                self.duration_label.setText(f"{hours}:{minutes:02d}:{seconds:02d}")
            else:
                self.duration_label.setText(f"{minutes}:{seconds:02d}")
        else:
            self.duration_label.setText("Unknown")
        
        size = media_info.get("size")
        if size:
            size_mb = size / (1024 * 1024)
            self.size_label.setText(f"{size_mb:.2f} MB ({size:,} bytes)")
        else:
            self.size_label.setText("Unknown")
        
        overall_bitrate = media_info.get("bitrate")
        if overall_bitrate:
            self.overall_bitrate_label.setText(f"{overall_bitrate} kbps")
        else:
            self.overall_bitrate_label.setText("Unknown")
        
        # Raw data
        import json
        raw_data = {
            "quality_analysis": quality_info,
            "media_info": media_info
        }
        self.raw_text.setPlainText(json.dumps(raw_data, indent=2))

