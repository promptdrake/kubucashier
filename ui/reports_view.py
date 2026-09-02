"""
Reports and Analytics View for KubuCashier.
Provides Owner/Admin with real-time Gross vs Net Profit (Omset Kotor vs Omset Bersih),
Total HPP (Cost of Goods Sold), Cashier Rating Performance Ratio (1-5 stars),
interactive revenue trend charts, best-selling items ranking, and filterable transaction logs.
Clean Light Minimalist Black & White theme matching KubuCashier design system.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSpacerItem,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPaintEvent

from database.db_manager import db_manager
from ui.i18n import t, get_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors


class SalesBarChartWidget(QWidget):
    """Clean vector bar chart widget rendering daily/monthly revenue trends using QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_data: List[Dict[str, Any]] = []
        self.setMinimumHeight(240)
        self.setStyleSheet("background-color: transparent;")

    def set_data(self, data: List[Dict[str, Any]]):
        self.chart_data = data
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_bottom = 36
        margin_top = 30
        margin_left = 20
        margin_right = 20

        usable_w = w - margin_left - margin_right
        usable_h = h - margin_top - margin_bottom

        if not self.chart_data:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("", 13))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Belum ada data transaksi.")
            return

        max_val = max((float(d.get("total_sales", 0)) for d in self.chart_data), default=0.0)
        if max_val <= 0:
            max_val = 100000.0  # fallback baseline

        n = len(self.chart_data)
        slot_w = usable_w / max(1, n)
        bar_w = min(46, max(18, slot_w * 0.55))

        # Draw light horizontal grid line at bottom
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawLine(margin_left, int(h - margin_bottom), int(w - margin_right), int(h - margin_bottom))

        for i, item in enumerate(self.chart_data):
            val = float(item.get("total_sales", 0))
            date_raw = str(item.get("date_str", ""))

            # Format date label (e.g., "02 Sep" or "02")
            try:
                dt = datetime.strptime(date_raw, "%Y-%m-%d")
                day_lbl = dt.strftime("%d %b")
            except Exception:
                day_lbl = date_raw[-5:] if len(date_raw) >= 5 else date_raw

            center_x = margin_left + (i + 0.5) * slot_w
            bar_x = center_x - bar_w / 2

            bar_h = max(4.0, (val / max_val) * usable_h) if val > 0 else 4.0
            bar_y = (h - margin_bottom) - bar_h

            # Bar Fill
            if val > 0:
                bar_color = QColor("#0f172a") if i == n - 1 else QColor("#334155")
            else:
                bar_color = QColor("#e2e8f0")

            painter.setBrush(QBrush(bar_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 6, 6)

            # Amount Label above bar
            if val > 0:
                painter.setPen(QColor("#0f172a"))
                painter.setFont(QFont("", 10, QFont.Weight.Bold))
                if val >= 1000000:
                    val_str = f"{val/1000000:.1f}M"
                elif val >= 1000:
                    val_str = f"{val/1000:.0f}k"
                else:
                    val_str = f"{val:.0f}"
                painter.drawText(QRectF(center_x - 35, bar_y - 20, 70, 18), Qt.AlignmentFlag.AlignCenter, val_str)

            # Date Label below bar
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("", 10, QFont.Weight.Medium))
            painter.drawText(QRectF(center_x - 30, h - margin_bottom + 8, 60, 20), Qt.AlignmentFlag.AlignCenter, day_lbl)


class ReportsView(QWidget):
    """Comprehensive sales performance, gross/net profit, and transaction logs view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user: Optional[Dict[str, Any]] = None
        self.current_page: int = 1
        self.page_size: int = 10
        self.filtered_transactions: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(28, 24, 28, 28)
        self.content_layout.setSpacing(24)

        # -------------------------------------------------------------
        # 1. HEADER & REFRESH BAR
        # -------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)

        title_lbl = QLabel(t("reports"))
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #0f172a;")
        sub_lbl = QLabel("Ringkasan omset kotor, HPP modal, omset bersih, rasio rating kasir, dan grafik penjualan.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #64748b;")

        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(sub_lbl)
        header_row.addLayout(header_vbox)

        header_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Refresh Button
        self.refresh_btn = QPushButton("  Refresh Data")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIcon(get_svg_icon("refresh", "#0f172a", 15))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_all_reports)
        header_row.addWidget(self.refresh_btn)

        self.content_layout.addLayout(header_row)

        # -------------------------------------------------------------
        # 2. TOP KPI CARDS (4 STATS IN ROW)
        # -------------------------------------------------------------
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        # KPI 1: Omset Kotor (Gross Sales)
        self.card_gross, self.val_gross_sales, self.sub_gross_desc = self._create_kpi_card(
            title="Omset Kotor (Gross)",
            icon_name="dollar-sign",
            icon_color="#0f172a"
        )
        kpi_grid.addWidget(self.card_gross, 0, 0)

        # KPI 2: Total HPP (Cost of Goods)
        self.card_hpp, self.val_total_hpp, self.sub_hpp_desc = self._create_kpi_card(
            title="Total Modal (HPP)",
            icon_name="package",
            icon_color="#64748b"
        )
        kpi_grid.addWidget(self.card_hpp, 0, 1)

        # KPI 3: Omset Bersih (Net Profit)
        self.card_net, self.val_net_profit, self.sub_net_desc = self._create_kpi_card(
            title="Omset Bersih (Laba)",
            icon_name="trending-up",
            icon_color="#16a34a"
        )
        kpi_grid.addWidget(self.card_net, 0, 2)

        # KPI 4: Customer Satisfaction & Rating
        self.card_rating, self.val_avg_rating, self.sub_rating_desc = self._create_kpi_card(
            title="Rating Kepuasan Pelanggan",
            icon_name="star",
            icon_color="#eab308"
        )
        kpi_grid.addWidget(self.card_rating, 0, 3)

        self.content_layout.addLayout(kpi_grid)

        # -------------------------------------------------------------
        # 3. MIDDLE SECTION: SALES GRAPH + TOP SELLING ITEMS
        # -------------------------------------------------------------
        mid_row = QHBoxLayout()
        mid_row.setSpacing(18)

        # Left Card: Sales Trend Bar Chart
        chart_card = QFrame()
        chart_card.setObjectName("CustomerCard")
        chart_card.setStyleSheet("""
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        chart_layout.setSpacing(14)

        chart_head = QHBoxLayout()
        chart_title = QLabel(t("sales_trend"))
        chart_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        chart_head.addWidget(chart_title)
        chart_head.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.chart_period_cb = QComboBox()
        self.chart_period_cb.addItems(["7 Hari Terakhir", "30 Hari Terakhir"])
        self.chart_period_cb.setStyleSheet("""
            QComboBox {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                color: #0f172a;
            }
        """)
        self.chart_period_cb.currentIndexChanged.connect(self._on_chart_period_changed)
        chart_head.addWidget(self.chart_period_cb)
        chart_layout.addLayout(chart_head)

        self.sales_chart = SalesBarChartWidget()
        chart_layout.addWidget(self.sales_chart)

        mid_row.addWidget(chart_card, stretch=6)

        # Right Card: Top Best Selling Products
        top_card = QFrame()
        top_card.setObjectName("CustomerCard")
        top_card.setStyleSheet("""
            QFrame#CustomerCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(20, 20, 20, 20)
        top_layout.setSpacing(12)

        top_title = QLabel(t("best_selling_products"))
        top_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        top_layout.addWidget(top_title)

        self.top_items_container = QVBoxLayout()
        self.top_items_container.setSpacing(10)
        top_layout.addLayout(self.top_items_container)
        top_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        mid_row.addWidget(top_card, stretch=4)
        self.content_layout.addLayout(mid_row)

        # -------------------------------------------------------------
        # 4. BOTTOM SECTION: TRANSACTION LOGS TABLE WITH PAGINATION (10 ROWS PER PAGE)
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
        t_card_layout.setContentsMargins(20, 20, 20, 20)
        t_card_layout.setSpacing(16)

        table_header_row = QHBoxLayout()
        t_title = QLabel(t("recent_transactions_log"))
        t_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        table_header_row.addWidget(t_title)

        table_header_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Filter Period dropdown
        self.filter_period_cb = QComboBox()
        self.filter_period_cb.addItem(t("filter_period_all"), "all")
        self.filter_period_cb.addItem(t("filter_period_today"), "today")
        self.filter_period_cb.addItem(t("filter_period_week"), "week")
        self.filter_period_cb.addItem(t("filter_period_month"), "month")
        self.filter_period_cb.setStyleSheet("""
            QComboBox {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                color: #0f172a;
            }
        """)
        self.filter_period_cb.currentIndexChanged.connect(self._on_table_filter_changed)
        table_header_row.addWidget(self.filter_period_cb)

        # Search Bar for Transactions
        self.search_tx_input = QLineEdit()
        self.search_tx_input.setPlaceholderText("Cari No. Invoice / Kasir...")
        self.search_tx_input.setFixedWidth(200)
        self.search_tx_input.setFixedHeight(32)
        self.search_tx_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                color: #0f172a;
            }
        """)
        self.search_tx_input.textChanged.connect(self._on_table_filter_changed)
        table_header_row.addWidget(self.search_tx_input)

        t_card_layout.addLayout(table_header_row)

        # Transaction Table (Displays 10 rows per page)
        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(8)
        self.tx_table.setHorizontalHeaderLabels([
            "Invoice No", "Waktu", "Kasir", "Biaya (Fee)", "Total (Omset Kotor)", "Laba Bersih", "Metode", "Rating"
        ])
        self.tx_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setShowGrid(False)
        self.tx_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #f1f5f9;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px 10px;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f8fafc;
                padding: 6px 10px;
                font-size: 12px;
                color: #0f172a;
            }
        """)
        header = self.tx_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(1, 150)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(2, 90)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(3, 85)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(4, 130)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(5, 120)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(6, 75)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tx_table.setColumnWidth(7, 75)
        self.tx_table.setMinimumHeight(440)

        t_card_layout.addWidget(self.tx_table)

        # Pagination Control Bar
        pagination_row = QHBoxLayout()
        pagination_row.setContentsMargins(0, 8, 0, 0)

        self.showing_lbl = QLabel("Menampilkan 0-0 dari 0 transaksi")
        self.showing_lbl.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500;")
        pagination_row.addWidget(self.showing_lbl)

        pagination_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.prev_btn = QPushButton(t("prev_page"))
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover:!disabled { background-color: #f1f5f9; border-color: #94a3b8; }
            QPushButton:disabled { color: #cbd5e1; border-color: #e2e8f0; background-color: #f8fafc; }
        """)
        self.prev_btn.clicked.connect(self._prev_page)
        pagination_row.addWidget(self.prev_btn)

        self.page_info_lbl = QLabel("Halaman 1 dari 1")
        self.page_info_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a; padding: 0 10px;")
        pagination_row.addWidget(self.page_info_lbl)

        self.next_btn = QPushButton(t("next_page"))
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover:!disabled { background-color: #f1f5f9; border-color: #94a3b8; }
            QPushButton:disabled { color: #cbd5e1; border-color: #e2e8f0; background-color: #f8fafc; }
        """)
        self.next_btn.clicked.connect(self._next_page)
        pagination_row.addWidget(self.next_btn)

        t_card_layout.addLayout(pagination_row)
        self.content_layout.addWidget(table_card)

        scroll_area.setWidget(content_widget)
        master_layout.addWidget(scroll_area)

    def _create_kpi_card(self, title: str, icon_name: str, icon_color: str):
        card = QFrame()
        card.setObjectName("KPICard")
        card.setStyleSheet("""
            QFrame#KPICard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Header Row
        head_row = QHBoxLayout()
        head_row.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, icon_color, 16))

        head_row.addWidget(title_lbl)
        head_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        head_row.addWidget(icon_lbl)
        layout.addLayout(head_row)

        val_lbl = QLabel("Rp 0")
        val_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #0f172a;")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel("0 Transaksi")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        layout.addWidget(sub_lbl)

        return card, val_lbl, sub_lbl

    def refresh_all_reports(self):
        """Refreshes all KPIs, charts, best selling products, and transaction tables."""
        self._refresh_kpis()
        self._refresh_sales_chart()
        self._refresh_top_products()
        self._refresh_transactions_table()

    def _refresh_kpis(self):
        kpis = db_manager.get_sales_kpis()
        
        # 1. Gross Sales (Today & Month)
        today_gross = kpis.get("today_sales", 0.0)
        today_orders = kpis.get("today_orders", 0)
        month_gross = kpis.get("month_sales", 0.0)
        self.val_gross_sales.setText(f"Rp {today_gross:,.0f}".replace(",", "."))
        self.sub_gross_desc.setText(f"{today_orders} Transaksi Hari Ini • Bulan: Rp {month_gross:,.0f}".replace(",", "."))

        # 2. Total HPP (Cost of Goods)
        today_cost = kpis.get("today_cost", 0.0)
        month_cost = kpis.get("month_cost", 0.0)
        self.val_total_hpp.setText(f"Rp {today_cost:,.0f}".replace(",", "."))
        self.sub_hpp_desc.setText(f"Biaya Modal Hari Ini • Bulan: Rp {month_cost:,.0f}".replace(",", "."))

        # 3. Omset Bersih (Net Profit)
        today_net = kpis.get("today_net", 0.0)
        margin = kpis.get("profit_margin", 0.0)
        self.val_net_profit.setText(f"Rp {today_net:,.0f}".replace(",", "."))
        self.sub_net_desc.setText(f"Laba Bersih Hari Ini • Margin {margin:.1f}%")

        # 4. Customer Rating
        avg_rating = kpis.get("avg_rating", 0.0)
        total_rev = kpis.get("total_reviews", 0)
        if total_rev > 0:
            self.val_avg_rating.setText(f"⭐ {avg_rating:.1f} / 5.0")
            self.sub_rating_desc.setText(f"Berdasarkan {total_rev} Ulasan Pelanggan")
        else:
            self.val_avg_rating.setText("⭐ 5.0 / 5.0")
            self.sub_rating_desc.setText("Belum ada rating pelanggan")

    def _refresh_sales_chart(self):
        days = 30 if self.chart_period_cb.currentIndex() == 1 else 7
        data = db_manager.get_daily_sales_chart_data(days=days)
        self.sales_chart.set_data(data)

    def _on_chart_period_changed(self):
        self._refresh_sales_chart()

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                w = child.widget()
                w.setParent(None)
                w.deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _refresh_top_products(self):
        self._clear_layout(self.top_items_container)

        top_prods = db_manager.get_top_selling_products(limit=6)
        if not top_prods:
            empty_lbl = QLabel("Belum ada data penjualan produk.")
            empty_lbl.setStyleSheet("font-size: 12px; color: #94a3b8; font-style: italic;")
            self.top_items_container.addWidget(empty_lbl)
            return

        max_qty = max((p.get("total_qty", 0) for p in top_prods), default=1)
        if max_qty <= 0:
            max_qty = 1

        for idx, prod in enumerate(top_prods, start=1):
            row_box = QVBoxLayout()
            row_box.setSpacing(4)

            # Top: Rank, Name, Price, Sold
            h_line = QHBoxLayout()
            rank_lbl = QLabel(f"#{idx}")
            rank_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748b;")
            rank_lbl.setFixedWidth(24)

            name_lbl = QLabel(prod["product_name"])
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")

            rev_val = float(prod.get("total_revenue", 0))
            rev_lbl = QLabel(f"Rp {rev_val:,.0f}".replace(",", "."))
            rev_lbl.setStyleSheet("font-size: 12px; color: #64748b;")

            qty_val = int(prod.get("total_qty", 0))
            qty_badge = QLabel(f" {qty_val} terjual ")
            qty_badge.setStyleSheet("""
                background-color: #f1f5f9;
                color: #0f172a;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 6px;
            """)

            h_line.addWidget(rank_lbl)
            h_line.addWidget(name_lbl, stretch=1)
            h_line.addWidget(rev_lbl)
            h_line.addWidget(qty_badge)
            row_box.addLayout(h_line)

            # Progress Bar
            pbar = QProgressBar()
            pbar.setFixedHeight(5)
            pbar.setTextVisible(False)
            pbar.setRange(0, max_qty)
            pbar.setValue(qty_val)
            pbar.setStyleSheet("""
                QProgressBar {
                    background-color: #f1f5f9;
                    border: none;
                    border-radius: 2px;
                }
                QProgressBar::chunk {
                    background-color: #0f172a;
                    border-radius: 2px;
                }
            """)
            row_box.addWidget(pbar)
            self.top_items_container.addLayout(row_box)

    def _refresh_transactions_table(self):
        period = self.filter_period_cb.currentData() or "all"
        search = self.search_tx_input.text().strip()
        self.filtered_transactions = db_manager.get_filtered_transactions(period=period, search=search, limit=500)
        self._render_page_transactions()

    def _get_total_pages(self) -> int:
        total = len(self.filtered_transactions)
        return max(1, (total + self.page_size - 1) // self.page_size)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_page_transactions()

    def _next_page(self):
        if self.current_page < self._get_total_pages():
            self.current_page += 1
            self._render_page_transactions()

    def _render_page_transactions(self):
        total_items = len(self.filtered_transactions)
        total_pages = self._get_total_pages()
        self.current_page = min(max(1, self.current_page), total_pages)

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        page_txs = self.filtered_transactions[start_idx:end_idx]

        # Update Showing count and Pagination buttons
        if total_items > 0:
            self.showing_lbl.setText(f"Menampilkan {start_idx + 1}-{end_idx} dari {total_items} transaksi")
        else:
            self.showing_lbl.setText("Menampilkan 0-0 dari 0 transaksi")

        self.page_info_lbl.setText(f"Halaman {self.current_page} dari {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

        self.tx_table.setRowCount(len(page_txs))
        for row, tx in enumerate(page_txs):
            self.tx_table.setRowHeight(row, 40)

            inv_item = QTableWidgetItem(tx["invoice_no"])
            inv_item.setFont(QFont("", 11, QFont.Weight.Bold))

            date_str = str(tx.get("created_at", ""))
            date_item = QTableWidgetItem(date_str)
            date_item.setFont(QFont("", 11))

            cashier_name = tx.get("cashier_name") or "System"
            cashier_item = QTableWidgetItem(cashier_name)

            fee_amt = float(tx.get("fee_amount", 0.0))
            fee_str = f"+ Rp {fee_amt:,.0f}".replace(",", ".") if fee_amt > 0 else "-"
            fee_item = QTableWidgetItem(fee_str)
            fee_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            tot_val = float(tx.get("total_amount", 0.0))
            tot_str = f"Rp {tot_val:,.0f}".replace(",", ".")
            tot_item = QTableWidgetItem(tot_str)
            tot_item.setFont(QFont("", 11, QFont.Weight.Bold))
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            net_val = float(tx.get("net_profit", 0.0))
            net_str = f"Rp {net_val:,.0f}".replace(",", ".")
            net_item = QTableWidgetItem(net_str)
            net_item.setFont(QFont("", 11, QFont.Weight.Bold))
            net_item.setForeground(QColor("#16a34a"))
            net_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            method_item = QTableWidgetItem(tx.get("payment_method", "Cash"))
            method_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            rating_val = int(tx.get("rating", 0))
            rating_str = f"⭐ {rating_val}" if rating_val > 0 else "-"
            rating_item = QTableWidgetItem(rating_str)
            rating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            rating_item.setFont(QFont("", 11, QFont.Weight.Bold))

            self.tx_table.setItem(row, 0, inv_item)
            self.tx_table.setItem(row, 1, date_item)
            self.tx_table.setItem(row, 2, cashier_item)
            self.tx_table.setItem(row, 3, fee_item)
            self.tx_table.setItem(row, 4, tot_item)
            self.tx_table.setItem(row, 5, net_item)
            self.tx_table.setItem(row, 6, method_item)
            self.tx_table.setItem(row, 7, rating_item)

    def _on_table_filter_changed(self):
        self.current_page = 1
        self._refresh_transactions_table()

    def set_user(self, user: Dict[str, Any]):
        self.current_user = user
        self.refresh_all_reports()
