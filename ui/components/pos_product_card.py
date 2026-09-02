"""
Touch-Friendly Product Card Component for KubuCashier POS Register.
Large click target ("tap-tap" ordering) with product thumbnail, price, category, and stock indicator.
Supports responsive UI scaling for Zoom In / Zoom Out.
"""

import os
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from ui.i18n import t
from ui.icons import get_svg_pixmap
from ui.theme import ThemeColors


class POSProductCard(QFrame):
    """Large, touch-friendly product card for rapid POS cashier ordering."""

    clicked = pyqtSignal(dict)

    def __init__(self, product_data: Dict[str, Any], scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.scale = scale
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        card_w = max(110, int(145 * scale))
        card_h = max(135, int(175 * scale))
        self.setFixedSize(card_w, card_h)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("POSProductCard")

        self.setStyleSheet("""
            QFrame#POSProductCard {
                background-color: #ffffff;
                border: 1px solid #f1f5f9;
                border-radius: 12px;
            }
            QFrame#POSProductCard:hover {
                background-color: #f8fafc;
                border-color: #cbd5e1;
            }
        """)

        pad = max(6, int(10 * self.scale))
        spacing = max(4, int(6 * self.scale))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(spacing)

        # 1. Product Image / Icon Thumbnail Container
        img_box_size = max(40, int(56 * self.scale))
        img_container = QLabel()
        img_container.setFixedSize(img_box_size, img_box_size)
        img_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_container.setStyleSheet("background-color: #f1f5f9; border: none; border-radius: 10px;")

        img_path = self.product_data.get("image_path")
        pix_size = max(34, int(50 * self.scale))
        if img_path and os.path.exists(img_path):
            pix = QPixmap(img_path)
            scaled = pix.scaled(pix_size, pix_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_container.setPixmap(scaled)
        else:
            icon_size = max(20, int(30 * self.scale))
            img_container.setPixmap(get_svg_pixmap("package", "#64748b", icon_size))

        img_row = QHBoxLayout()
        img_row.setContentsMargins(0, 0, 0, 0)
        img_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_row.addWidget(img_container)
        layout.addLayout(img_row)

        # 2. Product Name
        f_name = max(10, int(12 * self.scale))
        name_lbl = QLabel(self.product_data.get("name", "Product"))
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"font-weight: 600; font-size: {f_name}px; color: #0f172a; line-height: 1.1;")
        layout.addWidget(name_lbl)

        # 3. Price
        f_price = max(11, int(13 * self.scale))
        price_val = float(self.product_data.get("price", 0))
        price_str = f"Rp {price_val:,.0f}".replace(",", ".")
        price_lbl = QLabel(price_str)
        price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_lbl.setStyleSheet(f"font-weight: 700; font-size: {f_price}px; color: #0f172a;")
        layout.addWidget(price_lbl)

        # 4. Stock Badge
        f_badge = max(8, int(10 * self.scale))
        stock_val = int(self.product_data.get("stock", 0))
        if stock_val <= 0:
            stock_text = t("stock_out")
            badge_style = "background-color: #fef2f2; color: #ef4444; border: 1px solid #fecaca;"
        else:
            stock_text = t("stock_left", count=stock_val)
            badge_style = "background-color: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;"

        stock_lbl = QLabel(f" {stock_text} ")
        stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stock_lbl.setStyleSheet(f"{badge_style} border-radius: 4px; font-size: {f_badge}px; font-weight: 500; padding: 1px 4px;")

        stock_row = QHBoxLayout()
        stock_row.setContentsMargins(0, 0, 0, 0)
        stock_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stock_row.addWidget(stock_lbl)
        layout.addLayout(stock_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.product_data)
        super().mousePressEvent(event)
