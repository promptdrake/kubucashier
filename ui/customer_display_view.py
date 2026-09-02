"""
Customer Facing Display (CFD) / Second Monitor Window for KubuCashier.
Real-time synchronized dual-screen POS customer display with clean Light Minimalist Black & White theme.
High-visibility, large-format typography for counter distance visibility:
- Huge prominent Kembalian / Change display (54px+ green badge).
- Large scannable Dynamic QRIS code and bold Total Tagihan.
- Live itemized order cart with large text and clear subtotals.
- Welcoming store branding & live Jakarta clock.
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpacerItem, QSizePolicy, QStackedWidget, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont, QIcon

from config import ASSETS_DIR, config
from database.db_manager import db_manager
from services.qris_service import convert_to_dynamic_qris, generate_qr_pixmap, parse_qris_data
from ui.i18n import t, get_language
from ui.datetime_utils import get_formatted_clock
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from utils.logger import log_cfd


class CustomerDisplayWindow(QMainWindow):
    """Secondary customer-facing monitor display with high-visibility large UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KubuCashier - Customer Display")
        self.setObjectName("CustomerDisplayWindow")
        self._set_window_icon()

        self.cart_items: Dict[int, Dict[str, Any]] = {}
        self.grand_total: float = 0.0
        self.current_user: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._setup_clock()
        self.set_idle_state()

    def _set_window_icon(self):
        ico_path = ASSETS_DIR / "app_icon.ico"
        png_path = ASSETS_DIR / "logo_square.png"
        if ico_path.exists():
            self.setWindowIcon(QIcon(str(ico_path)))
        elif png_path.exists():
            self.setWindowIcon(QIcon(str(png_path)))

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow#CustomerDisplayWindow, QWidget#CFDCentral {
                background-color: #f8fafc;
                color: #0f172a;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
            }
            QFrame#CustomerSuccessCard {
                background-color: #ffffff;
                border: 1px solid #bbf7d0;
                border-radius: 20px;
            }
            QFrame#TotalBox {
                background-color: #f1f5f9;
                border: none;
                border-radius: 14px;
            }
            QFrame#ChangeBox {
                background-color: #f0fdf4;
                border: 2px solid #86efac;
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        central = QWidget()
        central.setObjectName("CFDCentral")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(48, 32, 48, 32)
        main_layout.setSpacing(24)

        # -------------------------------------------------------------
        # TOP HEADER: BRANDING & LIVE WIB CLOCK
        # -------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(20)

        # Store Logo / Brand
        self.logo_label = QLabel()
        self._load_logo()
        header_bar.addWidget(self.logo_label)

        header_bar.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Live Clock Box
        clock_box = QHBoxLayout()
        clock_box.setSpacing(10)
        clock_icon = QLabel()
        clock_icon.setPixmap(get_svg_pixmap("clock", "#64748b", 20))

        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet("font-size: 16px; font-weight: 500; color: #64748b; font-family: monospace;")

        clock_box.addWidget(clock_icon)
        clock_box.addWidget(self.clock_lbl)
        header_bar.addLayout(clock_box)

        main_layout.addLayout(header_bar)

        # -------------------------------------------------------------
        # MAIN CONTENT STACK (IDLE / ACTIVE ORDER / CHECKOUT / SUCCESS)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        # Page 0: Idle State
        self.stack.addWidget(self._create_idle_page())

        # Page 1: Active Order State
        self.stack.addWidget(self._create_order_page())

        # Page 2: Checkout & Payment State
        self.stack.addWidget(self._create_checkout_page())

        # Page 3: Transaction Success State (With Star Rating)
        self.stack.addWidget(self._create_success_page())

        # Page 4: Store Break / Istirahat State
        self.stack.addWidget(self._create_break_page())

        main_layout.addWidget(self.stack, stretch=1)

        # -------------------------------------------------------------
        # BOTTOM FOOTER BAR
        # -------------------------------------------------------------
        footer_layout = QHBoxLayout()
        self.footer_lbl = QLabel("Terima kasih telah berbelanja • Thank you for your visit")
        self.footer_lbl.setStyleSheet("font-size: 14px; color: #94a3b8;")
        footer_layout.addWidget(self.footer_lbl)
        footer_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.cashier_shift_lbl = QLabel("KubuCashier Customer Display")
        self.cashier_shift_lbl.setStyleSheet("font-size: 14px; color: #94a3b8; font-weight: 500;")
        footer_layout.addWidget(self.cashier_shift_lbl)

        main_layout.addLayout(footer_layout)

    def _load_logo(self):
        horizontal_path = ASSETS_DIR / "logo_horizontal.png"
        if horizontal_path.exists():
            pix = QPixmap(str(horizontal_path))
            scaled = pix.scaled(220, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("KubuCashier")
            self.logo_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #0f172a;")

    # -----------------------------------------------------------------
    # PAGE 0: IDLE / WELCOME STATE
    # -----------------------------------------------------------------
    def _create_idle_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("CustomerCard")
        card.setMinimumWidth(850)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(60, 60, 60, 60)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(20)

        icon_box = QLabel()
        icon_box.setFixedSize(110, 110)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet("background-color: #f1f5f9; border-radius: 55px;")
        icon_box.setPixmap(get_svg_pixmap("cart", "#0f172a", 54))

        title_lbl = QLabel("Selamat Datang di Kubu Cashier")
        title_lbl.setStyleSheet("font-size: 34px; font-weight: 700; color: #0f172a;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QLabel("Silakan memesan pada kasir kami. Rincian pesanan Anda akan muncul di layar ini secara langsung.")
        sub_lbl.setStyleSheet("font-size: 17px; color: #64748b; max-width: 650px; line-height: 1.4;")
        sub_lbl.setWordWrap(True)
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(icon_box, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(sub_lbl)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    # -----------------------------------------------------------------
    # PAGE 1: ACTIVE ORDER ITEM LIST & REAL-TIME BILL
    # -----------------------------------------------------------------
    def _create_order_page(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # Left: Order Items Table
        table_card = QFrame()
        table_card.setObjectName("CustomerCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(28, 24, 28, 24)
        table_layout.setSpacing(16)

        table_title = QLabel("Daftar Pesanan / Current Order")
        table_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        table_layout.addWidget(table_title)

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(4)
        self.order_table.setHorizontalHeaderLabels(["Menu / Item", "Harga Satuan", "Qty", "Subtotal"])
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.order_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.order_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.order_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.verticalHeader().setDefaultSectionSize(54)
        self.order_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.order_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.order_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #0f172a;
                border: none;
                gridline-color: #f1f5f9;
                font-size: 15px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                font-weight: 600;
                font-size: 14px;
                padding: 10px 14px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
        """)

        table_layout.addWidget(self.order_table)
        layout.addWidget(table_card, stretch=6)

        # Right: Grand Total Summary Box
        summary_card = QFrame()
        summary_card.setObjectName("CustomerCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(32, 32, 32, 32)
        summary_layout.setSpacing(20)

        sum_title = QLabel("Ringkasan Pembayaran")
        sum_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        summary_layout.addWidget(sum_title)

        self.cfd_items_count_lbl = QLabel("Total Item: 0")
        self.cfd_items_count_lbl.setStyleSheet("font-size: 16px; color: #64748b; font-weight: 500;")
        summary_layout.addWidget(self.cfd_items_count_lbl)

        # Subtotal row (Itemized)
        self.cfd_subtotal_row = QWidget()
        cfd_sub_layout = QHBoxLayout(self.cfd_subtotal_row)
        cfd_sub_layout.setContentsMargins(0, 0, 0, 0)
        cfd_sub_lbl = QLabel("Subtotal Pesanan:")
        cfd_sub_lbl.setStyleSheet("font-size: 15px; color: #64748b; font-weight: 500;")
        self.cfd_subtotal_val = QLabel("Rp 0")
        self.cfd_subtotal_val.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        cfd_sub_layout.addWidget(cfd_sub_lbl)
        cfd_sub_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        cfd_sub_layout.addWidget(self.cfd_subtotal_val)
        summary_layout.addWidget(self.cfd_subtotal_row)

        # Fee row (Itemized)
        self.cfd_fee_row = QWidget()
        cfd_fee_layout = QHBoxLayout(self.cfd_fee_row)
        cfd_fee_layout.setContentsMargins(0, 0, 0, 0)
        self.cfd_fee_lbl = QLabel("Biaya / Pajak:")
        self.cfd_fee_lbl.setStyleSheet("font-size: 15px; color: #64748b; font-weight: 500;")
        self.cfd_fee_val = QLabel("+ Rp 0")
        self.cfd_fee_val.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        cfd_fee_layout.addWidget(self.cfd_fee_lbl)
        cfd_fee_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        cfd_fee_layout.addWidget(self.cfd_fee_val)
        summary_layout.addWidget(self.cfd_fee_row)

        self.cfd_subtotal_row.setVisible(False)
        self.cfd_fee_row.setVisible(False)

        summary_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        tot_card = QFrame()
        tot_card.setObjectName("TotalBox")
        tot_layout = QVBoxLayout(tot_card)
        tot_layout.setContentsMargins(24, 20, 24, 20)
        tot_layout.setSpacing(6)

        tot_caption = QLabel("TOTAL TAGIHAN")
        tot_caption.setStyleSheet("font-size: 13px; font-weight: 700; color: #64748b; letter-spacing: 1px;")

        self.cfd_grand_total_lbl = QLabel("Rp 0")
        self.cfd_grand_total_lbl.setStyleSheet("font-size: 42px; font-weight: 800; color: #0f172a;")

        tot_layout.addWidget(tot_caption)
        tot_layout.addWidget(self.cfd_grand_total_lbl)
        summary_layout.addWidget(tot_card)

        layout.addWidget(summary_card, stretch=4)
        return widget

    # -----------------------------------------------------------------
    # PAGE 2: CHECKOUT & PAYMENT MODES (QRIS, CASH, DEBIT)
    # -----------------------------------------------------------------
    def _create_checkout_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.checkout_card = QFrame()
        self.checkout_card.setObjectName("CustomerCard")
        self.checkout_card.setMinimumWidth(880)
        self.checkout_card_layout = QVBoxLayout(self.checkout_card)
        self.checkout_card_layout.setContentsMargins(48, 44, 48, 44)
        self.checkout_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.checkout_card_layout.setSpacing(18)

        # Header Title
        self.pay_method_header = QLabel("Pembayaran")
        self.pay_method_header.setStyleSheet("font-size: 24px; font-weight: 700; color: #0f172a;")
        self.pay_method_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Total Tagihan Display
        self.pay_total_box = QFrame()
        self.pay_total_box.setObjectName("TotalBox")
        self.pay_total_box.setMinimumWidth(680)
        pay_tot_layout = QVBoxLayout(self.pay_total_box)
        pay_tot_layout.setContentsMargins(32, 20, 32, 20)
        pay_tot_layout.setSpacing(4)
        pay_tot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tot_tag_cap = QLabel("TOTAL TAGIHAN")
        tot_tag_cap.setStyleSheet("font-size: 13px; font-weight: 700; color: #64748b; letter-spacing: 1px;")
        tot_tag_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pay_amount_display = QLabel("Rp 0")
        self.pay_amount_display.setStyleSheet("font-size: 42px; font-weight: 800; color: #0f172a;")
        self.pay_amount_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pay_fee_breakdown_lbl = QLabel("")
        self.pay_fee_breakdown_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #64748b; margin-top: 4px;")
        self.pay_fee_breakdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pay_fee_breakdown_lbl.setVisible(False)

        pay_tot_layout.addWidget(tot_tag_cap)
        pay_tot_layout.addWidget(self.pay_amount_display)
        pay_tot_layout.addWidget(self.pay_fee_breakdown_lbl)

        # --- Sub-view 1: QRIS View ---
        self.qris_view_widget = QWidget()
        qris_v_layout = QVBoxLayout(self.qris_view_widget)
        qris_v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qris_v_layout.setSpacing(12)

        self.cfd_qr_label = QLabel()
        self.cfd_qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cfd_qr_label.setFixedSize(280, 280)
        self.cfd_qr_label.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 10px;")

        self.qris_instruction_lbl = QLabel("Pindai kode QRIS dengan aplikasi e-wallet / mobile banking Anda.")
        self.qris_instruction_lbl.setStyleSheet("font-size: 16px; color: #64748b; font-weight: 500;")
        self.qris_instruction_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qris_v_layout.addWidget(self.cfd_qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        qris_v_layout.addWidget(self.qris_instruction_lbl)

        # --- Sub-view 2: CASH (LARGE KEMBALIAN DISPLAY) ---
        self.cash_view_widget = QWidget()
        self.cash_view_widget.setMinimumWidth(680)
        cash_v_layout = QVBoxLayout(self.cash_view_widget)
        cash_v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cash_v_layout.setSpacing(16)



        # HUGE PROMINENT KEMBALIAN BOX (Ample width, no text clipping)
        self.change_box_card = QFrame()
        self.change_box_card.setObjectName("ChangeBox")
        self.change_box_card.setMinimumWidth(680)
        change_c_layout = QVBoxLayout(self.change_box_card)
        change_c_layout.setContentsMargins(40, 24, 40, 24)
        change_c_layout.setSpacing(6)
        change_c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        change_badge = QLabel("KEMBALIAN ANDA")
        change_badge.setStyleSheet("font-size: 16px; font-weight: 800; color: #15803d; letter-spacing: 1.5px;")
        change_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cash_change_amount_lbl = QLabel("Rp 0")
        self.cash_change_amount_lbl.setStyleSheet("font-size: 50px; font-weight: 900; color: #16a34a;")
        self.cash_change_amount_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        change_c_layout.addWidget(change_badge)
        change_c_layout.addWidget(self.cash_change_amount_lbl)

        cash_v_layout.addWidget(self.change_box_card)

        # --- Sub-view 3: EDC / Card & General View ---
        self.generic_view_widget = QWidget()
        gen_v_layout = QVBoxLayout(self.generic_view_widget)
        gen_v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gen_v_layout.setSpacing(14)

        self.gen_icon = QLabel()
        self.gen_icon.setPixmap(get_svg_pixmap("credit-card", "#0f172a", 64))
        self.gen_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gen_msg = QLabel("Silakan tempel atau gesek kartu pada mesin EDC.")
        self.gen_msg.setStyleSheet("font-size: 18px; font-weight: 600; color: #0f172a;")
        self.gen_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gen_v_layout.addWidget(self.gen_icon)
        gen_v_layout.addWidget(self.gen_msg)

        # Add all to checkout card
        self.checkout_card_layout.addWidget(self.pay_method_header)
        self.checkout_card_layout.addWidget(self.pay_total_box)
        self.checkout_card_layout.addWidget(self.qris_view_widget)
        self.checkout_card_layout.addWidget(self.cash_view_widget)
        self.checkout_card_layout.addWidget(self.generic_view_widget)

        layout.addWidget(self.checkout_card, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    # -----------------------------------------------------------------
    # PAGE 3: TRANSACTION SUCCESS CONFIRMATION
    # -----------------------------------------------------------------
    def _create_success_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("CustomerSuccessCard")
        card.setMinimumWidth(850)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(54, 50, 54, 50)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setSpacing(16)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap("check-circle", "#16a34a", 80))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.succ_title_lbl = QLabel(t("thank_you_for_purchasing"))
        self.succ_title_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #16a34a;")
        self.succ_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.succ_invoice_lbl = QLabel("Invoice #INV-2026-0001")
        self.succ_invoice_lbl.setStyleSheet("font-size: 16px; color: #64748b; font-weight: 500;")
        self.succ_invoice_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Large Change Card in Success
        self.succ_change_card = QFrame()
        self.succ_change_card.setObjectName("ChangeBox")
        succ_chg_layout = QVBoxLayout(self.succ_change_card)
        succ_chg_layout.setContentsMargins(32, 20, 32, 20)
        succ_chg_layout.setSpacing(4)
        succ_chg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        succ_chg_title = QLabel("KEMBALIAN ANDA")
        succ_chg_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #15803d; letter-spacing: 1.5px;")
        succ_chg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.succ_change_amount_lbl = QLabel("Rp 0")
        self.succ_change_amount_lbl.setStyleSheet("font-size: 48px; font-weight: 900; color: #16a34a;")
        self.succ_change_amount_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        succ_chg_layout.addWidget(succ_chg_title)
        succ_chg_layout.addWidget(self.succ_change_amount_lbl)

        # -------------------------------------------------------------
        # Star Rating Section on Success Screen
        # -------------------------------------------------------------
        rating_box = QVBoxLayout()
        rating_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rating_box.setSpacing(8)

        self.rating_prompt_lbl = QLabel("Bagaimana Pengalaman Pelayanan Kami?")
        self.rating_prompt_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 6px;")
        self.rating_prompt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stars_layout = QHBoxLayout()
        self.stars_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stars_layout.setSpacing(10)

        self.star_buttons = []
        for star_idx in range(1, 6):
            btn = QPushButton(f"⭐ {star_idx}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(70, 44)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: 700;
                    color: #0f172a;
                }
                QPushButton:hover {
                    background-color: #fef08a;
                    border-color: #eab308;
                    color: #a16207;
                }
            """)
            btn.clicked.connect(lambda _, s=star_idx: self._on_star_clicked(s))
            self.star_buttons.append(btn)
            self.stars_layout.addWidget(btn)

        self.rating_feedback_lbl = QLabel("")
        self.rating_feedback_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ca8a04;")
        self.rating_feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        rating_box.addWidget(self.rating_prompt_lbl)
        rating_box.addLayout(self.stars_layout)
        rating_box.addWidget(self.rating_feedback_lbl)

        c_layout.addWidget(icon_lbl)
        c_layout.addWidget(self.succ_title_lbl)
        c_layout.addWidget(self.succ_invoice_lbl)
        c_layout.addWidget(self.succ_change_card)
        c_layout.addLayout(rating_box)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    def _create_break_page(self) -> QWidget:
        """Page 4: Store Break / Istirahat Display."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("CustomerBreakCard")
        card.setMinimumWidth(850)
        card.setStyleSheet("""
            QFrame#CustomerBreakCard {
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 20px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(54, 50, 54, 50)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setSpacing(16)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap("coffee", "#64748b", 80))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel("Kasir Sedang Istirahat")
        title_lbl.setStyleSheet("font-size: 32px; font-weight: 800; color: #0f172a;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_lbl = QLabel("Mohon tunggu sebentar, kasir kami akan segera kembali melayani Anda.\nCurrently on Break - We'll be right back!")
        subtitle_lbl.setStyleSheet("font-size: 16px; color: #64748b; font-weight: 500; line-height: 1.4;")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        c_layout.addWidget(icon_lbl)
        c_layout.addWidget(title_lbl)
        c_layout.addWidget(subtitle_lbl)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    def _on_star_clicked(self, star_num: int):
        """Records star rating from customer screen."""
        if hasattr(self, "current_invoice") and self.current_invoice:
            db_manager.record_transaction_rating(self.current_invoice, star_num)
            log_cfd("RATING", f"Customer rated {star_num} Stars for Invoice #{self.current_invoice}")

        for idx, btn in enumerate(self.star_buttons, start=1):
            if idx <= star_num:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #fef08a;
                        border: 2px solid #eab308;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: 800;
                        color: #a16207;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        border: 2px solid #e2e8f0;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: 700;
                        color: #94a3b8;
                    }
                """)

        self.rating_feedback_lbl.setText(f"⭐⭐⭐⭐⭐ Terima kasih atas penilaian {star_num} Bintang Anda!")
        QTimer.singleShot(2500, self.set_idle_state)

    # -----------------------------------------------------------------
    # SYNCHRONIZATION SLOTS (CALLED FROM POS REGISTER)
    # -----------------------------------------------------------------
    def update_cart(
        self,
        cart_items: Dict[int, Dict[str, Any]],
        grand_total: float,
        subtotal_amount: float = 0.0,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0
    ):
        """Live updates customer display with current POS cart items and fee breakdown."""
        self.cart_items = cart_items
        self.grand_total = grand_total
        self.subtotal_amount = subtotal_amount if subtotal_amount > 0 else (grand_total - fee_amount if fee_amount > 0 else grand_total)
        self.fee_type = fee_type
        self.fee_value = fee_value
        self.fee_amount = fee_amount

        if not cart_items:
            self.set_idle_state()
            return

        self.stack.setCurrentIndex(1)  # Active Order page
        tot_str = f"Rp {grand_total:,.0f}".replace(",", ".")
        self.cfd_grand_total_lbl.setText(tot_str)

        total_qty = sum(item["quantity"] for item in cart_items.values())
        self.cfd_items_count_lbl.setText(f"Total Item: {total_qty}")

        # Itemized Subtotal & Fee
        if fee_amount > 0:
            sub_str = f"Rp {self.subtotal_amount:,.0f}".replace(",", ".")
            self.cfd_subtotal_val.setText(sub_str)
            fee_tag = f"Biaya / Pajak ({fee_value:g}%):" if fee_type == "percent" else "Biaya / Pajak:"
            self.cfd_fee_lbl.setText(fee_tag)
            self.cfd_fee_val.setText(f"+ Rp {fee_amount:,.0f}".replace(",", "."))
            self.cfd_subtotal_row.setVisible(True)
            self.cfd_fee_row.setVisible(True)
        else:
            self.cfd_subtotal_row.setVisible(False)
            self.cfd_fee_row.setVisible(False)

        # Update table rows
        self.order_table.setRowCount(len(cart_items))
        for row, (prod_id, item) in enumerate(cart_items.items()):
            name_item = QTableWidgetItem(str(item["name"]))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            name_item.setFont(QFont("", 14, QFont.Weight.Medium))

            unit_val = float(item["price"])
            unit_str = f"Rp {unit_val:,.0f}".replace(",", ".")
            unit_item = QTableWidgetItem(unit_str)
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            unit_item.setFont(QFont("", 14, QFont.Weight.Medium))

            qty_item = QTableWidgetItem(f"x{item['quantity']}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            qty_item.setFont(QFont("", 14, QFont.Weight.DemiBold))

            subtotal_val = float(item["price"] * item["quantity"])
            subtotal_str = f"Rp {subtotal_val:,.0f}".replace(",", ".")
            sub_item = QTableWidgetItem(subtotal_str)
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sub_item.setFont(QFont("", 14, QFont.Weight.Bold))

            self.order_table.setItem(row, 0, name_item)
            self.order_table.setItem(row, 1, unit_item)
            self.order_table.setItem(row, 2, qty_item)
            self.order_table.setItem(row, 3, sub_item)

    def show_checkout_state(
        self,
        method: str,
        total_amount: float,
        paid_amount: float = 0.0,
        change_amount: float = 0.0,
        subtotal_amount: float = 0.0,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0
    ):
        """Configures Customer Display for active payment checkout with optional fee."""
        self.stack.setCurrentIndex(2)  # Checkout state
        tot_str = f"Rp {total_amount:,.0f}".replace(",", ".")
        self.pay_amount_display.setText(tot_str)

        if fee_amount > 0:
            sub_val = subtotal_amount if subtotal_amount > 0 else (total_amount - fee_amount)
            sub_str = f"Rp {sub_val:,.0f}".replace(",", ".")
            fee_tag = f"Biaya ({fee_value:g}%)" if fee_type == "percent" else "Biaya"
            fee_str = f"+ Rp {fee_amount:,.0f}".replace(",", ".")
            self.pay_fee_breakdown_lbl.setText(f"Subtotal: {sub_str}  •  {fee_tag}: {fee_str}")
            self.pay_fee_breakdown_lbl.setVisible(True)
        else:
            self.pay_fee_breakdown_lbl.setVisible(False)

        if method == "QRIS":
            self.pay_method_header.setText("Pembayaran QRIS")
            self.qris_view_widget.setVisible(True)
            self.cash_view_widget.setVisible(False)
            self.generic_view_widget.setVisible(False)

            if config.qris_static_payload:
                dyn_qr = convert_to_dynamic_qris(config.qris_static_payload, int(total_amount))
                if dyn_qr:
                    qr_pixmap = generate_qr_pixmap(dyn_qr, size=240)
                    self.cfd_qr_label.setPixmap(qr_pixmap)
                else:
                    self.cfd_qr_label.setPixmap(get_svg_pixmap("qr-code", "#0f172a", 120))
            else:
                self.cfd_qr_label.setPixmap(get_svg_pixmap("qr-code", "#0f172a", 120))

        elif method == "Cash":
            self.pay_method_header.setText("Pembayaran Tunai (Cash)")
            self.qris_view_widget.setVisible(False)
            self.cash_view_widget.setVisible(True)
            self.generic_view_widget.setVisible(False)

            paid_str = f"Rp {paid_amount:,.0f}".replace(",", ".")
            chg_str = f"Rp {change_amount:,.0f}".replace(",", ".")
            self.cash_change_amount_lbl.setText(chg_str)

        elif method == "Debit":
            self.pay_method_header.setText("Pembayaran Kartu / EDC")
            self.qris_view_widget.setVisible(False)
            self.cash_view_widget.setVisible(False)
            self.generic_view_widget.setVisible(True)
            self.gen_msg.setText("Silakan tempel atau masukkan kartu pada mesin EDC.")
        else:
            self.pay_method_header.setText("Pembayaran")
            self.qris_view_widget.setVisible(False)
            self.cash_view_widget.setVisible(False)
            self.generic_view_widget.setVisible(True)
            self.gen_msg.setText("Silakan selesaikan transaksi dengan kasir.")

    def show_transaction_success(self, invoice_no: str, change_amount: float = 0.0):
        """Shows success message with star rating and returns to idle state."""
        self.current_invoice = invoice_no
        self.stack.setCurrentIndex(3)
        self.succ_invoice_lbl.setText(f"Invoice #{invoice_no}")
        self.rating_feedback_lbl.setText("")

        for btn in self.star_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: 700;
                    color: #0f172a;
                }
                QPushButton:hover {
                    background-color: #fef08a;
                    border-color: #eab308;
                    color: #a16207;
                }
            """)

        if change_amount > 0:
            chg_str = f"Rp {change_amount:,.0f}".replace(",", ".")
            self.succ_change_amount_lbl.setText(chg_str)
            self.succ_change_card.setVisible(True)
        else:
            self.succ_change_card.setVisible(False)

        QTimer.singleShot(7000, self.set_idle_state)

    def set_break_state(self):
        """Switches customer display to Store Break Mode."""
        self.stack.setCurrentIndex(4)

    def resume_from_break(self):
        """Resumes customer display from Break Mode."""
        if self.cart_items and self.grand_total > 0:
            self.stack.setCurrentIndex(1)
        else:
            self.set_idle_state()

    def set_idle_state(self):
        self.cart_items.clear()
        self.grand_total = 0.0
        self.order_table.setRowCount(0)
        self.cfd_grand_total_lbl.setText("Rp 0")
        self.cfd_items_count_lbl.setText("Total Item: 0")
        self.pay_amount_display.setText("Rp 0")
        self.cash_change_amount_lbl.setText("Rp 0")
        self.stack.setCurrentIndex(0)

    def set_user(self, user: Optional[Dict[str, Any]]):
        self.current_user = user
        if user:
            name = user.get("name", "Cashier")
            self.cashier_shift_lbl.setText(f"Kasir: {name} • KubuCashier")
        else:
            self.cashier_shift_lbl.setText("KubuCashier Customer Display")

    def _setup_clock(self):
        self._update_clock()
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

    def _update_clock(self):
        clock_text = get_formatted_clock(get_language())
        self.clock_lbl.setText(clock_text)
