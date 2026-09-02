"""
Custom Notification Banner Component for KubuCashier.
Provides toast-style alerts with icons, single-line clean layout, auto-dismiss timers, and close buttons.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

from ui.icons import get_svg_pixmap
from ui.theme import ThemeColors


class NotificationBanner(QFrame):
    """Clean single-line alert banner supporting Success, Error, Warning, and Info notifications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationBanner")
        self.setFixedHeight(38)
        self.setVisible(False)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_banner)

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Status Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # Message Text (Single-line, expands to fill available width)
        self.msg_label = QLabel()
        self.msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.msg_label.setStyleSheet("font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.msg_label.setWordWrap(False)
        layout.addWidget(self.msg_label)

        # Close / Dismiss Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                color: #0f172a;
            }
        """)
        self.close_btn.clicked.connect(self.hide_banner)
        layout.addWidget(self.close_btn)

    def show_success(self, message: str, auto_hide_ms: int = 4000):
        self.setStyleSheet("""
            QFrame#NotificationBanner {
                background-color: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 6px;
            }
        """)
        self.msg_label.setStyleSheet("color: #15803d; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.icon_label.setPixmap(get_svg_pixmap("check", "#16a34a", 14))
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def show_error(self, message: str, auto_hide_ms: int = 5000):
        self.setStyleSheet("""
            QFrame#NotificationBanner {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 6px;
            }
        """)
        self.msg_label.setStyleSheet("color: #b91c1c; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.icon_label.setPixmap(get_svg_pixmap("alert", "#ef4444", 14))
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def show_warning(self, message: str, auto_hide_ms: int = 4500):
        self.setStyleSheet("""
            QFrame#NotificationBanner {
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 6px;
            }
        """)
        self.msg_label.setStyleSheet("color: #b45309; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.icon_label.setPixmap(get_svg_pixmap("alert", "#d97706", 14))
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def show_info(self, message: str, auto_hide_ms: int = 4000):
        self.setStyleSheet("""
            QFrame#NotificationBanner {
                background-color: #f0f9ff;
                border: 1px solid #bae6fd;
                border-radius: 6px;
            }
        """)
        self.msg_label.setStyleSheet("color: #0369a1; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.icon_label.setPixmap(get_svg_pixmap("clock", "#0284c7", 14))
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._timer.start(auto_hide_ms)

    def text(self) -> str:
        """Returns the current message text."""
        return self.msg_label.text()

    def hide_banner(self):
        self._timer.stop()
        self.setVisible(False)
