"""
Settings View for KubuCashier.
Provides:
1. Personal Preferences (Available to ALL Users):
   - Language Switcher (English / Bahasa Indonesia)
2. System Configuration (Admin / Owner Only):
   - Fullscreen Kiosk Mode & Target Monitor (Requires Restart)
   - Authentication Code (Credential Token)
   - Payment Options & Static-to-Dynamic QRIS Setup
   - Cloud Sync (Requires Restart)
   - Sidebar Logo Customization (Recommended 200x48 px, Save As, Upload)
3. Modernized Single-Line Notification Banner and Application Restart Alerts.
"""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QFrame, QFileDialog, QScrollArea,
    QSpacerItem, QSizePolicy, QApplication, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR, config, is_admin_or_owner
from services.qris_service import decode_qr_from_image, parse_qris_data
from ui.i18n import t, get_language, set_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner
from utils.screen_utils import get_detected_screens_info


class SettingsView(QWidget):
    """Universal Settings View with role-aware sections, clean checkboxes, and restart alerts."""

    language_changed = pyqtSignal(str)
    restart_requested = pyqtSignal()
    fullscreen_changed = pyqtSignal(bool)
    monitor_changed = pyqtSignal(int)
    black_other_monitors_changed = pyqtSignal(bool)
    cloud_sync_changed = pyqtSignal(bool)
    logo_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token_visible = False
        self._current_user: Optional[Dict[str, Any]] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(36, 28, 36, 36)
        self.content_layout.setSpacing(18)

        # Page Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        self.title_label = QLabel(t("settings_title"))
        self.title_label.setObjectName("GreetingTitle")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #0f172a;")

        self.desc_label = QLabel(t("settings_subtitle"))
        self.desc_label.setObjectName("SubtitleLabel")
        self.desc_label.setStyleSheet("font-size: 13px; color: #64748b;")

        header_box.addWidget(self.title_label)
        header_box.addWidget(self.desc_label)
        self.content_layout.addLayout(header_box)

        # Single-Line Toast / Alert Notification Banner
        self.status_banner = NotificationBanner(self)
        self.content_layout.addWidget(self.status_banner)

        # Restart Required Prompt Banner (Hidden by default)
        self.restart_card = QFrame()
        self.restart_card.setObjectName("SurfaceCard")
        self.restart_card.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 8px;
            }
        """)
        restart_layout = QHBoxLayout(self.restart_card)
        restart_layout.setContentsMargins(16, 12, 16, 12)
        restart_layout.setSpacing(12)

        alert_icon = QLabel()
        alert_icon.setPixmap(get_svg_pixmap("alert", "#d97706", 20))

        restart_text_layout = QVBoxLayout()
        restart_text_layout.setSpacing(2)
        self.restart_title = QLabel(t("restart_required_title"))
        self.restart_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #92400e;")
        self.restart_desc = QLabel(t("restart_required_msg"))
        self.restart_desc.setStyleSheet("font-size: 12px; color: #b45309;")

        restart_text_layout.addWidget(self.restart_title)
        restart_text_layout.addWidget(self.restart_desc)

        self.restart_btn = QPushButton(t("restart_now_btn"))
        self.restart_btn.setObjectName("PrimaryButton")
        self.restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_btn.setFixedHeight(34)
        self.restart_btn.clicked.connect(self.restart_requested.emit)

        restart_layout.addWidget(alert_icon)
        restart_layout.addLayout(restart_text_layout)
        restart_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        restart_layout.addWidget(self.restart_btn)

        self.restart_card.setVisible(False)
        self.content_layout.addWidget(self.restart_card)

        # -------------------------------------------------------------
        # 1. PERSONAL PREFERENCES SECTION (ALL USERS)
        # -------------------------------------------------------------
        lang_card = self._create_card()
        lang_layout = QVBoxLayout(lang_card)
        lang_layout.setContentsMargins(24, 20, 24, 20)
        lang_layout.setSpacing(10)

        lang_section_title = QLabel(t("section_personal"))
        lang_section_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px;")
        lang_layout.addWidget(lang_section_title)

        lang_row = QHBoxLayout()
        lang_text_layout = QVBoxLayout()
        lang_text_layout.setSpacing(2)

        self.lang_title = QLabel(t("language_label"))
        self.lang_title.setStyleSheet("font-size: 13px; font-weight: 500; color: #0f172a;")

        self.lang_desc = QLabel(t("language_desc"))
        self.lang_desc.setObjectName("SubtitleLabel")
        self.lang_desc.setStyleSheet("font-size: 12px; color: #64748b;")

        lang_text_layout.addWidget(self.lang_title)
        lang_text_layout.addWidget(self.lang_desc)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(180)
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Bahasa Indonesia", "id")
        current_idx = 0 if get_language() == "en" else 1
        self.lang_combo.setCurrentIndex(current_idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

        lang_row.addLayout(lang_text_layout)
        lang_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        lang_row.addWidget(self.lang_combo)

        lang_layout.addLayout(lang_row)
        self.content_layout.addWidget(lang_card)

        # -------------------------------------------------------------
        # 2. ADMIN & OWNER CONFIGURATION SECTIONS
        # -------------------------------------------------------------
        self.admin_container = QWidget()
        admin_layout = QVBoxLayout(self.admin_container)
        admin_layout.setContentsMargins(0, 0, 0, 0)
        admin_layout.setSpacing(18)

        # Display Card: Fullscreen Kiosk Mode & Monitor Selection
        display_card = self._create_card()
        display_layout = QVBoxLayout(display_card)
        display_layout.setContentsMargins(24, 20, 24, 20)
        display_layout.setSpacing(12)

        display_section_title = QLabel(t("section_display"))
        display_section_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px;")
        display_layout.addWidget(display_section_title)

        self.fullscreen_cb = QCheckBox(t("fullscreen_label"))
        self.fullscreen_cb.setChecked(config.fullscreen)
        self.fullscreen_cb.toggled.connect(self._on_fullscreen_toggled)

        self.fullscreen_desc = QLabel(t("fullscreen_desc"))
        self.fullscreen_desc.setObjectName("SubtitleLabel")
        self.fullscreen_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        self.fullscreen_desc.setWordWrap(True)

        display_layout.addWidget(self.fullscreen_cb)
        display_layout.addWidget(self.fullscreen_desc)

        # Target Display Monitor Selector
        # Detected Monitors dropdown with real device/EDID names & resolution
        screens_info = get_detected_screens_info()
        num_screens = len(screens_info)

        monitor_row = QHBoxLayout()
        monitor_text_layout = QVBoxLayout()
        monitor_text_layout.setSpacing(2)

        self.monitor_title = QLabel(t("target_monitor_label"))
        self.monitor_title.setStyleSheet("font-size: 13px; font-weight: 500; color: #0f172a;")

        self.monitor_desc = QLabel(t("target_monitor_desc", count=num_screens))
        self.monitor_desc.setObjectName("SubtitleLabel")
        self.monitor_desc.setStyleSheet("font-size: 12px; color: #64748b;")

        monitor_text_layout.addWidget(self.monitor_title)
        monitor_text_layout.addWidget(self.monitor_desc)

        self.monitor_combo = QComboBox()
        self.monitor_combo.setMinimumWidth(260)
        self.monitor_combo.setFixedHeight(36)
        for scr in screens_info:
            self.monitor_combo.addItem(scr["display_label"], scr["index"])

        cur_mon = config.monitor if config.monitor else 1
        idx = self.monitor_combo.findData(cur_mon)
        if idx >= 0:
            self.monitor_combo.setCurrentIndex(idx)
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)

        monitor_row.addLayout(monitor_text_layout)
        monitor_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        monitor_row.addWidget(self.monitor_combo)
        display_layout.addLayout(monitor_row)

        # Black Other Monitors Checkbox
        self.black_other_monitors_cb = QCheckBox(t("black_other_monitors_label"))
        self.black_other_monitors_cb.setChecked(config.black_other_monitors)
        self.black_other_monitors_cb.toggled.connect(self._on_black_other_monitors_toggled)

        self.black_other_desc_lbl = QLabel(t("black_other_monitors_desc"))
        self.black_other_desc_lbl.setObjectName("SubtitleLabel")
        self.black_other_desc_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        self.black_other_desc_lbl.setWordWrap(True)

        display_layout.addWidget(self.black_other_monitors_cb)
        display_layout.addWidget(self.black_other_desc_lbl)

        # Divider
        disp_div = QFrame()
        disp_div.setFrameShape(QFrame.Shape.HLine)
        disp_div.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        display_layout.addWidget(disp_div)

        # Customer Second Monitor Display Setting
        self.customer_display_cb = QCheckBox(t("customer_display_label"))
        self.customer_display_cb.setChecked(config.customer_display_enabled)
        self.customer_display_cb.toggled.connect(self._on_customer_display_toggled)

        self.customer_display_desc = QLabel(t("customer_display_desc"))
        self.customer_display_desc.setObjectName("SubtitleLabel")
        self.customer_display_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        self.customer_display_desc.setWordWrap(True)

        display_layout.addWidget(self.customer_display_cb)
        display_layout.addWidget(self.customer_display_desc)

        # Customer Target Monitor Selector
        cust_mon_row = QHBoxLayout()
        cust_mon_text = QVBoxLayout()
        cust_mon_text.setSpacing(2)

        self.cust_mon_title = QLabel(t("customer_display_monitor_label"))
        self.cust_mon_title.setStyleSheet("font-size: 13px; font-weight: 500; color: #0f172a;")

        cust_mon_text.addWidget(self.cust_mon_title)

        self.cust_mon_combo = QComboBox()
        self.cust_mon_combo.setMinimumWidth(260)
        self.cust_mon_combo.setFixedHeight(36)
        for scr in screens_info:
            self.cust_mon_combo.addItem(scr["display_label"], scr["index"])

        cur_cust_mon = config.customer_display_monitor if config.customer_display_monitor else 2
        idx_cust = self.cust_mon_combo.findData(cur_cust_mon)
        if idx_cust >= 0:
            self.cust_mon_combo.setCurrentIndex(idx_cust)
        self.cust_mon_combo.currentIndexChanged.connect(self._on_customer_monitor_changed)

        cust_mon_row.addLayout(cust_mon_text)
        cust_mon_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        cust_mon_row.addWidget(self.cust_mon_combo)
        display_layout.addLayout(cust_mon_row)

        admin_layout.addWidget(display_card)

        # -------------------------------------------------------------
        # PAYMENT OPTIONS & QRIS CONFIGURATION CARD
        # -------------------------------------------------------------
        pay_card = self._create_card()
        pay_layout = QVBoxLayout(pay_card)
        pay_layout.setContentsMargins(24, 20, 24, 20)
        pay_layout.setSpacing(14)

        pay_section_title = QLabel(t("section_payments"))
        pay_section_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px;")
        pay_layout.addWidget(pay_section_title)

        self.pay_options_title = QLabel(t("enable_payment_options_label"))
        self.pay_options_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")
        self.pay_options_desc = QLabel(t("enable_payment_options_desc"))
        self.pay_options_desc.setObjectName("SubtitleLabel")
        self.pay_options_desc.setStyleSheet("font-size: 12px; color: #64748b;")

        pay_layout.addWidget(self.pay_options_title)
        pay_layout.addWidget(self.pay_options_desc)

        # Payment options checkboxes grid
        opts_grid = QGridLayout()
        opts_grid.setSpacing(10)

        self.pay_cash_cb = QCheckBox("Cash / Tunai")
        self.pay_cash_cb.setChecked(config.payment_cash_enabled)
        self.pay_cash_cb.toggled.connect(lambda c: self._on_payment_option_toggled("cash", c))

        self.pay_qris_cb = QCheckBox("QRIS")
        self.pay_qris_cb.setChecked(config.payment_qris_enabled)
        self.pay_qris_cb.toggled.connect(lambda c: self._on_payment_option_toggled("qris", c))

        self.pay_debit_cb = QCheckBox("Kartu Debit / Kredit")
        self.pay_debit_cb.setChecked(config.payment_debit_enabled)
        self.pay_debit_cb.toggled.connect(lambda c: self._on_payment_option_toggled("debit", c))

        self.pay_debt_cb = QCheckBox("Debt / Utang")
        self.pay_debt_cb.setChecked(config.payment_debt_enabled)
        self.pay_debt_cb.toggled.connect(lambda c: self._on_payment_option_toggled("debt", c))

        opts_grid.addWidget(self.pay_cash_cb, 0, 0)
        opts_grid.addWidget(self.pay_qris_cb, 0, 1)
        opts_grid.addWidget(self.pay_debit_cb, 1, 0)
        opts_grid.addWidget(self.pay_debt_cb, 1, 1)
        pay_layout.addLayout(opts_grid)

        # Divider
        p_div = QFrame()
        p_div.setFrameShape(QFrame.Shape.HLine)
        p_div.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        pay_layout.addWidget(p_div)

        # QRIS Setup Box
        self.qris_setup_box = QWidget()
        qris_setup_layout = QVBoxLayout(self.qris_setup_box)
        qris_setup_layout.setContentsMargins(0, 0, 0, 0)
        qris_setup_layout.setSpacing(10)

        self.qris_title = QLabel(t("qris_config_title"))
        self.qris_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")

        self.qris_desc = QLabel(t("qris_config_desc"))
        self.qris_desc.setObjectName("SubtitleLabel")
        self.qris_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        self.qris_desc.setWordWrap(True)

        qris_setup_layout.addWidget(self.qris_title)
        qris_setup_layout.addWidget(self.qris_desc)

        # Upload & Payload Row
        upload_row = QHBoxLayout()
        upload_row.setSpacing(10)

        self.upload_qris_btn = QPushButton(f"  {t('upload_qris_btn')}")
        self.upload_qris_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_qris_btn.setIcon(get_svg_icon("qr-code", ThemeColors.TEXT_PRIMARY, 16))
        self.upload_qris_btn.setFixedHeight(36)
        self.upload_qris_btn.clicked.connect(self._upload_qris_image)

        upload_row.addWidget(self.upload_qris_btn)
        upload_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        qris_setup_layout.addLayout(upload_row)

        # QRIS String Payload input
        payload_row = QHBoxLayout()
        payload_row.setSpacing(8)

        self.qris_input = QLineEdit()
        self.qris_input.setPlaceholderText("00020101021126600014ID.LINKAJA...")
        self.qris_input.setText(config.qris_static_payload)
        self.qris_input.setFixedHeight(36)

        self.save_qris_btn = QPushButton(t("save_qris_btn"))
        self.save_qris_btn.setObjectName("PrimaryButton")
        self.save_qris_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_qris_btn.setFixedHeight(36)
        self.save_qris_btn.clicked.connect(self._save_qris_payload)

        payload_row.addWidget(self.qris_input, stretch=1)
        payload_row.addWidget(self.save_qris_btn)
        qris_setup_layout.addLayout(payload_row)

        # Decoded QRIS Merchant Info Display
        self.qris_info_card = QFrame()
        self.qris_info_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;")
        qris_info_layout = QHBoxLayout(self.qris_info_card)
        qris_info_layout.setContentsMargins(12, 8, 12, 8)

        self.qris_info_lbl = QLabel()
        self.qris_info_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: #0891b2;")
        qris_info_layout.addWidget(self.qris_info_lbl)
        self._refresh_qris_info_display()

        qris_setup_layout.addWidget(self.qris_info_card)
        pay_layout.addWidget(self.qris_setup_box)

        admin_layout.addWidget(pay_card)

        # Security Card: Authentication Code
        auth_card = self._create_card()
        auth_layout = QVBoxLayout(auth_card)
        auth_layout.setContentsMargins(24, 20, 24, 20)
        auth_layout.setSpacing(12)

        auth_section_title = QLabel(t("section_security"))
        auth_section_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px;")
        auth_layout.addWidget(auth_section_title)

        self.auth_title = QLabel(t("auth_code_label"))
        self.auth_title.setStyleSheet("font-size: 13px; font-weight: 500; color: #0f172a;")

        self.auth_desc = QLabel(t("auth_code_desc"))
        self.auth_desc.setObjectName("SubtitleLabel")
        self.auth_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        self.auth_desc.setWordWrap(True)

        token_row = QHBoxLayout()
        token_row.setSpacing(8)

        self.token_input = QLineEdit()
        self.token_input.setText(config.credential_token)
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Enter system credential token")

        self.toggle_token_btn = QPushButton()
        self.toggle_token_btn.setObjectName("IconButton")
        self.toggle_token_btn.setFixedSize(36, 36)
        self.toggle_token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)

        self.save_token_btn = QPushButton(t("save_code_btn"))
        self.save_token_btn.setObjectName("PrimaryButton")
        self.save_token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_token_btn.setFixedHeight(36)
        self.save_token_btn.clicked.connect(self._save_token)

        token_row.addWidget(self.token_input)
        token_row.addWidget(self.toggle_token_btn)
        token_row.addWidget(self.save_token_btn)

        auth_layout.addWidget(self.auth_title)
        auth_layout.addWidget(self.auth_desc)
        auth_layout.addLayout(token_row)
        admin_layout.addWidget(auth_card)

        # Branding Card: Sidebar Logo
        logo_card = self._create_card()
        logo_layout = QVBoxLayout(logo_card)
        logo_layout.setContentsMargins(24, 20, 24, 20)
        logo_layout.setSpacing(14)

        logo_section_title = QLabel(t("section_branding"))
        logo_section_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px;")
        logo_layout.addWidget(logo_section_title)

        self.logo_title = QLabel(t("sidebar_logo_label"))
        self.logo_title.setStyleSheet("font-size: 13px; font-weight: 500; color: #0f172a;")

        rec_box = QHBoxLayout()
        rec_box.setSpacing(8)
        rec_icon = QLabel()
        rec_icon.setPixmap(get_svg_pixmap("image", "#0891b2", 16))

        self.rec_label = QLabel(t("sidebar_logo_rec"))
        self.rec_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #0891b2;")

        rec_box.addWidget(rec_icon)
        rec_box.addWidget(self.rec_label)
        rec_box.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        preview_container = QFrame()
        preview_container.setStyleSheet("""
            background-color: #f8fafc;
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            padding: 16px;
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.logo_preview = QLabel()
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_logo_preview()
        preview_layout.addWidget(self.logo_preview)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.save_as_btn = QPushButton(f"  {t('save_as_btn')}")
        self.save_as_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_as_btn.setIcon(get_svg_icon("download", ThemeColors.TEXT_PRIMARY, 16))
        self.save_as_btn.clicked.connect(self._save_logo_as)

        self.change_logo_btn = QPushButton(f"  {t('change_logo_btn')}")
        self.change_logo_btn.setObjectName("PrimaryButton")
        self.change_logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_logo_btn.setIcon(get_svg_icon("upload", "#ffffff", 16))
        self.change_logo_btn.clicked.connect(self._change_logo)

        btn_row.addWidget(self.save_as_btn)
        btn_row.addWidget(self.change_logo_btn)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        logo_layout.addWidget(self.logo_title)
        logo_layout.addLayout(rec_box)
        logo_layout.addWidget(preview_container)
        logo_layout.addLayout(btn_row)
        admin_layout.addWidget(logo_card)

        # 6. DANGER ZONE / WIPE DATA TRANSACTION CARD
        danger_card = self._create_card()
        danger_card.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #fff1f2;
                border: 1px solid #fecdd3;
                border-radius: 12px;
            }
        """)
        danger_layout = QVBoxLayout(danger_card)
        danger_layout.setContentsMargins(20, 18, 20, 18)
        danger_layout.setSpacing(12)

        danger_head = QHBoxLayout()
        danger_head.setSpacing(8)
        d_icon = QLabel()
        d_icon.setPixmap(get_svg_pixmap("trash", "#e11d48", 18))
        self.danger_title = QLabel(t("wipe_transactions"))
        self.danger_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #9f1239;")
        danger_head.addWidget(d_icon)
        danger_head.addWidget(self.danger_title)
        danger_head.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        danger_layout.addLayout(danger_head)

        self.danger_desc = QLabel(t("wipe_transactions_desc"))
        self.danger_desc.setWordWrap(True)
        self.danger_desc.setStyleSheet("font-size: 12px; color: #be123c; line-height: 1.4;")
        danger_layout.addWidget(self.danger_desc)

        d_btn_row = QHBoxLayout()
        self.wipe_tx_btn = QPushButton(f"  {t('wipe_transactions')}")
        self.wipe_tx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wipe_tx_btn.setIcon(get_svg_icon("trash", "#ffffff", 14))
        self.wipe_tx_btn.setStyleSheet("""
            QPushButton {
                background-color: #e11d48;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #be123c;
            }
        """)
        self.wipe_tx_btn.clicked.connect(self._on_wipe_transactions_clicked)
        d_btn_row.addWidget(self.wipe_tx_btn)
        d_btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        danger_layout.addLayout(d_btn_row)

        admin_layout.addWidget(danger_card)

        self.content_layout.addWidget(self.admin_container)
        self.content_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def _create_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SurfaceCard")
        return card

    def set_user(self, user: Dict[str, Any]):
        """Sets active user and configures role-based section visibility."""
        self._current_user = user
        role = user.get("role", "Cashier") if user else "Cashier"
        is_admin = is_admin_or_owner(role)
        self.admin_container.setVisible(is_admin)

    def _show_restart_prompt(self):
        self.restart_card.setVisible(True)

    def _show_success(self, msg: str):
        self.status_banner.show_success(msg)

    def _show_error(self, msg: str):
        self.status_banner.show_error(msg)

    def _on_language_changed(self):
        lang = self.lang_combo.currentData()
        if lang and lang != get_language():
            config.set_language(lang, persist=True)
            self.language_changed.emit(lang)
            self._show_restart_prompt()
            self._show_success(t("settings_saved"))

    def _on_fullscreen_toggled(self, checked: bool):
        config.set_fullscreen(checked, persist=True)
        self.fullscreen_changed.emit(checked)
        self._show_restart_prompt()
        self._show_success(t("settings_saved"))

    def _on_monitor_changed(self):
        mon = self.monitor_combo.currentData()
        if mon:
            config.set_monitor(mon, persist=True)
            self.monitor_changed.emit(mon)
            self._show_restart_prompt()
            self._show_success(t("settings_saved"))

    def _on_black_other_monitors_toggled(self, checked: bool):
        config.set_black_other_monitors(checked, persist=True)
        self.black_other_monitors_changed.emit(checked)
        self._show_restart_prompt()
        self._show_success(t("settings_saved"))

    def _on_customer_display_toggled(self, checked: bool):
        mon = self.cust_mon_combo.currentData() or config.customer_display_monitor
        from services.customer_display_manager import customer_display_manager
        customer_display_manager.set_enabled(checked, mon)
        self._show_success(t("settings_saved"))

    def _on_customer_monitor_changed(self):
        mon = self.cust_mon_combo.currentData()
        if mon:
            from services.customer_display_manager import customer_display_manager
            customer_display_manager.set_enabled(config.customer_display_enabled, mon)
            self._show_success(t("settings_saved"))

    def _on_payment_option_toggled(self, option: str, checked: bool):
        config.set_payment_option(option, checked, persist=True)
        self._show_success(t("settings_saved"))

    def _upload_qris_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("upload_qris_btn"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            decoded_payload = decode_qr_from_image(file_path)
            if decoded_payload:
                self.qris_input.setText(decoded_payload)
                config.set_qris_config(decoded_payload, image_path=file_path, persist=True)
                parsed = parse_qris_data(decoded_payload)
                self._refresh_qris_info_display()
                self._show_success(t("qris_decoded_success", name=parsed["merchant_name"], nmid=parsed["nmid"]))
            else:
                self._show_error(t("qris_decode_failed"))

    def _save_qris_payload(self):
        raw = self.qris_input.text().strip()
        config.set_qris_config(raw, persist=True)
        self._refresh_qris_info_display()
        self._show_success(t("qris_saved"))

    def _refresh_qris_info_display(self):
        raw = config.qris_static_payload
        if raw:
            parsed = parse_qris_data(raw)
            self.qris_info_lbl.setText(f"✓ Merchant: {parsed['merchant_name']}  •  NMID: {parsed['nmid']}  •  ID: {parsed['id']}")
            self.qris_info_card.setVisible(True)
        else:
            self.qris_info_lbl.setText("Belum ada QRIS statis tersimpan.")
            self.qris_info_card.setVisible(False)

    def _toggle_token_visibility(self):
        self._token_visible = not self._token_visible
        if self._token_visible:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setIcon(get_svg_icon("eye-off", ThemeColors.TEXT_MUTED, 16))
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setIcon(get_svg_icon("eye", ThemeColors.TEXT_MUTED, 16))

    def _save_token(self):
        new_token = self.token_input.text().strip()
        if not new_token:
            self._show_error("Authentication Code cannot be empty.")
            return

        config.set_credential_token(new_token, persist=True)
        self._show_success(t("token_saved"))

    def _refresh_logo_preview(self):
        horizontal_path = ASSETS_DIR / "logo_horizontal.png"
        if horizontal_path.exists():
            pixmap = QPixmap(str(horizontal_path))
            scaled = pixmap.scaled(200, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_preview.setPixmap(scaled)
        else:
            self.logo_preview.setText("No Logo Image")

    def _save_logo_as(self):
        src_path = ASSETS_DIR / "logo_horizontal.png"
        if not src_path.exists():
            self._show_error("No current logo image to export.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Current Logo As",
            "logo_horizontal.png",
            "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg)"
        )
        if save_path:
            try:
                shutil.copyfile(str(src_path), save_path)
                self._show_success(t("logo_saved", filename=Path(save_path).name))
            except Exception as e:
                self._show_error(f"Failed to export logo: {e}")

    def _change_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select New Sidebar Logo",
            "",
            "Image Files (*.png *.jpg *.jpeg *.svg *.webp)"
        )
        if file_path:
            try:
                dest_path = ASSETS_DIR / "logo_horizontal.png"
                shutil.copyfile(file_path, str(dest_path))
                self._refresh_logo_preview()
                self.logo_updated.emit()
                self._show_success(t("logo_updated"))
            except Exception as e:
                self._show_error(f"Failed to update logo: {e}")

    def _on_wipe_transactions_clicked(self):
        reply = QMessageBox.warning(
            self,
            t("wipe_transactions_confirm_title"),
            t("wipe_transactions_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            from database.db_manager import db_manager
            from utils.logger import log_settings
            db_manager.wipe_transactions()
            log_settings("WIPE_TRANSACTIONS", "Admin wiped all transaction and sales history.")
            self._show_success(t("wipe_transactions_success"))

    def refresh_translations(self):
        self.title_label.setText(t("settings_title"))
        self.desc_label.setText(t("settings_subtitle"))
        self.restart_title.setText(t("restart_required_title"))
        self.restart_desc.setText(t("restart_required_msg"))
        self.restart_btn.setText(t("restart_now_btn"))
        self.lang_title.setText(t("language_label"))
        self.lang_desc.setText(t("language_desc"))
        cur_lang = get_language()
        idx_lang = self.lang_combo.findData(cur_lang)
        if idx_lang >= 0 and idx_lang != self.lang_combo.currentIndex():
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx_lang)
            self.lang_combo.blockSignals(False)
        self.fullscreen_cb.setText(t("fullscreen_label"))
        self.fullscreen_desc.setText(t("fullscreen_desc"))
        screens_info = get_detected_screens_info()
        self.monitor_title.setText(t("target_monitor_label"))
        self.monitor_desc.setText(t("target_monitor_desc", count=len(screens_info)))
        self.black_other_monitors_cb.setText(t("black_other_monitors_label"))
        self.black_other_desc_lbl.setText(t("black_other_monitors_desc"))
        self.customer_display_cb.setText(t("customer_display_label"))
        self.customer_display_desc.setText(t("customer_display_desc"))
        self.cust_mon_title.setText(t("customer_display_monitor_label"))
        self.auth_title.setText(t("auth_code_label"))
        self.auth_desc.setText(t("auth_code_desc"))
        self.save_token_btn.setText(t("save_code_btn"))
        self.pay_options_title.setText(t("enable_payment_options_label"))
        self.pay_options_desc.setText(t("enable_payment_options_desc"))
        self.qris_title.setText(t("qris_config_title"))
        self.qris_desc.setText(t("qris_config_desc"))
        self.upload_qris_btn.setText(f"  {t('upload_qris_btn')}")
        self.save_qris_btn.setText(t("save_qris_btn"))
        self.logo_title.setText(t("sidebar_logo_label"))
        self.rec_label.setText(t("sidebar_logo_rec"))
        self.save_as_btn.setText(f"  {t('save_as_btn')}")
        self.change_logo_btn.setText(f"  {t('change_logo_btn')}")
        self.danger_title.setText(t("wipe_transactions"))
        self.danger_desc.setText(t("wipe_transactions_desc"))
        self.wipe_tx_btn.setText(f"  {t('wipe_transactions')}")
