"""
Add Fee / Tax / Service Charge Modal Dialog for KubuCashier.
Supports Percent presets (0.7%, 1%, 11%, 12%, Custom) and Nominal presets (500, 1000, 3000, 5000, Custom).
"""

from typing import Tuple, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QRadioButton, QButtonGroup, QFrame, QGridLayout,
    QSpacerItem, QSizePolicy, QCheckBox
)
from PyQt6.QtCore import Qt
from config import config
from ui.i18n import t
from ui.icons import get_svg_icon


class FeeDialog(QDialog):
    """Clean modal dialog for configuring order fee/tax (Percent or Nominal)."""

    def __init__(
        self,
        subtotal: float,
        current_fee_type: str = "none",
        current_fee_value: float = 0.0,
        scale: float = 1.0,
        parent=None
    ):
        super().__init__(parent)
        self.subtotal = subtotal
        self.fee_type = current_fee_type if current_fee_type in ["percent", "nominal"] else "percent"
        self.fee_value = current_fee_value
        self.scale = scale

        self.setWindowTitle("Tambah Biaya / Pajak (Fee)")
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #ffffff;
            }}
            QFrame#Card {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }}
            QPushButton#PresetBtn {{
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: #0f172a;
            }}
            QPushButton#PresetBtnSelected {{
                background-color: #0f172a;
                border: 1px solid #0f172a;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 700;
                color: #ffffff;
            }}
            QLineEdit {{
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #0f172a;
            }}
            QLineEdit:focus {{
                border-color: #0f172a;
            }}
        """)

        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_lbl = QLabel("Pengaturan Biaya / Pajak (Add Fee)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title_lbl)

        # Subtotal Information
        sub_str = f"Rp {self.subtotal:,.0f}".replace(",", ".")
        self.sub_info_lbl = QLabel(f"Subtotal Pesanan: {sub_str}")
        self.sub_info_lbl.setStyleSheet("font-size: 13px; color: #64748b; font-weight: 500;")
        layout.addWidget(self.sub_info_lbl)

        # Mode Selector Buttons (Percent vs Nominal)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(8)

        self.btn_percent_mode = QPushButton("Persentase (%)")
        self.btn_percent_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_percent_mode.setFixedHeight(34)
        self.btn_percent_mode.clicked.connect(lambda: self._set_mode("percent"))

        self.btn_nominal_mode = QPushButton("Nominal Tetap (Rp)")
        self.btn_nominal_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nominal_mode.setFixedHeight(34)
        self.btn_nominal_mode.clicked.connect(lambda: self._set_mode("nominal"))

        mode_box.addWidget(self.btn_percent_mode)
        mode_box.addWidget(self.btn_nominal_mode)
        layout.addLayout(mode_box)

        # Presets Card Container
        self.preset_card = QFrame()
        self.preset_card.setObjectName("Card")
        self.preset_layout = QVBoxLayout(self.preset_card)
        self.preset_layout.setContentsMargins(16, 14, 16, 14)
        self.preset_layout.setSpacing(10)

        self.preset_title = QLabel("Pilih Preset:")
        self.preset_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.preset_layout.addWidget(self.preset_title)

        self.grid_presets = QGridLayout()
        self.grid_presets.setSpacing(8)
        self.preset_layout.addLayout(self.grid_presets)

        layout.addWidget(self.preset_card)

        # Custom Input Row
        custom_box = QVBoxLayout()
        custom_box.setSpacing(6)
        self.custom_label = QLabel("Atau masukkan nilai kustom:")
        self.custom_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("0")
        self.custom_input.textChanged.connect(self._on_custom_text_changed)

        custom_box.addWidget(self.custom_label)
        custom_box.addWidget(self.custom_input)
        layout.addLayout(custom_box)

        # Preview Summary Card
        summary_card = QFrame()
        summary_card.setObjectName("Card")
        s_layout = QVBoxLayout(summary_card)
        s_layout.setContentsMargins(14, 12, 14, 12)
        s_layout.setSpacing(4)

        self.preview_fee_lbl = QLabel("+ Biaya: Rp 0")
        self.preview_fee_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")

        self.preview_total_lbl = QLabel(f"Total Baru: Rp {self.subtotal:,.0f}".replace(",", "."))
        self.preview_total_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #0f172a;")

        s_layout.addWidget(self.preview_fee_lbl)
        s_layout.addWidget(self.preview_total_lbl)
        layout.addWidget(summary_card)

        # Checkbox: Save for next purchases
        self.save_for_next_cb = QCheckBox("Simpan biaya ini untuk transaksi berikutnya")
        self.save_for_next_cb.setChecked(config.default_fee_enabled)
        self.save_for_next_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_for_next_cb.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                font-weight: 600;
                color: #0f172a;
                spacing: 8px;
                padding-top: 2px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1.5px solid #94a3b8;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #0f172a;
                border-color: #0f172a;
            }
        """)
        layout.addWidget(self.save_for_next_cb)

        # Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.clear_fee_btn = QPushButton("Hapus Biaya")
        self.clear_fee_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_fee_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #ef4444; border: 1px solid #fca5a5;
                border-radius: 8px; padding: 8px 14px; font-weight: 600; font-size: 13px;
            }
            QPushButton:hover { background: #fee2e2; }
        """)
        self.clear_fee_btn.clicked.connect(self._clear_fee)

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #64748b; border: 1px solid #e2e8f0;
                border-radius: 8px; padding: 8px 14px; font-weight: 500; font-size: 13px;
            }
            QPushButton:hover { background: #f1f5f9; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Terapkan")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: #0f172a; color: #ffffff; border: 1px solid #0f172a;
                border-radius: 8px; padding: 8px 20px; font-weight: 700; font-size: 13px;
            }
            QPushButton:hover { background: #1e293b; }
        """)
        self.apply_btn.clicked.connect(self._apply_fee)

        btn_row.addWidget(self.clear_fee_btn)
        btn_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.apply_btn)
        layout.addLayout(btn_row)

        self._set_mode(self.fee_type)
        if self.fee_value > 0:
            self.custom_input.setText(str(self.fee_value if self.fee_type == "percent" else int(self.fee_value)))

    def _set_mode(self, mode: str):
        self.fee_type = mode
        if mode == "percent":
            self.btn_percent_mode.setStyleSheet("background-color: #0f172a; color: #ffffff; font-weight: 700; border-radius: 8px;")
            self.btn_nominal_mode.setStyleSheet("background-color: #f1f5f9; color: #64748b; font-weight: 500; border: 1px solid #e2e8f0; border-radius: 8px;")
            self.custom_label.setText("Atau masukkan persen kustom (%):")
            self._render_percent_presets()
        else:
            self.btn_nominal_mode.setStyleSheet("background-color: #0f172a; color: #ffffff; font-weight: 700; border-radius: 8px;")
            self.btn_percent_mode.setStyleSheet("background-color: #f1f5f9; color: #64748b; font-weight: 500; border: 1px solid #e2e8f0; border-radius: 8px;")
            self.custom_label.setText("Atau masukkan nominal kustom (Rp):")
            self._render_nominal_presets()

        self._recalculate_preview()

    def _render_percent_presets(self):
        while self.grid_presets.count():
            item = self.grid_presets.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets = [
            ("0.7%", 0.7),
            ("1.0%", 1.0),
            ("11.0%", 11.0),
            ("12.0%", 12.0),
        ]
        for idx, (label, val) in enumerate(presets):
            btn = QPushButton(label)
            btn.setObjectName("PresetBtnSelected" if (self.fee_type == "percent" and abs(self.fee_value - val) < 0.01) else "PresetBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=val: self._select_preset(v))
            self.grid_presets.addWidget(btn, idx // 2, idx % 2)

    def _render_nominal_presets(self):
        while self.grid_presets.count():
            item = self.grid_presets.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets = [
            ("Rp 500", 500.0),
            ("Rp 1.000", 1000.0),
            ("Rp 3.000", 3000.0),
            ("Rp 5.000", 5000.0),
        ]
        for idx, (label, val) in enumerate(presets):
            btn = QPushButton(label)
            btn.setObjectName("PresetBtnSelected" if (self.fee_type == "nominal" and abs(self.fee_value - val) < 0.01) else "PresetBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=val: self._select_preset(v))
            self.grid_presets.addWidget(btn, idx // 2, idx % 2)

    def _select_preset(self, val: float):
        self.fee_value = val
        self.custom_input.setText(str(val if self.fee_type == "percent" else int(val)))
        if self.fee_type == "percent":
            self._render_percent_presets()
        else:
            self._render_nominal_presets()
        self._recalculate_preview()

    def _on_custom_text_changed(self, text: str):
        clean = text.replace(",", ".").strip()
        try:
            val = float(clean) if clean else 0.0
        except ValueError:
            val = 0.0
        self.fee_value = max(0.0, val)
        self._recalculate_preview()

    def _apply_fee(self):
        if self.save_for_next_cb.isChecked() and self.fee_value > 0:
            config.set_default_fee(True, self.fee_type, self.fee_value, persist=True)
        else:
            config.set_default_fee(False, "percent", 0.0, persist=True)
        self.accept()

    def _clear_fee(self):
        self.fee_type = "none"
        self.fee_value = 0.0
        config.set_default_fee(False, "percent", 0.0, persist=True)
        self.accept()

    def _recalculate_preview(self):
        if self.fee_type == "percent":
            fee_amt = (self.subtotal * self.fee_value) / 100.0
            fee_desc = f"+ Biaya ({self.fee_value:g}%): Rp {fee_amt:,.0f}".replace(",", ".")
        elif self.fee_type == "nominal":
            fee_amt = self.fee_value
            fee_desc = f"+ Biaya: Rp {fee_amt:,.0f}".replace(",", ".")
        else:
            fee_amt = 0.0
            fee_desc = "+ Biaya: Rp 0"

        total_new = self.subtotal + fee_amt
        self.preview_fee_lbl.setText(fee_desc)
        self.preview_total_lbl.setText(f"Total Baru: Rp {total_new:,.0f}".replace(",", "."))

    def get_result(self) -> Tuple[str, float, float]:
        """Returns (fee_type, fee_value, fee_amount)."""
        if self.fee_type == "percent":
            fee_amt = (self.subtotal * self.fee_value) / 100.0
            return ("percent" if self.fee_value > 0 else "none", self.fee_value, fee_amt)
        elif self.fee_type == "nominal":
            fee_amt = self.fee_value
            return ("nominal" if self.fee_value > 0 else "none", self.fee_value, fee_amt)
        return ("none", 0.0, 0.0)
