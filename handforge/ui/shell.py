"""Sidebar library chrome and stage transitions for the HandForge desktop shell."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QParallelAnimationGroup,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .theme import brand_font


NavItem = Tuple[str, str, str]  # id, label, tip


class _IndicatorBar(QFrame):
    """Animated accent rail that tracks the active sidebar row."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("hfNavIndicator")
        self.setFixedWidth(3)
        self.setStyleSheet(
            "QFrame#hfNavIndicator {"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "stop:0 #e9a84f, stop:1 #d4893a);"
            "border-radius: 2px;"
            "}"
        )
        self._y = 0.0
        self._h = 36.0
        self._anim: Optional[QPropertyAnimation] = None

    def getY(self) -> float:
        return self._y

    def setY(self, value: float) -> None:
        self._y = value
        self.move(0, int(value))

    yPos = pyqtProperty(float, getY, setY)

    def slide_to(self, y: int, height: int, duration_ms: int = 220) -> None:
        self.setFixedHeight(max(height, 24))
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(self, b"yPos", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(float(self._y))
        anim.setEndValue(float(y))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim = anim
        anim.start()


class SidebarNav(QWidget):
    """Brand-first sidebar with section navigation."""

    section_changed = pyqtSignal(str)

    def __init__(
        self,
        items: List[NavItem],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("hfSidebar")
        self.setFixedWidth(216)
        self._buttons: Dict[str, QPushButton] = {}
        self._order: List[str] = []
        self._active = items[0][0] if items else ""

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 18, 14, 16)
        root.setSpacing(6)

        brand = QLabel("HandForge")
        brand.setObjectName("hfBrandMark")
        brand.setFont(brand_font(20))
        root.addWidget(brand)

        tag = QLabel("MEDIA CONVERTER")
        tag.setObjectName("hfBrandTag")
        root.addWidget(tag)

        nav_host = QWidget()
        nav_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._nav_layout = QVBoxLayout(nav_host)
        self._nav_layout.setContentsMargins(8, 8, 0, 0)
        self._nav_layout.setSpacing(4)

        self._indicator = _IndicatorBar(nav_host)
        self._indicator.raise_()

        for nav_id, label, tip in items:
            btn = QPushButton(label)
            btn.setObjectName("hfNavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setProperty("hfActive", "false")
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _=False, i=nav_id: self.set_section(i, animate=True))
            self._nav_layout.addWidget(btn)
            self._buttons[nav_id] = btn
            self._order.append(nav_id)

        self._nav_layout.addStretch(1)
        root.addWidget(nav_host, 1)

        foot = QLabel("VoxHash Technologies")
        foot.setStyleSheet("color: rgba(139, 154, 171, 160); font-size: 10px;")
        root.addWidget(foot)

        if self._active:
            self.set_section(self._active, animate=False)

    def set_section(self, section_id: str, *, animate: bool = True) -> None:
        if section_id not in self._buttons:
            return
        self._active = section_id
        for nid, btn in self._buttons.items():
            active = nid == section_id
            btn.setProperty("hfActive", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            if active:
                # Geometry relative to nav_host
                pos = btn.mapTo(self._indicator.parentWidget(), btn.rect().topLeft())
                target_y = pos.y() + 4
                height = btn.height() - 8
                if animate:
                    self._indicator.slide_to(target_y, height)
                else:
                    self._indicator.setFixedHeight(max(height, 24))
                    self._indicator.setY(float(target_y))
        self.section_changed.emit(section_id)

    def current_section(self) -> str:
        return self._active


class StageStack(QStackedWidget):
    """Stacked main stage with short cross-fade on page change."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._fade_group: Optional[QParallelAnimationGroup] = None
        self._effects: Dict[int, QGraphicsOpacityEffect] = {}

    def _ensure_effect(self, index: int) -> QGraphicsOpacityEffect:
        w = self.widget(index)
        if index not in self._effects:
            effect = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(effect)
            self._effects[index] = effect
        return self._effects[index]

    def fade_to(self, index: int, duration_ms: int = 180) -> None:
        if index == self.currentIndex() or index < 0 or index >= self.count():
            return
        if self._fade_group is not None:
            self._fade_group.stop()

        outgoing = self.currentIndex()
        out_fx = self._ensure_effect(outgoing)
        in_fx = self._ensure_effect(index)
        in_fx.setOpacity(0.0)
        self.setCurrentIndex(index)

        fade_out = QPropertyAnimation(out_fx, b"opacity")
        fade_out.setDuration(duration_ms)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.35)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        fade_in = QPropertyAnimation(in_fx, b"opacity")
        fade_in.setDuration(duration_ms)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade_out)
        group.addAnimation(fade_in)

        def _cleanup() -> None:
            out_fx.setOpacity(1.0)
            in_fx.setOpacity(1.0)

        group.finished.connect(_cleanup)
        self._fade_group = group
        group.start()


def wrap_stage_header(title: str, subtitle: str, body: QWidget) -> QWidget:
    """Title + calm subtitle above a dense content region."""
    page = QWidget()
    page.setObjectName("hfStagePage")
    page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)

    head = QVBoxLayout()
    head.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("hfStageTitle")
    s = QLabel(subtitle)
    s.setObjectName("hfStageSub")
    s.setWordWrap(True)
    head.addWidget(t)
    head.addWidget(s)
    layout.addLayout(head)

    # Scroll so Convert / Library reflow at compact heights and widths
    # without locking the main window to a large fixed footprint.
    scroll = QScrollArea()
    scroll.setObjectName("hfStageScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    scroll.setWidget(body)
    layout.addWidget(scroll, 1)
    return page


def pulse_widget(widget: QWidget, *, scale_peak: float = 1.04, duration_ms: int = 280) -> None:
    """Brief emphasis pulse (used on Start Conversion)."""
    # Geometry pulse via maximumWidth wobble is fragile; use opacity instead.
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setKeyValueAt(0.0, 1.0)
    anim.setKeyValueAt(0.45, 0.72)
    anim.setKeyValueAt(1.0, 1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    # Keep a reference so GC does not kill the animation mid-flight.
    widget._hf_pulse_anim = anim  # type: ignore[attr-defined]
    anim.start()


def build_shell(
    sidebar: SidebarNav,
    stage: QWidget,
    parent: Optional[QWidget] = None,
) -> QWidget:
    """Compose sidebar + main stage into one shell root."""
    root = QWidget(parent)
    root.setObjectName("hfShellRoot")
    root.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    row = QHBoxLayout(root)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addWidget(sidebar, 0)
    row.addWidget(stage, 1)
    return root
