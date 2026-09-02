"""
Theme and Styling System for KubuCashier.
Clean Light Minimalist Theme with lighter, refined typography and Cyan accents.
Zero gradients, no heavy shadows, crisp 1px borders.
Supports dynamic UI scaling for Zoom In / Zoom Out.
"""

from pathlib import Path
from config import ASSETS_DIR


class ThemeColors:
    """Color tokens for KubuCashier (Light Minimalist)."""
    CYAN_ACCENT = "#06b6d4"

    BG = "#f8fafc"
    SURFACE = "#ffffff"
    SURFACE_ALT = "#f1f5f9"
    SIDEBAR_BG = "#ffffff"
    INPUT_BG = "#ffffff"
    BORDER = "#e2e8f0"
    BORDER_HOVER = "#94a3b8"
    BORDER_FOCUS = "#06b6d4"
    TEXT_PRIMARY = "#0f172a"
    TEXT_SECONDARY = "#64748b"
    TEXT_MUTED = "#94a3b8"
    BTN_PRIMARY_BG = "#0f172a"
    BTN_PRIMARY_TEXT = "#ffffff"
    BTN_PRIMARY_HOVER = "#334155"
    BTN_PRIMARY_ACTIVE = "#1e293b"
    DANGER = "#ef4444"
    DANGER_BG = "#fef2f2"
    DANGER_BORDER = "#fecaca"
    SUCCESS = "#16a34a"
    SUCCESS_BG = "#f0fdf4"
    SUCCESS_BORDER = "#bbf7d0"
    WARNING = "#d97706"
    WARNING_BG = "#fffbeb"
    WARNING_BORDER = "#fde68a"
    BADGE_BG = "#f1f5f9"
    BADGE_TEXT = "#0891b2"


def generate_stylesheet(scale: float = 1.0) -> str:
    """Generates clean minimalist light stylesheet with scalable font sizing and softer font weights."""
    f_base = max(10, int(13 * scale))
    f_sm = max(9, int(12 * scale))
    f_xs = max(8, int(11 * scale))
    f_md = max(11, int(14 * scale))
    f_lg = max(13, int(16 * scale))
    f_xl = max(15, int(18 * scale))
    f_2xl = max(17, int(20 * scale))
    f_3xl = max(19, int(22 * scale))

    p_btn_v = max(6, int(8 * scale))
    p_btn_h = max(10, int(16 * scale))
    p_inp_v = max(6, int(9 * scale))
    p_inp_h = max(8, int(12 * scale))

    # Path to checkmark image with forward slashes for Qt stylesheet
    check_icon_path = (ASSETS_DIR / "check_white.png").as_posix()

    return f"""
    /* Global Application */
    QMainWindow, QWidget#CentralWidget {{
        background-color: {ThemeColors.BG};
        color: {ThemeColors.TEXT_PRIMARY};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: {f_base}px;
        font-weight: 400;
    }}

    QWidget {{
        color: {ThemeColors.TEXT_PRIMARY};
    }}

    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent;
        border: none;
    }}

    /* Auth Cards */
    QFrame#AuthCard {{
        background-color: {ThemeColors.SURFACE};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 12px;
    }}

    /* Surface Card */
    QFrame#SurfaceCard {{
        background-color: {ThemeColors.SURFACE};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 10px;
    }}

    /* Sidebar */
    QFrame#Sidebar {{
        background-color: {ThemeColors.SIDEBAR_BG};
        border-right: 1px solid {ThemeColors.BORDER};
    }}

    /* Navbar Header */
    QFrame#NavHeader {{
        background-color: {ThemeColors.SURFACE};
        border-bottom: 1px solid {ThemeColors.BORDER};
    }}

    /* Profile Popup */
    QFrame#ProfileCard {{
        background-color: {ThemeColors.SURFACE};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 10px;
    }}

    /* Form Inputs */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {ThemeColors.INPUT_BG};
        color: {ThemeColors.TEXT_PRIMARY};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 6px;
        padding: {p_inp_v}px {p_inp_h}px;
        font-size: {f_base}px;
        font-weight: 400;
        selection-background-color: {ThemeColors.TEXT_PRIMARY};
        selection-color: #ffffff;
    }}

    QLineEdit:hover, QComboBox:hover {{
        border-color: {ThemeColors.BORDER_HOVER};
    }}

    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {ThemeColors.BORDER_FOCUS};
    }}

    /* CheckBox with White Checkmark Icon */
    QCheckBox {{
        font-size: {f_base}px;
        font-weight: 500;
        color: {ThemeColors.TEXT_PRIMARY};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #cbd5e1;
        background-color: #ffffff;
    }}

    QCheckBox::indicator:hover {{
        border-color: #94a3b8;
    }}

    QCheckBox::indicator:checked {{
        background-color: {ThemeColors.BTN_PRIMARY_BG};
        border: 1px solid {ThemeColors.BTN_PRIMARY_BG};
        image: url({check_icon_path});
    }}

    /* ComboBox */
    QComboBox {{
        padding-right: 28px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {ThemeColors.SURFACE};
        color: {ThemeColors.TEXT_PRIMARY};
        border: 1px solid {ThemeColors.BORDER};
        selection-background-color: {ThemeColors.SURFACE_ALT};
        selection-color: {ThemeColors.TEXT_PRIMARY};
        padding: 4px;
        outline: none;
    }}

    /* Base Buttons */
    QPushButton {{
        font-family: inherit;
        font-size: {f_base}px;
        font-weight: 500;
        border-radius: 6px;
        padding: {p_btn_v}px {p_btn_h}px;
        border: 1px solid {ThemeColors.BORDER};
        background-color: {ThemeColors.SURFACE};
        color: {ThemeColors.TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: {ThemeColors.SURFACE_ALT};
    }}

    /* Primary Solid Button (Clean Dark Button with Refined Weight) */
    QPushButton#PrimaryButton, QPushButton[objectName="PrimaryButton"] {{
        background-color: {ThemeColors.BTN_PRIMARY_BG};
        color: {ThemeColors.BTN_PRIMARY_TEXT};
        border: 1px solid {ThemeColors.BTN_PRIMARY_BG};
        font-weight: 600;
        font-size: {f_sm}px;
        letter-spacing: 0.5px;
        padding: {p_inp_v + 1}px {p_inp_h + 6}px;
        border-radius: 6px;
    }}

    QPushButton#PrimaryButton:hover, QPushButton[objectName="PrimaryButton"]:hover {{
        background-color: {ThemeColors.BTN_PRIMARY_HOVER};
        border-color: {ThemeColors.BTN_PRIMARY_HOVER};
        color: {ThemeColors.BTN_PRIMARY_TEXT};
    }}

    QPushButton#PrimaryButton:pressed, QPushButton[objectName="PrimaryButton"]:pressed {{
        background-color: {ThemeColors.BTN_PRIMARY_ACTIVE};
        border-color: {ThemeColors.BTN_PRIMARY_ACTIVE};
        color: {ThemeColors.BTN_PRIMARY_TEXT};
    }}

    /* Secondary / Outline Button */
    QPushButton#SecondaryButton {{
        background-color: transparent;
        color: {ThemeColors.TEXT_PRIMARY};
        border: 1px solid {ThemeColors.BORDER};
        font-weight: 500;
        font-size: {f_sm}px;
        border-radius: 6px;
        padding: {p_btn_v}px {p_btn_h}px;
    }}

    QPushButton#SecondaryButton:hover {{
        background-color: {ThemeColors.SURFACE_ALT};
        border-color: {ThemeColors.BORDER_HOVER};
    }}

    /* Link Style Button */
    QPushButton#LinkButton {{
        background-color: transparent;
        border: none;
        color: {ThemeColors.TEXT_SECONDARY};
        font-size: {f_base}px;
        font-weight: 500;
        padding: 4px;
        text-decoration: underline;
    }}

    QPushButton#LinkButton:hover {{
        color: {ThemeColors.TEXT_PRIMARY};
    }}

    /* Icon Buttons */
    QPushButton#IconButton, QToolButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
    }}

    QPushButton#IconButton:hover, QToolButton:hover {{
        background-color: {ThemeColors.SURFACE_ALT};
        border: 1px solid {ThemeColors.BORDER};
    }}

    /* Language Switcher Button */
    QPushButton#LangButton {{
        background-color: transparent;
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: {f_xs}px;
        font-weight: 600;
        color: {ThemeColors.TEXT_SECONDARY};
    }}

    QPushButton#LangButton:hover {{
        background-color: {ThemeColors.SURFACE_ALT};
        color: {ThemeColors.TEXT_PRIMARY};
    }}

    /* User Menu Button */
    QPushButton#UserMenuButton {{
        background-color: transparent;
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 6px;
        padding: 6px 12px;
        font-size: {f_base}px;
        font-weight: 500;
        color: {ThemeColors.TEXT_PRIMARY};
    }}

    QPushButton#UserMenuButton:hover {{
        background-color: {ThemeColors.SURFACE_ALT};
    }}

    /* Sidebar Nav Item Button */
    QPushButton#SidebarNavItem {{
        background-color: {ThemeColors.SURFACE_ALT};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 6px;
        padding: 10px 14px;
        font-size: {f_base}px;
        font-weight: 500;
        color: {ThemeColors.TEXT_PRIMARY};
        text-align: left;
    }}

    QPushButton#SidebarNavItem:hover {{
        border-color: {ThemeColors.BORDER_FOCUS};
    }}

    /* Labels */
    QLabel#FieldLabel {{
        color: {ThemeColors.TEXT_PRIMARY};
        font-weight: 500;
        font-size: {f_sm}px;
        letter-spacing: 0.1px;
    }}

    QLabel#TitleLabel {{
        color: {ThemeColors.TEXT_PRIMARY};
        font-size: {f_xl}px;
        font-weight: 600;
    }}

    QLabel#SubtitleLabel {{
        color: {ThemeColors.TEXT_SECONDARY};
        font-size: {f_base}px;
        font-weight: 400;
    }}

    QLabel#GreetingTitle {{
        color: {ThemeColors.TEXT_PRIMARY};
        font-size: {f_3xl}px;
        font-weight: 600;
    }}

    QLabel#ClockLabel {{
        color: {ThemeColors.TEXT_SECONDARY};
        font-size: {f_base}px;
        font-weight: 400;
        font-family: 'Consolas', 'Menlo', 'Courier New', monospace;
    }}

    QLabel#BadgeRole {{
        background-color: {ThemeColors.BADGE_BG};
        color: {ThemeColors.BADGE_TEXT};
        border: 1px solid {ThemeColors.BORDER};
        border-radius: 4px;
        padding: 3px 8px;
        font-size: {f_xs}px;
        font-weight: 600;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: {ThemeColors.BG};
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {ThemeColors.BORDER};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {ThemeColors.BORDER_HOVER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
