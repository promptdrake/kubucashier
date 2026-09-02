"""
Touch-Friendly POS Register Dashboard View for KubuCashier.
Features large "tap-tap" product cards, category pills, real-time cart stepper, and checkout modal.
"""

import os
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSpacerItem,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent

from config import config
from database.db_manager import db_manager
from ui.i18n import t, get_language
from ui.icons import get_svg_icon, get_svg_pixmap
from services.customer_display_manager import customer_display_manager
from utils.logger import log_pos, log_checkout
from ui.components.notification_banner import NotificationBanner
from ui.components.pos_product_card import POSProductCard
from ui.components.checkout_dialog import CheckoutDialog
from ui.components.fee_dialog import FeeDialog


class DashboardPOSView(QWidget):
    """Main POS Register Cashier view with touch-grid catalog and active order cart."""

    transaction_completed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale: float = 1.0
        self.current_user: Optional[Dict[str, Any]] = None
        self.cart_items: Dict[int, Dict[str, Any]] = {}
        self.selected_category_id: Optional[int] = None

        if config.default_fee_enabled and config.default_fee_value > 0:
            self.fee_type: str = config.default_fee_type
            self.fee_value: float = config.default_fee_value
        else:
            self.fee_type: str = "none"
            self.fee_value: float = 0.0
        self.fee_amount: float = 0.0
        self.is_store_on_break: bool = False
        self._init_ui()
        self.refresh_catalog()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. LEFT / CENTER: PRODUCT CATALOG & CATEGORIES
        # -------------------------------------------------------------
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Top Bar: Shift info & Shortcuts guide
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.shift_info_lbl = QLabel("POS Cashier Shift Active")
        self.shift_info_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")

        self.store_break_btn = QPushButton(t("store_break"))
        self.store_break_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.store_break_btn.setFixedHeight(36)
        self.store_break_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
                color: #0f172a;
            }
        """)
        self.store_break_btn.clicked.connect(self._toggle_store_break)

        self.shortcuts_lbl = QLabel(t("shortcuts_tip"))
        self.shortcuts_lbl.setStyleSheet("""
            background-color: #f1f5f9;
            color: #64748b;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 500;
        """)

        top_bar.addWidget(self.shift_info_lbl)
        top_bar.addWidget(self.store_break_btn)
        top_bar.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        top_bar.addWidget(self.shortcuts_lbl)
        left_layout.addLayout(top_bar)

        # Notification Banner
        self.status_banner = NotificationBanner(self)
        left_layout.addWidget(self.status_banner)

        # Search Bar Row
        search_box = QHBoxLayout()
        search_box.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("pos_search_placeholder"))
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet("font-size: 13px; padding-left: 10px;")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_box.addWidget(self.search_input)

        left_layout.addLayout(search_box)

        # Category Filter Pills Container (Horizontal scroll)
        self.cat_pills_container = QFrame()
        self.cat_pills_container.setStyleSheet("background: transparent; border: none;")
        self.cat_pills_layout = QHBoxLayout(self.cat_pills_container)
        self.cat_pills_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_pills_layout.setSpacing(8)
        self.cat_pills_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(42)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setWidget(self.cat_pills_container)
        left_layout.addWidget(cat_scroll)

        # Product Grid Scroll Area
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("background: transparent; border: none;")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 4, 10, 10)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        grid_scroll.setWidget(self.grid_widget)
        left_layout.addWidget(grid_scroll)

        # Break Mode Overlay Frame
        self.break_overlay = QFrame(self)
        self.break_overlay.setObjectName("BreakOverlay")
        self.break_overlay.setStyleSheet("""
            QFrame#BreakOverlay {
                background-color: rgba(255, 255, 255, 0.97);
                border: 2px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        bo_layout = QVBoxLayout(self.break_overlay)
        bo_layout.setContentsMargins(40, 40, 40, 40)
        bo_layout.setSpacing(16)
        bo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bo_icon = QLabel()
        bo_icon.setPixmap(get_svg_pixmap("coffee", "#64748b", 64))
        bo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bo_title = QLabel("Kasir Sedang Istirahat")
        bo_title.setStyleSheet("font-size: 24px; font-weight: 800; color: #0f172a;")
        bo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bo_sub = QLabel("Mode istirahat aktif. Layanan transaksi kasir dinonaktifkan sementara.\nTekan tombol di bawah untuk membuka kasir kembali.")
        bo_sub.setStyleSheet("font-size: 13px; color: #64748b; text-align: center;")
        bo_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bo_resume_btn = QPushButton("▶ Buka Kasir Kembali")
        self.bo_resume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bo_resume_btn.setFixedHeight(42)
        self.bo_resume_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a; color: #ffffff;
                border-radius: 8px; font-size: 14px; font-weight: 700; padding: 0 24px;
            }
            QPushButton:hover { background-color: #1e293b; }
        """)
        self.bo_resume_btn.clicked.connect(self._toggle_store_break)

        bo_layout.addWidget(bo_icon)
        bo_layout.addWidget(bo_title)
        bo_layout.addWidget(bo_sub)
        bo_layout.addWidget(self.bo_resume_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.break_overlay.setVisible(False)

        main_layout.addWidget(left_container, stretch=3)

        # -------------------------------------------------------------
        # 2. RIGHT: ACTIVE ORDER CART PANEL
        # -------------------------------------------------------------
        self.cart_panel = QFrame()
        self.cart_panel.setObjectName("SurfaceCard")
        self.cart_panel.setFixedWidth(340)
        self.cart_panel.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)

        cart_layout = QVBoxLayout(self.cart_panel)
        cart_layout.setContentsMargins(18, 16, 18, 16)
        cart_layout.setSpacing(12)

        # Cart Header
        cart_header = QHBoxLayout()
        cart_header.setSpacing(8)

        cart_icon = QLabel()
        cart_icon.setPixmap(get_svg_pixmap("shopping-bag", "#0f172a", 20))

        self.cart_title = QLabel(t("order_cart"))
        self.cart_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0f172a;")

        self.clear_cart_btn = QPushButton(t("clear_cart_btn"))
        self.clear_cart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_cart_btn.setFixedHeight(28)
        self.clear_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                color: #ef4444;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
                border-color: #fecaca;
            }
        """)
        self.clear_cart_btn.clicked.connect(self.clear_cart)

        cart_header.addWidget(cart_icon)
        cart_header.addWidget(self.cart_title)
        cart_header.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        cart_header.addWidget(self.clear_cart_btn)
        cart_layout.addLayout(cart_header)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("color: #e2e8f0;")
        cart_layout.addWidget(div1)

        # Cart Scroll Items
        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setStyleSheet("background: transparent; border: none;")

        self.cart_items_widget = QWidget()
        self.cart_items_layout = QVBoxLayout(self.cart_items_widget)
        self.cart_items_layout.setContentsMargins(0, 0, 4, 0)
        self.cart_items_layout.setSpacing(8)
        self.cart_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.cart_scroll.setWidget(self.cart_items_widget)
        cart_layout.addWidget(self.cart_scroll, stretch=1)

        # Empty Cart Placeholder Widget
        self.empty_cart_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_cart_widget)
        empty_layout.setContentsMargins(10, 40, 10, 40)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel()
        empty_icon.setPixmap(get_svg_pixmap("cart", "#cbd5e1", 42))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_lbl1 = QLabel(t("empty_cart_title"))
        self.empty_lbl1.setStyleSheet("font-size: 13px; font-weight: 600; color: #94a3b8;")
        self.empty_lbl1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_lbl2 = QLabel(t("empty_cart_sub"))
        self.empty_lbl2.setStyleSheet("font-size: 11px; color: #cbd5e1;")
        self.empty_lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl2.setWordWrap(True)

        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(self.empty_lbl1)
        empty_layout.addWidget(self.empty_lbl2)
        self.cart_items_layout.addWidget(self.empty_cart_widget)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("color: #e2e8f0;")
        cart_layout.addWidget(div2)

        # Summary & Checkout Section
        summary_box = QVBoxLayout()
        summary_box.setSpacing(6)

        # Subtotal row
        sub_row = QHBoxLayout()
        self.subtotal_lbl = QLabel(t("subtotal_label"))
        self.subtotal_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        self.subtotal_val = QLabel("Rp 0")
        self.subtotal_val.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")
        sub_row.addWidget(self.subtotal_lbl)
        sub_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        sub_row.addWidget(self.subtotal_val)
        summary_box.addLayout(sub_row)

        # Fee / Tax Row
        fee_row = QHBoxLayout()
        fee_row.setSpacing(6)
        self.fee_lbl = QLabel("+ Biaya / Fee:")
        self.fee_lbl.setStyleSheet("font-size: 12px; color: #64748b;")

        self.fee_btn = QPushButton("+ Biaya")
        self.fee_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fee_btn.setFixedHeight(22)
        self.fee_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 6px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.fee_btn.clicked.connect(self._open_fee_dialog)

        self.fee_val = QLabel("+ Rp 0")
        self.fee_val.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")

        fee_row.addWidget(self.fee_lbl)
        fee_row.addWidget(self.fee_btn)
        fee_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        fee_row.addWidget(self.fee_val)
        summary_box.addLayout(fee_row)

        # Grand Total row
        grand_row = QHBoxLayout()
        self.grand_title = QLabel(t("grand_total_label"))
        self.grand_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        self.grand_val = QLabel("Rp 0")
        self.grand_val.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        grand_row.addWidget(self.grand_title)
        grand_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        grand_row.addWidget(self.grand_val)
        summary_box.addLayout(grand_row)

        cart_layout.addLayout(summary_box)

        # Big Pay Now Button
        self.pay_btn = QPushButton(t("pay_now_btn"))
        self.pay_btn.setObjectName("PrimaryButton")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setFixedHeight(44)
        self.pay_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #94a3b8;
            }
        """)
        self.pay_btn.setEnabled(False)
        self.pay_btn.clicked.connect(self._open_checkout_dialog)
        cart_layout.addWidget(self.pay_btn)

        main_layout.addWidget(self.cart_panel, stretch=1)

    def set_user(self, user: Dict[str, Any]):
        self.current_user = user
        name = user.get("name", "Cashier")
        role = user.get("role", "Cashier")
        self.shift_info_lbl.setText(f"POS Register  •  {name} ({role})")
        self.refresh_catalog()

    # -------------------------------------------------------------
    # CATALOG & CATEGORY FILTERING
    # -------------------------------------------------------------
    def refresh_catalog(self):
        self._refresh_category_pills()
        self._refresh_product_grid()

    def _refresh_category_pills(self):
        # Clear existing pills
        while self.cat_pills_layout.count():
            item = self.cat_pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # "All Items" Pill
        all_btn = QPushButton(t("all_items"))
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        all_btn.setFixedHeight(32)
        is_all_selected = self.selected_category_id is None
        self._style_pill_button(all_btn, is_all_selected)
        all_btn.clicked.connect(lambda: self._select_category(None))
        self.cat_pills_layout.addWidget(all_btn)

        # Database categories
        categories = db_manager.get_all_categories()
        for cat in categories:
            cat_btn = QPushButton(cat["name"])
            cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cat_btn.setFixedHeight(32)
            is_selected = self.selected_category_id == cat["id"]
            self._style_pill_button(cat_btn, is_selected)
            cat_id = cat["id"]
            cat_btn.clicked.connect(lambda _, cid=cat_id: self._select_category(cid))
            self.cat_pills_layout.addWidget(cat_btn)

    def _style_pill_button(self, btn: QPushButton, is_selected: bool):
        if is_selected:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0f172a;
                    color: #ffffff;
                    border: 1px solid #0f172a;
                    border-radius: 16px;
                    padding: 4px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                    padding: 4px 14px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    border-color: #0f172a;
                    color: #0f172a;
                }
            """)

    def _select_category(self, cat_id: Optional[int]):
        self.selected_category_id = cat_id
        self._refresh_category_pills()
        self._refresh_product_grid()

    def _on_search_changed(self):
        self._refresh_product_grid()

    def _refresh_product_grid(self):
        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search_query = self.search_input.text().strip()
        products = db_manager.get_all_products(
            category_id=self.selected_category_id,
            search_query=search_query
        )

        if not products:
            no_prod_lbl = QLabel(t("no_products"))
            no_prod_lbl.setStyleSheet("font-size: 13px; color: #94a3b8; padding: 40px;")
            self.grid_layout.addWidget(no_prod_lbl, 0, 0)
            return

        columns = 4
        for idx, prod in enumerate(products):
            row = idx // columns
            col = idx % columns
            card = POSProductCard(prod, scale=self.scale)
            card.clicked.connect(self._on_product_clicked)
            self.grid_layout.addWidget(card, row, col)

    def apply_zoom_scale(self, scale: float):
        """Scales POS layout, cards, and panels proportionally during zoom."""
        self.scale = scale
        self.cart_panel.setFixedWidth(max(260, int(340 * scale)))
        self.search_input.setFixedHeight(max(32, int(40 * scale)))
        self.pay_btn.setFixedHeight(max(36, int(44 * scale)))
        self._refresh_product_grid()
        self._refresh_cart_display()

    # -------------------------------------------------------------
    # CART & ORDER MANAGEMENT
    # -------------------------------------------------------------
    def _on_product_clicked(self, prod: Dict[str, Any]):
        prod_id = prod["id"]
        stock = int(prod.get("stock", 0))

        if prod_id in self.cart_items:
            current_qty = self.cart_items[prod_id]["quantity"]
            if current_qty < stock:
                self.cart_items[prod_id]["quantity"] += 1
            else:
                self.status_banner.show_error(f"Cannot add more '{prod['name']}'. Reached available stock ({stock}).")
                return
        else:
            if stock <= 0:
                self.status_banner.show_error(f"'{prod['name']}' is out of stock.")
                return
            self.cart_items[prod_id] = {
                "id": prod_id,
                "name": prod["name"],
                "price": float(prod.get("price", 0)),
                "quantity": 1,
                "stock": stock
            }

        self.status_banner.show_success(t("item_added", name=prod["name"]))
        self._refresh_cart_display()
        tot_amount = sum(it["quantity"] * it["price"] for it in self.cart_items.values())
        log_pos("ITEM_ADDED", f"'{prod['name']}' (Qty: {self.cart_items[prod_id]['quantity']}) | Cart Total: Rp {tot_amount:,.0f}")

    def _increment_item(self, prod_id: int):
        if prod_id in self.cart_items:
            item = self.cart_items[prod_id]
            if item["quantity"] < item["stock"]:
                item["quantity"] += 1
                self._refresh_cart_display()
                tot_amount = sum(it["quantity"] * it["price"] for it in self.cart_items.values())
                log_pos("ITEM_INCREMENT", f"'{item['name']}' Qty -> {item['quantity']} | Cart Total: Rp {tot_amount:,.0f}")
            else:
                self.status_banner.show_error(f"Reached available stock limit ({item['stock']}).")

    def _decrement_item(self, prod_id: int):
        if prod_id in self.cart_items:
            if self.cart_items[prod_id]["quantity"] > 1:
                self.cart_items[prod_id]["quantity"] -= 1
                item_name = self.cart_items[prod_id]["name"]
                qty = self.cart_items[prod_id]["quantity"]
            else:
                item_name = self.cart_items[prod_id]["name"]
                del self.cart_items[prod_id]
                qty = 0
            self._refresh_cart_display()
            tot_amount = sum(it["quantity"] * it["price"] for it in self.cart_items.values())
            log_pos("ITEM_DECREMENT", f"'{item_name}' Qty -> {qty} | Cart Total: Rp {tot_amount:,.0f}")

    def _remove_item(self, prod_id: int):
        if prod_id in self.cart_items:
            item_name = self.cart_items[prod_id]["name"]
            del self.cart_items[prod_id]
            self._refresh_cart_display()
            tot_amount = sum(it["quantity"] * it["price"] for it in self.cart_items.values())
            log_pos("ITEM_REMOVED", f"Removed '{item_name}' from cart | Cart Total: Rp {tot_amount:,.0f}")

    def clear_cart(self):
        if self.cart_items:
            self.cart_items.clear()
            if config.default_fee_enabled and config.default_fee_value > 0:
                self.fee_type = config.default_fee_type
                self.fee_value = config.default_fee_value
            else:
                self.fee_type = "none"
                self.fee_value = 0.0
            self.fee_amount = 0.0
            self._refresh_cart_display()
            self.status_banner.show_success(t("cart_cleared"))
            log_pos("CART_CLEARED", "All items cleared from cart (ESC / Clear button).")

    def _refresh_cart_display(self):
        # Clear existing cart item widgets cleanly
        while self.cart_items_layout.count() > 1:
            item = self.cart_items_layout.takeAt(1)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

        total_amount = 0.0
        total_items_count = 0

        if not self.cart_items:
            self.empty_cart_widget.setVisible(True)
            self.pay_btn.setEnabled(False)
            self.subtotal_val.setText("Rp 0")
            self.fee_val.setText("+ Rp 0")
            self.grand_val.setText("Rp 0")
            self.pay_btn.setText(t("pay_now_btn"))
            customer_display_manager.update_cart({}, 0.0, 0.0, "none", 0.0, 0.0)
            return

        self.empty_cart_widget.setVisible(False)
        self.pay_btn.setEnabled(True)

        for prod_id, item in self.cart_items.items():
            qty = item["quantity"]
            price = item["price"]
            subtotal = qty * price
            total_amount += subtotal
            total_items_count += qty

            # Cart item row card
            item_card = QFrame()
            item_card.setStyleSheet("""
                QFrame {
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                }
            """)
            item_layout = QVBoxLayout(item_card)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(4)

            # Top: Name and Subtotal
            top_line = QHBoxLayout()
            name_lbl = QLabel(item["name"])
            name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")

            sub_str = f"Rp {subtotal:,.0f}".replace(",", ".")
            sub_lbl = QLabel(sub_str)
            sub_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #0f172a;")

            top_line.addWidget(name_lbl, stretch=1)
            top_line.addWidget(sub_lbl)
            item_layout.addLayout(top_line)

            # Bottom: Unit price & Quantity stepper
            bottom_line = QHBoxLayout()
            price_str = f"@ Rp {price:,.0f}".replace(",", ".")
            unit_lbl = QLabel(price_str)
            unit_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
            bottom_line.addWidget(unit_lbl)
            bottom_line.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

            # Stepper Controls (- / qty / +)
            minus_btn = QPushButton("−")
            minus_btn.setFixedSize(24, 24)
            minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            minus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                    color: #0f172a;
                    padding: 0;
                }
                QPushButton:hover { background-color: #e2e8f0; border-color: #94a3b8; }
            """)
            minus_btn.clicked.connect(lambda _, pid=prod_id: self._decrement_item(pid))

            qty_lbl = QLabel(f" {qty} ")
            qty_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")

            plus_btn = QPushButton("+")
            plus_btn.setFixedSize(24, 24)
            plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            plus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                    color: #0f172a;
                    padding: 0;
                }
                QPushButton:hover { background-color: #e2e8f0; border-color: #94a3b8; }
            """)
            plus_btn.clicked.connect(lambda _, pid=prod_id: self._increment_item(pid))

            del_btn = QPushButton()
            del_btn.setFixedSize(24, 24)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setIcon(get_svg_icon("trash", "#ef4444", 13))
            del_btn.setStyleSheet("background: transparent; border: none; padding: 2px;")
            del_btn.clicked.connect(lambda _, pid=prod_id: self._remove_item(pid))

            bottom_line.addWidget(minus_btn)
            bottom_line.addWidget(qty_lbl)
            bottom_line.addWidget(plus_btn)
            bottom_line.addWidget(del_btn)

            item_layout.addLayout(bottom_line)
            self.cart_items_layout.addWidget(item_card)

        # Update totals with fee
        subtotal_amount = sum(item["quantity"] * item["price"] for item in self.cart_items.values())
        if self.fee_type == "percent":
            self.fee_amount = (subtotal_amount * self.fee_value) / 100.0
        elif self.fee_type == "nominal":
            self.fee_amount = self.fee_value
        else:
            self.fee_amount = 0.0

        grand_total = subtotal_amount + self.fee_amount

        sub_str = f"Rp {subtotal_amount:,.0f}".replace(",", ".")
        self.subtotal_val.setText(sub_str)

        if self.fee_amount > 0:
            fee_tag = f"{self.fee_value:g}%" if self.fee_type == "percent" else "Rp"
            self.fee_btn.setText(f"{fee_tag}")
            self.fee_val.setText(f"+ Rp {self.fee_amount:,.0f}".replace(",", "."))
        else:
            self.fee_btn.setText("+ Biaya")
            self.fee_val.setText("+ Rp 0")

        grand_str = f"Rp {grand_total:,.0f}".replace(",", ".")
        self.grand_val.setText(grand_str)
        self.pay_btn.setText(t("pay_now_btn"))

        # Synchronize with Customer Facing Display
        customer_display_manager.update_cart(
            self.cart_items,
            grand_total,
            subtotal_amount=subtotal_amount,
            fee_type=self.fee_type,
            fee_value=self.fee_value,
            fee_amount=self.fee_amount
        )

    def _open_fee_dialog(self):
        subtotal = sum(item["quantity"] * item["price"] for item in self.cart_items.values())
        dlg = FeeDialog(
            subtotal=subtotal,
            current_fee_type=self.fee_type,
            current_fee_value=self.fee_value,
            scale=self.scale,
            parent=self
        )
        if dlg.exec():
            self.fee_type, self.fee_value, self.fee_amount = dlg.get_result()
            self._refresh_cart_display()
            log_pos("FEE_UPDATED", f"Fee applied: {self.fee_type} ({self.fee_value:g}) = Rp {self.fee_amount:,.0f}")

    def _toggle_store_break(self):
        self.is_store_on_break = not self.is_store_on_break
        if self.is_store_on_break:
            self.break_overlay.setGeometry(self.rect())
            self.break_overlay.setVisible(True)
            self.break_overlay.raise_()
            self.store_break_btn.setText(t("store_resume"))
            self.store_break_btn.setFixedHeight(36)
            self.store_break_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: #ffffff;
                    border: 1px solid #dc2626;
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 700;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
            customer_display_manager.show_break_mode()
            log_pos("STORE_BREAK", "Cashier placed register on Break / Istirahat mode.")
        else:
            self.break_overlay.setVisible(False)
            self.store_break_btn.setText(t("store_break"))
            self.store_break_btn.setFixedHeight(36)
            self.store_break_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #0f172a;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                    border-color: #94a3b8;
                    color: #0f172a;
                }
            """)
            customer_display_manager.resume_from_break()
            log_pos("STORE_RESUME", "Cashier resumed register from Break mode.")

    def refresh_translations(self):
        self.search_input.setPlaceholderText(t("pos_search_placeholder"))
        self.shortcuts_lbl.setText(t("shortcuts_tip"))
        if self.is_store_on_break:
            self.store_break_btn.setText(t("store_resume"))
        else:
            self.store_break_btn.setText(t("store_break"))
        self.cart_title.setText(t("order_cart"))
        self.clear_cart_btn.setText(t("clear_cart_btn"))
        if hasattr(self, "empty_lbl1"):
            self.empty_lbl1.setText(t("empty_cart_title"))
        if hasattr(self, "empty_lbl2"):
            self.empty_lbl2.setText(t("empty_cart_sub"))
        self.subtotal_lbl.setText(t("subtotal_label"))
        self.grand_title.setText(t("grand_total_label"))
        self.pay_btn.setText(t("pay_now_btn"))
        if self.current_user:
            name = self.current_user.get("name", "Cashier")
            role = self.current_user.get("role", "Cashier")
            self.shift_info_lbl.setText(f"POS Register  •  {name} ({role})")
        self.refresh_catalog()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "break_overlay") and self.break_overlay.isVisible():
            self.break_overlay.setGeometry(self.rect())

    # -------------------------------------------------------------
    # CHECKOUT & TRANSACTION
    # -------------------------------------------------------------
    def _open_checkout_dialog(self):
        if not self.cart_items:
            return

        subtotal_amount = sum(item["quantity"] * item["price"] for item in self.cart_items.values())
        if self.fee_type == "percent":
            self.fee_amount = (subtotal_amount * self.fee_value) / 100.0
        elif self.fee_type == "nominal":
            self.fee_amount = self.fee_value
        else:
            self.fee_amount = 0.0

        grand_total = subtotal_amount + self.fee_amount
        total_items = sum(item["quantity"] for item in self.cart_items.values())

        dlg = CheckoutDialog(
            grand_total=grand_total,
            items_count=total_items,
            scale=self.scale,
            subtotal_amount=subtotal_amount,
            fee_type=self.fee_type,
            fee_value=self.fee_value,
            fee_amount=self.fee_amount,
            parent=self
        )
        if dlg.exec():
            user_id = self.current_user.get("id") if self.current_user else None
            items_list = list(self.cart_items.values())

            success, invoice_no, _ = db_manager.create_transaction(
                user_id=user_id,
                items=items_list,
                total_amount=grand_total,
                paid_amount=dlg.paid_amount,
                change_amount=dlg.change_amount,
                payment_method=dlg.selected_method,
                subtotal_amount=subtotal_amount,
                fee_type=self.fee_type,
                fee_value=self.fee_value,
                fee_amount=self.fee_amount
            )

            if success:
                self.cart_items.clear()
                if config.default_fee_enabled and config.default_fee_value > 0:
                    self.fee_type = config.default_fee_type
                    self.fee_value = config.default_fee_value
                else:
                    self.fee_type = "none"
                    self.fee_value = 0.0
                self.fee_amount = 0.0
                self._refresh_cart_display()
                self.refresh_catalog()
                self.status_banner.show_success(t("transaction_success", invoice=invoice_no))
                self.transaction_completed.emit(invoice_no)
                customer_display_manager.show_success(invoice_no, dlg.change_amount)
                log_pos("TRANSACTION", f"Completed Invoice #{invoice_no} | Grand Total: Rp {grand_total:,.0f} | Method: {dlg.selected_method}")
            else:
                self.status_banner.show_error(f"Checkout error: {invoice_no}")
        else:
            # Revert customer display to active cart if checkout cancelled
            customer_display_manager.update_cart(
                self.cart_items,
                grand_total,
                subtotal_amount=subtotal_amount,
                fee_type=self.fee_type,
                fee_value=self.fee_value,
                fee_amount=self.fee_amount
            )

    # -------------------------------------------------------------
    # KEYBOARD SHORTCUTS
    # -------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F2:
            self.search_input.setFocus()
            self.search_input.selectAll()
            event.accept()
        elif event.key() == Qt.Key.Key_F9:
            if self.cart_items and not self.is_store_on_break:
                self._open_checkout_dialog()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.clear_cart()
            event.accept()
        else:
            super().keyPressEvent(event)
