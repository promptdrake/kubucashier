"""Integration and UI interaction tests for KubuCashier."""
import os
import sys
import unittest
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from database.db_manager import DatabaseManager
from auth.auth_service import AuthService
from auth.biometric_service import BiometricService
from ui.main_window import MainWindow
from ui.i18n import set_language, get_language
from config import config, is_admin_or_owner, ASSETS_DIR


# Ensure QApplication is initialized
app = QApplication.instance() or QApplication(sys.argv)


class TestKubuCashierIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = DatabaseManager(self.temp_db_path)
        self.auth = AuthService(self.db)

        # Patch global auth and db for UI testing
        import ui.login_view as login_mod
        import ui.register_view as reg_mod
        import ui.main_window as main_mod

        self.orig_auth = login_mod.auth_service
        login_mod.auth_service = self.auth
        reg_mod.auth_service = self.auth
        main_mod.auth_service = self.auth
        config.fullscreen = False
        config.customer_display_enabled = False
        config.set_language("en", persist=False)
        self.window = MainWindow()

    def tearDown(self):
        self.window._can_close = True
        self.window.close()
        import ui.login_view as login_mod
        import ui.register_view as reg_mod
        import ui.main_window as main_mod
        login_mod.auth_service = self.orig_auth
        reg_mod.auth_service = self.orig_auth
        main_mod.auth_service = self.orig_auth

        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_full_user_flow_cashier(self):
        # 1. Starts on Login View
        self.assertEqual(self.window.stack.currentWidget(), self.window.login_view)

        # 2. Click switch to Register
        self.window.login_view.register_link_btn.click()
        self.assertEqual(self.window.stack.currentWidget(), self.window.register_view)

        # 3. Attempt register with invalid token
        self.window.register_view.name_input.setText("Jane Doe")
        self.window.register_view.username_input.setText("janedoe")
        self.window.register_view.password_input.setText("password123")
        self.window.register_view.role_combo.setCurrentText("Cashier")
        self.window.register_view.token_input.setText("wrong_token_123")
        self.window.register_view.register_btn.click()

        # Should remain on register view and show error
        self.assertEqual(self.window.stack.currentWidget(), self.window.register_view)
        self.assertFalse(self.window.register_view.status_banner.isHidden())
        self.assertIn("Invalid Credential Token", self.window.register_view.status_banner.text())

        # 4. Attempt register with valid token
        valid_token = config.credential_token
        self.window.register_view.token_input.setText(valid_token)
        self.window.register_view.register_btn.click()

        # Should transition back to login view with username prefilled
        self.assertEqual(self.window.stack.currentWidget(), self.window.login_view)
        self.assertEqual(self.window.login_view.username_input.text(), "janedoe")

        # 5. Login with correct password
        self.window.login_view.password_input.setText("password123")
        self.window.login_view.login_btn.click()

        # Should transition to Dashboard View (POS Register)
        self.assertEqual(self.window.stack.currentWidget(), self.window.dashboard_view)
        self.assertIn("Jane Doe", self.window.dashboard_view.user_btn.text())
        self.assertIn("Jane Doe", self.window.dashboard_view.pos_view.shift_info_lbl.text())

        # Test Cashier POS Cart Addition
        cat_id = self.db.add_category("Beverages")
        prod_id = self.db.add_product("Iced Tea", cat_id, 10000.0, stock=20)
        self.window.dashboard_view.pos_view.refresh_catalog()

        # Tap product
        prod = self.db.get_product_by_id(prod_id)
        self.window.dashboard_view.pos_view._on_product_clicked(prod)
        self.assertIn(prod_id, self.window.dashboard_view.pos_view.cart_items)
        self.assertEqual(self.window.dashboard_view.pos_view.cart_items[prod_id]["quantity"], 1)

        # Products and Users menu should be hidden for Cashier
        self.assertTrue(self.window.dashboard_view.nav_products_btn.isHidden())
        self.assertTrue(self.window.dashboard_view.nav_users_btn.isHidden())

        # Settings is available for ALL users (Cashier has personal settings)
        self.assertFalse(self.window.dashboard_view.nav_settings_btn.isHidden())
        self.window.dashboard_view.nav_settings_btn.click()
        self.assertEqual(self.window.dashboard_view.body_stack.currentIndex(), 1)
        # Cashier should not see admin container in settings
        self.assertTrue(self.window.dashboard_view.settings_view.admin_container.isHidden())

        # 6. Test Logout
        self.window.dashboard_view.profile_popup.logout_btn.click()
        self.assertEqual(self.window.stack.currentWidget(), self.window.login_view)
        self.assertFalse(self.auth.is_logged_in())

    def test_admin_role_and_settings_page(self):
        # Register Admin
        self.auth.register("Admin User", "adminuser", "admin123", "Admin", config.credential_token)
        _, _, user = self.auth.login("adminuser", "admin123")
        self.window._on_login_success(user)

        # Admin role SHOULD see Products, Users, and Settings
        self.assertFalse(self.window.dashboard_view.nav_products_btn.isHidden())
        self.assertFalse(self.window.dashboard_view.nav_users_btn.isHidden())
        self.assertFalse(self.window.dashboard_view.nav_settings_btn.isHidden())

        # Click Products in sidebar
        self.window.dashboard_view.nav_products_btn.click()
        self.assertEqual(self.window.dashboard_view.body_stack.currentIndex(), 2)

        # Click Users in sidebar
        self.window.dashboard_view.nav_users_btn.click()
        self.assertEqual(self.window.dashboard_view.body_stack.currentIndex(), 3)

        # Click Settings in sidebar
        self.window.dashboard_view.nav_settings_btn.click()
        self.assertEqual(self.window.dashboard_view.body_stack.currentIndex(), 1)
        self.assertFalse(self.window.dashboard_view.settings_view.admin_container.isHidden())

        # Test Authentication code saving
        settings = self.window.dashboard_view.settings_view
        settings.token_input.setText("admin")
        settings.save_token_btn.click()
        self.assertEqual(config.credential_token, "admin")
        self.assertFalse(settings.status_banner.isHidden())

    def test_language_switcher_toggle(self):
        from ui.i18n import set_language
        set_language("en")
        self.window.login_view._refresh_translations()
        self.assertEqual(get_language(), "en")

        self.window.login_view.lang_btn.click()
        self.assertEqual(get_language(), "id")
        self.assertEqual(self.window.login_view.login_btn.text(), "MASUK")

        self.window.login_view.lang_btn.click()
        self.assertEqual(get_language(), "en")
        self.assertEqual(self.window.login_view.login_btn.text(), "LOG IN")

    def test_zoom_controls(self):
        self.assertEqual(self.window._zoom_level, 100)

        # Zoom In
        self.window.zoom_in()
        self.assertEqual(self.window._zoom_level, 110)
        self.assertEqual(self.window.dashboard_view.zoom_reset_btn.text(), "110%")

        # Zoom Out
        self.window.zoom_out()
        self.assertEqual(self.window._zoom_level, 100)
        self.assertEqual(self.window.dashboard_view.zoom_reset_btn.text(), "100%")

        # Zoom Reset
        self.window.zoom_in()
        self.window.zoom_in()
        self.assertEqual(self.window._zoom_level, 120)
        self.window.zoom_reset()
        self.assertEqual(self.window._zoom_level, 100)
        self.assertEqual(self.window.dashboard_view.zoom_reset_btn.text(), "100%")


if __name__ == "__main__":
    unittest.main()
