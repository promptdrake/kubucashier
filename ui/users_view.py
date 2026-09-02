"""
User Management View for KubuCashier.
Clean Black and White Minimalist Interface.
Accessible exclusively to Owner and Admin roles to manage staff accounts, roles, and passwords.
"""

from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from auth.auth_service import auth_service
from database.db_manager import db_manager
from ui.i18n import t, get_language
from ui.icons import get_svg_icon, get_svg_pixmap
from ui.theme import ThemeColors
from ui.components.notification_banner import NotificationBanner
from ui.components.user_dialog import UserDialog


class UsersView(QWidget):
    """Staff user accounts management interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user: Optional[Dict[str, Any]] = None
        self._init_ui()
        self.refresh_all_users()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 24, 36, 28)
        main_layout.setSpacing(16)

        # 1. HEADER ROW
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_text_box = QVBoxLayout()
        header_text_box.setSpacing(2)

        self.title_lbl = QLabel(t("users_title"))
        self.title_lbl.setObjectName("GreetingTitle")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #0f172a;")

        self.subtitle_lbl = QLabel(t("users_subtitle"))
        self.subtitle_lbl.setObjectName("SubtitleLabel")
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748b;")

        header_text_box.addWidget(self.title_lbl)
        header_text_box.addWidget(self.subtitle_lbl)
        header_row.addLayout(header_text_box)
        header_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Add User Button (Black & White style)
        self.add_user_btn = QPushButton(f"  {t('add_user_btn')}")
        self.add_user_btn.setObjectName("PrimaryButton")
        self.add_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_user_btn.setFixedHeight(36)
        self.add_user_btn.setIcon(get_svg_icon("plus", "#ffffff", 16))
        self.add_user_btn.clicked.connect(self._open_add_user_dialog)
        header_row.addWidget(self.add_user_btn)

        main_layout.addLayout(header_row)

        # Status Alert Banner
        self.status_banner = NotificationBanner(self)
        main_layout.addWidget(self.status_banner)

        # 2. SEARCH TOOLBAR
        filter_box = QHBoxLayout()
        filter_box.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_users"))
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search_changed)

        filter_box.addWidget(self.search_input, stretch=1)
        main_layout.addLayout(filter_box)

        # 3. USERS TABLE
        table_frame = QFrame()
        table_frame.setObjectName("SurfaceCard")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            t("th_fullname"), t("th_username"), t("th_role"),
            t("th_created_at"), t("th_actions")
        ])
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setShowGrid(False)
        self.users_table.setStyleSheet("""
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

        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.users_table.setColumnWidth(1, 160)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.users_table.setColumnWidth(2, 130)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.users_table.setColumnWidth(3, 160)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.users_table.setColumnWidth(4, 110)

        table_layout.addWidget(self.users_table)
        main_layout.addWidget(table_frame)

    def set_current_user(self, user: Dict[str, Any]):
        self.current_user = user
        self.refresh_all_users()

    def refresh_translations(self):
        self.title_lbl.setText(t("users_title"))
        self.subtitle_lbl.setText(t("users_subtitle"))
        self.add_user_btn.setText(f"  {t('add_user_btn')}")
        self.search_input.setPlaceholderText(t("search_users"))
        self.users_table.setHorizontalHeaderLabels([
            t("th_fullname"), t("th_username"), t("th_role"),
            t("th_created_at"), t("th_actions")
        ])
        self.refresh_all_users()

    def _on_search_changed(self):
        self.refresh_all_users()

    def refresh_all_users(self):
        self.users_table.clearContents()
        search_query = self.search_input.text().strip().lower()

        all_users = db_manager.get_all_users()
        if search_query:
            all_users = [
                u for u in all_users
                if search_query in u.get("name", "").lower() or search_query in u.get("username", "").lower()
            ]

        self.users_table.setRowCount(len(all_users))
        curr_user_id = self.current_user.get("id") if self.current_user else None

        for row_idx, user in enumerate(all_users):
            self.users_table.setRowHeight(row_idx, 48)

            # 1. Full Name
            name_text = user.get("name", "")
            if curr_user_id and user.get("id") == curr_user_id:
                name_text += " (You)"
            name_item = QTableWidgetItem(name_text)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row_idx, 0, name_item)

            # 2. Username
            uname_item = QTableWidgetItem(f"@{user.get('username', '')}")
            uname_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row_idx, 1, uname_item)

            # 3. Role Badge
            role_str = user.get("role", "Cashier").upper()
            role_container = QWidget()
            role_layout = QHBoxLayout(role_container)
            role_layout.setContentsMargins(0, 0, 0, 0)
            role_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            role_lbl = QLabel(f" {role_str} ")
            role_lbl.setStyleSheet("""
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            """)
            role_layout.addWidget(role_lbl)
            self.users_table.setCellWidget(row_idx, 2, role_container)

            # 4. Registered Date
            created_str = str(user.get("created_at", ""))
            if len(created_str) > 10:
                created_str = created_str[:10]
            date_item = QTableWidgetItem(created_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.users_table.setItem(row_idx, 3, date_item)

            # 5. Actions (Edit & Delete)
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
            edit_btn.clicked.connect(lambda _, u=user: self._open_edit_user_dialog(u))

            del_btn = QPushButton()
            del_btn.setObjectName("IconButton")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setToolTip(t("delete"))
            del_btn.setIcon(get_svg_icon("trash", "#ef4444", 14))

            # Guard: Cannot delete self
            is_self = curr_user_id and user.get("id") == curr_user_id
            if is_self:
                del_btn.setEnabled(False)
                del_btn.setToolTip(t("cannot_delete_self"))
                del_btn.setIcon(get_svg_icon("trash", "#cbd5e1", 14))
            else:
                del_btn.clicked.connect(lambda _, u=user: self._delete_user(u))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            self.users_table.setCellWidget(row_idx, 4, action_widget)

    # -------------------------------------------------------------
    # DIALOG HANDLERS
    # -------------------------------------------------------------
    def _open_add_user_dialog(self):
        dlg = UserDialog(self)
        if dlg.exec():
            vals = dlg.get_user_values()
            success, msg, _ = auth_service.admin_create_user(
                name=vals["name"],
                username=vals["username"],
                password=vals["password"],
                role=vals["role"]
            )
            if success:
                self.refresh_all_users()
                self.status_banner.show_success(t("user_saved"))
            else:
                self.status_banner.show_error(msg)

    def _open_edit_user_dialog(self, user: Dict[str, Any]):
        dlg = UserDialog(self, user_data=user)
        if dlg.exec():
            vals = dlg.get_user_values()
            success, msg = auth_service.update_user_account(
                user_id=user["id"],
                name=vals["name"],
                role=vals["role"],
                new_password=vals["password"] if vals["password"] else None
            )
            if success:
                self.refresh_all_users()
                self.status_banner.show_success(t("user_saved"))
            else:
                self.status_banner.show_error(msg)

    def _delete_user(self, user: Dict[str, Any]):
        curr_user_id = self.current_user.get("id") if self.current_user else None
        confirm_msg = t("confirm_delete_user", name=user["name"], username=user["username"])
        reply = QMessageBox.question(
            self,
            t("delete"),
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = auth_service.delete_user_account(user["id"], current_user_id=curr_user_id)
            if success:
                self.refresh_all_users()
                self.status_banner.show_success(t("user_deleted"))
            else:
                self.status_banner.show_error(msg)
