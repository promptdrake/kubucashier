"""
Welcome / Dashboard View for KubuCashier.
Features:
- Left Sidebar with dynamic logo, POS Register, Products Management (Admin/Owner), User Management (Admin/Owner), and Universal Settings navigation
- Top Navbar with live Asia/Jakarta (WIB) clock in ID/EN format, language switcher, zoom controls, user popup menu, and exit button
- Touch-Friendly POS Register (Page 0)
- Universal Settings Page (Page 1)
- Products & Categories Management Page (Page 2, Admin/Owner)
- User Management Page (Page 3, Admin/Owner)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QSpacerItem, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR, config, is_admin_or_owner
from ui.i18n import t, get_language, set_language
from ui.datetime_utils import get_jakarta_now, get_greeting, get_formatted_clock, ID_DAYS, ID_MONTHS
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.settings_view import SettingsView
from ui.products_view import ProductsView
from ui.users_view import UsersView
from ui.reports_view import ReportsView
from ui.ratings_view import CashierRatingsView
from ui.dashboard_pos_view import DashboardPOSView


class UserProfilePopup(QFrame):
    """Clean user dropdown popup menu."""

    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("ProfileCard")
        self.setFixedWidth(240)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # User Info
        self.name_label = QLabel("User Name")
        self.name_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #0f172a;")

        self.username_label = QLabel("@username")
        self.username_label.setObjectName("SubtitleLabel")
        self.username_label.setStyleSheet("font-size: 12px; color: #64748b;")

        layout.addWidget(self.name_label)
        layout.addWidget(self.username_label)

        # Role Badge
        role_row = QHBoxLayout()
        role_row.setSpacing(6)
        role_prefix = QLabel(f"{t('role')}:")
        role_prefix.setObjectName("SubtitleLabel")
        role_prefix.setStyleSheet("font-size: 11px; color: #64748b;")

        self.role_badge = QLabel("CASHIER")
        self.role_badge.setObjectName("BadgeRole")

        role_row.addWidget(role_prefix)
        role_row.addWidget(self.role_badge)
        role_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(role_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        layout.addWidget(divider)

        # Logout Button
        self.logout_btn = QPushButton(t("logout"))
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                font-weight: 500;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(self.logout_btn)

    def set_user_info(self, user: Optional[Dict[str, Any]]):
        if user:
            self.name_label.setText(user.get("name", "Unknown"))
            self.username_label.setText(f"@{user.get('username', 'user')}")
            self.role_badge.setText(user.get("role", "Cashier").upper())
        else:
            self.name_label.setText("Guest")
            self.username_label.setText("@guest")
            self.role_badge.setText("CASHIER")

    def _on_logout(self):
        self.hide()
        self.logout_clicked.emit()


class DashboardView(QWidget):
    """Main Post-Login Layout with Left Sidebar, Top Navbar, POS Register, Products, Users, and Settings."""

    logout_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_reset_requested = pyqtSignal()
    fullscreen_changed = pyqtSignal(bool)
    monitor_changed = pyqtSignal(int)
    black_other_monitors_changed = pyqtSignal(bool)
    language_changed = pyqtSignal(str)
    restart_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user: Optional[Dict[str, Any]] = None
        self._init_ui()
        self._setup_clock()

    def _init_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. LEFT SIDEBAR
        # -------------------------------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(18, 20, 18, 20)
        sidebar_layout.setSpacing(18)

        # Sidebar Logo Header
        self.sidebar_logo = QLabel()
        self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.refresh_sidebar_logo()
        sidebar_layout.addWidget(self.sidebar_logo)

        # Sidebar Divider
        sidebar_divider = QFrame()
        sidebar_divider.setFrameShape(QFrame.Shape.HLine)
        sidebar_divider.setStyleSheet("color: #e2e8f0; margin: 6px 0;")
        sidebar_layout.addWidget(sidebar_divider)

        # Navigation Links
        nav_vbox = QVBoxLayout()
        nav_vbox.setSpacing(6)

        self.nav_header_label = QLabel(t("navigation"))
        self.nav_header_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px; margin-bottom: 4px;")
        nav_vbox.addWidget(self.nav_header_label)

        # 1. POS Register (Dashboard)
        self.nav_dashboard_btn = QPushButton(f"  {t('dashboard')}")
        self.nav_dashboard_btn.setObjectName("SidebarNavItem")
        self.nav_dashboard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_dashboard_btn.setIcon(get_svg_icon("cart", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_dashboard_btn.clicked.connect(self._show_dashboard_page)
        nav_vbox.addWidget(self.nav_dashboard_btn)

        # 2. Reports & Analytics (Admin / Owner Only)
        self.nav_reports_btn = QPushButton(f"  {t('reports')}")
        self.nav_reports_btn.setObjectName("SidebarNavItem")
        self.nav_reports_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_reports_btn.setIcon(get_svg_icon("trending-up", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_reports_btn.clicked.connect(self._show_reports_page)
        self.nav_reports_btn.setVisible(False)
        nav_vbox.addWidget(self.nav_reports_btn)

        # 3. Cashier Ratings & Performance (Admin / Owner Only)
        self.nav_ratings_btn = QPushButton(f"  {t('cashier_ratings')}")
        self.nav_ratings_btn.setObjectName("SidebarNavItem")
        self.nav_ratings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_ratings_btn.setIcon(get_svg_icon("star", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_ratings_btn.clicked.connect(self._show_ratings_page)
        self.nav_ratings_btn.setVisible(False)
        nav_vbox.addWidget(self.nav_ratings_btn)

        # 4. Products (Admin / Owner Only)
        self.nav_products_btn = QPushButton(f"  {t('products')}")
        self.nav_products_btn.setObjectName("SidebarNavItem")
        self.nav_products_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_products_btn.setIcon(get_svg_icon("package", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_products_btn.clicked.connect(self._show_products_page)
        self.nav_products_btn.setVisible(False)
        nav_vbox.addWidget(self.nav_products_btn)

        # 5. Users (Admin / Owner Only)
        self.nav_users_btn = QPushButton(f"  {t('users')}")
        self.nav_users_btn.setObjectName("SidebarNavItem")
        self.nav_users_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_users_btn.setIcon(get_svg_icon("user", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_users_btn.clicked.connect(self._show_users_page)
        self.nav_users_btn.setVisible(False)
        nav_vbox.addWidget(self.nav_users_btn)

        # 6. Universal Settings Button for ALL users
        self.nav_settings_btn = QPushButton(f"  {t('settings')}")
        self.nav_settings_btn.setObjectName("SidebarNavItem")
        self.nav_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_settings_btn.setIcon(get_svg_icon("settings", ThemeColors.TEXT_PRIMARY, 18))
        self.nav_settings_btn.clicked.connect(self._show_settings_page)
        nav_vbox.addWidget(self.nav_settings_btn)

        sidebar_layout.addLayout(nav_vbox)
        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Bottom Sidebar Version Info
        app_info = QLabel("KubuCashier v1.0.0")
        app_info.setStyleSheet("font-size: 11px; color: #94a3b8;")
        sidebar_layout.addWidget(app_info)

        master_layout.addWidget(self.sidebar)

        # -------------------------------------------------------------
        # 2. RIGHT CONTAINER (TOP NAVBAR + BODY STACK)
        # -------------------------------------------------------------
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # TOP NAVBAR
        self.navbar = QFrame()
        self.navbar.setObjectName("NavHeader")
        self.navbar.setFixedHeight(64)

        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(20, 0, 16, 0)
        nav_layout.setSpacing(8)

        # Page Title in Navbar
        self.nav_page_title = QLabel(t("dashboard"))
        self.nav_page_title.setStyleSheet("font-weight: 600; font-size: 15px; color: #0f172a;")
        nav_layout.addWidget(self.nav_page_title)

        nav_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Live Digital Clock in Navbar (Asia/Jakarta WIB)
        clock_box = QHBoxLayout()
        clock_box.setSpacing(6)
        clock_icon = QLabel()
        clock_icon.setPixmap(get_svg_pixmap("clock", ThemeColors.TEXT_MUTED, 14))

        self.clock_label = QLabel()
        self.clock_label.setObjectName("ClockLabel")

        clock_box.addWidget(clock_icon)
        clock_box.addWidget(self.clock_label)
        nav_layout.addLayout(clock_box)

        nav_layout.addSpacerItem(QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Language Switcher in Navbar
        self.lang_btn = QPushButton(f"  {get_language().upper()}")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setFixedHeight(30)
        self.lang_btn.setMinimumWidth(64)
        self.lang_btn.setIcon(get_svg_icon("globe", ThemeColors.TEXT_MUTED, 14))
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                color: #64748b;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #f1f5f9;
                color: #0f172a;
            }
        """)
        self.lang_btn.clicked.connect(self._toggle_language)
        nav_layout.addWidget(self.lang_btn)

        nav_layout.addSpacerItem(QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Zoom Controls Box
        zoom_box = QHBoxLayout()
        zoom_box.setSpacing(4)

        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setObjectName("IconButton")
        self.zoom_out_btn.setFixedSize(32, 32)
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.setToolTip("Zoom Out (Ctrl + -)")
        self.zoom_out_btn.setIcon(get_svg_icon("minus", ThemeColors.TEXT_MUTED, 14))
        self.zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)

        self.zoom_reset_btn = QPushButton("100%")
        self.zoom_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_reset_btn.setToolTip("Reset Zoom (Ctrl + 0)")
        self.zoom_reset_btn.setFixedHeight(30)
        self.zoom_reset_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
                color: #64748b;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #f1f5f9;
                color: #0f172a;
            }
        """)
        self.zoom_reset_btn.clicked.connect(self.zoom_reset_requested.emit)

        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setObjectName("IconButton")
        self.zoom_in_btn.setFixedSize(32, 32)
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.setToolTip("Zoom In (Ctrl + +)")
        self.zoom_in_btn.setIcon(get_svg_icon("plus", ThemeColors.TEXT_MUTED, 14))
        self.zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)

        zoom_box.addWidget(self.zoom_out_btn)
        zoom_box.addWidget(self.zoom_reset_btn)
        zoom_box.addWidget(self.zoom_in_btn)
        nav_layout.addLayout(zoom_box)

        nav_layout.addSpacerItem(QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # User Button
        self.user_btn = QPushButton(f"  {t('account')}")
        self.user_btn.setObjectName("UserMenuButton")
        self.user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_btn.setFixedHeight(36)
        self.user_btn.setMinimumWidth(130)
        self.user_btn.setIcon(get_svg_icon("user", ThemeColors.TEXT_MUTED, 16))
        self.user_btn.clicked.connect(self._toggle_user_popup)
        nav_layout.addWidget(self.user_btn)

        # Subtle Navbar Exit Button
        self.exit_btn = QPushButton()
        self.exit_btn.setObjectName("IconButton")
        self.exit_btn.setFixedSize(36, 36)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setToolTip(t("exit_app"))
        self.exit_btn.setIcon(get_svg_icon("power", ThemeColors.TEXT_MUTED, 18))
        self.exit_btn.clicked.connect(self.exit_requested.emit)
        nav_layout.addWidget(self.exit_btn)

        right_layout.addWidget(self.navbar)

        # User Profile Popup
        self.profile_popup = UserProfilePopup(self)
        self.profile_popup.logout_clicked.connect(self.logout_requested.emit)

        # -------------------------------------------------------------
        # 3. BODY PAGES STACK (0: POS, 1: Settings, 2: Products, 3: Users, 4: Reports, 5: Ratings)
        # -------------------------------------------------------------
        self.body_stack = QStackedWidget()

        # Page 0: POS Register
        self.pos_view = DashboardPOSView(self)
        self.body_stack.addWidget(self.pos_view)  # index 0

        # Page 1: Universal Settings View
        self.settings_view = SettingsView(self)
        self.settings_view.fullscreen_changed.connect(self.fullscreen_changed.emit)
        self.settings_view.monitor_changed.connect(self.monitor_changed.emit)
        self.settings_view.black_other_monitors_changed.connect(self.black_other_monitors_changed.emit)
        self.settings_view.language_changed.connect(self.language_changed.emit)
        self.settings_view.restart_requested.connect(self.restart_requested.emit)
        self.settings_view.logo_updated.connect(self.refresh_sidebar_logo)
        self.body_stack.addWidget(self.settings_view)  # index 1

        # Page 2: Products & Categories View
        self.products_view = ProductsView(self)
        self.body_stack.addWidget(self.products_view)  # index 2

        # Page 3: Users Management View
        self.users_view = UsersView(self)
        self.body_stack.addWidget(self.users_view)  # index 3

        # Page 4: Reports & Analytics View (Admin / Owner)
        self.reports_view = ReportsView(self)
        self.body_stack.addWidget(self.reports_view)  # index 4

        # Page 5: Cashier Ratings & Performance View (Admin / Owner)
        self.ratings_view = CashierRatingsView(self)
        self.body_stack.addWidget(self.ratings_view)  # index 5

        # Auto-refresh reports and ratings on completed transactions
        self.pos_view.transaction_completed.connect(lambda _: self.reports_view.refresh_all_reports())
        self.pos_view.transaction_completed.connect(lambda _: self.ratings_view.refresh_data())

        right_layout.addWidget(self.body_stack)
        master_layout.addWidget(right_container)

    def _toggle_language(self):
        new_lang = "id" if get_language() == "en" else "en"
        config.set_language(new_lang, persist=True)
        self.lang_btn.setText(f"  {new_lang.upper()}")
        self._refresh_translations()
        self.language_changed.emit(new_lang)

    def _refresh_translations(self):
        self.nav_header_label.setText(t("navigation"))
        self.nav_dashboard_btn.setText(f"  {t('dashboard')}")
        self.nav_reports_btn.setText(f"  {t('reports')}")
        self.nav_ratings_btn.setText(f"  {t('cashier_ratings')}")
        self.nav_products_btn.setText(f"  {t('products')}")
        self.nav_users_btn.setText(f"  {t('users')}")
        self.nav_settings_btn.setText(f"  {t('settings')}")
        self.exit_btn.setToolTip(t("exit_app"))

        curr_idx = self.body_stack.currentIndex()
        if curr_idx == 0:
            self.nav_page_title.setText(t("dashboard"))
        elif curr_idx == 1:
            self.nav_page_title.setText(t("settings"))
        elif curr_idx == 2:
            self.nav_page_title.setText(t("products"))
        elif curr_idx == 3:
            self.nav_page_title.setText(t("users"))
        elif curr_idx == 4:
            self.nav_page_title.setText(t("reports"))
        elif curr_idx == 5:
            self.nav_page_title.setText(t("cashier_ratings"))

        self.pos_view.refresh_translations()
        self.products_view.refresh_translations()
        self.users_view.refresh_translations()
        self.ratings_view.refresh_translations()
        self.settings_view.refresh_translations()
        self._update_clock()

    def refresh_sidebar_logo(self):
        horizontal_logo_path = ASSETS_DIR / "logo_horizontal.png"
        if horizontal_logo_path.exists():
            pixmap = QPixmap(str(horizontal_logo_path))
            scaled_pixmap = pixmap.scaled(200, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.sidebar_logo.setPixmap(scaled_pixmap)
        else:
            self.sidebar_logo.setText("KUBU CASHIER")
            self.sidebar_logo.setStyleSheet("font-weight: 700; font-size: 16px; color: #0f172a;")

    def _show_dashboard_page(self):
        self.body_stack.setCurrentIndex(0)
        self.nav_page_title.setText(t("dashboard"))
        self.pos_view.refresh_catalog()
        self.nav_dashboard_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_reports_btn.setStyleSheet("")
        self.nav_ratings_btn.setStyleSheet("")
        self.nav_products_btn.setStyleSheet("")
        self.nav_users_btn.setStyleSheet("")
        self.nav_settings_btn.setStyleSheet("")

    def _show_reports_page(self):
        self.body_stack.setCurrentIndex(4)
        self.nav_page_title.setText(t("reports"))
        self.reports_view.refresh_all_reports()
        self.nav_reports_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_dashboard_btn.setStyleSheet("")
        self.nav_ratings_btn.setStyleSheet("")
        self.nav_products_btn.setStyleSheet("")
        self.nav_users_btn.setStyleSheet("")
        self.nav_settings_btn.setStyleSheet("")

    def _show_ratings_page(self):
        self.body_stack.setCurrentIndex(5)
        self.nav_page_title.setText(t("cashier_ratings"))
        self.ratings_view.refresh_data()
        self.nav_ratings_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_dashboard_btn.setStyleSheet("")
        self.nav_reports_btn.setStyleSheet("")
        self.nav_products_btn.setStyleSheet("")
        self.nav_users_btn.setStyleSheet("")
        self.nav_settings_btn.setStyleSheet("")

    def _show_products_page(self):
        self.body_stack.setCurrentIndex(2)
        self.nav_page_title.setText(t("products"))
        self.products_view.refresh_all_data()
        self.nav_products_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_dashboard_btn.setStyleSheet("")
        self.nav_reports_btn.setStyleSheet("")
        self.nav_ratings_btn.setStyleSheet("")
        self.nav_users_btn.setStyleSheet("")
        self.nav_settings_btn.setStyleSheet("")

    def _show_users_page(self):
        self.body_stack.setCurrentIndex(3)
        self.nav_page_title.setText(t("users"))
        self.users_view.refresh_all_users()
        self.nav_users_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_dashboard_btn.setStyleSheet("")
        self.nav_reports_btn.setStyleSheet("")
        self.nav_ratings_btn.setStyleSheet("")
        self.nav_products_btn.setStyleSheet("")
        self.nav_settings_btn.setStyleSheet("")

    def _show_settings_page(self):
        self.body_stack.setCurrentIndex(1)
        self.nav_page_title.setText(t("settings"))
        self.nav_settings_btn.setStyleSheet("background-color: #f1f5f9; border-color: #06b6d4;")
        self.nav_dashboard_btn.setStyleSheet("")
        self.nav_reports_btn.setStyleSheet("")
        self.nav_ratings_btn.setStyleSheet("")
        self.nav_products_btn.setStyleSheet("")
        self.nav_users_btn.setStyleSheet("")

    def set_zoom_label(self, percent: int):
        self.zoom_reset_btn.setText(f"{percent}%")

    def apply_zoom_scale(self, scale: float):
        """Proportionally scales sidebar, navbar, and POS catalog screens."""
        self.sidebar.setFixedWidth(max(180, int(240 * scale)))
        self.navbar.setFixedHeight(max(50, int(64 * scale)))
        if hasattr(self.pos_view, "apply_zoom_scale"):
            self.pos_view.apply_zoom_scale(scale)

    def _setup_clock(self):
        self._update_clock()
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

    def _update_clock(self):
        clock_text = get_formatted_clock(get_language())
        self.clock_label.setText(clock_text)

    def _toggle_user_popup(self):
        if self.profile_popup.isVisible():
            self.profile_popup.hide()
        else:
            btn_pos = self.user_btn.mapToGlobal(QPoint(0, self.user_btn.height() + 4))
            popup_x = btn_pos.x() + self.user_btn.width() - self.profile_popup.width()
            self.profile_popup.move(popup_x, btn_pos.y())
            self.profile_popup.show()

    def set_user(self, user: Dict[str, Any]):
        """Updates dashboard with logged in user data."""
        self.current_user = user
        name = user.get("name", "User")
        role = user.get("role", "Cashier")
        self.user_btn.setText(f"  {name}")

        self.profile_popup.set_user_info(user)
        self.pos_view.set_user(user)
        self.settings_view.set_user(user)
        self.users_view.set_current_user(user)
        self.reports_view.set_user(user)
        self.ratings_view.set_current_user(user)

        # Reports, Ratings, Products and Users are visible ONLY to Admin and Owner
        is_admin_owner = is_admin_or_owner(role)
        self.nav_reports_btn.setVisible(is_admin_owner)
        self.nav_ratings_btn.setVisible(is_admin_owner)
        self.nav_products_btn.setVisible(is_admin_owner)
        self.nav_users_btn.setVisible(is_admin_owner)

        self.nav_settings_btn.setVisible(True)
        self._show_dashboard_page()
