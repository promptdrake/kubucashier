import sys
import platform
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

from config import ASSETS_DIR, config
from database.db_manager import db
from ui.main_window import MainWindow


def main():
    """Main execution loop for KubuCashier."""
    # On Windows, set explicit AppUserModelID so the taskbar displays the custom app icon instead of python.exe
    if platform.system() == "Windows":
        try:
            import ctypes
            app_id = "kubu.cashier.pos.app.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    print("Initialize KubuCashier v1.0.0...")
    config.parse_cli_args()
    from ui.i18n import set_language
    set_language(config.language)
    db.init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("KubuCashier")
    app.setOrganizationName("Kubu")
    app.setFont(QFont("Segoe UI", 10))

    # Set application icon (uses .ico on Windows for crisp taskbar rendering, or .png fallback)
    ico_path = ASSETS_DIR / "app_icon.ico"
    png_path = ASSETS_DIR / "logo_square.png"
    if ico_path.exists():
        app.setWindowIcon(QIcon(str(ico_path)))
    elif png_path.exists():
        app.setWindowIcon(QIcon(str(png_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
