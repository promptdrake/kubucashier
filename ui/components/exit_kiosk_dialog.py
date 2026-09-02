"""
Exit Kiosk Confirmation Dialog.
Prompts for system credential token before allowing application exit when in fullscreen mode.
Clean compact modal with right-aligned proportional action buttons.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config import config
from ui.i18n import t
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class ExitKioskDialog(QDialog):
    """Modal dialog asking for Credential Token before exiting fullscreen mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token_visible = False
        self.setWindowTitle(t("exit_kiosk_title"))
        self.setFixedSize(430, 240)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header with Lock Icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        lock_icon = QLabel()
        lock_icon.setPixmap(get_svg_pixmap("lock", "#0f172a", 22))

        header_text_box = QVBoxLayout()
        header_text_box.setSpacing(2)

        title_lbl = QLabel(t("exit_kiosk_title"))
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #0f172a;")

        desc_lbl = QLabel(t("exit_kiosk_msg"))
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        desc_lbl.setWordWrap(True)

        header_text_box.addWidget(title_lbl)
        header_text_box.addWidget(desc_lbl)

        header_layout.addWidget(lock_icon)
        header_layout.addLayout(header_text_box)
        header_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        layout.addLayout(header_layout)

        # Error Banner
        self.status_banner = NotificationBanner(self)
        layout.addWidget(self.status_banner)

        # Token Input Field
        token_box = QHBoxLayout()
        token_box.setSpacing(6)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText(t("enter_token"))
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setFixedHeight(36)
        self.token_input.returnPressed.connect(self._verify_and_exit)

        self.toggle_token_btn = QPushButton()
        self.toggle_token_btn.setObjectName("IconButton")
        self.toggle_token_btn.setFixedSize(36, 36)
        self.toggle_token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)

        token_box.addWidget(self.token_input)
        token_box.addWidget(self.toggle_token_btn)
        layout.addLayout(token_box)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Right-Aligned Action Buttons Row with Natural Spacing
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self.reject)

        self.exit_btn = QPushButton(t("confirm_exit_btn"))
        self.exit_btn.setObjectName("PrimaryButton")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setFixedHeight(36)
        self.exit_btn.clicked.connect(self._verify_and_exit)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.exit_btn)
        layout.addLayout(btn_row)

    def _toggle_token_visibility(self):
        self._token_visible = not self._token_visible
        if self._token_visible:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_MUTED, 16))
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _verify_and_exit(self):
        entered = self.token_input.text().strip()
        required = config.credential_token

        if entered == required:
            self.accept()
        else:
            self.status_banner.show_error(t("invalid_token"))
            self.token_input.selectAll()
            self.token_input.setFocus()
