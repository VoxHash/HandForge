"""Preferences dialog for HandForge."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget, QWidget,
    QFormLayout, QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, List, Optional
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
        
        # Cloud tab (local sync folders + optional rclone)
        cloud_tab = self.create_cloud_tab()
        tabs.addTab(cloud_tab, "Cloud")

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
        self.parallel_spin.setToolTip("Maximum files to convert simultaneously (hard ceiling)")
        parallel_layout.addRow("Parallel Conversions:", self.parallel_spin)

        self.adaptive_parallel_check = QCheckBox(
            "Adapt concurrency from free RAM / CPU load"
        )
        self.adaptive_parallel_check.setToolTip(
            "Lower parallel jobs when memory or load is high (Rust scheduler if built, else Python)"
        )
        parallel_layout.addRow("", self.adaptive_parallel_check)
        
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

        # 3-band EQ (FFmpeg equalizer)
        eq_group = QGroupBox("Equalizer (3-band)")
        eq_layout = QFormLayout(eq_group)
        self.eq_enabled_check = QCheckBox("Enable equalizer")
        self.eq_enabled_check.setToolTip(
            "Apply FFmpeg equalizer bands at ~100 Hz / 1 kHz / 8 kHz"
        )
        eq_layout.addRow("", self.eq_enabled_check)
        self.eq_bass_spin = QDoubleSpinBox()
        self.eq_bass_spin.setRange(-24.0, 24.0)
        self.eq_bass_spin.setSingleStep(0.5)
        self.eq_bass_spin.setSuffix(" dB")
        self.eq_bass_spin.setToolTip("Bass gain at ~100 Hz")
        eq_layout.addRow("Bass:", self.eq_bass_spin)
        self.eq_mid_spin = QDoubleSpinBox()
        self.eq_mid_spin.setRange(-24.0, 24.0)
        self.eq_mid_spin.setSingleStep(0.5)
        self.eq_mid_spin.setSuffix(" dB")
        self.eq_mid_spin.setToolTip("Mid gain at ~1 kHz")
        eq_layout.addRow("Mid:", self.eq_mid_spin)
        self.eq_treble_spin = QDoubleSpinBox()
        self.eq_treble_spin.setRange(-24.0, 24.0)
        self.eq_treble_spin.setSingleStep(0.5)
        self.eq_treble_spin.setSuffix(" dB")
        self.eq_treble_spin.setToolTip("Treble gain at ~8 kHz")
        eq_layout.addRow("Treble:", self.eq_treble_spin)
        layout.addWidget(eq_group)

        # Compressor (FFmpeg acompressor)
        comp_group = QGroupBox("Compressor")
        comp_layout = QFormLayout(comp_group)
        self.compressor_enabled_check = QCheckBox("Enable compressor")
        self.compressor_enabled_check.setToolTip(
            "Reduce dynamic range via FFmpeg acompressor"
        )
        comp_layout.addRow("", self.compressor_enabled_check)
        self.compressor_threshold_spin = QDoubleSpinBox()
        self.compressor_threshold_spin.setRange(0.001, 1.0)
        self.compressor_threshold_spin.setDecimals(3)
        self.compressor_threshold_spin.setSingleStep(0.01)
        self.compressor_threshold_spin.setToolTip(
            "Threshold (linear 0–1; FFmpeg default 0.125 ≈ -18 dBFS)"
        )
        comp_layout.addRow("Threshold:", self.compressor_threshold_spin)
        self.compressor_ratio_spin = QDoubleSpinBox()
        self.compressor_ratio_spin.setRange(1.0, 20.0)
        self.compressor_ratio_spin.setSingleStep(0.5)
        self.compressor_ratio_spin.setToolTip("Compression ratio")
        comp_layout.addRow("Ratio:", self.compressor_ratio_spin)
        self.compressor_attack_spin = QDoubleSpinBox()
        self.compressor_attack_spin.setRange(0.01, 2000.0)
        self.compressor_attack_spin.setSuffix(" ms")
        self.compressor_attack_spin.setToolTip("Attack time")
        comp_layout.addRow("Attack:", self.compressor_attack_spin)
        self.compressor_release_spin = QDoubleSpinBox()
        self.compressor_release_spin.setRange(0.01, 9000.0)
        self.compressor_release_spin.setSuffix(" ms")
        self.compressor_release_spin.setToolTip("Release time")
        comp_layout.addRow("Release:", self.compressor_release_spin)
        self.compressor_makeup_spin = QDoubleSpinBox()
        self.compressor_makeup_spin.setRange(1.0, 64.0)
        self.compressor_makeup_spin.setSingleStep(0.5)
        self.compressor_makeup_spin.setToolTip("Makeup gain (linear)")
        comp_layout.addRow("Makeup:", self.compressor_makeup_spin)
        layout.addWidget(comp_group)

        # Limiter (FFmpeg alimiter)
        lim_group = QGroupBox("Limiter")
        lim_layout = QFormLayout(lim_group)
        self.limiter_enabled_check = QCheckBox("Enable limiter")
        self.limiter_enabled_check.setToolTip(
            "Peak-limit via FFmpeg alimiter (lookahead)"
        )
        lim_layout.addRow("", self.limiter_enabled_check)
        self.limiter_limit_spin = QDoubleSpinBox()
        self.limiter_limit_spin.setRange(0.01, 1.0)
        self.limiter_limit_spin.setDecimals(3)
        self.limiter_limit_spin.setSingleStep(0.01)
        self.limiter_limit_spin.setToolTip("Peak ceiling (linear; 0.95 ≈ -0.4 dBFS)")
        lim_layout.addRow("Limit:", self.limiter_limit_spin)
        self.limiter_attack_spin = QDoubleSpinBox()
        self.limiter_attack_spin.setRange(0.1, 80.0)
        self.limiter_attack_spin.setSuffix(" ms")
        self.limiter_attack_spin.setToolTip("Lookahead / attack")
        lim_layout.addRow("Attack:", self.limiter_attack_spin)
        self.limiter_release_spin = QDoubleSpinBox()
        self.limiter_release_spin.setRange(1.0, 2000.0)
        self.limiter_release_spin.setSuffix(" ms")
        self.limiter_release_spin.setToolTip("Release time")
        lim_layout.addRow("Release:", self.limiter_release_spin)
        layout.addWidget(lim_group)

        # Noise reduction (FFmpeg afftdn)
        denoise_group = QGroupBox("Noise Reduction")
        denoise_layout = QFormLayout(denoise_group)
        self.denoise_enabled_check = QCheckBox("Enable noise reduction")
        self.denoise_enabled_check.setToolTip(
            "FFT denoise via FFmpeg afftdn (speech / podcast friendly)"
        )
        denoise_layout.addRow("", self.denoise_enabled_check)
        self.denoise_nr_spin = QDoubleSpinBox()
        self.denoise_nr_spin.setRange(0.01, 97.0)
        self.denoise_nr_spin.setSingleStep(1.0)
        self.denoise_nr_spin.setSuffix(" dB")
        self.denoise_nr_spin.setToolTip("Noise reduction amount")
        denoise_layout.addRow("Reduction:", self.denoise_nr_spin)
        self.denoise_nf_spin = QDoubleSpinBox()
        self.denoise_nf_spin.setRange(-80.0, -20.0)
        self.denoise_nf_spin.setSingleStep(1.0)
        self.denoise_nf_spin.setSuffix(" dB")
        self.denoise_nf_spin.setToolTip("Noise floor estimate")
        denoise_layout.addRow("Noise floor:", self.denoise_nf_spin)
        self.denoise_track_noise_check = QCheckBox("Track noise floor automatically")
        self.denoise_track_noise_check.setToolTip(
            "Enable afftdn tn=1 for adaptive noise-floor tracking"
        )
        denoise_layout.addRow("", self.denoise_track_noise_check)
        layout.addWidget(denoise_group)
        
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

        self.hw_accel_combo = QComboBox()
        # Display label → preference value
        self._hw_accel_choices = [
            ("Auto (detect)", "auto"),
            ("Software (libx264/libx265)", "software"),
            ("NVIDIA NVENC", "nvenc"),
            ("Intel Quick Sync", "qsv"),
            ("VAAPI", "vaapi"),
            ("Apple VideoToolbox", "videotoolbox"),
        ]
        for label, _value in self._hw_accel_choices:
            self.hw_accel_combo.addItem(label)
        self.hw_accel_combo.setToolTip(
            "Hardware video encoder. Auto probes FFmpeg for NVENC / Quick Sync / "
            "VAAPI / VideoToolbox and falls back to software if unavailable or if "
            "the encode fails."
        )
        video_layout.addRow("Hardware Acceleration:", self.hw_accel_combo)

        self.hw_accel_status = QLabel("")
        self.hw_accel_status.setWordWrap(True)
        self.hw_accel_status.setStyleSheet("color: gray; font-size: 11px;")
        video_layout.addRow("", self.hw_accel_status)
        detect_btn = QPushButton("Detect Hardware Encoders…")
        detect_btn.setToolTip("Probe FFmpeg on this machine for working HW encoders")
        detect_btn.clicked.connect(lambda: self.refresh_hw_accel_status(probe=True))
        video_layout.addRow("", detect_btn)
        
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

        # Color adjust (FFmpeg eq)
        color_group = QGroupBox("Color Adjust (brightness / contrast / saturation)")
        color_layout = QFormLayout(color_group)
        self.video_color_enabled_check = QCheckBox("Enable color adjust")
        self.video_color_enabled_check.setToolTip(
            "Apply FFmpeg eq filter (brightness, contrast, saturation) on video encodes"
        )
        color_layout.addRow("", self.video_color_enabled_check)
        self.video_brightness_spin = QDoubleSpinBox()
        self.video_brightness_spin.setRange(-1.0, 1.0)
        self.video_brightness_spin.setSingleStep(0.05)
        self.video_brightness_spin.setDecimals(2)
        self.video_brightness_spin.setToolTip("Brightness (−1.0 … 1.0; default 0)")
        color_layout.addRow("Brightness:", self.video_brightness_spin)
        self.video_contrast_spin = QDoubleSpinBox()
        self.video_contrast_spin.setRange(0.0, 2.0)
        self.video_contrast_spin.setSingleStep(0.05)
        self.video_contrast_spin.setDecimals(2)
        self.video_contrast_spin.setToolTip("Contrast (typically 0 … 2; default 1)")
        color_layout.addRow("Contrast:", self.video_contrast_spin)
        self.video_saturation_spin = QDoubleSpinBox()
        self.video_saturation_spin.setRange(0.0, 3.0)
        self.video_saturation_spin.setSingleStep(0.05)
        self.video_saturation_spin.setDecimals(2)
        self.video_saturation_spin.setToolTip("Saturation (0 … 3; default 1)")
        color_layout.addRow("Saturation:", self.video_saturation_spin)
        layout.addWidget(color_group)

        # Stabilization (FFmpeg deshake — single-pass)
        stab_group = QGroupBox("Stabilization")
        stab_layout = QFormLayout(stab_group)
        self.video_stabilize_enabled_check = QCheckBox("Enable stabilization")
        self.video_stabilize_enabled_check.setToolTip(
            "Single-pass shake reduction via FFmpeg deshake. Milder than multi-pass "
            "vidstab; works with software and HW encode paths (CPU filter before upload)."
        )
        stab_layout.addRow("", self.video_stabilize_enabled_check)
        self.video_stabilize_rx_spin = QSpinBox()
        self.video_stabilize_rx_spin.setRange(0, 64)
        self.video_stabilize_rx_spin.setSingleStep(16)
        self.video_stabilize_rx_spin.setToolTip(
            "Horizontal search range (deshake rx; snapped to multiple of 16)"
        )
        stab_layout.addRow("Search range X:", self.video_stabilize_rx_spin)
        self.video_stabilize_ry_spin = QSpinBox()
        self.video_stabilize_ry_spin.setRange(0, 64)
        self.video_stabilize_ry_spin.setSingleStep(16)
        self.video_stabilize_ry_spin.setToolTip(
            "Vertical search range (deshake ry; snapped to multiple of 16)"
        )
        stab_layout.addRow("Search range Y:", self.video_stabilize_ry_spin)
        self.video_stabilize_edge_combo = QComboBox()
        self.video_stabilize_edge_combo.addItems(
            ["mirror", "clamp", "original", "blank"]
        )
        self.video_stabilize_edge_combo.setToolTip(
            "How to fill edges after motion compensation"
        )
        stab_layout.addRow("Edge fill:", self.video_stabilize_edge_combo)
        layout.addWidget(stab_group)
        
        layout.addStretch()
        return widget
    
    def create_cloud_tab(self) -> QWidget:
        """Create cloud storage settings tab (sync folders + optional rclone)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        roots_group = QGroupBox("Cloud Roots (local sync folders)")
        roots_layout = QVBoxLayout(roots_group)
        roots_hint = QLabel(
            "Point HandForge at Dropbox, Google Drive, OneDrive, Nextcloud, "
            "or any mounted sync folder. FFmpeg reads/writes these paths "
            "locally; your sync client uploads in the background. No API keys."
        )
        roots_hint.setWordWrap(True)
        roots_layout.addWidget(roots_hint)

        self.cloud_roots_list = QListWidget()
        self.cloud_roots_list.setMinimumHeight(120)
        roots_layout.addWidget(self.cloud_roots_list)

        roots_btn_row = QHBoxLayout()
        add_root_btn = QPushButton("Add Folder…")
        add_root_btn.clicked.connect(self.add_cloud_root)
        remove_root_btn = QPushButton("Remove")
        remove_root_btn.clicked.connect(self.remove_cloud_root)
        detect_btn = QPushButton("Detect Sync Folders")
        detect_btn.setToolTip(
            "Scan common Dropbox / Google Drive / OneDrive / Nextcloud locations"
        )
        detect_btn.clicked.connect(self.detect_cloud_roots)
        use_out_btn = QPushButton("Use as Output Dir")
        use_out_btn.setToolTip("Set Conversion → Output Directory to the selected root")
        use_out_btn.clicked.connect(self.use_cloud_root_as_output)
        use_in_btn = QPushButton("Use as Input Browse Start")
        use_in_btn.setToolTip("Start Add Folder / file dialogs in the selected root")
        use_in_btn.clicked.connect(self.use_cloud_root_as_input)
        roots_btn_row.addWidget(add_root_btn)
        roots_btn_row.addWidget(remove_root_btn)
        roots_btn_row.addWidget(detect_btn)
        roots_btn_row.addWidget(use_out_btn)
        roots_btn_row.addWidget(use_in_btn)
        roots_layout.addLayout(roots_btn_row)

        self.cloud_input_root_edit = QLineEdit()
        self.cloud_input_root_edit.setReadOnly(True)
        self.cloud_input_root_edit.setPlaceholderText("(optional — defaults to first cloud root)")
        roots_layout.addWidget(QLabel("Input browse start:"))
        roots_layout.addWidget(self.cloud_input_root_edit)

        layout.addWidget(roots_group)

        rclone_group = QGroupBox("rclone (optional)")
        rclone_layout = QFormLayout(rclone_group)
        self.rclone_enabled_check = QCheckBox("Enable rclone remote:path support")
        self.rclone_enabled_check.setToolTip(
            "When rclone is installed, allow remote:path inputs/outputs "
            "(staged locally for FFmpeg, then uploaded)"
        )
        rclone_layout.addRow("", self.rclone_enabled_check)

        self.rclone_status_label = QLabel("")
        self.rclone_status_label.setWordWrap(True)
        rclone_layout.addRow("Status:", self.rclone_status_label)

        self.rclone_remote_combo = QComboBox()
        self.rclone_remote_combo.setEditable(True)
        self.rclone_remote_combo.setToolTip(
            "Default rclone remote from `rclone listremotes` (empty = none)"
        )
        rclone_layout.addRow("Default remote:", self.rclone_remote_combo)

        self.rclone_binary_edit = QLineEdit()
        self.rclone_binary_edit.setPlaceholderText("rclone (PATH) or full path")
        rclone_layout.addRow("rclone binary:", self.rclone_binary_edit)

        refresh_rclone_btn = QPushButton("Refresh remotes")
        refresh_rclone_btn.clicked.connect(self.refresh_rclone_status)
        rclone_layout.addRow("", refresh_rclone_btn)

        layout.addWidget(rclone_group)
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

        self.performance_analytics_check = QCheckBox(
            "Enable performance analytics (local only)"
        )
        self.performance_analytics_check.setToolTip(
            "When on, record per-job and batch metrics (encode speed, duration, "
            "throughput, peak parallel, ETA accuracy) under ~/.handforge/analytics/. "
            "Nothing is uploaded. Off by default."
        )
        self.performance_analytics_check.stateChanged.connect(
            lambda *_: self.refresh_analytics_status()
        )
        perf_layout.addRow("", self.performance_analytics_check)

        self.analytics_status_label = QLabel("")
        self.analytics_status_label.setWordWrap(True)
        self.analytics_status_label.setStyleSheet("color: #666; font-size: 11px;")
        perf_layout.addRow("", self.analytics_status_label)
        
        layout.addWidget(perf_group)

        # Companion remote monitor + shared workstation control (opt-in)
        companion_group = QGroupBox("Companion (monitor + shared workstation)")
        companion_layout = QFormLayout(companion_group)

        self.companion_enabled_check = QCheckBox(
            "Enable companion HTTP server (phone / LAN / shared UI)"
        )
        self.companion_enabled_check.setToolTip(
            "When on, HandForge serves a mobile/desktop web UI with live queue "
            "status and shared-workstation controls (start/stop, add/remove jobs, "
            "output/preset). Off by default. Prefer localhost; LAN bind and all "
            "control writes require a shared token."
        )
        self.companion_enabled_check.stateChanged.connect(
            lambda *_: self.refresh_companion_status()
        )
        companion_layout.addRow("", self.companion_enabled_check)

        self.companion_host_edit = QLineEdit()
        self.companion_host_edit.setPlaceholderText("127.0.0.1")
        self.companion_host_edit.setToolTip(
            "Bind address. Use 127.0.0.1 (default) for this machine only. "
            "Use 0.0.0.0 to allow other devices on your LAN (requires token)."
        )
        self.companion_host_edit.textChanged.connect(
            lambda *_: self.refresh_companion_status()
        )
        companion_layout.addRow("Bind host:", self.companion_host_edit)

        self.companion_port_spin = QSpinBox()
        self.companion_port_spin.setMinimum(1)
        self.companion_port_spin.setMaximum(65535)
        self.companion_port_spin.setToolTip("TCP port for the companion server")
        self.companion_port_spin.valueChanged.connect(
            lambda *_: self.refresh_companion_status()
        )
        companion_layout.addRow("Port:", self.companion_port_spin)

        token_row = QHBoxLayout()
        self.companion_token_edit = QLineEdit()
        self.companion_token_edit.setPlaceholderText("required for control; required for LAN")
        self.companion_token_edit.setToolTip(
            "Shared secret. Required for LAN binds and for all mutating control "
            "API calls (start/stop/add jobs). Pass as ?token=… or Authorization: Bearer."
        )
        self.companion_token_edit.textChanged.connect(
            lambda *_: self.refresh_companion_status()
        )
        token_row.addWidget(self.companion_token_edit)
        gen_token_btn = QPushButton("Generate")
        gen_token_btn.setToolTip("Generate a new random shared token")
        gen_token_btn.clicked.connect(self._generate_companion_token)
        token_row.addWidget(gen_token_btn)
        companion_layout.addRow("Token:", token_row)

        self.companion_status_label = QLabel("")
        self.companion_status_label.setWordWrap(True)
        self.companion_status_label.setStyleSheet("color: #666; font-size: 11px;")
        companion_layout.addRow("", self.companion_status_label)

        layout.addWidget(companion_group)
        
        layout.addStretch()
        return widget

    def _generate_companion_token(self) -> None:
        from ..companion.server import generate_token

        self.companion_token_edit.setText(generate_token())
        self.refresh_companion_status()
    
    def browse_output_dir(self):
        """Browse for output directory."""
        from ..util.cloud import default_browse_dir

        current_dir = (
            self.output_dir_edit.text()
            or default_browse_dir(self.settings)
            or self.get_default_output_dir()
        )
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

    def _cloud_roots_from_list(self) -> List[str]:
        roots: List[str] = []
        for i in range(self.cloud_roots_list.count()):
            item = self.cloud_roots_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole) or item.text()
            if path:
                roots.append(str(path))
        return roots

    def _set_cloud_roots_list(self, paths: List[str]) -> None:
        self.cloud_roots_list.clear()
        seen = set()
        for path in paths:
            if not path or path in seen:
                continue
            seen.add(path)
            item = QListWidgetItem(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.cloud_roots_list.addItem(item)

    def add_cloud_root(self):
        """Browse and add a cloud sync / mount folder."""
        from ..util.cloud import default_browse_dir

        start = default_browse_dir(self.settings)
        dir_path = QFileDialog.getExistingDirectory(
            self, "Add Cloud Root Folder", start
        )
        if dir_path:
            roots = self._cloud_roots_from_list()
            if dir_path not in roots:
                roots.append(dir_path)
                self._set_cloud_roots_list(roots)

    def remove_cloud_root(self):
        """Remove the selected cloud root."""
        row = self.cloud_roots_list.currentRow()
        if row >= 0:
            self.cloud_roots_list.takeItem(row)

    def detect_cloud_roots(self):
        """Merge detected sync client folders into the cloud roots list."""
        from ..util.cloud import detect_sync_mounts

        roots = self._cloud_roots_from_list()
        for mount in detect_sync_mounts():
            if mount.path not in roots:
                roots.append(mount.path)
        self._set_cloud_roots_list(roots)
        if not roots:
            QMessageBox.information(
                self,
                "Cloud Roots",
                "No Dropbox / Google Drive / OneDrive / Nextcloud folders were found.\n"
                "Add a synced folder manually, or install/configure rclone for remote:path.",
            )

    def use_cloud_root_as_output(self):
        """Set Conversion output directory to the selected cloud root."""
        item = self.cloud_roots_list.currentItem()
        if not item:
            QMessageBox.information(self, "Cloud Roots", "Select a cloud root first.")
            return
        path = item.data(Qt.ItemDataRole.UserRole) or item.text()
        self.output_dir_edit.setText(str(path))

    def use_cloud_root_as_input(self):
        """Set preferred browse start to the selected cloud root."""
        item = self.cloud_roots_list.currentItem()
        if not item:
            QMessageBox.information(self, "Cloud Roots", "Select a cloud root first.")
            return
        path = item.data(Qt.ItemDataRole.UserRole) or item.text()
        self.cloud_input_root_edit.setText(str(path))

    def refresh_rclone_status(self):
        """Update rclone availability and remote combo from the real CLI."""
        from ..util.cloud import find_rclone, list_rclone_remotes

        binary_override = self.rclone_binary_edit.text().strip() or None
        rclone = find_rclone(binary_override)
        current = self.rclone_remote_combo.currentText().strip()
        self.rclone_remote_combo.blockSignals(True)
        self.rclone_remote_combo.clear()
        self.rclone_remote_combo.addItem("")  # none
        if rclone:
            remotes = list_rclone_remotes(binary=binary_override)
            for name in remotes:
                bare = name.rstrip(":")
                self.rclone_remote_combo.addItem(bare)
            self.rclone_status_label.setText(
                f"rclone found: {rclone}"
                + (f" — {len(remotes)} remote(s)" if remotes else " — no remotes (run `rclone config`)")
            )
        else:
            self.rclone_status_label.setText(
                "rclone not found — install from https://rclone.org/install/ "
                "or use local sync folders above. Local workflows stay unchanged."
            )
        if current:
            idx = self.rclone_remote_combo.findText(current)
            if idx >= 0:
                self.rclone_remote_combo.setCurrentIndex(idx)
            else:
                self.rclone_remote_combo.setEditText(current)
        self.rclone_remote_combo.blockSignals(False)
    
    def load_settings(self):
        """Load settings into UI."""
        # General
        self.parallel_spin.setValue(self.settings.get("parallel", 2))
        self.adaptive_parallel_check.setChecked(
            self.settings.get("adaptive_parallel", True)
        )
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
        self.eq_enabled_check.setChecked(self.settings.get("eq_enabled", False))
        self.eq_bass_spin.setValue(self.settings.get("eq_bass", 0.0))
        self.eq_mid_spin.setValue(self.settings.get("eq_mid", 0.0))
        self.eq_treble_spin.setValue(self.settings.get("eq_treble", 0.0))
        self.compressor_enabled_check.setChecked(
            self.settings.get("compressor_enabled", False)
        )
        self.compressor_threshold_spin.setValue(
            self.settings.get("compressor_threshold", 0.125)
        )
        self.compressor_ratio_spin.setValue(self.settings.get("compressor_ratio", 4.0))
        self.compressor_attack_spin.setValue(
            self.settings.get("compressor_attack", 20.0)
        )
        self.compressor_release_spin.setValue(
            self.settings.get("compressor_release", 250.0)
        )
        self.compressor_makeup_spin.setValue(
            self.settings.get("compressor_makeup", 2.0)
        )
        self.limiter_enabled_check.setChecked(
            self.settings.get("limiter_enabled", False)
        )
        self.limiter_limit_spin.setValue(self.settings.get("limiter_limit", 0.95))
        self.limiter_attack_spin.setValue(self.settings.get("limiter_attack", 5.0))
        self.limiter_release_spin.setValue(self.settings.get("limiter_release", 50.0))
        self.denoise_enabled_check.setChecked(
            self.settings.get("denoise_enabled", False)
        )
        self.denoise_nr_spin.setValue(self.settings.get("denoise_nr", 12.0))
        self.denoise_nf_spin.setValue(self.settings.get("denoise_nf", -50.0))
        self.denoise_track_noise_check.setChecked(
            self.settings.get("denoise_track_noise", True)
        )
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

        hw_pref = self.settings.get("hw_accel", "auto")
        hw_index = next(
            (i for i, (_label, value) in enumerate(self._hw_accel_choices) if value == hw_pref),
            0,
        )
        self.hw_accel_combo.setCurrentIndex(hw_index)
        self.refresh_hw_accel_status(probe=False)
        
        self.default_reduction_factor_spin.setValue(self.settings.get("default_reduction_factor", 7.0))
        self.default_two_pass_check.setChecked(self.settings.get("default_two_pass", False))

        self.video_color_enabled_check.setChecked(
            self.settings.get("video_color_enabled", False)
        )
        self.video_brightness_spin.setValue(self.settings.get("video_brightness", 0.0))
        self.video_contrast_spin.setValue(self.settings.get("video_contrast", 1.0))
        self.video_saturation_spin.setValue(self.settings.get("video_saturation", 1.0))
        self.video_stabilize_enabled_check.setChecked(
            self.settings.get("video_stabilize_enabled", False)
        )
        self.video_stabilize_rx_spin.setValue(self.settings.get("video_stabilize_rx", 16))
        self.video_stabilize_ry_spin.setValue(self.settings.get("video_stabilize_ry", 16))
        edge = self.settings.get("video_stabilize_edge", "mirror")
        edge_index = self.video_stabilize_edge_combo.findText(edge)
        if edge_index >= 0:
            self.video_stabilize_edge_combo.setCurrentIndex(edge_index)

        # Cloud
        self._set_cloud_roots_list(list(self.settings.get("cloud_roots") or []))
        input_root = self.settings.get("cloud_input_root") or ""
        self.cloud_input_root_edit.setText(str(input_root) if input_root else "")
        self.rclone_enabled_check.setChecked(
            bool(self.settings.get("rclone_enabled", True))
        )
        self.rclone_binary_edit.setText(str(self.settings.get("rclone_binary") or ""))
        self.refresh_rclone_status()
        remote = str(self.settings.get("rclone_remote") or "").strip()
        if remote:
            idx = self.rclone_remote_combo.findText(remote.rstrip(":"))
            if idx >= 0:
                self.rclone_remote_combo.setCurrentIndex(idx)
            else:
                self.rclone_remote_combo.setEditText(remote.rstrip(":"))
        
        # Advanced
        self.auto_retry_check.setChecked(self.settings.get("auto_retry_enabled", True))
        self.ewma_alpha_spin.setValue(self.settings.get("ewma_alpha", 0.3))
        self.performance_analytics_check.setChecked(
            bool(self.settings.get("performance_analytics", False))
        )
        self.refresh_analytics_status()
        self.companion_enabled_check.setChecked(
            bool(self.settings.get("companion_enabled", False))
        )
        self.companion_host_edit.setText(
            str(self.settings.get("companion_host") or "127.0.0.1")
        )
        try:
            self.companion_port_spin.setValue(
                int(self.settings.get("companion_port") or 8765)
            )
        except (TypeError, ValueError):
            self.companion_port_spin.setValue(8765)
        self.companion_token_edit.setText(
            str(self.settings.get("companion_token") or "")
        )
        self.refresh_companion_status()
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from UI."""
        settings = self.settings.copy()
        
        # General
        settings["parallel"] = self.parallel_spin.value()
        settings["adaptive_parallel"] = self.adaptive_parallel_check.isChecked()
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
        settings["eq_enabled"] = self.eq_enabled_check.isChecked()
        settings["eq_bass"] = self.eq_bass_spin.value()
        settings["eq_mid"] = self.eq_mid_spin.value()
        settings["eq_treble"] = self.eq_treble_spin.value()
        settings["compressor_enabled"] = self.compressor_enabled_check.isChecked()
        settings["compressor_threshold"] = self.compressor_threshold_spin.value()
        settings["compressor_ratio"] = self.compressor_ratio_spin.value()
        settings["compressor_attack"] = self.compressor_attack_spin.value()
        settings["compressor_release"] = self.compressor_release_spin.value()
        settings["compressor_makeup"] = self.compressor_makeup_spin.value()
        settings["limiter_enabled"] = self.limiter_enabled_check.isChecked()
        settings["limiter_limit"] = self.limiter_limit_spin.value()
        settings["limiter_attack"] = self.limiter_attack_spin.value()
        settings["limiter_release"] = self.limiter_release_spin.value()
        settings["denoise_enabled"] = self.denoise_enabled_check.isChecked()
        settings["denoise_nr"] = self.denoise_nr_spin.value()
        settings["denoise_nf"] = self.denoise_nf_spin.value()
        settings["denoise_track_noise"] = self.denoise_track_noise_check.isChecked()
        settings["prefer_external_cover"] = self.prefer_external_cover_check.isChecked()
        
        # Video
        settings["default_video_quality"] = self.default_video_quality_combo.currentText()
        settings["default_video_codec"] = self.default_video_codec_combo.currentText()
        hw_idx = self.hw_accel_combo.currentIndex()
        if 0 <= hw_idx < len(self._hw_accel_choices):
            settings["hw_accel"] = self._hw_accel_choices[hw_idx][1]
        else:
            settings["hw_accel"] = "auto"
        settings["default_reduction_factor"] = self.default_reduction_factor_spin.value()
        settings["default_two_pass"] = self.default_two_pass_check.isChecked()
        settings["video_color_enabled"] = self.video_color_enabled_check.isChecked()
        settings["video_brightness"] = self.video_brightness_spin.value()
        settings["video_contrast"] = self.video_contrast_spin.value()
        settings["video_saturation"] = self.video_saturation_spin.value()
        settings["video_stabilize_enabled"] = (
            self.video_stabilize_enabled_check.isChecked()
        )
        settings["video_stabilize_rx"] = self.video_stabilize_rx_spin.value()
        settings["video_stabilize_ry"] = self.video_stabilize_ry_spin.value()
        settings["video_stabilize_edge"] = self.video_stabilize_edge_combo.currentText()

        # Cloud
        settings["cloud_roots"] = self._cloud_roots_from_list()
        input_root = self.cloud_input_root_edit.text().strip()
        settings["cloud_input_root"] = input_root or None
        settings["rclone_enabled"] = self.rclone_enabled_check.isChecked()
        settings["rclone_binary"] = self.rclone_binary_edit.text().strip()
        settings["rclone_remote"] = self.rclone_remote_combo.currentText().strip()
        
        # Advanced
        settings["auto_retry_enabled"] = self.auto_retry_check.isChecked()
        settings["ewma_alpha"] = self.ewma_alpha_spin.value()
        settings["performance_analytics"] = self.performance_analytics_check.isChecked()
        settings["companion_enabled"] = self.companion_enabled_check.isChecked()
        host = self.companion_host_edit.text().strip() or "127.0.0.1"
        settings["companion_host"] = host
        settings["companion_port"] = int(self.companion_port_spin.value())
        token = self.companion_token_edit.text().strip()
        # Auto-mint when enabling companion without a token (control writes need one)
        from ..companion.server import generate_token

        if settings["companion_enabled"] and not token:
            token = generate_token()
            self.companion_token_edit.setText(token)
        settings["companion_token"] = token
        
        return settings

    def refresh_analytics_status(self) -> None:
        """Update the local-only analytics status label."""
        try:
            from ..util.analytics import format_analytics_status

            probe = dict(self.settings)
            probe["performance_analytics"] = self.performance_analytics_check.isChecked()
            self.analytics_status_label.setText(format_analytics_status(probe))
        except Exception:
            self.analytics_status_label.setText(
                "Performance analytics: LOCAL ONLY under ~/.handforge/analytics/"
            )

    def refresh_companion_status(self) -> None:
        """Update companion bind / URL hint label."""
        try:
            from ..companion.server import (
                companion_url,
                format_companion_status,
                is_loopback_host,
                resolve_companion_bind,
            )

            probe = dict(self.settings)
            probe["companion_enabled"] = self.companion_enabled_check.isChecked()
            probe["companion_host"] = self.companion_host_edit.text().strip() or "127.0.0.1"
            probe["companion_port"] = int(self.companion_port_spin.value())
            probe["companion_token"] = self.companion_token_edit.text().strip()
            host, port, token = resolve_companion_bind(probe)
            lines = format_companion_status(probe).splitlines()
            if probe["companion_enabled"]:
                lines.append(f"  URL: {companion_url(host, port, token)}")
            if not is_loopback_host(host):
                lines.append(
                    "  LAN exposure: anyone on the network with the token can "
                    "see queue filenames. Keep the token private."
                )
            self.companion_status_label.setText("\n".join(lines))
        except Exception:
            self.companion_status_label.setText(
                "Companion: opt-in HTTP status API + mobile web UI (default off / localhost)."
            )
    
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
                "adaptive_parallel": True,
                "dup_handling": "Overwrite",
                "delete_original": False,
                "minimize_to_tray": True,
                "codec_threads": {"mp3": 1, "aac": 1, "flac": 1},
                "normalize_lufs": False,
                "target_lufs": -14.0,
                "eq_enabled": False,
                "eq_bass": 0.0,
                "eq_mid": 0.0,
                "eq_treble": 0.0,
                "compressor_enabled": False,
                "compressor_threshold": 0.125,
                "compressor_ratio": 4.0,
                "compressor_attack": 20.0,
                "compressor_release": 250.0,
                "compressor_makeup": 2.0,
                "limiter_enabled": False,
                "limiter_limit": 0.95,
                "limiter_attack": 5.0,
                "limiter_release": 50.0,
                "denoise_enabled": False,
                "denoise_nr": 12.0,
                "denoise_nf": -50.0,
                "denoise_track_noise": True,
                "prefer_external_cover": False,
                "default_video_quality": "medium",
                "default_video_codec": "libx264",
                "hw_accel": "auto",
                "default_reduction_factor": 7.0,
                "default_two_pass": False,
                "video_color_enabled": False,
                "video_brightness": 0.0,
                "video_contrast": 1.0,
                "video_saturation": 1.0,
                "video_stabilize_enabled": False,
                "video_stabilize_rx": 16,
                "video_stabilize_ry": 16,
                "video_stabilize_edge": "mirror",
                "auto_retry_enabled": True,
                "ewma_alpha": 0.3,
                "performance_analytics": False,
                "companion_enabled": False,
                "companion_host": "127.0.0.1",
                "companion_port": 8765,
                "companion_token": "",
                "cloud_roots": [],
                "cloud_input_root": None,
                "rclone_enabled": True,
                "rclone_remote": "",
                "rclone_binary": "",
            }
            self.load_settings()

    def refresh_hw_accel_status(self, probe: bool = True):
        """Update the hardware encoder status label (optionally probing FFmpeg)."""
        try:
            from ..util.hwaccel import detect_available_backends, format_detection_report

            info = detect_available_backends(probe=bool(probe), force_refresh=bool(probe))
            available = [
                name
                for name, ok in (info.get("backends") or {}).items()
                if ok
            ]
            if available:
                summary = "Detected: " + ", ".join(available)
            else:
                summary = "No working hardware encoders detected (software will be used)."
            if not probe:
                summary += " Click Detect for a live FFmpeg probe."
            self.hw_accel_status.setText(summary)
            self.hw_accel_status.setToolTip(format_detection_report(info))
        except Exception as exc:
            self.hw_accel_status.setText(f"Detection unavailable: {exc}")
    
    def accept(self):
        """Save settings and close."""
        settings = self.get_settings()
        save_settings(settings)
        super().accept()

