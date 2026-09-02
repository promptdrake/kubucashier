"""
Main Application Window for KubuCashier.
Manages views (Login, Register, Dashboard/Settings), multi-monitor geometry,
locked fullscreen kiosk mode, keyboard shortcut blocking, and secondary screen blackouts.
"""

import sys
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QApplication
)
from PyQt6.QtCore import Qt, QProcess, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QCloseEvent, QKeyEvent

from config import config, ASSETS_DIR
from auth.auth_service import auth_service
from ui.login_view import LoginView
from ui.register_view import RegisterView
from ui.dashboard_view import DashboardView
from ui.i18n import get_language, set_language
from ui.theme import generate_stylesheet
from ui.kiosk_manager import kiosk_keyboard_blocker, blackout_manager


class MainWindow(QMainWindow):
    """Primary application window handling authentication views, dashboard navigation, and kiosk mode."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KubuCashier")
        self.setMinimumSize(960, 600)
        self.resize(1080, 720)

        self._can_close = False
        self._zoom_level = 100  # Default 100% zoom
        self._set_window_icon()
        self._init_ui()
        self.apply_theme(scale=1.0)
        self._apply_monitor_and_fullscreen()

    def _set_window_icon(self):
        ico_path = ASSETS_DIR / "app_icon.ico"
        png_path = ASSETS_DIR / "logo_square.png"
        if ico_path.exists():
            self.setWindowIcon(QIcon(str(ico_path)))
        elif png_path.exists():
            self.setWindowIcon(QIcon(str(png_path)))

    def _init_ui(self):
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Initialize view components
        self.login_view = LoginView(self)
        self.register_view = RegisterView(self)
        self.dashboard_view = DashboardView(self)

        # Add to stack
        self.stack.addWidget(self.login_view)      # index 0
        self.stack.addWidget(self.register_view)   # index 1
        self.stack.addWidget(self.dashboard_view)  # index 2

        # Wire navigation signals
        self.login_view.switch_to_register.connect(self._go_to_register)
        self.login_view.login_successful.connect(self._on_login_success)

        self.register_view.switch_to_login.connect(self._go_to_login)
        self.register_view.registration_successful.connect(self._on_registration_success)

        self.dashboard_view.logout_requested.connect(self._on_logout)

        # Wire exit and restart buttons
        self.login_view.exit_requested.connect(self.exit_application)
        self.register_view.exit_requested.connect(self.exit_application)
        self.dashboard_view.exit_requested.connect(self.exit_application)
        self.dashboard_view.restart_requested.connect(self.restart_application)

        # Wire zoom signals
        self.dashboard_view.zoom_in_requested.connect(self.zoom_in)
        self.dashboard_view.zoom_out_requested.connect(self.zoom_out)
        self.dashboard_view.zoom_reset_requested.connect(self.zoom_reset)

        # Wire language change events
        self.login_view.language_changed.connect(self._on_language_changed)
        self.register_view.language_changed.connect(self._on_language_changed)
        self.dashboard_view.language_changed.connect(self._on_language_changed)

        # Wire settings fullscreen, monitor, and blackout changes
        self.dashboard_view.fullscreen_changed.connect(self.set_fullscreen_mode)
        self.dashboard_view.monitor_changed.connect(self.set_target_monitor)
        self.dashboard_view.black_other_monitors_changed.connect(self._on_black_other_monitors_changed)

        # Start on login view
        self.stack.setCurrentWidget(self.login_view)

    def _on_language_changed(self, lang_code: str):
        self.login_view.lang_btn.setText(f"  {lang_code.upper()}")
        self.login_view._refresh_translations()
        self.register_view.lang_btn.setText(f"  {lang_code.upper()}")
        self.register_view._refresh_translations()
        self.dashboard_view.lang_btn.setText(f"  {lang_code.upper()}")
        self.dashboard_view._refresh_translations()

    # -----------------------------------------------------------------
    # MONITOR & FULLSCREEN MANAGEMENT
    # -----------------------------------------------------------------
    def _get_target_screen(self):
        screens = QApplication.screens()
        if not screens:
            return None
        if config.monitor is not None and config.monitor >= 1:
            idx = config.monitor - 1
            if idx < len(screens):
                return screens[idx]
        return screens[0]

    def _apply_monitor_and_fullscreen(self):
        """Positions the window on the target monitor and applies fullscreen mode if requested."""
        target_screen = self._get_target_screen()
        if target_screen is not None:
            geo = target_screen.geometry()
            w = self.width()
            h = self.height()
            x = geo.left() + max(0, (geo.width() - w) // 2)
            y = geo.top() + max(0, (geo.height() - h) // 2)
            self.move(x, y)
            if self.windowHandle():
                self.windowHandle().setScreen(target_screen)

        if config.fullscreen:
            self.set_fullscreen_mode(True)
        else:
            self.show()

    def set_target_monitor(self, monitor_num: int):
        """Switches the window to the chosen monitor number (1-indexed)."""
        screens = QApplication.screens()
        if not screens:
            return

        idx = monitor_num - 1
        if 0 <= idx < len(screens):
            target_screen = screens[idx]
        else:
            target_screen = screens[0]

        is_fs = self.isFullScreen() or config.fullscreen
        if is_fs:
            self.showNormal()

        geo = target_screen.geometry()
        w = self.width()
        h = self.height()
        x = geo.left() + max(0, (geo.width() - w) // 2)
        y = geo.top() + max(0, (geo.height() - h) // 2)
        self.move(x, y)

        if self.windowHandle():
            self.windowHandle().setScreen(target_screen)

        if is_fs:
            self.set_fullscreen_mode(True)
        else:
            self.showNormal()

    def set_fullscreen_mode(self, enabled: bool):
        """Activates or deactivates locked fullscreen kiosk mode."""
        if enabled:
            target_screen = self._get_target_screen()
            if target_screen:
                self.setGeometry(target_screen.geometry())
            self.showFullScreen()
            kiosk_keyboard_blocker.enable()
            if config.black_other_monitors and target_screen:
                blackout_manager.show_blackouts(target_screen)
        else:
            kiosk_keyboard_blocker.disable()
            blackout_manager.hide_blackouts()
            self.showNormal()

    def _on_black_other_monitors_changed(self, enabled: bool):
        is_fs = self.isFullScreen() or config.fullscreen
        if is_fs:
            if enabled:
                target_screen = self._get_target_screen()
                if target_screen:
                    blackout_manager.show_blackouts(target_screen)
            else:
                blackout_manager.hide_blackouts()

    # -----------------------------------------------------------------
    # ZOOM CONTROLS
    # -----------------------------------------------------------------
    def zoom_in(self):
        if self._zoom_level < 160:
            self._zoom_level += 10
            self._apply_zoom()

    def zoom_out(self):
        if self._zoom_level > 70:
            self._zoom_level -= 10
            self._apply_zoom()

    def zoom_reset(self):
        self._zoom_level = 100
        self._apply_zoom()

    def _apply_zoom(self):
        scale = self._zoom_level / 100.0
        self.apply_theme(scale=scale)
        self.dashboard_view.set_zoom_label(self._zoom_level)
        self.dashboard_view.apply_zoom_scale(scale)
        from utils.logger import log_settings
        log_settings("ZOOM", f"Application zoom scale adjusted to {self._zoom_level}% (scale: {scale:.2f})")

    # -----------------------------------------------------------------
    # NAVIGATION & AUTH SLOTS
    # -----------------------------------------------------------------
    def _go_to_register(self):
        self.register_view.clear_inputs()
        self.stack.setCurrentWidget(self.register_view)

    def _go_to_login(self):
        self.login_view.clear_inputs()
        self.stack.setCurrentWidget(self.login_view)

    def _on_registration_success(self, user_info: Any):
        self.login_view.clear_inputs()
        username = user_info.get("username", "") if isinstance(user_info, dict) else str(user_info)
        self.login_view.username_input.setText(username)
        self.login_view._show_success("Account created successfully! Please log in.")
        self.stack.setCurrentWidget(self.login_view)

    def _on_login_success(self, user: Dict[str, Any]):
        self.dashboard_view.set_user(user)
        self.stack.setCurrentWidget(self.dashboard_view)
        from services.customer_display_manager import customer_display_manager
        customer_display_manager.set_user(user)
        customer_display_manager.initialize()
        from utils.logger import log_auth
        log_auth("LOGIN", f"User '{user.get('username')}' ({user.get('role')}) logged in successfully.")

    def _on_logout(self):
        auth_service.logout()
        from services.customer_display_manager import customer_display_manager
        customer_display_manager.set_user(None)
        customer_display_manager.close()
        from utils.logger import log_auth
        log_auth("LOGOUT", "User logged out -> returning to login screen.")
        self.login_view.clear_inputs()
        self.register_view.clear_inputs()
        self.stack.setCurrentWidget(self.login_view)

    def restart_application(self):
        """Cleanly restarts the application to apply updated system settings."""
        self._can_close = True
        kiosk_keyboard_blocker.disable()
        blackout_manager.hide_blackouts()
        QProcess.startDetached(sys.executable, sys.argv)
        app = QApplication.instance()
        if app:
            app.quit()
        else:
            self.close()

    def exit_application(self):
        """Clean application exit triggered by Exit Button. Prompts for credential token in fullscreen."""
        is_fs = self.isFullScreen() or config.fullscreen
        if is_fs:
            from ui.components.exit_kiosk_dialog import ExitKioskDialog
            dlg = ExitKioskDialog(self)
            if not dlg.exec():
                return

        self._can_close = True
        kiosk_keyboard_blocker.disable()
        blackout_manager.hide_blackouts()
        app = QApplication.instance()
        if app:
            app.quit()
        else:
            self.close()

    def closeEvent(self, event: QCloseEvent):
        """Prevent exiting without entering credential token in locked fullscreen mode."""
        is_fs = self.isFullScreen() or config.fullscreen
        if is_fs and not self._can_close:
            event.ignore()
            from ui.components.exit_kiosk_dialog import ExitKioskDialog
            dlg = ExitKioskDialog(self)
            if dlg.exec():
                self._can_close = True
                kiosk_keyboard_blocker.disable()
                blackout_manager.hide_blackouts()
                event.accept()
                app = QApplication.instance()
                if app:
                    app.quit()
        else:
            kiosk_keyboard_blocker.disable()
            blackout_manager.hide_blackouts()
            event.accept()

    def changeEvent(self, event: QEvent):
        """Ensure fullscreen kiosk window stays focused."""
        if event.type() == QEvent.Type.ActivationChange:
            is_fs = self.isFullScreen() or config.fullscreen
            if is_fs and not self.isActiveWindow() and not self._can_close:
                # Re-raise to ensure kiosk integrity
                self.raise_()
        super().changeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle zoom keyboard shortcuts and block Esc/F11 in fullscreen kiosk mode."""
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
                event.accept()
                return
            elif event.key() in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_out()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_0:
                self.zoom_reset()
                event.accept()
                return

        # POS Shortcuts on Dashboard Register
        if self.stack.currentWidget() == self.dashboard_view and self.dashboard_view.body_stack.currentIndex() == 0:
            if event.key() == Qt.Key.Key_F2:
                self.dashboard_view.pos_view.search_input.setFocus()
                self.dashboard_view.pos_view.search_input.selectAll()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_F9:
                if self.dashboard_view.pos_view.cart_items:
                    self.dashboard_view.pos_view._open_checkout_dialog()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                if self.dashboard_view.pos_view.cart_items:
                    self.dashboard_view.pos_view.clear_cart()
                    event.accept()
                    return

        if config.fullscreen or self.isFullScreen():
            if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F11):
                event.ignore()
                return
        super().keyPressEvent(event)

    def apply_theme(self, scale: float = 1.0):
        stylesheet = generate_stylesheet(scale=scale)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)
        else:
            self.setStyleSheet(stylesheet)
