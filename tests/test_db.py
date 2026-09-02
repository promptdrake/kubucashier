"""Unit tests for SQLite database manager (Users, Categories, Products)."""
import os
import unittest
import tempfile
import sqlite3

from database.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = DatabaseManager(self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_add_and_get_user(self):
        user_id = self.db.add_user(
            name="Alice Smith",
            username="alicesmith",
            password_hash="hash123",
            salt="salt123",
            role="Cashier"
        )
        self.assertGreater(user_id, 0)

        # Retrieve by exact username
        user = self.db.get_user_by_username("alicesmith")
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Alice Smith")
        self.assertEqual(user["role"], "Cashier")

        # Retrieve case-insensitively
        user_case = self.db.get_user_by_username("ALICESMITH")
        self.assertIsNotNone(user_case)
        self.assertEqual(user_case["id"], user_id)

    def test_unique_username_constraint(self):
        self.db.add_user("User 1", "uniqueuser", "hash1", "salt1", "Owner")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_user("User 2", "uniqueuser", "hash2", "salt2", "Sales")

    def test_count_and_get_all(self):
        self.assertEqual(self.db.count_users(), 0)
        self.db.add_user("User A", "usera", "h", "s", "Cashier")
        self.db.add_user("User B", "userb", "h", "s", "Sales")
        self.assertEqual(self.db.count_users(), 2)
        users = self.db.get_all_users()
        self.assertEqual(len(users), 2)

    def test_categories_crud(self):
        # Starts with zero categories
        cats = self.db.get_all_categories()
        self.assertEqual(len(cats), 0)

        # Add new category
        cat_id = self.db.add_category("Snack Bar")
        self.assertGreater(cat_id, 0)

        # Update category
        self.assertTrue(self.db.update_category(cat_id, "Snack & Pastry"))
        cat = self.db.get_category_by_id(cat_id)
        self.assertEqual(cat["name"], "Snack & Pastry")

        # Delete category
        self.assertTrue(self.db.delete_category(cat_id))
        self.assertIsNone(self.db.get_category_by_id(cat_id))

    def test_products_crud(self):
        cat_id = self.db.add_category("Coffee")

        # Add product
        prod_id = self.db.add_product(
            name="Iced Caramel Macchiato",
            category_id=cat_id,
            price=28000.0,
            stock=45,
            image_path=None
        )
        self.assertGreater(prod_id, 0)
        self.assertEqual(self.db.count_products(), 1)

        # Get product
        prod = self.db.get_product_by_id(prod_id)
        self.assertIsNotNone(prod)
        self.assertEqual(prod["name"], "Iced Caramel Macchiato")
        self.assertEqual(prod["price"], 28000.0)
        self.assertEqual(prod["stock"], 45)
        self.assertEqual(prod["category_name"], "Coffee")

        # Filter products by category and search
        filtered = self.db.get_all_products(category_id=cat_id, search_query="caramel")
        self.assertEqual(len(filtered), 1)

        # Update product
        self.assertTrue(self.db.update_product(
            product_id=prod_id,
            name="Iced Caramel Macchiato Large",
            category_id=cat_id,
            price=32000.0,
            stock=40,
            image_path=None
        ))
        updated_prod = self.db.get_product_by_id(prod_id)
        self.assertEqual(updated_prod["price"], 32000.0)
        self.assertEqual(updated_prod["name"], "Iced Caramel Macchiato Large")

        # Delete product
        self.assertTrue(self.db.delete_product(prod_id))
        self.assertEqual(self.db.count_products(), 0)

    def test_create_transaction_and_stock_deduction(self):
        cat_id = self.db.add_category("Food")
        prod_id = self.db.add_product("Nasi Goreng", cat_id, 25000.0, stock=10)

        items = [
            {"product_id": prod_id, "name": "Nasi Goreng", "price": 25000.0, "quantity": 3}
        ]

        success, invoice_no, tx_id = self.db.create_transaction(
            user_id=1,
            items=items,
            total_amount=75000.0,
            paid_amount=100000.0,
            change_amount=25000.0,
            payment_method="Cash"
        )
        self.assertTrue(success)
        self.assertTrue(invoice_no.startswith("INV-"))
        self.assertGreater(tx_id, 0)

        # Stock should be decremented from 10 to 7
        updated_prod = self.db.get_product_by_id(prod_id)
        self.assertEqual(updated_prod["stock"], 7)

        # Recent transactions should include this invoice
        txs = self.db.get_recent_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["invoice_no"], invoice_no)
        self.assertEqual(txs[0]["total_amount"], 75000.0)

    def test_wipe_transactions(self):
        cat_id = self.db.add_category("Beverages")
        prod_id = self.db.add_product("Mineral Water", cat_id, 5000.0, stock=20)
        u_id = self.db.add_user("Cashier 1", "cashier1", "h", "s", "Cashier")

        # Create 2 transactions
        self.db.create_transaction(u_id, [{"product_id": prod_id, "name": "Mineral Water", "price": 5000.0, "quantity": 1}], 5000.0, 5000.0, 0.0, "Cash")
        self.db.create_transaction(u_id, [{"product_id": prod_id, "name": "Mineral Water", "price": 5000.0, "quantity": 2}], 10000.0, 10000.0, 0.0, "QRIS")

        txs_before = self.db.get_recent_transactions(limit=10)
        self.assertEqual(len(txs_before), 2)

        # Wipe transactions
        self.assertTrue(self.db.wipe_transactions())

        # Transactions should be 0, but product and user remain intact
        txs_after = self.db.get_recent_transactions(limit=10)
        self.assertEqual(len(txs_after), 0)
        self.assertEqual(self.db.count_products(), 1)
        self.assertEqual(self.db.count_users(), 1)

    def test_cashier_rating_stats(self):
        u_id = self.db.add_user("John Cashier", "john", "h", "s", "Cashier")
        cat_id = self.db.add_category("Food")
        prod_id = self.db.add_product("Burger", cat_id, 30000.0, stock=50, cost_price=18000.0)

        # Create transaction with rating
        _, inv_no, _ = self.db.create_transaction(
            user_id=u_id,
            items=[{"product_id": prod_id, "name": "Burger", "price": 30000.0, "quantity": 1}],
            total_amount=30000.0,
            paid_amount=30000.0,
            change_amount=0.0,
            payment_method="Cash",
            subtotal_amount=30000.0
        )
        self.db.record_transaction_rating(inv_no, 5)

        stats = self.db.get_cashier_rating_stats()
        self.assertGreaterEqual(len(stats), 1)
        john_stat = next(s for s in stats if s["id"] == u_id)
        self.assertEqual(john_stat["total_tx"], 1)
        self.assertEqual(john_stat["total_sales"], 30000.0)
        self.assertEqual(john_stat["total_net"], 12000.0)
        self.assertEqual(john_stat["star_5"], 1)
        self.assertEqual(john_stat["avg_rating"], 5.0)


if __name__ == "__main__":
    unittest.main()
