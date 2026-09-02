"""
Product Add/Edit Modal Dialog for KubuCashier.
Clean Black and White Minimalist Style with Image Upload & Preview.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame, QFileDialog, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR
from ui.i18n import t
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class ProductDialog(QDialog):
    """Modal dialog for adding or editing a product with image upload."""

    def __init__(
        self,
        parent=None,
        product_data: Optional[Dict[str, Any]] = None,
        categories: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(parent)
        self.product_data = product_data
        self.categories = categories or []
        self.is_edit = product_data is not None
        self.image_path: Optional[str] = product_data.get("image_path") if product_data else None

        title = t("product_dialog_edit") if self.is_edit else t("product_dialog_add")
        self.setWindowTitle(title)
        self.setFixedSize(480, 520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(get_svg_pixmap("package", "#0f172a", 22))

        title_lbl = QLabel(t("product_dialog_edit") if self.is_edit else t("product_dialog_add"))
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_lbl)
        header_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(header_layout)

        # Alert Banner
        self.status_banner = NotificationBanner(self)
        layout.addWidget(self.status_banner)

        # Image Upload Section (Horizontal card)
        img_card = QFrame()
        img_card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        img_layout = QHBoxLayout(img_card)
        img_layout.setContentsMargins(10, 8, 10, 8)
        img_layout.setSpacing(14)

        # Thumbnail Preview Box
        self.preview_lbl = QLabel()
        self.preview_lbl.setFixedSize(64, 64)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
            }
        """)
        self._refresh_image_preview()
        img_layout.addWidget(self.preview_lbl)

        # Upload Controls
        img_ctrl_box = QVBoxLayout()
        img_ctrl_box.setSpacing(4)

        img_text_lbl = QLabel(t("th_image"))
        img_text_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.upload_btn = QPushButton(t("upload_image"))
        self.upload_btn.setObjectName("SecondaryButton")
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.setFixedHeight(30)
        self.upload_btn.setIcon(get_svg_icon("upload", ThemeColors.TEXT_PRIMARY, 14))
        self.upload_btn.clicked.connect(self._select_image)

        self.remove_img_btn = QPushButton(t("remove_image"))
        self.remove_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_img_btn.setFixedHeight(30)
        self.remove_img_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e2e8f0;
                color: #ef4444;
                font-size: 11px;
                font-weight: 500;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
                border-color: #fecaca;
            }
        """)
        self.remove_img_btn.clicked.connect(self._remove_image)

        btn_box.addWidget(self.upload_btn)
        btn_box.addWidget(self.remove_img_btn)
        btn_box.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        img_ctrl_box.addWidget(img_text_lbl)
        img_ctrl_box.addLayout(btn_box)
        img_layout.addLayout(img_ctrl_box)

        layout.addWidget(img_card)

        # 1. Product Name Field
        name_box = QVBoxLayout()
        name_box.setSpacing(3)
        name_lbl = QLabel(t("th_name"))
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("enter_product_name"))
        self.name_input.setFixedHeight(34)
        if self.is_edit and self.product_data:
            self.name_input.setText(self.product_data.get("name", ""))

        name_box.addWidget(name_lbl)
        name_box.addWidget(self.name_input)
        layout.addLayout(name_box)

        # 2. Category Dropdown Field
        cat_box = QVBoxLayout()
        cat_box.setSpacing(3)
        cat_lbl = QLabel(t("th_category"))
        cat_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(34)
        self.cat_combo.addItem(f"-- {t('select_category')} --", None)

        current_cat_id = self.product_data.get("category_id") if self.product_data else None
        selected_idx = 0
        for i, cat in enumerate(self.categories, start=1):
            self.cat_combo.addItem(cat["name"], cat["id"])
            if current_cat_id is not None and cat["id"] == current_cat_id:
                selected_idx = i

        self.cat_combo.setCurrentIndex(selected_idx)
        cat_box.addWidget(cat_lbl)
        cat_box.addWidget(self.cat_combo)
        layout.addLayout(cat_box)

        # 3. Price, HPP & Stock Row
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        # Price (Harga Jual)
        price_box = QVBoxLayout()
        price_box.setSpacing(3)
        price_lbl = QLabel(t("th_price"))
        price_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.price_input = QDoubleSpinBox()
        self.price_input.setFixedHeight(34)
        self.price_input.setRange(0, 999999999)
        self.price_input.setDecimals(0)
        self.price_input.setPrefix("Rp ")
        self.price_input.setGroupSeparatorShown(True)
        if self.is_edit and self.product_data:
            self.price_input.setValue(float(self.product_data.get("price", 0)))
        else:
            self.price_input.setValue(10000)

        self.price_input.valueChanged.connect(self._update_margin_preview)
        price_box.addWidget(price_lbl)
        price_box.addWidget(self.price_input)
        row2.addLayout(price_box)

        # HPP (Harga Modal)
        cost_box = QVBoxLayout()
        cost_box.setSpacing(3)
        cost_lbl = QLabel("HPP / Modal")
        cost_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setFixedHeight(34)
        self.cost_input.setRange(0, 999999999)
        self.cost_input.setDecimals(0)
        self.cost_input.setPrefix("Rp ")
        self.cost_input.setGroupSeparatorShown(True)
        if self.is_edit and self.product_data:
            self.cost_input.setValue(float(self.product_data.get("cost_price", 0)))
        else:
            self.cost_input.setValue(6000)

        self.cost_input.valueChanged.connect(self._update_margin_preview)
        cost_box.addWidget(cost_lbl)
        cost_box.addWidget(self.cost_input)
        row2.addLayout(cost_box)

        # Stock
        stock_box = QVBoxLayout()
        stock_box.setSpacing(3)
        stock_lbl = QLabel(t("th_stock"))
        stock_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.stock_input = QSpinBox()
        self.stock_input.setFixedHeight(34)
        self.stock_input.setRange(0, 999999)
        if self.is_edit and self.product_data:
            self.stock_input.setValue(int(self.product_data.get("stock", 0)))
        else:
            self.stock_input.setValue(20)

        stock_box.addWidget(stock_lbl)
        stock_box.addWidget(self.stock_input)
        row2.addLayout(stock_box)

        layout.addLayout(row2)

        # Profit & Margin preview label
        self.margin_preview_lbl = QLabel("Laba Bersih: Rp 4.000 / unit (40.0% Margin)")
        self.margin_preview_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #16a34a; padding: 2px 4px;")
        self._update_margin_preview()
        layout.addWidget(self.margin_preview_lbl)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(t("save"))
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(34)
        self.save_btn.clicked.connect(self._validate_and_save)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _refresh_image_preview(self):
        if self.image_path and os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            scaled = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_lbl.setPixmap(scaled)
        else:
            self.preview_lbl.setPixmap(get_svg_pixmap("image", "#94a3b8", 32))

    def _select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Product Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            try:
                products_dir = ASSETS_DIR / "products"
                products_dir.mkdir(parents=True, exist_ok=True)

                ext = Path(file_path).suffix
                filename = f"prod_{uuid.uuid4().hex[:8]}{ext}"
                dest_path = products_dir / filename
                shutil.copyfile(file_path, str(dest_path))

                self.image_path = str(dest_path)
                self._refresh_image_preview()
            except Exception as e:
                self.status_banner.show_error(f"Failed to load image: {e}")

    def _remove_image(self):
        self.image_path = None
        self._refresh_image_preview()

    def _update_margin_preview(self):
        p = self.price_input.value()
        c = self.cost_input.value()
        profit = p - c
        margin = (profit / p * 100.0) if p > 0 else 0.0
        color = "#16a34a" if profit >= 0 else "#ef4444"
        self.margin_preview_lbl.setText(f"Laba: Rp {profit:,.0f} / unit ({margin:.1f}% Margin)".replace(",", "."))
        self.margin_preview_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {color}; padding: 2px 4px;")

    def get_product_values(self) -> Dict[str, Any]:
        return {
            "name": self.name_input.text().strip(),
            "category_id": self.cat_combo.currentData(),
            "price": self.price_input.value(),
            "cost_price": self.cost_input.value(),
            "stock": self.stock_input.value(),
            "image_path": self.image_path
        }

    def _validate_and_save(self):
        name = self.name_input.text().strip()
        if not name:
            self.status_banner.show_error("Please enter product name.")
            self.name_input.setFocus()
            return

        self.accept()
