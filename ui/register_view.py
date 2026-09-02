"""
Register View for KubuCashier - Minimalist Light Style.
Handles user registration with Name, Username, Password, Role, and Credential Token.
Includes Language Switcher, clean lighter typography, and NotificationBanner alerts.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QSpacerItem, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR, config
from auth.auth_service import auth_service
from ui.i18n import t, get_language, set_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class RegisterView(QWidget):
    """Clean Light Minimalist Registration View with NotificationBanner."""

    registration_successful = pyqtSignal(dict)
    switch_to_login = pyqtSignal()
    exit_requested = pyqtSignal()
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._password_visible = False
        self._token_visible = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(0)

        # Top Bar with Language Switcher and Exit Button
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.lang_btn = QPushButton(f"  {get_language().upper()}")
        self.lang_btn.setObjectName("LangButton")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setIcon(get_svg_icon("globe", ThemeColors.TEXT_MUTED, 14))
        self.lang_btn.setToolTip("Switch Language (English / Bahasa Indonesia)")
        self.lang_btn.clicked.connect(self._toggle_language)
        top_bar.addWidget(self.lang_btn)

        top_bar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

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
        content_layout.setSpacing(14)

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
        card_layout.setSpacing(14)

        # Notification Banner
        self.status_banner = NotificationBanner(self)
        card_layout.addWidget(self.status_banner)

        # 1. Enter Your Name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        self.name_label = QLabel(t("enter_name"))
        self.name_label.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("enter_name"))
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input)
        card_layout.addLayout(name_layout)

        # 2. Enter Your Username
        user_layout = QVBoxLayout()
        user_layout.setSpacing(4)
        self.user_label = QLabel(t("enter_username"))
        self.user_label.setObjectName("FieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t("enter_username"))
        user_layout.addWidget(self.user_label)
        user_layout.addWidget(self.username_input)
        card_layout.addLayout(user_layout)

        # 3. Enter Password
        pwd_layout = QVBoxLayout()
        pwd_layout.setSpacing(4)
        self.pwd_label = QLabel(t("enter_password"))
        self.pwd_label.setObjectName("FieldLabel")

        pwd_input_box = QHBoxLayout()
        pwd_input_box.setSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(t("enter_password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.toggle_pwd_btn = QPushButton()
        self.toggle_pwd_btn.setObjectName("IconButton")
        self.toggle_pwd_btn.setFixedSize(36, 36)
        self.toggle_pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)

        pwd_input_box.addWidget(self.password_input)
        pwd_input_box.addWidget(self.toggle_pwd_btn)
        pwd_layout.addWidget(self.pwd_label)
        pwd_layout.addLayout(pwd_input_box)
        card_layout.addLayout(pwd_layout)

        # 4. Enter Role (Admin / Cashier / Owner / Sales)
        role_layout = QVBoxLayout()
        role_layout.setSpacing(4)
        self.role_label = QLabel(t("enter_role"))
        self.role_label.setObjectName("FieldLabel")

        self.role_combo = QComboBox()
        for role in config.roles:
            self.role_combo.addItem(role)
        self.role_combo.setCurrentText("Cashier")

        role_layout.addWidget(self.role_label)
        role_layout.addWidget(self.role_combo)
        card_layout.addLayout(role_layout)

        # 5. Enter Credential Token
        token_layout = QVBoxLayout()
        token_layout.setSpacing(4)
        self.token_label = QLabel(t("enter_token"))
        self.token_label.setObjectName("FieldLabel")

        token_input_box = QHBoxLayout()
        token_input_box.setSpacing(6)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText(t("enter_token"))
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.returnPressed.connect(self._handle_register)

        self.toggle_token_btn = QPushButton()
        self.toggle_token_btn.setObjectName("IconButton")
        self.toggle_token_btn.setFixedSize(36, 36)
        self.toggle_token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)

        token_input_box.addWidget(self.token_input)
        token_input_box.addWidget(self.toggle_token_btn)
        token_layout.addWidget(self.token_label)
        token_layout.addLayout(token_input_box)
        card_layout.addLayout(token_layout)

        # Primary Action Button: REGISTER (Full width)
        self.register_btn = QPushButton(t("register_btn"))
        self.register_btn.setObjectName("PrimaryButton")
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_btn.setFixedHeight(40)
        self.register_btn.clicked.connect(self._handle_register)
        card_layout.addWidget(self.register_btn)

        # Divider between Button and Login Link
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        card_layout.addWidget(divider)

        # Bottom Card Footer: Centered Login Link
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.setSpacing(4)

        self.have_account_label = QLabel(t("have_account"))
        self.have_account_label.setObjectName("SubtitleLabel")
        self.have_account_label.setStyleSheet("font-size: 13px; color: #64748b;")

        self.login_link_btn = QPushButton(t("login_link"))
        self.login_link_btn.setObjectName("LinkButton")
        self.login_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_link_btn.clicked.connect(self._on_switch_to_login)

        footer_layout.addWidget(self.have_account_label)
        footer_layout.addWidget(self.login_link_btn)
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
        self.name_label.setText(t("enter_name"))
        self.name_input.setPlaceholderText(t("enter_name"))
        self.user_label.setText(t("enter_username"))
        self.username_input.setPlaceholderText(t("enter_username"))
        self.pwd_label.setText(t("enter_password"))
        self.password_input.setPlaceholderText(t("enter_password"))
        self.role_label.setText(t("enter_role"))
        self.token_label.setText(t("enter_token"))
        self.token_input.setPlaceholderText(t("enter_token"))
        self.register_btn.setText(t("register_btn"))
        self.have_account_label.setText(t("have_account"))
        self.login_link_btn.setText(t("login_link"))
        self.exit_btn.setToolTip(t("exit_app"))

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_MUTED, 16))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _toggle_token_visibility(self):
        self._token_visible = not self._token_visible
        if self._token_visible:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_MUTED, 16))
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _show_error(self, message: str):
        self.status_banner.show_error(message)

    def _show_success(self, message: str):
        self.status_banner.show_success(message)

    def clear_inputs(self):
        self.name_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.token_input.clear()
        self.role_combo.setCurrentIndex(0)
        self.status_banner.hide_banner()
        self._password_visible = False
        self._token_visible = False
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle_pwd_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _handle_register(self):
        name = self.name_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        role = self.role_combo.currentText()
        token = self.token_input.text()

        success, message, user = auth_service.register(name, username, password, role, token)
        if success:
            self._show_success(message)
            self.registration_successful.emit(user)
        else:
            self._show_error(message)

    def _on_switch_to_login(self):
        self.clear_inputs()
        self.switch_to_login.emit()
