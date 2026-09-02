"""
Products and Categories Management View for KubuCashier.
Clean Black and White Minimalist Interface (Laravel Breeze style).
Accessible by Owner and Admin roles.
"""

import os
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QScrollArea, QSpacerItem, QSizePolicy,
    QMessageBox, QStackedWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from config import ASSETS_DIR
from database.db_manager import db_manager
from ui.i18n import t, get_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner
from ui.components.product_dialog import ProductDialog
from ui.components.category_dialog import CategoryDialog


class ProductsView(QWidget):
    """Main Products & Categories management view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tab_idx = 0
        self._init_ui()
        self.refresh_all_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 24, 36, 28)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. HEADER & ACTION BUTTONS
        # -------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_text_box = QVBoxLayout()
        header_text_box.setSpacing(2)

        self.title_lbl = QLabel(t("products_title"))
        self.title_lbl.setObjectName("GreetingTitle")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #0f172a;")

        self.subtitle_lbl = QLabel(t("products_subtitle"))
        self.subtitle_lbl.setObjectName("SubtitleLabel")
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748b;")

        header_text_box.addWidget(self.title_lbl)
        header_text_box.addWidget(self.subtitle_lbl)
        header_row.addLayout(header_text_box)
        header_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Top Action Buttons (Black & White style)
        self.add_cat_btn = QPushButton(f"  {t('add_category_btn')}")
        self.add_cat_btn.setObjectName("SecondaryButton")
        self.add_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_cat_btn.setFixedHeight(36)
        self.add_cat_btn.setIcon(get_svg_icon("tag", ThemeColors.TEXT_PRIMARY, 16))
        self.add_cat_btn.clicked.connect(self._open_add_category_dialog)

        self.add_prod_btn = QPushButton(f"  {t('add_product_btn')}")
        self.add_prod_btn.setObjectName("PrimaryButton")
        self.add_prod_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_prod_btn.setFixedHeight(36)
        self.add_prod_btn.setIcon(get_svg_icon("plus", "#ffffff", 16))
        self.add_prod_btn.clicked.connect(self._open_add_product_dialog)

        header_row.addWidget(self.add_cat_btn)
        header_row.addWidget(self.add_prod_btn)
        main_layout.addLayout(header_row)

        # Status Alert Banner
        self.status_banner = NotificationBanner(self)
        main_layout.addWidget(self.status_banner)

        # -------------------------------------------------------------
        # 2. TAB SWITCHER BAR (Products / Categories)
        # -------------------------------------------------------------
        tab_bar_card = QFrame()
        tab_bar_card.setStyleSheet("""
            QFrame {
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 3px;
            }
        """)
        tab_bar_layout = QHBoxLayout(tab_bar_card)
        tab_bar_layout.setContentsMargins(4, 4, 4, 4)
        tab_bar_layout.setSpacing(6)

        self.tab_prod_btn = QPushButton(f"  {t('tab_products')}")
        self.tab_prod_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_prod_btn.setFixedHeight(32)
        self.tab_prod_btn.setIcon(get_svg_icon("package", ThemeColors.TEXT_PRIMARY, 14))
        self.tab_prod_btn.clicked.connect(lambda: self._switch_tab(0))

        self.tab_cat_btn = QPushButton(f"  {t('tab_categories')}")
        self.tab_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_cat_btn.setFixedHeight(32)
        self.tab_cat_btn.setIcon(get_svg_icon("tag", ThemeColors.TEXT_MUTED, 14))
        self.tab_cat_btn.clicked.connect(lambda: self._switch_tab(1))

        tab_bar_layout.addWidget(self.tab_prod_btn)
        tab_bar_layout.addWidget(self.tab_cat_btn)
        tab_bar_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        main_layout.addWidget(tab_bar_card)

        # -------------------------------------------------------------
        # 3. TAB STACK (0: Products, 1: Categories)
        # -------------------------------------------------------------
        self.tab_stack = QStackedWidget()

        # TAB 0: PRODUCTS TAB
        prod_tab_widget = QWidget()
        prod_tab_layout = QVBoxLayout(prod_tab_widget)
        prod_tab_layout.setContentsMargins(0, 0, 0, 0)
        prod_tab_layout.setSpacing(12)

        # Search & Filter Toolbar
        filter_box = QHBoxLayout()
        filter_box.setSpacing(10)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_products"))
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_filter_changed)

        # Category Filter Dropdown
        self.filter_cat_combo = QComboBox()
        self.filter_cat_combo.setMinimumWidth(180)
        self.filter_cat_combo.setFixedHeight(36)
        self.filter_cat_combo.currentIndexChanged.connect(self._on_filter_changed)

        filter_box.addWidget(self.search_input, stretch=1)
        filter_box.addWidget(self.filter_cat_combo)
        prod_tab_layout.addLayout(filter_box)

        # Products Table Container
        prod_table_frame = QFrame()
        prod_table_frame.setObjectName("SurfaceCard")
        prod_table_layout = QVBoxLayout(prod_table_frame)
        prod_table_layout.setContentsMargins(0, 0, 0, 0)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(7)
        self.products_table.setHorizontalHeaderLabels([
            t("th_image"), t("th_name"), t("th_category"),
            "HPP (Modal)", t("th_price"), t("th_stock"), t("th_actions")
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.setShowGrid(False)
        self.products_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 10px 12px;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f1f5f9;
                padding: 6px 10px;
                color: #0f172a;
            }
            QTableWidget::item:selected {
                background-color: #f1f5f9;
                color: #0f172a;
            }
        """)

        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(2, 110)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(4, 110)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(5, 75)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.products_table.setColumnWidth(6, 95)

        prod_table_layout.addWidget(self.products_table)
        prod_tab_layout.addWidget(prod_table_frame)
        self.tab_stack.addWidget(prod_tab_widget)  # Index 0

        # TAB 1: CATEGORIES TAB
        cat_tab_widget = QWidget()
        cat_tab_layout = QVBoxLayout(cat_tab_widget)
        cat_tab_layout.setContentsMargins(0, 0, 0, 0)
        cat_tab_layout.setSpacing(12)

        cat_table_frame = QFrame()
        cat_table_frame.setObjectName("SurfaceCard")
        cat_table_layout = QVBoxLayout(cat_table_frame)
        cat_table_layout.setContentsMargins(0, 0, 0, 0)

        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(3)
        self.categories_table.setHorizontalHeaderLabels([
            t("th_cat_name"), t("th_cat_items"), t("th_actions")
        ])
        self.categories_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.categories_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.categories_table.verticalHeader().setVisible(False)
        self.categories_table.setShowGrid(False)
        self.categories_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 10px 12px;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f1f5f9;
                padding: 8px 12px;
                color: #0f172a;
            }
            QTableWidget::item:selected {
                background-color: #f1f5f9;
                color: #0f172a;
            }
        """)

        cat_header = self.categories_table.horizontalHeader()
        cat_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cat_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.categories_table.setColumnWidth(1, 150)
        cat_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.categories_table.setColumnWidth(2, 110)

        cat_table_layout.addWidget(self.categories_table)
        cat_tab_layout.addWidget(cat_table_frame)
        self.tab_stack.addWidget(cat_tab_widget)  # Index 1

        main_layout.addWidget(self.tab_stack)

        self._switch_tab(0)

    def _switch_tab(self, idx: int):
        self._current_tab_idx = idx
        self.tab_stack.setCurrentIndex(idx)
        if idx == 0:
            self.tab_prod_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #0f172a;
                    font-weight: 600;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 4px 12px;
                }
            """)
            self.tab_cat_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    font-weight: 500;
                    border: none;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    color: #0f172a;
                }
            """)
        else:
            self.tab_cat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #0f172a;
                    font-weight: 600;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 4px 12px;
                }
            """)
            self.tab_prod_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    font-weight: 500;
                    border: none;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    color: #0f172a;
                }
            """)

    def refresh_translations(self):
        self.title_lbl.setText(t("products_title"))
        self.subtitle_lbl.setText(t("products_subtitle"))
        self.add_prod_btn.setText(f"  {t('add_product_btn')}")
        self.add_cat_btn.setText(f"  {t('add_category_btn')}")
        self.tab_prod_btn.setText(f"  {t('tab_products')}")
        self.tab_cat_btn.setText(f"  {t('tab_categories')}")
        self.search_input.setPlaceholderText(t("search_products"))

        self.products_table.setHorizontalHeaderLabels([
            t("th_image"), t("th_name"), t("th_category"),
            "HPP (Modal)", t("th_price"), t("th_stock"), t("th_actions")
        ])
        self.categories_table.setHorizontalHeaderLabels([
            t("th_cat_name"), t("th_cat_items"), t("th_actions")
        ])
        self.refresh_all_data()

    def refresh_all_data(self):
        self._refresh_categories_filter()
        self._refresh_products_table()
        self._refresh_categories_table()

    def _refresh_categories_filter(self):
        current_data = self.filter_cat_combo.currentData()
        self.filter_cat_combo.blockSignals(True)
        self.filter_cat_combo.clear()
        self.filter_cat_combo.addItem(f"-- {t('filter_all_categories')} --", None)

        categories = db_manager.get_all_categories()
        selected_idx = 0
        for i, cat in enumerate(categories, start=1):
            self.filter_cat_combo.addItem(cat["name"], cat["id"])
            if current_data is not None and cat["id"] == current_data:
                selected_idx = i

        self.filter_cat_combo.setCurrentIndex(selected_idx)
        self.filter_cat_combo.blockSignals(False)

    def _on_filter_changed(self):
        self._refresh_products_table()

    def _refresh_products_table(self):
        self.products_table.clearContents()
        cat_id = self.filter_cat_combo.currentData()
        search_term = self.search_input.text().strip()

        products = db_manager.get_all_products(category_id=cat_id, search_query=search_term)
        self.products_table.setRowCount(len(products))

        for row_idx, prod in enumerate(products):
            self.products_table.setRowHeight(row_idx, 52)

            # 1. Thumbnail Image
            img_container = QWidget()
            img_layout = QHBoxLayout(img_container)
            img_layout.setContentsMargins(0, 0, 0, 0)
            img_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            img_lbl = QLabel()
            img_lbl.setFixedSize(38, 38)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;")

            img_path = prod.get("image_path")
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                scaled = pixmap.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_lbl.setPixmap(scaled)
            else:
                img_lbl.setPixmap(get_svg_pixmap("package", "#94a3b8", 20))

            img_layout.addWidget(img_lbl)
            self.products_table.setCellWidget(row_idx, 0, img_container)

            # 2. Product Name
            name_item = QTableWidgetItem(prod["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.products_table.setItem(row_idx, 1, name_item)

            # 3. Category Badge
            cat_name = prod.get("category_name") or "-"
            cat_badge_container = QWidget()
            cat_layout = QHBoxLayout(cat_badge_container)
            cat_layout.setContentsMargins(0, 0, 0, 0)
            cat_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            cat_lbl = QLabel(f" {cat_name} ")
            cat_lbl.setStyleSheet("""
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 500;
            """)
            cat_layout.addWidget(cat_lbl)
            self.products_table.setCellWidget(row_idx, 2, cat_badge_container)

            # 4. HPP (Modal)
            cost_val = float(prod.get("cost_price", 0))
            cost_str = f"Rp {cost_val:,.0f}".replace(",", ".")
            cost_item = QTableWidgetItem(cost_str)
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cost_item.setForeground(Qt.GlobalColor.gray)
            self.products_table.setItem(row_idx, 3, cost_item)

            # 5. Price (Harga Jual)
            price_val = float(prod.get("price", 0))
            price_str = f"Rp {price_val:,.0f}".replace(",", ".")
            price_item = QTableWidgetItem(price_str)
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.products_table.setItem(row_idx, 4, price_item)

            # 6. Stock
            stock_val = int(prod.get("stock", 0))
            stock_item = QTableWidgetItem(f"{stock_val}")
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.products_table.setItem(row_idx, 5, stock_item)

            # 7. Actions (Edit & Delete buttons)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton()
            edit_btn.setObjectName("IconButton")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setToolTip(t("edit"))
            edit_btn.setIcon(get_svg_icon("edit", ThemeColors.TEXT_PRIMARY, 14))
            edit_btn.clicked.connect(lambda _, p=prod: self._open_edit_product_dialog(p))

            del_btn = QPushButton()
            del_btn.setObjectName("IconButton")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setToolTip(t("delete"))
            del_btn.setIcon(get_svg_icon("trash", "#ef4444", 14))
            del_btn.clicked.connect(lambda _, p=prod: self._delete_product(p))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            self.products_table.setCellWidget(row_idx, 6, action_widget)

    def _refresh_categories_table(self):
        self.categories_table.clearContents()
        categories = db_manager.get_all_categories()
        self.categories_table.setRowCount(len(categories))

        for row_idx, cat in enumerate(categories):
            self.categories_table.setRowHeight(row_idx, 44)

            # 1. Category Name
            name_item = QTableWidgetItem(cat["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.categories_table.setItem(row_idx, 0, name_item)

            # 2. Total Items
            p_count = cat.get("product_count", 0)
            count_item = QTableWidgetItem(f"{p_count} item(s)")
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.categories_table.setItem(row_idx, 1, count_item)

            # 3. Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton()
            edit_btn.setObjectName("IconButton")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setToolTip(t("edit"))
            edit_btn.setIcon(get_svg_icon("edit", ThemeColors.TEXT_PRIMARY, 14))
            edit_btn.clicked.connect(lambda _, c=cat: self._open_edit_category_dialog(c))

            del_btn = QPushButton()
            del_btn.setObjectName("IconButton")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setToolTip(t("delete"))
            del_btn.setIcon(get_svg_icon("trash", "#ef4444", 14))
            del_btn.clicked.connect(lambda _, c=cat: self._delete_category(c))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            self.categories_table.setCellWidget(row_idx, 2, action_widget)

    # -------------------------------------------------------------
    # DIALOG HANDLERS
    # -------------------------------------------------------------
    def _open_add_category_dialog(self):
        dlg = CategoryDialog(self)
        if dlg.exec():
            name = dlg.get_category_name()
            try:
                db_manager.add_category(name)
                self.refresh_all_data()
                self.status_banner.show_success(t("category_saved"))
            except Exception as e:
                self.status_banner.show_error(f"Failed to save category: {e}")

    def _open_edit_category_dialog(self, cat: Dict[str, Any]):
        dlg = CategoryDialog(self, category_data=cat)
        if dlg.exec():
            name = dlg.get_category_name()
            try:
                db_manager.update_category(cat["id"], name)
                self.refresh_all_data()
                self.status_banner.show_success(t("category_saved"))
            except Exception as e:
                self.status_banner.show_error(f"Failed to update category: {e}")

    def _delete_category(self, cat: Dict[str, Any]):
        confirm_msg = t("confirm_delete_category", name=cat["name"])
        reply = QMessageBox.question(
            self,
            t("delete"),
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db_manager.delete_category(cat["id"])
            self.refresh_all_data()
            self.status_banner.show_success(t("category_deleted"))

    def _open_add_product_dialog(self):
        categories = db_manager.get_all_categories()
        dlg = ProductDialog(self, categories=categories)
        if dlg.exec():
            vals = dlg.get_product_values()
            try:
                db_manager.add_product(
                    name=vals["name"],
                    category_id=vals["category_id"],
                    price=vals["price"],
                    cost_price=vals.get("cost_price", 0.0),
                    stock=vals["stock"],
                    image_path=vals["image_path"]
                )
                self.refresh_all_data()
                self.status_banner.show_success(t("product_saved"))
            except Exception as e:
                self.status_banner.show_error(f"Failed to create product: {e}")

    def _open_edit_product_dialog(self, prod: Dict[str, Any]):
        categories = db_manager.get_all_categories()
        dlg = ProductDialog(self, product_data=prod, categories=categories)
        if dlg.exec():
            vals = dlg.get_product_values()
            try:
                db_manager.update_product(
                    product_id=prod["id"],
                    name=vals["name"],
                    category_id=vals["category_id"],
                    price=vals["price"],
                    cost_price=vals.get("cost_price", 0.0),
                    stock=vals["stock"],
                    image_path=vals["image_path"]
                )
                self.refresh_all_data()
                self.status_banner.show_success(t("product_saved"))
            except Exception as e:
                self.status_banner.show_error(f"Failed to update product: {e}")

    def _delete_product(self, prod: Dict[str, Any]):
        confirm_msg = t("confirm_delete_product", name=prod["name"])
        reply = QMessageBox.question(
            self,
            t("delete"),
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db_manager.delete_product(prod["id"])
            self.refresh_all_data()
            self.status_banner.show_success(t("product_deleted"))
