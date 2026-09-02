"""
Payment and Checkout Modal Dialog for KubuCashier.
Clean, borderless modern UI supporting Cash, QRIS (Static-to-Dynamic QR), Debit Card (Empty / Clean), and Debt.
Dynamically displays only payment methods enabled in Settings.
Responsive layout supporting zoom scaling and dual-screen customer display sync.
"""

from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QGridLayout,
    QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config import config
from services.qris_service import convert_to_dynamic_qris, generate_qr_pixmap, parse_qris_data
from services.customer_display_manager import customer_display_manager
from utils.logger import log_checkout
from ui.i18n import t
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class CheckoutDialog(QDialog):
    """Modern borderless checkout dialog supporting Cash, QRIS, Debit Card, and Debt."""

    def __init__(
        self,
        grand_total: float,
        items_count: int,
        scale: float = 1.0,
        subtotal_amount: Optional[float] = None,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0,
        parent=None
    ):
        super().__init__(parent)
        self.grand_total = grand_total
        self.items_count = items_count
        self.scale = scale
        self.subtotal_amount = subtotal_amount if subtotal_amount is not None else (grand_total - fee_amount)
        self.fee_type = fee_type
        self.fee_value = fee_value
        self.fee_amount = fee_amount
        self.selected_method: str = "Cash"
        self.paid_amount: float = grand_total
        self.change_amount: float = 0.0
        self.payment_note: str = ""

        self.setWindowTitle(t("checkout_title"))
        min_w = max(480, int(520 * scale))
        min_h = max(520, int(580 * scale))
        self.setMinimumSize(min_w, min_h)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        pad = max(18, int(24 * self.scale))
        spacing = max(10, int(14 * self.scale))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(spacing)

        # 1. Header (Clean & Minimalist)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon_size = max(18, int(22 * self.scale))
        icon_label.setPixmap(get_svg_pixmap("banknote", "#0f172a", icon_size))

        title_lbl = QLabel(t("checkout_title"))
        f_title = max(14, int(17 * self.scale))
        title_lbl.setStyleSheet(f"font-size: {f_title}px; font-weight: 700; color: #0f172a;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_lbl)
        header_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(header_layout)

        # Status Alert Banner
        self.status_banner = NotificationBanner(self)
        layout.addWidget(self.status_banner)

        # 2. Total Bill Summary Box (Completely borderless, smooth surface)
        bill_card = QFrame()
        bill_card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: none;
                border-radius: 10px;
            }
        """)
        bill_layout = QVBoxLayout(bill_card)
        bill_layout.setContentsMargins(16, 12, 16, 12)
        bill_layout.setSpacing(2)

        if self.fee_amount > 0:
            fee_tag = f"{self.fee_value:g}%" if self.fee_type == "percent" else "Nominal"
            sub_str = f"Rp {self.subtotal_amount:,.0f}".replace(",", ".")
            fee_str = f"+ Rp {self.fee_amount:,.0f}".replace(",", ".")
            bill_caption = QLabel(f"Subtotal: {sub_str} • Biaya ({fee_tag}): {fee_str}")
        else:
            bill_caption = QLabel(f"{t('grand_total_label')} ({self.items_count} item)")

        f_cap = max(10, int(11 * self.scale))
        bill_caption.setStyleSheet(f"font-size: {f_cap}px; font-weight: 500; color: #64748b;")

        total_str = f"Rp {self.grand_total:,.0f}".replace(",", ".")
        self.total_display = QLabel(total_str)
        f_tot = max(18, int(24 * self.scale))
        self.total_display.setStyleSheet(f"font-size: {f_tot}px; font-weight: 700; color: #0f172a; margin-top: 2px;")

        bill_layout.addWidget(bill_caption)
        bill_layout.addWidget(self.total_display)
        layout.addWidget(bill_card)

        # 3. Payment Method Tabs / Segmented Buttons
        method_box = QVBoxLayout()
        method_box.setSpacing(6)

        method_lbl = QLabel(t("payment_method_label"))
        f_method = max(11, int(12 * self.scale))
        method_lbl.setStyleSheet(f"font-size: {f_method}px; font-weight: 600; color: #0f172a;")
        method_box.addWidget(method_lbl)

        method_row = QHBoxLayout()
        method_row.setSpacing(8)

        self.method_buttons: Dict[str, QPushButton] = {}
        all_methods = [
            ("Cash", t("pay_method_cash"), "banknote", config.payment_cash_enabled),
            ("QRIS", t("pay_method_qris"), "qr-code", config.payment_qris_enabled),
            ("Debit", t("pay_method_debit"), "credit-card", config.payment_debit_enabled),
            ("Debt", t("pay_method_debt"), "file-text", config.payment_debt_enabled),
        ]

        # Filter enabled methods (or fallback to Cash if all disabled)
        enabled_methods = [m for m in all_methods if m[3]]
        if not enabled_methods:
            enabled_methods = [all_methods[0]]

        btn_h = max(34, int(38 * self.scale))
        btn_f = max(11, int(12 * self.scale))

        for code, label, icon_name, _ in enabled_methods:
            btn = QPushButton(f" {label}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(btn_h)
            btn.setIcon(get_svg_icon(icon_name, "#0f172a", max(13, int(15 * self.scale))))
            btn.clicked.connect(lambda _, m=code: self._select_method(m))
            method_row.addWidget(btn)
            self.method_buttons[code] = btn

        method_box.addLayout(method_row)
        layout.addLayout(method_box)

        # 4. Method Specific Views (Stacked Widget)
        self.method_stack = QStackedWidget()

        # --- Stack Page 0: CASH ---
        cash_widget = QWidget()
        cash_layout = QVBoxLayout(cash_widget)
        cash_layout.setContentsMargins(0, 4, 0, 0)
        cash_layout.setSpacing(10)

        cash_input_box = QVBoxLayout()
        cash_input_box.setSpacing(4)
        cash_title = QLabel(t("cash_received_label"))
        cash_title.setStyleSheet(f"font-size: {f_cap}px; font-weight: 500; color: #64748b;")

        self.cash_input = QLineEdit()
        inp_h = max(34, int(38 * self.scale))
        self.cash_input.setMinimumHeight(inp_h)
        f_inp = max(13, int(15 * self.scale))
        self.cash_input.setStyleSheet(f"font-size: {f_inp}px; font-weight: 600; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px;")
        self.cash_input.setText(f"{int(self.grand_total)}")
        self.cash_input.textChanged.connect(self._calculate_change)

        cash_input_box.addWidget(cash_title)
        cash_input_box.addWidget(self.cash_input)
        cash_layout.addLayout(cash_input_box)

        # Quick cash nominal buttons (No fixed height clipping)
        nominals_grid = QGridLayout()
        nominals_grid.setSpacing(6)
        nominals = [
            (t("exact_amount"), self.grand_total),
            ("Rp 20.000", 20000),
            ("Rp 50.000", 50000),
            ("Rp 100.000", 100000),
            ("Rp 150.000", 150000),
            ("Rp 200.000", 200000)
        ]
        nom_h = max(30, int(34 * self.scale))
        nom_f = max(10, int(11 * self.scale))
        for idx, (lbl_txt, val) in enumerate(nominals):
            r = idx // 3
            c = idx % 3
            n_btn = QPushButton(lbl_txt)
            n_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            n_btn.setMinimumHeight(nom_h)
            n_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #f1f5f9;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    font-size: {nom_f}px;
                    font-weight: 500;
                    color: #0f172a;
                    padding: 4px 6px;
                }}
                QPushButton:hover {{
                    background-color: #e2e8f0;
                    border-color: #cbd5e1;
                }}
            """)
            n_btn.clicked.connect(lambda _, v=val: self._set_cash_nominal(v))
            nominals_grid.addWidget(n_btn, r, c)
        cash_layout.addLayout(nominals_grid)

        # Change display box (Completely borderless, smooth surface)
        change_card = QFrame()
        change_card.setStyleSheet("background-color: #f8fafc; border: none; border-radius: 8px;")
        change_layout = QHBoxLayout(change_card)
        change_layout.setContentsMargins(14, 10, 14, 10)

        change_lbl = QLabel(f"{t('change_label')}:")
        change_lbl.setStyleSheet(f"font-size: {f_method}px; font-weight: 500; color: #64748b;")

        self.change_display = QLabel("Rp 0")
        f_chg = max(14, int(16 * self.scale))
        self.change_display.setStyleSheet(f"font-size: {f_chg}px; font-weight: 700; color: #16a34a;")

        change_layout.addWidget(change_lbl)
        change_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        change_layout.addWidget(self.change_display)
        cash_layout.addWidget(change_card)

        self.method_stack.addWidget(cash_widget)  # Index 0: Cash

        # --- Stack Page 1: DYNAMIC QRIS ---
        qris_widget = QWidget()
        qris_layout = QVBoxLayout(qris_widget)
        qris_layout.setContentsMargins(0, 4, 0, 4)
        qris_layout.setSpacing(6)
        qris_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_box_size = max(140, int(160 * self.scale))
        self.qris_qr_label = QLabel()
        self.qris_qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qris_qr_label.setFixedSize(qr_box_size, qr_box_size)
        self.qris_qr_label.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;")

        self.qris_merchant_lbl = QLabel()
        self.qris_merchant_lbl.setStyleSheet(f"font-size: {f_method}px; font-weight: 600; color: #0f172a;")
        self.qris_merchant_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qris_info = QLabel(t("qris_scan_instruction"))
        qris_info.setStyleSheet(f"font-size: {f_cap}px; color: #64748b;")
        qris_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qris_sub = QLabel(f"Nominal: {total_str}")
        qris_sub.setStyleSheet(f"font-size: {f_inp}px; font-weight: 700; color: #06b6d4;")
        qris_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qris_layout.addWidget(self.qris_qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        qris_layout.addWidget(self.qris_merchant_lbl)
        qris_layout.addWidget(qris_info)
        qris_layout.addWidget(qris_sub)
        self.method_stack.addWidget(qris_widget)  # Index 1: QRIS

        # --- Stack Page 2: DEBIT / CREDIT CARD (CLEAN & EMPTY) ---
        debit_widget = QWidget()
        debit_layout = QVBoxLayout(debit_widget)
        debit_layout.setContentsMargins(0, 16, 0, 16)
        debit_layout.setSpacing(12)
        debit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_icon = QLabel()
        card_icon.setPixmap(get_svg_pixmap("credit-card", "#0f172a", max(36, int(48 * self.scale))))
        card_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        debit_msg = QLabel("Silakan proses pembayaran pada mesin EDC / Kartu")
        debit_msg.setStyleSheet(f"font-size: {f_method}px; font-weight: 600; color: #0f172a;")
        debit_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        debit_amt = QLabel(f"Total: {total_str}")
        debit_amt.setStyleSheet(f"font-size: {f_chg}px; font-weight: 700; color: #0f172a;")
        debit_amt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        debit_layout.addWidget(card_icon)
        debit_layout.addWidget(debit_msg)
        debit_layout.addWidget(debit_amt)
        self.method_stack.addWidget(debit_widget)  # Index 2: Debit

        # --- Stack Page 3: DEBT / UTANG ---
        debt_widget = QWidget()
        debt_layout = QVBoxLayout(debt_widget)
        debt_layout.setContentsMargins(0, 6, 0, 6)
        debt_layout.setSpacing(8)

        cust_title = QLabel(t("debt_customer_label"))
        cust_title.setStyleSheet(f"font-size: {f_method}px; font-weight: 500; color: #0f172a;")

        self.debt_cust_input = QLineEdit()
        self.debt_cust_input.setPlaceholderText("e.g. Pak Budi / Bu Siti (Wajib)")
        self.debt_cust_input.setMinimumHeight(inp_h)
        self.debt_cust_input.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px;")

        note_title = QLabel(t("debt_note_label"))
        note_title.setStyleSheet(f"font-size: {f_method}px; font-weight: 500; color: #0f172a;")

        self.debt_note_input = QLineEdit()
        self.debt_note_input.setPlaceholderText("e.g. Bayar akhir bulan / Catatan pesanan")
        self.debt_note_input.setMinimumHeight(inp_h)
        self.debt_note_input.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px;")

        debt_layout.addWidget(cust_title)
        debt_layout.addWidget(self.debt_cust_input)
        debt_layout.addWidget(note_title)
        debt_layout.addWidget(self.debt_note_input)
        self.method_stack.addWidget(debt_widget)  # Index 3: Debt

        layout.addWidget(self.method_stack)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # 5. Bottom Action Buttons (Flexible minimum height, no text clipping)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        action_btn_h = max(38, int(42 * self.scale))
        f_action = max(12, int(13 * self.scale))

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(action_btn_h)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffffff;
                color: #64748b;
                font-weight: 500;
                font-size: {f_action}px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: #f1f5f9;
                color: #0f172a;
            }}
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.pay_btn = QPushButton(t("complete_payment_btn"))
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setMinimumHeight(action_btn_h)
        self.pay_btn.setIcon(get_svg_icon("check-circle", "#ffffff", max(14, int(16 * self.scale))))
        self.pay_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0f172a;
                color: #ffffff;
                font-weight: 600;
                font-size: {f_action}px;
                border: 1px solid #0f172a;
                border-radius: 8px;
                padding: 6px 20px;
            }}
            QPushButton:hover {{
                background-color: #1e293b;
            }}
        """)
        self.pay_btn.clicked.connect(self._validate_and_pay)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.pay_btn)
        layout.addLayout(btn_row)

        first_method = enabled_methods[0][0]
        self._select_method(first_method)
        self._calculate_change()

    def _select_method(self, method: str):
        self.selected_method = method
        f_btn = max(11, int(12 * self.scale))
        for m, btn in self.method_buttons.items():
            if m == method:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #0f172a;
                        color: #ffffff;
                        border: 1px solid #0f172a;
                        border-radius: 8px;
                        font-size: {f_btn}px;
                        font-weight: 600;
                        padding: 4px 8px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #f8fafc;
                        color: #64748b;
                        border: 1px solid #e2e8f0;
                        border-radius: 8px;
                        font-size: {f_btn}px;
                        font-weight: 500;
                        padding: 4px 8px;
                    }}
                    QPushButton:hover {{
                        border-color: #0f172a;
                        color: #0f172a;
                    }}
                """)

        if method == "Cash":
            self.method_stack.setCurrentIndex(0)
            self._calculate_change()
        elif method == "QRIS":
            self.method_stack.setCurrentIndex(1)
            self.paid_amount = self.grand_total
            self.change_amount = 0.0
            self._generate_and_render_qris()
        elif method == "Debit":
            self.method_stack.setCurrentIndex(2)
            self.paid_amount = self.grand_total
            self.change_amount = 0.0
        elif method == "Debt":
            self.method_stack.setCurrentIndex(3)
            self.paid_amount = 0.0
            self.change_amount = 0.0

        # Sync with second monitor customer display
        customer_display_manager.show_checkout(
            self.selected_method,
            self.grand_total,
            self.paid_amount,
            self.change_amount,
            subtotal_amount=self.subtotal_amount,
            fee_type=self.fee_type,
            fee_value=self.fee_value,
            fee_amount=self.fee_amount
        )

    def _generate_and_render_qris(self):
        """Converts merchant's static QRIS to dynamic QRIS with exact amount and renders QR code."""
        static_payload = config.qris_static_payload
        if static_payload:
            dynamic_qris = convert_to_dynamic_qris(static_payload, int(self.grand_total))
            parsed = parse_qris_data(static_payload)
            self.qris_merchant_lbl.setText(f"QRIS: {parsed['merchant_name']}")
            qr_size = max(130, int(150 * self.scale))
            pix = generate_qr_pixmap(dynamic_qris, size=qr_size)
            if pix:
                self.qris_qr_label.setPixmap(pix)
            else:
                self.qris_qr_label.setPixmap(get_svg_pixmap("qr-code", "#0f172a", 64))
        else:
            self.qris_merchant_lbl.setText("QRIS Statis Belum Diatur")
            self.qris_qr_label.setPixmap(get_svg_pixmap("qr-code", "#94a3b8", 64))

    def _set_cash_nominal(self, val: float):
        self.cash_input.setText(f"{int(val)}")

    def _calculate_change(self):
        if self.selected_method != "Cash":
            return
        text = self.cash_input.text().replace(".", "").replace(",", "").strip()
        try:
            paid = float(text) if text else 0.0
        except ValueError:
            paid = 0.0

        self.paid_amount = paid
        self.change_amount = max(0.0, paid - self.grand_total)

        change_str = f"Rp {self.change_amount:,.0f}".replace(",", ".")
        self.change_display.setText(change_str)

        # Sync change to customer display
        customer_display_manager.show_checkout(
            "Cash",
            self.grand_total,
            self.paid_amount,
            self.change_amount,
            subtotal_amount=self.subtotal_amount,
            fee_type=self.fee_type,
            fee_value=self.fee_value,
            fee_amount=self.fee_amount
        )

    def _validate_and_pay(self):
        if self.selected_method == "Cash":
            self._calculate_change()
            if self.paid_amount < self.grand_total:
                self.status_banner.show_error(t("insufficient_cash"))
                self.cash_input.setFocus()
                return
            self.payment_note = ""
        elif self.selected_method == "QRIS":
            self.paid_amount = self.grand_total
            self.change_amount = 0.0
            self.payment_note = "Dynamic QRIS Scan"
        elif self.selected_method == "Debit":
            self.paid_amount = self.grand_total
            self.change_amount = 0.0
            self.payment_note = "Debit / Credit Card EDC"
        elif self.selected_method == "Debt":
            cust_name = self.debt_cust_input.text().strip()
            if not cust_name:
                self.status_banner.show_error(t("debt_customer_required"))
                self.debt_cust_input.setFocus()
                return
            notes = self.debt_note_input.text().strip()
            self.paid_amount = 0.0
            self.change_amount = 0.0
            self.payment_note = f"Debtor: {cust_name} | Notes: {notes}" if notes else f"Debtor: {cust_name}"

        self.accept()

    def reject(self):
        """Immediately restores active order on Customer Display when checkout is cancelled/ESC."""
        log_checkout("CANCELLED", "Checkout dialog cancelled by cashier (ESC / Batal) -> Reverted CFD to active order.")
        parent_widget = self.parent()
        if parent_widget and hasattr(parent_widget, "cart_items"):
            cart = getattr(parent_widget, "cart_items", {})
            sub = sum(it["quantity"] * it["price"] for it in cart.values())
            f_amt = getattr(parent_widget, "fee_amount", 0.0)
            f_type = getattr(parent_widget, "fee_type", "none")
            f_val = getattr(parent_widget, "fee_value", 0.0)
            tot = sub + f_amt
            customer_display_manager.update_cart(
                cart,
                tot,
                subtotal_amount=sub,
                fee_type=f_type,
                fee_value=f_val,
                fee_amount=f_amt
            )
        else:
            customer_display_manager.update_cart({}, 0.0)
        super().reject()
