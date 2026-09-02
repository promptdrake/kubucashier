"""
Unit and Integration Tests for Customer Facing Display (CFD) in KubuCashier.
"""

import unittest
import sys
from PyQt6.QtWidgets import QApplication

from config import config
from services.customer_display_manager import customer_display_manager
from ui.customer_display_view import CustomerDisplayWindow


class TestCustomerDisplay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfd = CustomerDisplayWindow()

    def tearDown(self):
        self.cfd.close()
        customer_display_manager.close()

    def test_customer_display_initial_state(self):
        self.assertEqual(self.cfd.stack.currentIndex(), 0)  # Idle state

    def test_customer_display_cart_sync(self):
        sample_cart = {
            1: {"name": "Soto Ayam", "price": 15000, "quantity": 2},
            2: {"name": "Es Teh", "price": 4000, "quantity": 1}
        }
        self.cfd.update_cart(sample_cart, 34000.0)
        self.assertEqual(self.cfd.stack.currentIndex(), 1)  # Active order state
        self.assertEqual(self.cfd.order_table.rowCount(), 2)
        self.assertEqual(self.cfd.cfd_grand_total_lbl.text(), "Rp 34.000")

    def test_customer_display_empty_cart_reverts_to_idle(self):
        self.cfd.update_cart({}, 0.0)
        self.assertEqual(self.cfd.stack.currentIndex(), 0)  # Idle state

    def test_customer_display_checkout_qris(self):
        config.qris_static_payload = "00020101021126600014ID.LINKAJA.WWW0118936009110022098273021000220982730303UMI51440014ID.CO.QRIS.WWW0215ID10200210002200303UMI5204581253033605802ID5918WARUNG KOPI KUBU6007JAKARTA61051234062070703A01630489AB"
        self.cfd.show_checkout_state("QRIS", 50000.0)
        self.assertEqual(self.cfd.stack.currentIndex(), 2)  # Checkout state
        self.assertFalse(self.cfd.qris_view_widget.isHidden())
        self.assertTrue(self.cfd.cash_view_widget.isHidden())

    def test_customer_display_checkout_cash(self):
        self.cfd.show_checkout_state("Cash", 50000.0, paid_amount=100000.0, change_amount=50000.0)
        self.assertEqual(self.cfd.stack.currentIndex(), 2)
        self.assertTrue(self.cfd.qris_view_widget.isHidden())
        self.assertFalse(self.cfd.cash_view_widget.isHidden())

    def test_customer_display_success_state(self):
        self.cfd.show_transaction_success("INV-2026-9999", change_amount=10000.0)
        self.assertEqual(self.cfd.stack.currentIndex(), 3)  # Success state
        self.assertIn("INV-2026-9999", self.cfd.succ_invoice_lbl.text())

    def test_config_customer_display_toggles(self):
        config.set_customer_display(True, monitor=2, persist=False)
        self.assertTrue(config.customer_display_enabled)
        self.assertEqual(config.customer_display_monitor, 2)

        config.set_customer_display(False, monitor=1, persist=False)
        self.assertFalse(config.customer_display_enabled)


if __name__ == "__main__":
    unittest.main()
