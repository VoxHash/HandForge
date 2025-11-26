"""Main window for HandForge."""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QComboBox, QLabel,
    QMenuBar, QMenu, QStatusBar, QMessageBox, QProgressBar, QHeaderView,
    QSplitter, QTextEdit, QDialog, QDialogButtonBox, QLineEdit, QCheckBox,
    QGroupBox, QFrame, QSizePolicy, QSystemTrayIcon,
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QColor

from ..core.models import Job
from ..core.orchestrator import Orchestrator
from ..core.settings import (
    load_settings, save_settings, load_custom_presets, save_custom_presets,
    load_patterns, save_patterns,
)
from ..util.ffmpeg import out_path
from ..dialogs.metadata import MetadataDialog
from ..dialogs.batch_metadata import BatchMetadataDialog
from ..dialogs.audio_quality import AudioQualityDialog
from ..dialogs.presetsdialog import PresetsDialog
from ..dialogs.patternmanagerdialog import PatternManagerDialog
from ..dialogs.auto_retry import AutoRetryDialog
from ..dialogs.preferences import PreferencesDialog
from ..i18n import get_translator


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.presets = load_custom_presets()
        self.patterns = load_patterns()
        self.queue: List[Job] = []
        self.workers_data: Dict[int, Dict[str, Any]] = {}
        self.file_subtitle_tracks: Dict[str, List[Dict[str, Any]]] = {}  # Store subtitle tracks per file
        
        # Initialize translator
        locale = self.settings.get("language", None)
        self.translator = get_translator(locale)
        
        self.orchestrator = Orchestrator(
            threads_per_job=1,
            max_parallel=self.settings.get("parallel", 2)
        )
        self.orchestrator.set_settings(self.settings)
        self.orchestrator.sig_worker_done.connect(self._on_worker_done)
        self.orchestrator.sig_worker_progress.connect(self._on_worker_progress)
        self.orchestrator.sig_worker_log.connect(self._on_worker_log)
        self.orchestrator.sig_worker_started.connect(self._on_worker_started)
        
        # System tray icon
        self.tray_icon = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setToolTip("HandForge - Audio & Video Converter")
            tray_menu = QMenu()
            show_action = tray_menu.addAction("Show Window")
            quit_action = tray_menu.addAction("Quit")
            show_action.triggered.connect(self.show)
            quit_action.triggered.connect(self.close)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()
        
        self.init_ui()
        self.apply_settings()
        self.load_window_state()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("HandForge - Audio & Video Converter")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Menu bar
        self.create_menu_bar()
        
        # Main control panel - grouped for better UX
        t = self.translator
        control_group = QGroupBox(t.tr("group_file_management"))
        control_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_layout = QVBoxLayout(control_group)
        control_layout.setSpacing(10)
        
        # Top row: File operations
        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        
        self.btn_add_files = QPushButton(t.tr("btn_add_files"))
        self.btn_add_files.setToolTip("Add individual files to the conversion queue")
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_files.setMinimumHeight(36)
        file_row.addWidget(self.btn_add_files)
        
        self.btn_add_folder = QPushButton(t.tr("btn_add_folder"))
        self.btn_add_folder.setToolTip("Add all media files from a folder (recursive)")
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_add_folder.setMinimumHeight(36)
        file_row.addWidget(self.btn_add_folder)
        
        # Queue count label
        self.queue_count_label = QLabel("0 " + t.tr("label_queue_count"))
        self.queue_count_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 11px;")
        file_row.addStretch()
        file_row.addWidget(self.queue_count_label)
        
        control_layout.addLayout(file_row)
        
        # Middle row: Preset and conversion controls
        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        
        preset_label = QLabel(t.tr("label_preset"))
        preset_label.setMinimumWidth(60)
        preset_row.addWidget(preset_label)
        
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("🎵 MP3 192k")
        self.combo_preset.addItem("🎵 AAC 256k")
        self.combo_preset.addItem("🎵 FLAC Lossless")
        self.combo_preset.addItem("🎬 MP4 H.264")
        self.combo_preset.addItem("🎬 MKV H.264")
        self.combo_preset.addItem("💾 MP4 H.265 (Smart Compression)")
        self.combo_preset.addItem("💾 MKV H.265 (Smart Compression)")
        self.combo_preset.addItem("🌐 WebM VP9")
        self.combo_preset.addItem("🎧 Extract Audio (MP3)")
        for name in self.presets.keys():
            self.combo_preset.addItem(name)
        self.combo_preset.setMinimumHeight(32)
        self.combo_preset.setToolTip("Select conversion preset or create custom presets in Settings")
        self.combo_preset.currentTextChanged.connect(self.on_preset_changed)
        preset_row.addWidget(self.combo_preset, 2)
        
        preset_row.addSpacing(20)
        
        # Action buttons
        self.btn_start = QPushButton("▶️ Start Conversion")
        self.btn_start.setToolTip("Start converting all files in the queue")
        self.btn_start.clicked.connect(self.start_conversion)
        self.btn_start.setMinimumHeight(36)
        self.btn_start.setMinimumWidth(140)
        preset_row.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹️ Stop")
        self.btn_stop.setToolTip("Stop all running conversions")
        self.btn_stop.clicked.connect(self.stop_conversion)
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setMinimumWidth(100)
        self.btn_stop.setEnabled(False)
        preset_row.addWidget(self.btn_stop)
        
        control_layout.addLayout(preset_row)
        
        layout.addWidget(control_group)
        
        # Options panel - grouped for better organization
        options_group = QGroupBox("⚙️ Advanced Options")
        options_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        options_layout = QHBoxLayout(options_group)
        options_layout.setSpacing(15)
        
        # Video compression options
        video_options = QHBoxLayout()
        video_options.setSpacing(10)
        
        self.checkbox_reduce_size = QCheckBox("💾 Reduce Video Size")
        self.checkbox_reduce_size.setToolTip("Use H.265/HEVC codec for smart compression (5-10x smaller) while maintaining quality")
        self.checkbox_reduce_size.setChecked(False)
        self.checkbox_reduce_size.stateChanged.connect(self.on_reduce_size_changed)
        video_options.addWidget(self.checkbox_reduce_size)
        
        reduction_label = QLabel("Target:")
        reduction_label.setEnabled(False)
        video_options.addWidget(reduction_label)
        
        self.combo_reduction = QComboBox()
        self.combo_reduction.addItem("5x smaller", 5.0)
        self.combo_reduction.addItem("7x smaller", 7.0)
        self.combo_reduction.addItem("10x smaller", 10.0)
        self.combo_reduction.addItem("Maximum compression", 15.0)
        self.combo_reduction.setCurrentIndex(1)  # Default to 7x
        self.combo_reduction.setEnabled(False)
        self.combo_reduction.setToolTip("Target file size reduction factor")
        video_options.addWidget(self.combo_reduction)
        
        self.checkbox_two_pass = QCheckBox("🔄 Two-Pass Encoding")
        self.checkbox_two_pass.setToolTip("Slower but provides optimal quality/size ratio (recommended for best results)")
        self.checkbox_two_pass.setChecked(False)
        video_options.addWidget(self.checkbox_two_pass)
        self.checkbox_two_pass.setEnabled(False)
        video_options.addWidget(self.checkbox_two_pass)
        
        options_layout.addLayout(video_options)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: rgba(255, 255, 255, 30);")
        options_layout.addWidget(separator)
        
        options_layout.addStretch()
        
        # File management option
        self.checkbox_delete_original = QCheckBox("🗑️ Delete Original After Conversion")
        self.checkbox_delete_original.setToolTip("⚠️ Remove source file after successful conversion (use with caution)")
        self.checkbox_delete_original.setChecked(self.settings.get("delete_original", False))
        self.checkbox_delete_original.stateChanged.connect(self.on_delete_original_changed)
        options_layout.addWidget(self.checkbox_delete_original)
        
        layout.addWidget(options_group)
        
        # Splitter for queue and workers
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Queue table with better styling
        queue_group = QGroupBox("📋 Conversion Queue")
        queue_layout = QVBoxLayout(queue_group)
        
        t = self.translator
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels([
            t.tr("table_number"), t.tr("table_filename"), t.tr("table_format"), t.tr("table_subtitle")
        ])
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.setDragDropMode(QTableWidget.DragDropMode.DropOnly)
        self.queue_table.setAcceptDrops(True)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setShowGrid(False)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        self.queue_table.setColumnWidth(0, 40)  # Narrow column for numbers
        self.queue_table.setColumnWidth(1, 350)  # Wide column for filenames
        self.queue_table.setColumnWidth(2, 120)  # Medium column for format
        self.queue_table.setColumnWidth(3, 220)  # Subtitle selection column (increased width)
        self.queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self.show_queue_context_menu)
        splitter.addWidget(self.queue_table)
        
        queue_layout.addWidget(self.queue_table)
        splitter.addWidget(queue_group)
        
        # Workers table with better styling
        workers_group = QGroupBox("⚡ Active Conversions")
        workers_layout = QVBoxLayout(workers_group)
        
        self.workers_table = QTableWidget()
        self.workers_table.setColumnCount(7)  # Removed Speed column
        self.workers_table.setHorizontalHeaderLabels([
            "ID", "File", "Elapsed", "ETA", "Log", "Status", "Progress"
        ])
        self.workers_table.horizontalHeader().setStretchLastSection(True)
        self.workers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.workers_table.setAlternatingRowColors(True)
        self.workers_table.setShowGrid(False)
        self.workers_table.verticalHeader().setVisible(False)
        self.workers_table.setColumnWidth(0, 40)   # ID
        self.workers_table.setColumnWidth(1, 250)  # File
        self.workers_table.setColumnWidth(2, 80)   # Elapsed (time passed)
        self.workers_table.setColumnWidth(3, 80)   # ETA (estimated time remaining)
        self.workers_table.setColumnWidth(4, 100)  # Log
        self.workers_table.setColumnWidth(5, 150)  # Status (wider to show error messages)
        self.workers_table.setColumnWidth(6, 120)  # Progress
        workers_layout.addWidget(self.workers_table)
        
        # Connect cell clicked signal for View Log button
        self.workers_table.cellClicked.connect(self._on_workers_table_cell_clicked)
        
        splitter.addWidget(workers_group)
        splitter.setSizes([450, 750])
        
        # Override drag/drop for queue table
        self.queue_table.dragEnterEvent = self.dragEnterEvent
        self.queue_table.dropEvent = self.dropEvent
        
        layout.addWidget(splitter, 1)  # Give splitter stretch factor
        
        # Status bar with better info
        self.statusBar().showMessage("✨ Ready - Add files to begin conversion")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                padding: 4px;
                font-size: 11px;
            }
        """)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def on_reduce_size_changed(self, state):
        """Enable/disable size reduction options."""
        enabled = (state == Qt.CheckState.Checked.value)
        self.combo_reduction.setEnabled(enabled)
        self.checkbox_two_pass.setEnabled(enabled)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        if self.is_audio_file(filepath) or self.is_video_file(filepath):
                            files.append(filepath)
        
        self.add_files_to_queue(files)
        event.acceptProposedAction()
    
    def is_video_file(self, path: str) -> bool:
        """Check if file is a video file."""
        from ..util.ffmpeg import is_video_file
        return is_video_file(path)
    
    def create_menu_bar(self):
        """Create menu bar."""
        t = self.translator
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(t.tr("menu_file"))
        file_menu.addAction(t.tr("menu_export_queue"), self.export_queue)
        file_menu.addAction(t.tr("menu_export_summary"), self.export_summary)
        file_menu.addSeparator()
        file_menu.addAction(t.tr("menu_clear_conversions"), self.clear_completed_workers)
        file_menu.addSeparator()
        file_menu.addAction(t.tr("menu_exit"), self.close)
        
        # View menu
        view_menu = menubar.addMenu(t.tr("menu_view"))
        view_menu.addAction(t.tr("menu_parse_tags"), self.parse_tags)
        view_menu.addAction(t.tr("menu_fetch_covers"), self.fetch_covers)
        view_menu.addSeparator()
        view_menu.addAction(t.tr("menu_analyze_quality"), self.analyze_audio_quality)
        
        # Edit menu
        edit_menu = menubar.addMenu(t.tr("menu_edit"))
        edit_menu.addAction(t.tr("menu_batch_metadata"), self.batch_edit_metadata)
        
        # Settings menu
        settings_menu = menubar.addMenu(t.tr("menu_settings"))
        settings_menu.addAction(t.tr("menu_manage_presets"), self.manage_presets)
        settings_menu.addAction(t.tr("menu_manage_patterns"), self.manage_patterns)
        settings_menu.addAction(t.tr("menu_autoretry"), self.manage_autoretry)
        settings_menu.addSeparator()
        settings_menu.addAction(t.tr("menu_preferences"), self.show_preferences)
        settings_menu.addAction(t.tr("menu_reset"), self.reset_settings)
    
    def apply_settings(self):
        """Apply application settings with Glassmorphism styling."""
        # Glassmorphism theme with transparency and blur effects
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 30, 60, 240), stop:1 rgba(20, 20, 40, 240));
                color: #ffffff;
            }
            QWidget {
                background: transparent;
                color: #ffffff;
            }
            QTableWidget {
                background: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                color: #ffffff;
                gridline-color: rgba(255, 255, 255, 20);
            }
            QTableWidget::item {
                background: transparent;
                padding: 5px;
            }
            QTableWidget::item:selected {
                background: rgba(100, 150, 255, 120);
                border-radius: 6px;
            }
            QTableWidget::item:hover {
                background: rgba(255, 255, 255, 30);
                border-radius: 6px;
            }
            QHeaderView::section {
                background: rgba(255, 255, 255, 20);
                border: none;
                padding: 8px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton {
                background: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 10px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 35);
                border: 1px solid rgba(255, 255, 255, 60);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 50);
            }
            QComboBox {
                background: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 10px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 60);
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 60, 240);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 8px;
                selection-background-color: rgba(100, 150, 255, 120);
            }
            QLabel {
                background: transparent;
                color: #ffffff;
            }
            QMenuBar {
                background: rgba(255, 255, 255, 15);
                border: none;
                color: #ffffff;
            }
            QMenuBar::item {
                background: transparent;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background: rgba(255, 255, 255, 30);
            }
            QMenu {
                background: rgba(30, 30, 60, 240);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 10px;
                color: #ffffff;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(100, 150, 255, 120);
            }
            QStatusBar {
                background: rgba(255, 255, 255, 15);
                border-top: 1px solid rgba(255, 255, 255, 30);
                color: #ffffff;
            }
            QSplitter::handle {
                background: rgba(255, 255, 255, 20);
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 600;
                font-size: 13px;
                color: rgba(255, 255, 255, 220);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(255, 255, 255, 50);
                border-radius: 4px;
                background: rgba(255, 255, 255, 10);
            }
            QCheckBox::indicator:checked {
                background: rgba(100, 150, 255, 200);
                border-color: rgba(100, 150, 255, 255);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(255, 255, 255, 80);
            }
            QCheckBox:disabled {
                color: rgba(255, 255, 255, 100);
            }
            QCheckBox::indicator:disabled {
                background: rgba(255, 255, 255, 5);
                border-color: rgba(255, 255, 255, 20);
            }
        """)
    
    def load_window_state(self):
        """Load window geometry and state."""
        if "win_geom" in self.settings:
            self.restoreGeometry(bytes.fromhex(self.settings["win_geom"]))
        if "win_state" in self.settings:
            self.restoreState(bytes.fromhex(self.settings["win_state"]))
    
    def save_window_state(self):
        """Save window geometry and state."""
        self.settings["win_geom"] = self.saveGeometry().toHex().data().decode()
        self.settings["win_state"] = self.saveState().toHex().data().decode()
        save_settings(self.settings)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_window_state()
        
        # Check if conversions are in progress
        if self.orchestrator.workers:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Conversions are in progress. Do you want to stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.orchestrator.stop_all()
                event.accept()
            else:
                event.ignore()
            return
        
        # Check if minimize to tray is enabled
        minimize_to_tray = self.settings.get("minimize_to_tray", True)
        if minimize_to_tray and self.tray_icon and self.tray_icon.isVisible():
            # Hide to tray instead of closing
            event.ignore()
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "HandForge",
                    "Application minimized to system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            event.accept()
    
    
    def is_audio_file(self, path: str) -> bool:
        """Check if file is an audio file."""
        from ..util.ffmpeg import is_audio_file
        return is_audio_file(path)
    
    def add_files(self):
        """Add files dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Media Files", "",
            "Media Files (*.mp3 *.aac *.m4a *.flac *.wav *.ogg *.opus *.wma *.ac3 *.eac3 *.ape *.tta *.wv *.mp2 *.amr *.caf *.au *.mka *.aiff *.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.3gp *.ogv);;Audio Files (*.mp3 *.aac *.m4a *.flac *.wav *.ogg *.opus *.wma *.ac3 *.eac3 *.ape *.tta *.wv *.mp2 *.amr *.caf *.au *.mka *.aiff);;Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.3gp *.ogv);;All Files (*)"
        )
        if files:
            self.add_files_to_queue(files)
    
    def add_folder(self):
        """Add folder dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if folder:
            files = []
            for root, dirs, filenames in os.walk(folder):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    if self.is_audio_file(filepath) or self.is_video_file(filepath):
                        files.append(filepath)
            self.add_files_to_queue(files)
    
    def add_files_to_queue(self, files: List[str]):
        """Add files to the queue."""
        from ..util.ffmpeg import is_video_file, is_audio_file, get_subtitle_tracks
        
        for filepath in files:
            # Determine default format based on file type
            # Note: The actual format will be set from the selected preset when conversion starts
            # The queue table will show the format from the current preset selection
            if is_video_file(filepath):
                default_format = "mp4"  # Default video format
                # Check for subtitles in this specific file
                tracks = get_subtitle_tracks(filepath)
                self.file_subtitle_tracks[filepath] = tracks
            elif is_audio_file(filepath):
                default_format = "mp3"  # Default audio format
                self.file_subtitle_tracks[filepath] = []  # No subtitles for audio
            else:
                continue  # Skip unsupported files
            
            job = Job(
                src=filepath,
                dst_dir=self.get_output_dir(),
                format=default_format,  # Placeholder - will be overridden by preset
                mode="CBR",
                bitrate="192",
            )
            self.queue.append(job)
        
        self.update_queue_table()
    
    def get_output_dir(self) -> str:
        """Get output directory."""
        if os.name == "nt":  # Windows
            return os.path.join(os.environ.get("USERPROFILE", ""), "HandForge_Output")
        else:  # Linux/macOS
            return os.path.expanduser("~/HandForge_Output")
    
    def update_queue_table(self):
        """Update the queue table."""
        # Get format from currently selected preset
        preset_name = self.combo_preset.currentText()
        # Remove emoji prefix if present (e.g., "🎬 MP4 H.264" -> "MP4 H.264")
        # Emojis are not ASCII, so check if first char is ASCII
        if " " in preset_name:
            parts = preset_name.split(" ", 1)
            first_part = parts[0]
            # If first part is not ASCII (likely emoji), remove it
            if first_part and not first_part.isascii():
                preset_name_clean = parts[1]
            else:
                preset_name_clean = preset_name
        else:
            preset_name_clean = preset_name
        
        preset = self.get_preset(preset_name_clean)
        target_format = preset.get("format", "mp3").upper()
        
        self.queue_table.setRowCount(len(self.queue))
        for i, job in enumerate(self.queue):
            # Row number
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 0, num_item)
            
            # File name
            file_item = QTableWidgetItem(os.path.basename(job.src))
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 1, file_item)
            
            # Format - show format from current preset, not job's stored format
            format_item = QTableWidgetItem(target_format)
            format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 2, format_item)
            
            # Subtitle selection (per file)
            tracks = self.file_subtitle_tracks.get(job.src, [])
            # Check if combo already exists to preserve selection
            existing_combo = self.queue_table.cellWidget(i, 3)
            if existing_combo and isinstance(existing_combo, QComboBox):
                current_selection = existing_combo.currentData()
            else:
                current_selection = getattr(job, 'subtitle_track', None)
            
            subtitle_combo = QComboBox()
            # Set smaller font for subtitle combo
            font = subtitle_combo.font()
            font.setPointSize(8)  # Smaller font size
            subtitle_combo.setFont(font)
            subtitle_combo.addItem("None", None)
            if tracks:
                for track in tracks:
                    display_text = f"{track['title']} ({track['language']})"
                    subtitle_combo.addItem(display_text, track['subtitle_index'])
                # Set current selection
                if current_selection is not None:
                    for track in tracks:
                        if track['index'] == current_selection:
                            subtitle_combo.setCurrentIndex(tracks.index(track) + 1)
                            break
            else:
                subtitle_combo.setEnabled(False)
            subtitle_combo.currentIndexChanged.connect(lambda idx, row=i: self.on_subtitle_changed(row, idx))
            self.queue_table.setCellWidget(i, 3, subtitle_combo)
        
        # Update queue count label
        self.update_queue_count()
    
    def update_queue_count(self):
        """Update the queue count label."""
        t = self.translator
        # Count pending files (queue + orchestrator's internal queue)
        pending = len(self.queue) + len(self.orchestrator.job_queue)
        active = len(self.orchestrator.workers)

        if pending == 0 and active == 0:
            self.queue_count_label.setText(f"0 {t.tr('label_queue_count')}")
        elif pending == 1 and active == 0:
            self.queue_count_label.setText(f"1 {t.tr('label_queue_count')}")
        elif active > 0:
            self.queue_count_label.setText(t.tr("label_queue_count_active").format(active=active).replace("{count}", str(pending)))
        else:
            self.queue_count_label.setText(f"{pending} {t.tr('label_queue_count')}")
    
    def start_conversion(self):
        """Start conversion."""
        if not self.queue:
            QMessageBox.warning(
                self, "No Files",
                "📋 Please add files to the queue first.\n\n"
                "Use 'Add Files' or 'Add Folder' buttons, or drag and drop files into the queue."
            )
            return
        
        # Update button states
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        # Get selected preset
        preset_name = self.combo_preset.currentText()
        # Remove emoji prefix if present
        if " " in preset_name:
            parts = preset_name.split(" ", 1)
            first_part = parts[0]
            if first_part and not first_part.isascii():
                preset_name_clean = parts[1]
            else:
                preset_name_clean = preset_name
        else:
            preset_name_clean = preset_name
        preset = self.get_preset(preset_name_clean)
        
        # Apply preset to all jobs
        jobs = []
        from ..util.ffmpeg import is_video_file, is_audio_file
        
        for i, job in enumerate(self.queue):
            # Determine if source is video
            src_is_video = is_video_file(job.src)
            dst_format = preset.get("format", "mp3")
            dst_is_video = is_video_file(f"dummy.{dst_format}") if dst_format else False
            
            job.format = dst_format
            job.mode = preset.get("mode", "CBR")
            job.bitrate = preset.get("bitrate")
            job.vbrq = preset.get("vbrq")
            job.prefer_external_cover = self.settings.get("prefer_external_cover", False)
            job.normalize_lufs = self.settings.get("normalize_lufs", False)
            job.target_lufs = self.settings.get("target_lufs", -14.0)
            
            # Video conversion options
            if src_is_video and dst_is_video:
                # Video to video
                job.video_codec = preset.get("video_codec")
                job.video_bitrate = preset.get("video_bitrate")
                job.video_quality = preset.get("video_quality")
                job.resolution = preset.get("resolution")
                job.fps = preset.get("fps")
                
                # Subtitle selection (per file from queue table)
                subtitle_combo = self.queue_table.cellWidget(i, 3)
                if subtitle_combo and isinstance(subtitle_combo, QComboBox):
                    subtitle_value = subtitle_combo.currentData()
                    if subtitle_value is not None:
                        # subtitle_value is the subtitle_index (0-based among subtitle streams)
                        # We need to find the actual stream index
                        tracks = self.file_subtitle_tracks.get(job.src, [])
                        for track in tracks:
                            if track['subtitle_index'] == subtitle_value:
                                job.subtitle_track = track['index']  # Use actual stream index
                                break
                        else:
                            job.subtitle_track = None
                    else:
                        job.subtitle_track = None
                else:
                    job.subtitle_track = None
                
                # Apply size reduction options from UI
                if self.checkbox_reduce_size.isChecked():
                    job.reduce_size = True
                    job.size_reduction_factor = self.combo_reduction.currentData()
                    job.use_hevc = True  # Use H.265/HEVC for better compression
                    job.two_pass = self.checkbox_two_pass.isChecked()
            elif src_is_video and not dst_is_video:
                # Video to audio extraction
                job.extract_audio_only = True
            
            # Delete original file option
            job.delete_original = self.checkbox_delete_original.isChecked()
            
            jobs.append(job)
        
        # Don't clear queue - keep pending files visible
        # Remove only the files that are starting conversion
        # The queue will be updated as files are processed
        
        # Start conversion
        self.orchestrator.enqueue(jobs)
        
        # Update queue counter (pending = total - active)
        self.update_queue_count()
        self.statusBar().showMessage(f"⚡ Converting {len(jobs)} file{'s' if len(jobs) != 1 else ''}...")
    
    def on_subtitle_changed(self, row: int, index: int):
        """Handle subtitle selection change for a specific file in queue."""
        if row < len(self.queue):
            job = self.queue[row]
            subtitle_combo = self.queue_table.cellWidget(row, 3)
            if subtitle_combo and isinstance(subtitle_combo, QComboBox):
                subtitle_value = subtitle_combo.currentData()
                if subtitle_value is not None:
                    tracks = self.file_subtitle_tracks.get(job.src, [])
                    for track in tracks:
                        if track['subtitle_index'] == subtitle_value:
                            job.subtitle_track = track['index']
                            break
                    else:
                        job.subtitle_track = None
                else:
                    job.subtitle_track = None
    
    def get_preset(self, name: str) -> Dict[str, Any]:
        """Get preset by name."""
        # Remove emoji prefix if present
        if " " in name:
            parts = name.split(" ", 1)
            first_part = parts[0]
            # If first part is not ASCII (likely emoji), remove it
            if first_part and not first_part.isascii():
                name_clean = parts[1]
            else:
                name_clean = name
        else:
            name_clean = name
        
        if name_clean in self.presets:
            return self.presets[name_clean]
        
        # Default presets (audio and video)
        defaults = {
            "MP3 192k": {"format": "mp3", "mode": "CBR", "bitrate": "192"},
            "AAC 256k": {"format": "aac", "mode": "CBR", "bitrate": "256"},
            "FLAC Lossless": {"format": "flac", "mode": "Lossless"},
            "MP4 H.264": {"format": "mp4", "mode": "CBR", "video_codec": "libx264", "video_bitrate": "5000", "bitrate": "192"},
            "MKV H.264": {"format": "mkv", "mode": "CBR", "video_codec": "libx264", "video_bitrate": "5000", "bitrate": "192"},
            "MP4 H.265 (Smart Compression)": {"format": "mp4", "mode": "CBR", "video_codec": "libx265", "reduce_size": True, "use_hevc": True, "size_reduction_factor": 7.0, "bitrate": "192"},
            "MKV H.265 (Smart Compression)": {"format": "mkv", "mode": "CBR", "video_codec": "libx265", "reduce_size": True, "use_hevc": True, "size_reduction_factor": 7.0, "bitrate": "192"},
            "WebM VP9": {"format": "webm", "mode": "CBR", "video_codec": "libvpx-vp9", "video_quality": "30", "bitrate": "192"},
            "Extract Audio (MP3)": {"format": "mp3", "mode": "CBR", "bitrate": "192", "extract_audio_only": True},
        }
        return defaults.get(name_clean, defaults["MP3 192k"])
    
    def stop_conversion(self):
        """Stop conversion."""
        reply = QMessageBox.question(
            self, "Stop Conversion",
            "⏹️ Are you sure you want to stop all running conversions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.orchestrator.stop_all()
            self.statusBar().showMessage("⏹️ Conversion stopped")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
    
    def _on_worker_done(self, wid: int, success: bool, message: str, output_path: str):
        """Handle worker completion."""
        if wid in self.workers_data:
            self.workers_data[wid]["status"] = "Done" if success else "Failed"
            self.workers_data[wid]["message"] = message
            self.workers_data[wid]["output_path"] = output_path
            self.update_workers_table()
            
            # Show notification with file location if successful
            if success and output_path:
                file_name = os.path.basename(output_path)
                self.statusBar().showMessage(f"✅ {file_name} saved to: {os.path.dirname(output_path)}", 5000)
                # System tray notification
                if self.tray_icon:
                    self.tray_icon.showMessage(
                        "Conversion Complete",
                        f"{file_name} saved successfully",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
            else:
                # Show error notification
                if self.tray_icon:
                    self.tray_icon.showMessage(
                        "Conversion Failed",
                        message[:100] if message else "Unknown error",
                        QSystemTrayIcon.MessageIcon.Critical,
                        5000
                    )
        
        # Update queue count when worker completes
        self.update_queue_count()
        
        t = self.translator
        if not self.orchestrator.workers and not self.orchestrator.job_queue:
            self.statusBar().showMessage(t.tr("msg_all_complete"))
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            # System tray notification for all done
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "All Conversions Complete",
                    "All files have been converted successfully",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )
    
    def _on_tray_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    
    def _on_worker_started(self, wid: int, file_path: str):
        """Handle worker started - initialize worker data with file name."""
        file_name = os.path.basename(file_path)
        self.workers_data[wid] = {
                "file": file_name,
                "elapsed": 0,
                "eta": 0,
                "speed": "0.0x",
                "progress": 0,
                "status": "Running",
                "log": [],
                "output_path": "",
            }
        self.update_workers_table()
    
    def _on_worker_progress(self, wid: int, progress: float, elapsed: float, eta: float, speed: str, peak: str, true_peak: str):
        """Handle worker progress."""
        if wid not in self.workers_data:
            # Get file name from orchestrator if available
            file_name = ""
            if wid in self.orchestrator.workers:
                worker = self.orchestrator.workers[wid]
                file_name = os.path.basename(worker.job.src)
            
            self.workers_data[wid] = {
                "file": file_name,
                "elapsed": 0,
                "eta": 0,
                "speed": "",
                "progress": 0,
                "status": "Running",
                "log": [],
                "output_path": "",
            }
        
        self.workers_data[wid]["elapsed"] = elapsed
        self.workers_data[wid]["eta"] = eta
        self.workers_data[wid]["speed"] = speed
        self.workers_data[wid]["progress"] = progress
        self.workers_data[wid]["status"] = "Running"
        self.update_workers_table()
    
    def _on_worker_log(self, wid: int, log_line: str):
        """Handle worker log."""
        if wid not in self.workers_data:
            self.workers_data[wid] = {
                "file": "",
                "elapsed": 0,
                "eta": 0,
                "speed": "",
                "progress": 0,
                "status": "Running",
                "log": [],
                "output_path": "",
            }
        self.workers_data[wid]["log"].append(log_line)
        if len(self.workers_data[wid]["log"]) > 100:
            self.workers_data[wid]["log"].pop(0)
    
    def update_workers_table(self):
        """Update the workers table."""
        self.workers_table.setRowCount(len(self.workers_data))
        for row, (wid, data) in enumerate(self.workers_data.items()):
            self.workers_table.setItem(row, 0, QTableWidgetItem(str(wid)))
            self.workers_table.setItem(row, 1, QTableWidgetItem(data.get("file", "")))
            
            # Elapsed - time that has passed
            elapsed = data.get('elapsed', 0)
            if elapsed < 60:
                elapsed_text = f"{elapsed:.1f}s"
            elif elapsed < 3600:
                elapsed_text = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            else:
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                elapsed_text = f"{hours}h {minutes}m"
            self.workers_table.setItem(row, 2, QTableWidgetItem(elapsed_text))
            
            # ETA - estimated time remaining
            eta = data.get('eta', 0)
            if eta <= 0:
                eta_text = "-"
            elif eta < 60:
                eta_text = f"{eta:.1f}s"
            elif eta < 3600:
                eta_text = f"{int(eta // 60)}m {int(eta % 60)}s"
            else:
                hours = int(eta // 3600)
                minutes = int((eta % 3600) // 60)
                eta_text = f"{hours}h {minutes}m"
            self.workers_table.setItem(row, 3, QTableWidgetItem(eta_text))
            
            # Log button (column 4)
            log_item = QTableWidgetItem("📋 View Log")
            log_item.setFlags(log_item.flags() | Qt.ItemFlag.ItemIsEnabled)
            log_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.workers_table.setItem(row, 4, log_item)
            
            # Status (column 5) - show error message if failed
            t = self.translator
            status = data.get("status", "Running")
            message = data.get("message", "")
            if status == "Failed" and message:
                # Show error message in status - clean up duplicate "Error:" prefixes
                clean_message = message
                error_prefix = t.tr("error_prefix")
                # Remove duplicate error prefixes
                while clean_message.startswith(f"{error_prefix} "):
                    clean_message = clean_message[len(error_prefix) + 1:]
                status_text = f"{t.tr('status_failed_prefix')} {clean_message[:50]}{'...' if len(clean_message) > 50 else ''}"
            else:
                status_text = {
                    "Running": t.tr("status_running"),
                    "Done": t.tr("status_done"),
                    "Failed": t.tr("status_failed"),
                    "Queued": t.tr("status_queued"),
                    "Retrying": t.tr("status_retrying"),
                }.get(status, status)
            
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if status == "Done":
                status_item.setForeground(QColor(100, 255, 100))
            elif status == "Failed":
                status_item.setForeground(QColor(255, 100, 100))
                # Set full error message as tooltip
                if message:
                    status_item.setToolTip(f"Error: {message}")
            elif status == "Running":
                status_item.setForeground(QColor(100, 200, 255))
            self.workers_table.setItem(row, 5, status_item)
            
            # Progress bar (column 6) with ETA
            progress = data.get("progress", 0)
            eta = data.get("eta", 0)
            status = data.get("status", "Running")
            
            # Format ETA
            if eta > 0:
                if eta < 60:
                    eta_str = f"{eta:.0f}s"
                elif eta < 3600:
                    eta_str = f"{eta/60:.1f}m"
                else:
                    eta_str = f"{eta/3600:.1f}h"
                progress_text = f"{progress:.1f}% (ETA: {eta_str})"
            else:
                progress_text = f"{progress:.1f}%"
            
            # Determine progress bar color based on status
            is_failed = (status == "Failed")
            
            # Determine progress bar color based on status
            is_failed = (status == "Failed")
            
            # Check if progress bar widget already exists
            existing_widget = self.workers_table.cellWidget(row, 6)
            if existing_widget:
                # Update existing progress bar
                progress_bar = existing_widget.findChild(QProgressBar)
                if progress_bar:
                    progress_bar.setValue(int(progress))
                    progress_bar.setFormat(progress_text)
                    # Update color if failed
                    if is_failed:
                        progress_bar.setStyleSheet("""
                            QProgressBar {
                                border: 1px solid rgba(255, 100, 100, 0.5);
                                border-radius: 4px;
                                text-align: center;
                                background-color: rgba(0, 0, 0, 0.3);
                            }
                            QProgressBar::chunk {
                                background-color: rgba(255, 100, 100, 0.8);
                                border-radius: 3px;
                            }
                        """)
                    # Update color if failed
                    if is_failed:
                        progress_bar.setStyleSheet("""
                            QProgressBar {
                                border: 1px solid rgba(255, 100, 100, 0.5);
                                border-radius: 4px;
                                text-align: center;
                                background-color: rgba(0, 0, 0, 0.3);
                            }
                            QProgressBar::chunk {
                                background-color: rgba(255, 100, 100, 0.8);
                                border-radius: 3px;
                            }
                        """)
            else:
                # Create new progress bar widget
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_layout.setContentsMargins(2, 2, 2, 2)
                progress_layout.setSpacing(0)
                
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(int(progress))
                progress_bar.setTextVisible(True)
                progress_bar.setFormat(progress_text)
                
                # Set color based on status
                if is_failed:
                    progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 1px solid rgba(255, 100, 100, 0.5);
                            border-radius: 4px;
                            text-align: center;
                            background-color: rgba(0, 0, 0, 0.3);
                        }
                        QProgressBar::chunk {
                            background-color: rgba(255, 100, 100, 0.8);
                            border-radius: 3px;
                        }
                    """)
                else:
                    progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            border-radius: 4px;
                            text-align: center;
                            background-color: rgba(0, 0, 0, 0.3);
                        }
                        QProgressBar::chunk {
                            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(100, 200, 255, 0.8), stop:1 rgba(100, 150, 255, 0.8));
                            border-radius: 3px;
                        }
                    """)
                progress_layout.addWidget(progress_bar)
                self.workers_table.setCellWidget(row, 6, progress_widget)
    
    def _on_workers_table_cell_clicked(self, row: int, column: int):
        """Handle cell click in workers table - show log dialog if Log or Status column clicked."""
        if column == 4:  # Log column (updated index after removing Speed)
            self._show_log_dialog(row)
        elif column == 5:  # Status column - show error log if failed
            wid_item = self.workers_table.item(row, 0)
            if wid_item:
                wid = int(wid_item.text())
                if wid in self.workers_data:
                    status = self.workers_data[wid].get("status", "")
                    if status == "Failed":
                        self._show_log_dialog(row, show_error=True)
    
    def _show_log_dialog(self, row: int, show_error: bool = False):
        """Show log dialog for a worker."""
        wid_item = self.workers_table.item(row, 0)
        if not wid_item:
            return
        
        wid = int(wid_item.text())
        if wid not in self.workers_data:
            return
        
        data = self.workers_data[wid]
        log_data = data.get("log", [])
        output_path = data.get("output_path", "")
        message = data.get("message", "")
        status = data.get("status", "")
        
        # Create log dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Conversion Log - Worker {wid}")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        
        # Add output path info if available
        if output_path:
            path_label = QLabel(f"<b>Output File:</b> {output_path}")
            path_label.setWordWrap(True)
            path_label.setStyleSheet("padding: 5px; background-color: rgba(100, 200, 255, 0.2); border-radius: 4px;")
            layout.addWidget(path_label)
        
        # Add error message if failed
        if status == "Failed" and message:
            # Clean up duplicate "Error:" prefixes
            clean_message = message
            while clean_message.startswith("Error: "):
                clean_message = clean_message[7:]
            error_label = QLabel(f"<b>Error:</b> {clean_message}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("padding: 5px; background-color: rgba(255, 100, 100, 0.3); border-radius: 4px; color: #ff6666;")
            layout.addWidget(error_label)
        
        # Log text area
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setFontFamily("Consolas")
        log_text.setFontPointSize(9)
        if log_data:
            log_text.setPlainText("\n".join(log_data))
        else:
            log_text.setPlainText("No log entries yet.")
        layout.addWidget(log_text)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.close)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def manage_presets(self):
        """Open presets manager dialog."""
        dialog = PresetsDialog(self.presets, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.presets = dialog.get_presets()
            save_custom_presets(self.presets)
            # Update combo box
            self.combo_preset.clear()
            self.combo_preset.addItem("MP3 192k")
            self.combo_preset.addItem("AAC 256k")
            self.combo_preset.addItem("FLAC Lossless")
            self.combo_preset.addItem("MP4 H.264")
            self.combo_preset.addItem("MKV H.264")
            self.combo_preset.addItem("WebM VP9")
            self.combo_preset.addItem("Extract Audio (MP3)")
            for name in self.presets.keys():
                self.combo_preset.addItem(name)
    
    def manage_patterns(self):
        """Open pattern manager dialog."""
        dialog = PatternManagerDialog(self.patterns, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.patterns = dialog.get_patterns()
            save_patterns(self.patterns)
    
    def manage_autoretry(self):
        """Open auto-retry dialog."""
        dialog = AutoRetryDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.update(dialog.get_settings())
            save_settings(self.settings)
            self.orchestrator.set_settings(self.settings)
    
    def show_preferences(self):
        """Show preferences dialog."""
        dialog = PreferencesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload settings
            self.settings = load_settings()
            self.orchestrator.set_settings(self.settings)
            # Reload translator if language changed
            new_lang = self.settings.get("language", None)
            if new_lang != self.translator.locale:
                from ..i18n import set_locale
                set_locale(new_lang if new_lang else 'en')
                self.translator = get_translator(new_lang)
                # Rebuild UI with new language
                self.init_ui()
            # Update UI elements that depend on settings
            self.checkbox_delete_original.setChecked(self.settings.get("delete_original", False))
            t = self.translator
            self.statusBar().showMessage("✅ Preferences saved successfully", 3000)
    
    def analyze_audio_quality(self):
        """Show audio quality analysis dialog."""
        # If files are selected in queue, use first selected file
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.queue):
                file_path = self.queue[row].src
                dialog = AudioQualityDialog(file_path, self)
                dialog.exec()
                return
        
        # Otherwise, open file browser
        dialog = AudioQualityDialog(None, self)
        dialog.exec()
    
    def batch_edit_metadata(self):
        """Batch edit metadata for selected files."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection",
                "Please select one or more files from the queue to edit metadata."
            )
            return
        
        # Get selected jobs
        selected_jobs = []
        for index in selected_rows:
            row = index.row()
            if row < len(self.queue):
                selected_jobs.append(self.queue[row])
        
        if not selected_jobs:
            return
        
        # Show batch metadata dialog
        dialog = BatchMetadataDialog(selected_jobs, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_queue_table()
            self.statusBar().showMessage(f"✅ Metadata updated for {len(selected_jobs)} file(s)", 3000)
    
    def show_queue_context_menu(self, position):
        """Show context menu for queue table."""
        menu = QMenu(self)
        
        # Get selected rows
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if selected_rows:
            menu.addAction("📝 Batch Edit Metadata", self.batch_edit_metadata)
            menu.addSeparator()
            menu.addAction("🗑️ Remove from Queue", self.remove_selected_from_queue)
        else:
            menu.addAction("No files selected")
        
        menu.exec(self.queue_table.viewport().mapToGlobal(position))
    
    def remove_selected_from_queue(self):
        """Remove selected files from queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Remove in reverse order to maintain indices
        rows_to_remove = sorted([index.row() for index in selected_rows], reverse=True)
        for row in rows_to_remove:
            if row < len(self.queue):
                self.queue.pop(row)
        
        self.update_queue_table()
        self.update_queue_count()
    
    def clear_completed_workers(self):
        """Clear completed and failed workers from the Active Conversions table."""
        # Find workers that are done or failed
        to_remove = []
        for wid, data in self.workers_data.items():
            status = data.get("status", "Running")
            if status in ["Done", "Failed"]:
                to_remove.append(wid)
        
        if not to_remove:
            QMessageBox.information(
                self, "No Items to Clear",
                "There are no completed or failed conversions to clear."
            )
            return
        
        # Confirm before clearing
        reply = QMessageBox.question(
            self, "Clear Active Conversions List",
            f"Remove {len(to_remove)} completed/failed conversion(s) from the Active Conversions table?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for wid in to_remove:
                if wid in self.workers_data:
                    del self.workers_data[wid]
            self.update_workers_table()
            self.statusBar().showMessage(f"✅ Cleared {len(to_remove)} item(s) from Active Conversions", 3000)
    
    def on_delete_original_changed(self, state):
        """Handle delete original checkbox change."""
        self.settings["delete_original"] = (state == Qt.CheckState.Checked.value)
        save_settings(self.settings)
    
    def on_preset_changed(self, text):
        """Handle preset selection change - update queue table format display."""
        self.update_queue_table()
    
    def reset_settings(self):
        """Reset settings to factory defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Clear settings directory
            from ..core.settings import get_config_dir
            import shutil
            config_dir = get_config_dir()
            if config_dir.exists():
                shutil.rmtree(config_dir)
            self.settings = load_settings()
            self.presets = load_custom_presets()
            self.patterns = load_patterns()
            QMessageBox.information(self, "Settings Reset", "Settings have been reset to factory defaults.")
    
    def parse_tags(self):
        """Parse tags from filename."""
        QMessageBox.information(self, "Parse Tags", "Parse tags feature not yet fully implemented.")
    
    def fetch_covers(self):
        """Fetch cover art from folder."""
        QMessageBox.information(self, "Fetch Covers", "Fetch covers feature not yet fully implemented.")
    
    def export_queue(self):
        """Export queue to CSV."""
        QMessageBox.information(self, "Export Queue", "Export queue feature not yet fully implemented.")
    
    def export_summary(self):
        """Export summary to CSV."""
        QMessageBox.information(self, "Export Summary", "Export summary feature not yet fully implemented.")

