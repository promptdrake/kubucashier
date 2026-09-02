"""UI, i18n, and Theme logic tests."""
import unittest
from PyQt6.QtWidgets import QApplication
import sys

from ui.dashboard_view import get_greeting, get_formatted_clock
from ui.theme import generate_stylesheet
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.i18n import t, set_language, get_language


# Ensure QApplication exists for UI tests
app = QApplication.instance() or QApplication(sys.argv)


class TestUILogic(unittest.TestCase):
    def test_greeting_logic(self):
        set_language("en")
        greeting_en = get_greeting("Alice")
        self.assertTrue(any(sal in greeting_en for sal in ["Good morning", "Good afternoon", "Good evening", "Good night"]))
        self.assertIn("Alice", greeting_en)

        set_language("id")
        greeting_id = get_greeting("Budi")
        self.assertTrue(any(sal in greeting_id for sal in ["Selamat pagi", "Selamat siang", "Selamat sore", "Selamat malam"]))
        self.assertIn("Budi", greeting_id)
        set_language("en")

    def test_jakarta_clock_formatting(self):
        clock_id = get_formatted_clock("id")
        self.assertIn("WIB", clock_id)

        clock_en = get_formatted_clock("en")
        self.assertIn("WIB", clock_en)

    def test_i18n_translations(self):
        set_language("en")
        self.assertEqual(t("login_btn"), "LOG IN")
        self.assertEqual(t("register_btn"), "REGISTER")

        set_language("id")
        self.assertEqual(t("login_btn"), "MASUK")
        self.assertEqual(t("register_btn"), "DAFTAR")
        set_language("en")

    def test_theme_stylesheet_generation(self):
        light_qss = generate_stylesheet(scale=1.0)
        self.assertIn("#f8fafc", light_qss)
        self.assertIn("#ffffff", light_qss)
        self.assertIn("#0f172a", light_qss)
        self.assertIn("check_white.png", light_qss)

    def test_svg_icon_generation(self):
        for icon_name in ["user", "lock", "eye", "eye-off", "clock", "logout", "cart", "chart", "globe", "settings"]:
            icon = get_svg_icon(icon_name)
            self.assertFalse(icon.isNull(), f"Icon {icon_name} should not be null")
            pixmap = get_svg_pixmap(icon_name, "#0f172a", 24)
            self.assertFalse(pixmap.isNull(), f"Pixmap {icon_name} should not be null")


if __name__ == "__main__":
    unittest.main()
