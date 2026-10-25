"""HandForge desktop visual system — forge charcoal + copper, expressive type."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

# Cool ink slate + forge copper (not violet glow, not cream/terracotta broadsheet).
COLORS = {
    "ink": "#0b1017",
    "ink_mid": "#121a24",
    "panel": "#161f2b",
    "panel_raised": "#1c2736",
    "line": "rgba(140, 170, 190, 48)",
    "text": "#e8eef4",
    "muted": "#8b9aab",
    "accent": "#d4893a",
    "accent_hot": "#e9a84f",
    "accent_dim": "rgba(212, 137, 58, 55)",
    "teal": "#3a9aaa",
    "ok": "#5cb88a",
    "warn": "#d4a04a",
    "err": "#d46b6b",
}

FONT_FAMILY = "Manrope"
_FONT_LOADED = False
_FONT_FAMILY_RESOLVED = FONT_FAMILY


def resources_fonts_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "fonts"


def load_application_fonts() -> Tuple[bool, str]:
    """Register bundled Manrope. Returns (ok, family_or_fallback).

    Requires a living ``QApplication`` (Qt font DB is unsafe beforehand).
    """
    global _FONT_LOADED, _FONT_FAMILY_RESOLVED
    if _FONT_LOADED:
        return True, _FONT_FAMILY_RESOLVED

    if QApplication.instance() is None:
        return False, "Sans Serif"

    fonts_dir = resources_fonts_dir()
    candidates = list(fonts_dir.glob("Manrope*.ttf")) + list(fonts_dir.glob("Manrope*.otf"))
    if not candidates:
        return False, "Sans Serif"

    for path in candidates:
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(fid)
        if families:
            _FONT_LOADED = True
            _FONT_FAMILY_RESOLVED = families[0]
            return True, _FONT_FAMILY_RESOLVED

    return False, "Sans Serif"


def application_font(point_size: int = 10, weight: int = QFont.Weight.Normal) -> QFont:
    ok, family = load_application_fonts()
    font = QFont(family if ok else "Sans Serif", point_size)
    font.setWeight(weight)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


def brand_font(point_size: int = 18) -> QFont:
    return application_font(point_size, QFont.Weight.DemiBold)


def app_stylesheet(font_family: Optional[str] = None) -> str:
    """Full-window QSS for the modern media desktop shell."""
    fam = font_family or FONT_FAMILY
    c = COLORS
    return f"""
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {c['ink']}, stop:0.45 {c['ink_mid']}, stop:1 #0e1620);
        color: {c['text']};
        font-family: "{fam}";
        font-size: 13px;
    }}
    QWidget {{
        background: transparent;
        color: {c['text']};
        font-family: "{fam}";
    }}
    QWidget#hfShellRoot {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {c['ink_mid']}, stop:1 {c['ink']});
    }}
    QWidget#hfSidebar {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0e1520, stop:0.55 #121c28, stop:1 #0f1822);
        border-right: 1px solid {c['line']};
    }}
    QLabel#hfBrandMark {{
        color: {c['text']};
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.6px;
        padding: 4px 0 2px 0;
    }}
    QLabel#hfBrandTag {{
        color: {c['muted']};
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.4px;
        padding-bottom: 10px;
    }}
    QPushButton#hfNavBtn {{
        background: transparent;
        border: none;
        border-radius: 10px;
        color: {c['muted']};
        text-align: left;
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 560;
    }}
    QPushButton#hfNavBtn:hover {{
        background: rgba(255, 255, 255, 18);
        color: {c['text']};
    }}
    QPushButton#hfNavBtn[hfActive="true"] {{
        background: {c['accent_dim']};
        color: {c['accent_hot']};
        border: 1px solid rgba(232, 168, 79, 70);
    }}
    QFrame#hfStageCard {{
        background: rgba(22, 31, 43, 210);
        border: 1px solid {c['line']};
        border-radius: 14px;
    }}
    QLabel#hfStageTitle {{
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: {c['text']};
    }}
    QLabel#hfStageSub {{
        color: {c['muted']};
        font-size: 12px;
    }}
    QTableWidget {{
        background: rgba(14, 20, 30, 180);
        border: 1px solid {c['line']};
        border-radius: 12px;
        color: {c['text']};
        gridline-color: rgba(120, 150, 170, 28);
        selection-background-color: rgba(212, 137, 58, 90);
        outline: none;
    }}
    QTableWidget::item {{
        background: transparent;
        padding: 6px 8px;
    }}
    QTableWidget::item:selected {{
        background: rgba(212, 137, 58, 100);
        border-radius: 4px;
    }}
    QTableWidget::item:hover {{
        background: rgba(255, 255, 255, 16);
    }}
    QHeaderView::section {{
        background: rgba(28, 39, 54, 230);
        border: none;
        border-bottom: 1px solid {c['line']};
        padding: 9px 10px;
        font-weight: 650;
        color: {c['muted']};
    }}
    QPushButton {{
        background: rgba(255, 255, 255, 16);
        border: 1px solid {c['line']};
        border-radius: 10px;
        padding: 8px 16px;
        color: {c['text']};
        font-weight: 560;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: rgba(255, 255, 255, 26);
        border-color: rgba(180, 200, 220, 90);
    }}
    QPushButton:pressed {{
        background: rgba(0, 0, 0, 40);
    }}
    QPushButton#hfPrimary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['accent']}, stop:1 {c['accent_hot']});
        border: 1px solid rgba(233, 168, 79, 120);
        color: #1a1208;
        font-weight: 700;
    }}
    QPushButton#hfPrimary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['accent_hot']}, stop:1 #f0bc6a);
    }}
    QPushButton#hfPrimary:disabled {{
        background: rgba(255, 255, 255, 12);
        color: {c['muted']};
        border-color: {c['line']};
    }}
    QPushButton#hfDanger {{
        background: rgba(212, 107, 107, 40);
        border: 1px solid rgba(212, 107, 107, 90);
        color: #f0c8c8;
    }}
    QComboBox {{
        background: rgba(14, 20, 30, 200);
        border: 1px solid {c['line']};
        border-radius: 10px;
        padding: 6px 12px;
        color: {c['text']};
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: rgba(212, 137, 58, 120);
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['panel_raised']};
        border: 1px solid {c['line']};
        border-radius: 8px;
        selection-background-color: rgba(212, 137, 58, 110);
        color: {c['text']};
        outline: none;
    }}
    QLabel {{
        background: transparent;
        color: {c['text']};
    }}
    QMenuBar {{
        background: rgba(11, 16, 23, 220);
        border-bottom: 1px solid {c['line']};
        color: {c['text']};
        padding: 2px 6px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 8px 12px;
        border-radius: 6px;
    }}
    QMenuBar::item:selected {{
        background: rgba(255, 255, 255, 18);
    }}
    QMenu {{
        background: {c['panel_raised']};
        border: 1px solid {c['line']};
        border-radius: 10px;
        color: {c['text']};
        padding: 6px;
    }}
    QMenu::item {{
        padding: 8px 24px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: rgba(212, 137, 58, 100);
    }}
    QStatusBar {{
        background: rgba(11, 16, 23, 230);
        border-top: 1px solid {c['line']};
        color: {c['muted']};
        padding: 4px 8px;
        font-size: 11px;
    }}
    QSplitter::handle {{
        background: rgba(140, 170, 190, 40);
    }}
    QSplitter::handle:horizontal {{
        width: 3px;
    }}
    QSplitter::handle:vertical {{
        height: 3px;
    }}
    QGroupBox {{
        border: 1px solid {c['line']};
        border-radius: 12px;
        margin-top: 14px;
        padding-top: 14px;
        font-weight: 650;
        font-size: 12px;
        color: {c['muted']};
        background: rgba(22, 31, 43, 120);
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: {c['accent_hot']};
    }}
    QCheckBox {{
        color: {c['text']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid rgba(140, 170, 190, 90);
        border-radius: 5px;
        background: rgba(14, 20, 30, 180);
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent_hot']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['accent_hot']};
    }}
    QCheckBox:disabled {{
        color: {c['muted']};
    }}
    QProgressBar {{
        border: 1px solid {c['line']};
        border-radius: 6px;
        background: rgba(14, 20, 30, 200);
        text-align: center;
        color: {c['text']};
        min-height: 16px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['teal']}, stop:1 {c['accent']});
        border-radius: 5px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(140, 170, 190, 70);
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QToolTip {{
        background: {c['panel_raised']};
        color: {c['text']};
        border: 1px solid {c['line']};
        padding: 6px 8px;
        border-radius: 6px;
    }}
    """
