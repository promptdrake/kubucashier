"""
Cashier Performance & Rating Ratios View for KubuCashier.
Dedicated analytics page evaluating cashier sales performance, gross & net profit contributions,
and detailed 1-5 star customer satisfaction ratios and distributions.
Clean Light Minimalist Black & White theme matching KubuCashier design system.
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSpacerItem,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db_manager import db_manager
from ui.i18n import t, get_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors


class CashierRatingsView(QWidget):
    """Dedicated Cashier Performance & 1-5 Star Customer Rating Ratios page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale: float = 1.0
        self.current_user: Optional[Dict[str, Any]] = None
        self._init_ui()

    def set_scale(self, scale: float):
        self.scale = scale

    def set_current_user(self, user: Optional[Dict[str, Any]]):
        self.current_user = user

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for responsive scrolling on smaller displays
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(28, 24, 28, 28)
        self.content_layout.setSpacing(20)

        # -------------------------------------------------------------
        # 1. HEADER ROW: Title, Subtitle, Refresh Button
        # -------------------------------------------------------------
        header_row = QHBoxLayout()
        header_text_vbox = QVBoxLayout()
        header_text_vbox.setSpacing(4)

        self.title_lbl = QLabel(t("cashier_ratings_title"))
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #0f172a;")
        header_text_vbox.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel(t("cashier_ratings_subtitle"))
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748b;")
        header_text_vbox.addWidget(self.subtitle_lbl)
        header_row.addLayout(header_text_vbox)

        header_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Refresh Data Button
        self.refresh_btn = QPushButton("  Refresh Data")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIcon(get_svg_icon("refresh-cw", "#0f172a", 14))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_row.addWidget(self.refresh_btn)

        self.content_layout.addLayout(header_row)

        # -------------------------------------------------------------
        # 2. TOP SUMMARY KPI METRIC CARDS (4 Cards)
        # -------------------------------------------------------------
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        # Card 1: Rata-rata Rating Toko
        self.kpi_rating_card, self.val_rating, self.sub_rating = self._create_kpi_card(
            "Rating Rata-rata Toko", "0.0 / 5.0", "0 Ulasan Pelanggan", "star", "#eab308"
        )
        kpi_grid.addWidget(self.kpi_rating_card, 0, 0)

        # Card 2: Total Ulasan Diberikan
        self.kpi_reviews_card, self.val_reviews, self.sub_reviews = self._create_kpi_card(
            "Total Ulasan Masuk", "0 Ulasan", "Tingkat Partisipasi Pelanggan", "heart", "#ec4899"
        )
        kpi_grid.addWidget(self.kpi_reviews_card, 0, 1)

        # Card 3: Total Omset Kotor Kasir
        self.kpi_gross_card, self.val_gross, self.sub_gross = self._create_kpi_card(
            "Total Omset Kotor", "Rp 0", "Semua Transaksi", "dollar-sign", "#0f172a"
        )
        kpi_grid.addWidget(self.kpi_gross_card, 0, 2)

        # Card 4: Total Laba Bersih
        self.kpi_net_card, self.val_net, self.sub_net = self._create_kpi_card(
            "Total Laba Bersih", "Rp 0", "Margin Keuntungan: 0%", "trending-up", "#10b981"
        )
        kpi_grid.addWidget(self.kpi_net_card, 0, 3)

        self.content_layout.addLayout(kpi_grid)

        # -------------------------------------------------------------
        # 3. STAR DISTRIBUTION BREAKDOWN SECTION
        # -------------------------------------------------------------
        dist_card = QFrame()
        dist_card.setObjectName("CustomerCard")
        dist_card.setStyleSheet("""
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        dist_layout = QVBoxLayout(dist_card)
        dist_layout.setContentsMargins(22, 20, 22, 20)
        dist_layout.setSpacing(14)

        dist_title = QLabel("Distribusi Ulasan Bintang Pelanggan (1 - 5 Stars)")
        dist_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        dist_layout.addWidget(dist_title)

        self.star_bars: Dict[int, Dict[str, Any]] = {}
        for star in [5, 4, 3, 2, 1]:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(12)

            star_lbl = QLabel(f"★ {star} Bintang")
            star_lbl.setFixedWidth(85)
            star_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")

            pbar = QProgressBar()
            pbar.setFixedHeight(8)
            pbar.setTextVisible(False)
            pbar.setStyleSheet("""
                QProgressBar {
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background-color: #0f172a;
                    border-radius: 3px;
                }
            """)

            count_lbl = QLabel("0 ulasan (0%)")
            count_lbl.setFixedWidth(120)
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count_lbl.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500;")

            row_layout.addWidget(star_lbl)
            row_layout.addWidget(pbar, stretch=1)
            row_layout.addWidget(count_lbl)
            dist_layout.addLayout(row_layout)

            self.star_bars[star] = {"bar": pbar, "lbl": count_lbl}

        self.content_layout.addWidget(dist_card)

        # -------------------------------------------------------------
        # 4. CASHIER PERFORMANCE & RATIO TABLE
        # -------------------------------------------------------------
        table_card = QFrame()
        table_card.setObjectName("CustomerCard")
        table_card.setStyleSheet("""
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        t_card_layout = QVBoxLayout(table_card)
        t_card_layout.setContentsMargins(22, 20, 22, 20)
        t_card_layout.setSpacing(14)

        t_title = QLabel("Tabel Performa Kasir & Rasio Bintang")
        t_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        t_card_layout.addWidget(t_title)

        self.cashier_table = QTableWidget()
        self.cashier_table.setColumnCount(7)
        self.cashier_table.setHorizontalHeaderLabels([
            "Nama Kasir", "Role", "Total Transaksi", "Omset Kotor",
            "Omset Bersih", "Rating Rata-rata", "Rasio Bintang (5★/4★/3★/2★/1★)"
        ])
        self.cashier_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cashier_table.verticalHeader().setVisible(False)
        self.cashier_table.setShowGrid(False)
        self.cashier_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #f1f5f9;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #ffffff;
                color: #64748b;
                font-weight: 600;
                font-size: 12px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 10px 12px;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f8fafc;
                padding: 10px 12px;
                font-size: 12px;
                color: #0f172a;
            }
        """)
        c_hdr = self.cashier_table.horizontalHeader()
        c_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.cashier_table.setMinimumHeight(240)

        t_card_layout.addWidget(self.cashier_table)
        self.content_layout.addWidget(table_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Initial data load
        self.refresh_data()

    def _create_kpi_card(self, title: str, init_val: str, init_sub: str, icon_name: str, icon_color: str):
        card = QFrame()
        card.setObjectName("CustomerCard")
        card.setStyleSheet("""
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase;")

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, icon_color, 16))

        top_row.addWidget(title_lbl)
        top_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        val_lbl = QLabel(init_val)
        val_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel(init_sub)
        sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(sub_lbl)

        return card, val_lbl, sub_lbl

    def refresh_data(self):
        """Loads and populates cashier rating ratios and performance stats."""
        try:
            cashiers = db_manager.get_cashier_rating_stats()
        except Exception:
            cashiers = []
        self.cashier_table.setRowCount(len(cashiers))

        total_tx = 0
        total_gross = 0.0
        total_net = 0.0
        all_rated_count = 0
        all_star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for row, c in enumerate(cashiers):
            # Cashier name
            name_item = QTableWidgetItem(str(c.get("name", "Unknown")))
            name_item.setFont(QFont("", 11, QFont.Weight.Bold))

            # Role
            role_item = QTableWidgetItem(str(c.get("role", "Cashier")).capitalize())
            role_item.setFont(QFont("", 11))

            # Total Transactions
            c_tx = int(c.get("total_tx", 0))
            total_tx += c_tx
            tx_item = QTableWidgetItem(f"{c_tx} Order")
            tx_item.setFont(QFont("", 11))

            # Omset Kotor
            gross = float(c.get("total_sales", 0.0))
            total_gross += gross
            gross_item = QTableWidgetItem(f"Rp {gross:,.0f}".replace(",", "."))
            gross_item.setFont(QFont("", 11, QFont.Weight.Medium))

            # Omset Bersih
            net = float(c.get("total_net", 0.0))
            total_net += net
            net_item = QTableWidgetItem(f"Rp {net:,.0f}".replace(",", "."))
            net_item.setFont(QFont("", 11, QFont.Weight.Bold))

            # Rating Rata-rata
            avg_r = float(c.get("avg_rating", 0.0))
            r_cnt = int(c.get("review_count", 0))
            all_rated_count += r_cnt
            if r_cnt > 0:
                rating_str = f"★ {avg_r:.1f} ({r_cnt} ulasan)"
            else:
                rating_str = "Belum Ada"
            rating_item = QTableWidgetItem(rating_str)
            rating_item.setFont(QFont("", 11, QFont.Weight.Bold))

            # Rasio Bintang
            s5 = int(c.get("star_5", 0))
            s4 = int(c.get("star_4", 0))
            s3 = int(c.get("star_3", 0))
            s2 = int(c.get("star_2", 0))
            s1 = int(c.get("star_1", 0))

            all_star_counts[5] += s5
            all_star_counts[4] += s4
            all_star_counts[3] += s3
            all_star_counts[2] += s2
            all_star_counts[1] += s1

            ratio_str = f"5★:{s5} | 4★:{s4} | 3★:{s3} | 2★:{s2} | 1★:{s1}"
            ratio_item = QTableWidgetItem(ratio_str)
            ratio_item.setFont(QFont("", 10))

            self.cashier_table.setItem(row, 0, name_item)
            self.cashier_table.setItem(row, 1, role_item)
            self.cashier_table.setItem(row, 2, tx_item)
            self.cashier_table.setItem(row, 3, gross_item)
            self.cashier_table.setItem(row, 4, net_item)
            self.cashier_table.setItem(row, 5, rating_item)
            self.cashier_table.setItem(row, 6, ratio_item)

        # 2. Overall Store Rating Stats
        kpis = db_manager.get_sales_kpis()
        avg_overall = kpis.get("avg_rating", 0.0)
        total_reviews = kpis.get("total_reviews", 0)

        if total_reviews > 0:
            self.val_rating.setText(f"★ {avg_overall:.1f} / 5.0")
            self.sub_rating.setText(f"Berdasarkan {total_reviews} Ulasan Pelanggan")
        else:
            self.val_rating.setText("Belum Ada")
            self.sub_rating.setText("Menunggu ulasan pelanggan")

        self.val_reviews.setText(f"{total_reviews} Ulasan")
        self.sub_reviews.setText(f"Dari {total_tx} total transaksi" if total_tx > 0 else "0 transaksi")

        self.val_gross.setText(f"Rp {total_gross:,.0f}".replace(",", "."))
        self.sub_gross.setText(f"{total_tx} total pesanan")

        margin_pct = (total_net / total_gross * 100.0) if total_gross > 0 else 0.0
        self.val_net.setText(f"Rp {total_net:,.0f}".replace(",", "."))
        self.sub_net.setText(f"Margin Keuntungan: {margin_pct:.1f}%")

        # 3. Update Distribution Bars
        for star, data in self.star_bars.items():
            cnt = all_star_counts.get(star, 0)
            pct = int((cnt / total_reviews * 100.0)) if total_reviews > 0 else 0
            data["bar"].setValue(pct)
            data["lbl"].setText(f"{cnt} ulasan ({pct}%)")

    def refresh_translations(self):
        """Refreshes translated labels upon language change."""
        self.title_lbl.setText(t("cashier_ratings_title"))
        self.subtitle_lbl.setText(t("cashier_ratings_subtitle"))
        self.refresh_data()
