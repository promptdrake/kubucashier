"""
User Add / Edit Modal Dialog for KubuCashier.
Clean Black and White Minimalist Interface.
Allows Admin/Owner to configure staff name, role, and reset password.
"""

from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt

from config import config
from ui.i18n import t
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class UserDialog(QDialog):
    """Modal dialog for creating or updating a staff user account."""

    def __init__(self, parent=None, user_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_data = user_data
        self.is_edit = user_data is not None

        title = t("user_dialog_edit") if self.is_edit else t("user_dialog_add")
        self.setWindowTitle(title)
        self.setFixedSize(460, 480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._show_pwd = False
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(get_svg_pixmap("user", "#0f172a", 22))

        title_lbl = QLabel(t("user_dialog_edit") if self.is_edit else t("user_dialog_add"))
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_lbl)
        header_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(header_layout)

        # Status Alert Banner
        self.status_banner = NotificationBanner(self)
        layout.addWidget(self.status_banner)

        # 1. Full Name
        name_box = QVBoxLayout()
        name_box.setSpacing(3)
        name_lbl = QLabel(t("th_fullname"))
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("enter_name"))
        self.name_input.setFixedHeight(34)
        if self.is_edit and self.user_data:
            self.name_input.setText(self.user_data.get("name", ""))

        name_box.addWidget(name_lbl)
        name_box.addWidget(self.name_input)
        layout.addLayout(name_box)

        # 2. Username
        uname_box = QVBoxLayout()
        uname_box.setSpacing(3)
        uname_lbl = QLabel(t("th_username"))
        uname_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t("enter_username"))
        self.username_input.setFixedHeight(34)
        if self.is_edit and self.user_data:
            self.username_input.setText(self.user_data.get("username", ""))
            self.username_input.setEnabled(False)
            self.username_input.setStyleSheet("background-color: #f1f5f9; color: #64748b;")

        uname_box.addWidget(uname_lbl)
        uname_box.addWidget(self.username_input)
        layout.addLayout(uname_box)

        # 3. Role Dropdown
        role_box = QVBoxLayout()
        role_box.setSpacing(3)
        role_lbl = QLabel(t("th_role"))
        role_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.role_combo = QComboBox()
        self.role_combo.setFixedHeight(34)
        for r in config.roles:
            self.role_combo.addItem(r, r)

        if self.is_edit and self.user_data:
            curr_role = self.user_data.get("role", "Cashier")
            idx = self.role_combo.findData(curr_role)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)

        role_box.addWidget(role_lbl)
        role_box.addWidget(self.role_combo)
        layout.addLayout(role_box)

        # 4. Password Field
        pwd_box = QVBoxLayout()
        pwd_box.setSpacing(3)

        pwd_lbl = QLabel(t("new_password_label") if self.is_edit else t("enter_password"))
        pwd_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        pwd_input_row = QHBoxLayout()
        pwd_input_row.setSpacing(6)

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText(t("enter_password"))
        self.pwd_input.setFixedHeight(34)

        self.toggle_pwd_btn = QPushButton()
        self.toggle_pwd_btn.setObjectName("IconButton")
        self.toggle_pwd_btn.setFixedSize(34, 34)
        self.toggle_pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)

        pwd_input_row.addWidget(self.pwd_input, stretch=1)
        pwd_input_row.addWidget(self.toggle_pwd_btn)

        pwd_box.addWidget(pwd_lbl)
        pwd_box.addLayout(pwd_input_row)

        if self.is_edit:
            help_lbl = QLabel(t("new_password_help"))
            help_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            pwd_box.addWidget(help_lbl)

        layout.addLayout(pwd_box)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(t("save"))
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(34)
        self.save_btn.clicked.connect(self._validate_and_save)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _toggle_password_visibility(self):
        self._show_pwd = not self._show_pwd
        if self._show_pwd:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_PRIMARY, 16))
        else:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def get_user_values(self) -> Dict[str, Any]:
        return {
            "name": self.name_input.text().strip(),
            "username": self.username_input.text().strip().lower(),
            "role": self.role_combo.currentData(),
            "password": self.pwd_input.text().strip()
        }

    def _validate_and_save(self):
        name = self.name_input.text().strip()
        username = self.username_input.text().strip()
        pwd = self.pwd_input.text().strip()

        if not name:
            self.status_banner.show_error("Please enter full name.")
            self.name_input.setFocus()
            return

        if not self.is_edit:
            if not username or len(username) < 3:
                self.status_banner.show_error("Username must be at least 3 characters.")
                self.username_input.setFocus()
                return

            if not pwd or len(pwd) < 4:
                self.status_banner.show_error("Password must be at least 4 characters.")
                self.pwd_input.setFocus()
                return
        else:
            if pwd and len(pwd) < 4:
                self.status_banner.show_error("New password must be at least 4 characters.")
                self.pwd_input.setFocus()
                return

        self.accept()
