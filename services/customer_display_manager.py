"""
Customer Display Manager for KubuCashier.
Manages dual-screen POS customer display lifecycle, fullscreen borderless kiosk placement,
and real-time state synchronization with POS register actions.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from config import config
from ui.customer_display_view import CustomerDisplayWindow
from utils.logger import log_cfd, log_info


class CustomerDisplayManager(QObject):
    """Manages secondary customer monitor window and data routing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.window: Optional[CustomerDisplayWindow] = None

    def initialize(self):
        """Initializes and positions the customer display window in borderless full screen."""
        if not config.customer_display_enabled:
            log_cfd("STATUS", "Customer Display is disabled in configuration.")
            self.close()
            return

        if self.window is None:
            self.window = CustomerDisplayWindow()

        self._position_on_screen()

    def _position_on_screen(self):
        """Positions customer display on the target screen in borderless fullscreen."""
        if self.window is None:
            return

        screens = QApplication.screens()
        target_idx = max(0, config.customer_display_monitor - 1)

        if target_idx < len(screens):
            target_screen = screens[target_idx]
        elif len(screens) > 1:
            target_screen = screens[1]
        else:
            target_screen = screens[0]

        geom = target_screen.geometry()
        screen_name = target_screen.name() or f"Display {target_idx + 1}"

        # Configure window as frameless fullscreen kiosk on the second monitor
        self.window.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.window.show()

        if self.window.windowHandle():
            self.window.windowHandle().setScreen(target_screen)

        self.window.setGeometry(geom)
        self.window.showFullScreen()

        log_cfd("INITIALIZED", f"Placed Customer Display on '{screen_name}' ({geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}) in Full Screen.")

    def update_cart(
        self,
        cart_items: Dict[int, Dict[str, Any]],
        grand_total: float,
        subtotal_amount: float = 0.0,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0
    ):
        if self.window and self.window.isVisible():
            self.window.update_cart(
                cart_items=cart_items,
                grand_total=grand_total,
                subtotal_amount=subtotal_amount,
                fee_type=fee_type,
                fee_value=fee_value,
                fee_amount=fee_amount
            )
            if cart_items and grand_total > 0:
                total_qty = sum(it.get("quantity", 1) for it in cart_items.values())
                tot_str = f"Rp {grand_total:,.0f}".replace(",", ".")
                fee_log = f" (Fee: Rp {fee_amount:,.0f})" if fee_amount > 0 else ""
                log_cfd("SYNC_CART", f"Active order displayed: {total_qty} items, Total: {tot_str}{fee_log}")
            else:
                log_cfd("SYNC_CART", "Cart is empty -> Customer Display reverted to IDLE state.")

    def show_checkout(
        self,
        method: str,
        total_amount: float,
        paid_amount: float = 0.0,
        change_amount: float = 0.0,
        subtotal_amount: float = 0.0,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0
    ):
        if self.window and self.window.isVisible():
            self.window.show_checkout_state(
                method=method,
                total_amount=total_amount,
                paid_amount=paid_amount,
                change_amount=change_amount,
                subtotal_amount=subtotal_amount,
                fee_type=fee_type,
                fee_value=fee_value,
                fee_amount=fee_amount
            )
            tot_str = f"Rp {total_amount:,.0f}".replace(",", ".")
            fee_log = f" | Fee=+Rp {fee_amount:,.0f}" if fee_amount > 0 else ""
            if method == "Cash":
                chg_str = f"Rp {change_amount:,.0f}".replace(",", ".")
                paid_str = f"Rp {paid_amount:,.0f}".replace(",", ".")
                log_cfd("CHECKOUT", f"Method=Cash | Total={tot_str}{fee_log} | Paid={paid_str} | Change={chg_str}")
            elif method == "QRIS":
                log_cfd("CHECKOUT", f"Method=Dynamic QRIS | Amount={tot_str}{fee_log} displayed for customer scan")
            else:
                log_cfd("CHECKOUT", f"Method={method} | Amount={tot_str}{fee_log}")

    def show_success(self, invoice_no: str, change_amount: float = 0.0):
        if self.window and self.window.isVisible():
            self.window.show_transaction_success(invoice_no, change_amount)
            chg_str = f"Rp {change_amount:,.0f}".replace(",", ".")
            log_cfd("SUCCESS", f"Transaction completed: Invoice #{invoice_no} | Kembalian: {chg_str}")

    def show_break_mode(self):
        if self.window and self.window.isVisible():
            self.window.set_break_state()
            log_cfd("BREAK", "Customer Display switched to Break / Istirahat Mode.")

    def resume_from_break(self):
        if self.window and self.window.isVisible():
            self.window.resume_from_break()
            log_cfd("RESUME", "Customer Display resumed from Break Mode.")

    def set_user(self, user: Optional[Dict[str, Any]]):
        if self.window:
            self.window.set_user(user)

    def set_enabled(self, enabled: bool, monitor: Optional[int] = None):
        config.set_customer_display(enabled, monitor, persist=True)
        log_cfd("CONFIG", f"Enabled={enabled}, Target Monitor={config.customer_display_monitor}")
        if enabled:
            self.initialize()
        else:
            self.close()

    def close(self):
        if self.window:
            self.window.close()
            self.window = None
            log_cfd("CLOSED", "Customer Display window closed.")


# Global singleton instance
customer_display_manager = CustomerDisplayManager()
