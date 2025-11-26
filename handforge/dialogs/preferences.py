"""Preferences dialog for HandForge."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget, QWidget,
    QFormLayout, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
from ..core.settings import load_settings, save_settings


class PreferencesDialog(QDialog):
    """Dialog for application preferences."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Preferences - HandForge")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # General tab
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Conversion tab
        conversion_tab = self.create_conversion_tab()
        tabs.addTab(conversion_tab, "Conversion")
        
        # Audio tab
        audio_tab = self.create_audio_tab()
        tabs.addTab(audio_tab, "Audio")
        
        # Video tab
        video_tab = self.create_video_tab()
        tabs.addTab(video_tab, "Video")
        
        # Advanced tab
        advanced_tab = self.create_advanced_tab()
        tabs.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        restore_btn = QPushButton("Restore Defaults")
        restore_btn.clicked.connect(self.restore_defaults)
        buttons.addButton(restore_btn, QDialogButtonBox.ButtonRole.ResetRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Language selection
        lang_group = QGroupBox("Language / Язык / Idioma")
        lang_layout = QVBoxLayout(lang_group)
        
        lang_label = QLabel("Interface Language:")
        lang_layout.addWidget(lang_label)
        
        self.lang_combo = QComboBox()
        from ..i18n import Translator
        for code, name in Translator.SUPPORTED_LOCALES.items():
            self.lang_combo.addItem(f"{name} ({code})", code)
        
        # Set current language
        current_lang = self.settings.get("language", None)
        if current_lang:
            index = self.lang_combo.findData(current_lang)
            if index >= 0:
                self.lang_combo.setCurrentIndex(index)
        else:
            # Auto-detect
            detected = Translator.detect_system_locale()
            index = self.lang_combo.findData(detected)
            if index >= 0:
                self.lang_combo.setCurrentIndex(index)
            # Add "Auto-detect" option
            self.lang_combo.insertItem(0, "Auto-detect (System)", None)
            self.lang_combo.setCurrentIndex(0)
        
        lang_layout.addWidget(self.lang_combo)
        layout.addWidget(lang_group)
        
        # Parallel processing
        parallel_group = QGroupBox("Parallel Processing")
        parallel_layout = QFormLayout(parallel_group)
        
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setMinimum(1)
        self.parallel_spin.setMaximum(16)
        self.parallel_spin.setToolTip("Number of files to convert simultaneously")
        parallel_layout.addRow("Parallel Conversions:", self.parallel_spin)
        
        layout.addWidget(parallel_group)
        
        # File handling
        file_group = QGroupBox("File Handling")
        file_layout = QFormLayout(file_group)
        
        self.dup_handling_combo = QComboBox()
        self.dup_handling_combo.addItems(["Overwrite", "Skip", "Rename"])
        self.dup_handling_combo.setToolTip("What to do when output file already exists")
        file_layout.addRow("Duplicate Handling:", self.dup_handling_combo)
        
        self.delete_original_check = QCheckBox("Delete original file after successful conversion")
        self.delete_original_check.setToolTip("⚠️ Permanently removes source file after conversion")
        file_layout.addRow("", self.delete_original_check)
        
        layout.addWidget(file_group)
        
        # System tray
        tray_group = QGroupBox("System Tray")
        tray_layout = QFormLayout(tray_group)
        
        self.minimize_to_tray_check = QCheckBox("Minimize to system tray when closing window")
        self.minimize_to_tray_check.setToolTip("Keep application running in system tray")
        tray_layout.addRow("", self.minimize_to_tray_check)
        
        layout.addWidget(tray_group)
        
        layout.addStretch()
        return widget
    
    def create_conversion_tab(self) -> QWidget:
        """Create conversion settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Default output
        output_group = QGroupBox("Default Output")
        output_layout = QFormLayout(output_group)
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(output_browse_btn)
        output_layout.addRow("Output Directory:", output_dir_layout)
        
        layout.addWidget(output_group)
        
        # Codec threads
        threads_group = QGroupBox("Codec Threads")
        threads_layout = QFormLayout(threads_group)
        
        self.mp3_threads = QSpinBox()
        self.mp3_threads.setMinimum(1)
        self.mp3_threads.setMaximum(16)
        threads_layout.addRow("MP3:", self.mp3_threads)
        
        self.aac_threads = QSpinBox()
        self.aac_threads.setMinimum(1)
        self.aac_threads.setMaximum(16)
        threads_layout.addRow("AAC:", self.aac_threads)
        
        self.flac_threads = QSpinBox()
        self.flac_threads.setMinimum(1)
        self.flac_threads.setMaximum(16)
        threads_layout.addRow("FLAC:", self.flac_threads)
        
        layout.addWidget(threads_group)
        
        layout.addStretch()
        return widget
    
    def create_audio_tab(self) -> QWidget:
        """Create audio settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Normalization
        norm_group = QGroupBox("Loudness Normalization")
        norm_layout = QFormLayout(norm_group)
        
        self.normalize_check = QCheckBox("Enable loudness normalization")
        self.normalize_check.setToolTip("Normalize audio to target LUFS level")
        norm_layout.addRow("", self.normalize_check)
        
        self.target_lufs_spin = QDoubleSpinBox()
        self.target_lufs_spin.setMinimum(-30.0)
        self.target_lufs_spin.setMaximum(0.0)
        self.target_lufs_spin.setSingleStep(0.5)
        self.target_lufs_spin.setSuffix(" LUFS")
        self.target_lufs_spin.setToolTip("Target loudness level (default: -14.0 LUFS)")
        norm_layout.addRow("Target LUFS:", self.target_lufs_spin)
        
        layout.addWidget(norm_group)
        
        # Cover art
        cover_group = QGroupBox("Cover Art")
        cover_layout = QFormLayout(cover_group)
        
        self.prefer_external_cover_check = QCheckBox("Prefer external cover art (folder.jpg, cover.jpg, etc.)")
        self.prefer_external_cover_check.setToolTip("Use cover art from folder instead of embedded")
        cover_layout.addRow("", self.prefer_external_cover_check)
        
        layout.addWidget(cover_group)
        
        layout.addStretch()
        return widget
    
    def create_video_tab(self) -> QWidget:
        """Create video settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Default video settings
        video_group = QGroupBox("Default Video Settings")
        video_layout = QFormLayout(video_group)
        
        self.default_video_quality_combo = QComboBox()
        self.default_video_quality_combo.addItems(["low", "medium", "high", "ultra"])
        self.default_video_quality_combo.setToolTip("Default quality preset for video conversions")
        video_layout.addRow("Default Quality:", self.default_video_quality_combo)
        
        self.default_video_codec_combo = QComboBox()
        self.default_video_codec_combo.addItems(["libx264", "libx265", "libvpx-vp9"])
        self.default_video_codec_combo.setToolTip("Default video codec")
        video_layout.addRow("Default Codec:", self.default_video_codec_combo)
        
        layout.addWidget(video_group)
        
        # Size reduction defaults
        reduction_group = QGroupBox("Size Reduction Defaults")
        reduction_layout = QFormLayout(reduction_group)
        
        self.default_reduction_factor_spin = QDoubleSpinBox()
        self.default_reduction_factor_spin.setMinimum(2.0)
        self.default_reduction_factor_spin.setMaximum(20.0)
        self.default_reduction_factor_spin.setSingleStep(0.5)
        self.default_reduction_factor_spin.setSuffix("x")
        self.default_reduction_factor_spin.setToolTip("Default size reduction factor")
        reduction_layout.addRow("Default Reduction:", self.default_reduction_factor_spin)
        
        self.default_two_pass_check = QCheckBox("Enable two-pass encoding by default")
        self.default_two_pass_check.setToolTip("Use two-pass encoding for better quality/size ratio")
        reduction_layout.addRow("", self.default_two_pass_check)
        
        layout.addWidget(reduction_group)
        
        layout.addStretch()
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Auto-retry
        retry_group = QGroupBox("Auto-Retry")
        retry_layout = QFormLayout(retry_group)
        
        self.auto_retry_check = QCheckBox("Enable automatic retry on errors")
        self.auto_retry_check.setToolTip("Automatically retry failed conversions")
        retry_layout.addRow("", self.auto_retry_check)
        
        layout.addWidget(retry_group)
        
        # Performance
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)
        
        self.ewma_alpha_spin = QDoubleSpinBox()
        self.ewma_alpha_spin.setMinimum(0.0)
        self.ewma_alpha_spin.setMaximum(1.0)
        self.ewma_alpha_spin.setSingleStep(0.1)
        self.ewma_alpha_spin.setToolTip("Exponentially weighted moving average alpha for progress smoothing")
        perf_layout.addRow("Progress Smoothing (α):", self.ewma_alpha_spin)
        
        layout.addWidget(perf_group)
        
        layout.addStretch()
        return widget
    
    def browse_output_dir(self):
        """Browse for output directory."""
        current_dir = self.output_dir_edit.text() or self.get_default_output_dir()
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current_dir
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def get_default_output_dir(self) -> str:
        """Get default output directory."""
        import os
        if os.name == "nt":  # Windows
            return os.path.join(os.environ.get("USERPROFILE", ""), "HandForge_Output")
        else:  # Linux/macOS
            return os.path.expanduser("~/HandForge_Output")
    
    def load_settings(self):
        """Load settings into UI."""
        # General
        self.parallel_spin.setValue(self.settings.get("parallel", 2))
        dup_handling = self.settings.get("dup_handling", "Overwrite")
        index = self.dup_handling_combo.findText(dup_handling)
        if index >= 0:
            self.dup_handling_combo.setCurrentIndex(index)
        self.delete_original_check.setChecked(self.settings.get("delete_original", False))
        self.minimize_to_tray_check.setChecked(self.settings.get("minimize_to_tray", True))
        
        # Conversion
        output_dir = self.settings.get("output_dir")
        if output_dir:
            self.output_dir_edit.setText(output_dir)
        else:
            self.output_dir_edit.setText(self.get_default_output_dir())
        
        codec_threads = self.settings.get("codec_threads", {})
        self.mp3_threads.setValue(codec_threads.get("mp3", 1))
        self.aac_threads.setValue(codec_threads.get("aac", 1))
        self.flac_threads.setValue(codec_threads.get("flac", 1))
        
        # Audio
        self.normalize_check.setChecked(self.settings.get("normalize_lufs", False))
        self.target_lufs_spin.setValue(self.settings.get("target_lufs", -14.0))
        self.prefer_external_cover_check.setChecked(self.settings.get("prefer_external_cover", False))
        
        # Video
        default_quality = self.settings.get("default_video_quality", "medium")
        quality_index = self.default_video_quality_combo.findText(default_quality)
        if quality_index >= 0:
            self.default_video_quality_combo.setCurrentIndex(quality_index)
        
        default_codec = self.settings.get("default_video_codec", "libx264")
        codec_index = self.default_video_codec_combo.findText(default_codec)
        if codec_index >= 0:
            self.default_video_codec_combo.setCurrentIndex(codec_index)
        
        self.default_reduction_factor_spin.setValue(self.settings.get("default_reduction_factor", 7.0))
        self.default_two_pass_check.setChecked(self.settings.get("default_two_pass", False))
        
        # Advanced
        self.auto_retry_check.setChecked(self.settings.get("auto_retry_enabled", True))
        self.ewma_alpha_spin.setValue(self.settings.get("ewma_alpha", 0.3))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from UI."""
        settings = self.settings.copy()
        
        # General
        settings["parallel"] = self.parallel_spin.value()
        settings["dup_handling"] = self.dup_handling_combo.currentText()
        settings["delete_original"] = self.delete_original_check.isChecked()
        settings["minimize_to_tray"] = self.minimize_to_tray_check.isChecked()
        # Save language setting
        lang_data = self.lang_combo.currentData()
        settings["language"] = lang_data  # None for auto-detect
        
        # Conversion
        output_dir = self.output_dir_edit.text()
        if output_dir:
            settings["output_dir"] = output_dir
        
        settings["codec_threads"] = {
            "mp3": self.mp3_threads.value(),
            "aac": self.aac_threads.value(),
            "flac": self.flac_threads.value(),
        }
        
        # Audio
        settings["normalize_lufs"] = self.normalize_check.isChecked()
        settings["target_lufs"] = self.target_lufs_spin.value()
        settings["prefer_external_cover"] = self.prefer_external_cover_check.isChecked()
        
        # Video
        settings["default_video_quality"] = self.default_video_quality_combo.currentText()
        settings["default_video_codec"] = self.default_video_codec_combo.currentText()
        settings["default_reduction_factor"] = self.default_reduction_factor_spin.value()
        settings["default_two_pass"] = self.default_two_pass_check.isChecked()
        
        # Advanced
        settings["auto_retry_enabled"] = self.auto_retry_check.isChecked()
        settings["ewma_alpha"] = self.ewma_alpha_spin.value()
        
        return settings
    
    def restore_defaults(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to factory defaults
            self.settings = {
                "parallel": 2,
                "dup_handling": "Overwrite",
                "delete_original": False,
                "minimize_to_tray": True,
                "codec_threads": {"mp3": 1, "aac": 1, "flac": 1},
                "normalize_lufs": False,
                "target_lufs": -14.0,
                "prefer_external_cover": False,
                "default_video_quality": "medium",
                "default_video_codec": "libx264",
                "default_reduction_factor": 7.0,
                "default_two_pass": False,
                "auto_retry_enabled": True,
                "ewma_alpha": 0.3,
            }
            self.load_settings()
    
    def accept(self):
        """Save settings and close."""
        settings = self.get_settings()
        save_settings(settings)
        super().accept()

