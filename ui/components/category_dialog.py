"""
Category Add/Edit Modal Dialog for KubuCashier.
Clean Black and White Minimalist Style.
"""

from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt

from ui.i18n import t
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner


class CategoryDialog(QDialog):
    """Modal dialog for creating or editing a product category."""

    def __init__(self, parent=None, category_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.category_data = category_data
        self.is_edit = category_data is not None

        title = t("category_dialog_edit") if self.is_edit else t("category_dialog_add")
        self.setWindowTitle(title)
        self.setFixedSize(400, 220)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(get_svg_pixmap("tag", "#0f172a", 20))

        title_lbl = QLabel(t("category_dialog_edit") if self.is_edit else t("category_dialog_add"))
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #0f172a;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_lbl)
        header_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(header_layout)

        # Status Alert Banner
        self.status_banner = NotificationBanner(self)
        layout.addWidget(self.status_banner)

        # Category Name Input
        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        name_lbl = QLabel(t("th_cat_name"))
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #0f172a;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("enter_product_name"))
        self.name_input.setFixedHeight(36)
        if self.is_edit and self.category_data:
            self.name_input.setText(self.category_data.get("name", ""))
        self.name_input.returnPressed.connect(self._validate_and_save)

        name_box.addWidget(name_lbl)
        name_box.addWidget(self.name_input)
        layout.addLayout(name_box)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Action Buttons Row (Right-aligned)
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

    def get_category_name(self) -> str:
        return self.name_input.text().strip()

    def _validate_and_save(self):
        name = self.get_category_name()
        if not name:
            self.status_banner.show_error("Please enter a category name.")
            self.name_input.setFocus()
            return
        self.accept()
