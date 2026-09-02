"""
Login View for KubuCashier - Minimalist Light Style.
Handles user authentication, Language Switching, and navigation.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR, config
from auth.auth_service import auth_service
from ui.i18n import t, get_language, set_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class LoginView(QWidget):
    """Clean Light Minimalist Login View with NotificationBanner and Language Switcher."""

    login_successful = pyqtSignal(dict)
    switch_to_register = pyqtSignal()
    exit_requested = pyqtSignal()
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._password_visible = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(0)

        # Top Bar with Language Switcher and Exit Button
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # Language Switcher Toggle
        self.lang_btn = QPushButton(f"  {get_language().upper()}")
        self.lang_btn.setObjectName("LangButton")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setIcon(get_svg_icon("globe", ThemeColors.TEXT_MUTED, 14))
        self.lang_btn.setToolTip("Switch Language (English / Bahasa Indonesia)")
        self.lang_btn.clicked.connect(self._toggle_language)
        top_bar.addWidget(self.lang_btn)

        top_bar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Discrete Exit Button
        self.exit_btn = QPushButton()
        self.exit_btn.setObjectName("IconButton")
        self.exit_btn.setFixedSize(36, 36)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setToolTip(t("exit_app"))
        self.exit_btn.setIcon(get_svg_icon("power", ThemeColors.TEXT_MUTED, 18))
        self.exit_btn.clicked.connect(self.exit_requested.emit)
        top_bar.addWidget(self.exit_btn)
        main_layout.addLayout(top_bar)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        content_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        center_vbox = QVBoxLayout()
        center_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_vbox.setSpacing(16)

        # Centered Application Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        square_logo_path = ASSETS_DIR / "logo_square.png"
        if square_logo_path.exists():
            pixmap = QPixmap(str(square_logo_path))
            scaled_pixmap = pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setPixmap(get_svg_pixmap("cart", ThemeColors.TEXT_PRIMARY, 48))

        center_vbox.addWidget(self.logo_label)

        # Form Card
        self.card = QFrame()
        self.card.setObjectName("AuthCard")
        self.card.setFixedWidth(440)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(16)

        # Notification Banner
        self.status_banner = NotificationBanner(self)
        card_layout.addWidget(self.status_banner)

        # Username Field
        user_field_layout = QVBoxLayout()
        user_field_layout.setSpacing(4)
        self.user_label = QLabel(t("enter_username"))
        self.user_label.setObjectName("FieldLabel")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t("enter_username"))
        self.username_input.returnPressed.connect(self._handle_login)

        user_field_layout.addWidget(self.user_label)
        user_field_layout.addWidget(self.username_input)
        card_layout.addLayout(user_field_layout)

        # Password Field
        pass_field_layout = QVBoxLayout()
        pass_field_layout.setSpacing(4)
        self.pass_label = QLabel(t("enter_password"))
        self.pass_label.setObjectName("FieldLabel")

        pass_input_box = QHBoxLayout()
        pass_input_box.setSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(t("enter_password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._handle_login)

        self.toggle_pwd_btn = QPushButton()
        self.toggle_pwd_btn.setObjectName("IconButton")
        self.toggle_pwd_btn.setFixedSize(36, 36)
        self.toggle_pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)

        pass_input_box.addWidget(self.password_input)
        pass_input_box.addWidget(self.toggle_pwd_btn)

        pass_field_layout.addWidget(self.pass_label)
        pass_field_layout.addLayout(pass_input_box)
        card_layout.addLayout(pass_field_layout)

        # Primary Action Button: LOG IN (Full width)
        self.login_btn = QPushButton(t("login_btn"))
        self.login_btn.setObjectName("PrimaryButton")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setFixedHeight(40)
        self.login_btn.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_btn)

        # Divider between Button and Register Link
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        card_layout.addWidget(divider)

        # Bottom Card Footer: Centered Register Link
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.setSpacing(4)

        self.no_account_label = QLabel(t("no_account"))
        self.no_account_label.setObjectName("SubtitleLabel")
        self.no_account_label.setStyleSheet("font-size: 13px; color: #64748b;")

        self.register_link_btn = QPushButton(t("register_link"))
        self.register_link_btn.setObjectName("LinkButton")
        self.register_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_link_btn.clicked.connect(self._on_switch_to_register)

        footer_layout.addWidget(self.no_account_label)
        footer_layout.addWidget(self.register_link_btn)
        card_layout.addLayout(footer_layout)

        center_vbox.addWidget(self.card)
        content_layout.addLayout(center_vbox)
        content_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def _toggle_language(self):
        new_lang = "id" if get_language() == "en" else "en"
        config.set_language(new_lang, persist=True)
        self.lang_btn.setText(f"  {new_lang.upper()}")
        self._refresh_translations()
        self.language_changed.emit(new_lang)

    def _refresh_translations(self):
        self.user_label.setText(t("enter_username"))
        self.username_input.setPlaceholderText(t("enter_username"))
        self.pass_label.setText(t("enter_password"))
        self.password_input.setPlaceholderText(t("enter_password"))
        self.login_btn.setText(t("login_btn"))
        self.no_account_label.setText(t("no_account"))
        self.register_link_btn.setText(t("register_link"))
        self.exit_btn.setToolTip(t("exit_app"))

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_MUTED, 16))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _show_error(self, message: str):
        self.status_banner.show_error(message)

    def _show_success(self, message: str):
        self.status_banner.show_success(message)

    def clear_inputs(self):
        self.username_input.clear()
        self.password_input.clear()
        self.status_banner.hide_banner()
        self._password_visible = False
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        success, message, user = auth_service.login(username, password)
        if success:
            self._show_success(message)
            self.login_successful.emit(user)
        else:
            self._show_error(message)

    def _on_switch_to_register(self):
        self.clear_inputs()
        self.switch_to_register.emit()
