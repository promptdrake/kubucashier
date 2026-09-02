"""
SQLite Database Manager for KubuCashier.
Handles schema initialization, user data storage, categories, products (with HPP / Cost Price),
transactions with fees (Percent / Nominal), profit tracking (Omset Kotor vs Omset Bersih),
and customer star ratings (1-5 stars) linked to cashier performance.
"""

import sqlite3
import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from contextlib import contextmanager


class DatabaseManager:
    """Manages SQLite database connections, migrations, and operations."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).resolve().parent.parent / "kubucashier.db")
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Yields a SQLite connection and guarantees closing it afterwards."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Creates necessary database tables if they do not exist and applies migrations."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Categories Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Products Table (Includes cost_price / HPP)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_id INTEGER,
                    price REAL NOT NULL DEFAULT 0.0,
                    cost_price REAL NOT NULL DEFAULT 0.0,
                    stock INTEGER NOT NULL DEFAULT 0,
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                );
            """)

            # 4. Transactions Table (Includes fee, cost, net profit, and rating)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no TEXT UNIQUE NOT NULL,
                    user_id INTEGER,
                    subtotal_amount REAL NOT NULL DEFAULT 0.0,
                    fee_type TEXT DEFAULT 'none',
                    fee_value REAL DEFAULT 0.0,
                    fee_amount REAL DEFAULT 0.0,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    total_cost REAL NOT NULL DEFAULT 0.0,
                    net_profit REAL NOT NULL DEFAULT 0.0,
                    paid_amount REAL NOT NULL DEFAULT 0.0,
                    change_amount REAL NOT NULL DEFAULT 0.0,
                    payment_method TEXT DEFAULT 'Cash',
                    rating INTEGER DEFAULT 0,
                    rating_comment TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );
            """)

            # 5. Transaction Items Table (Includes unit cost and total cost)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transaction_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    cost_price REAL NOT NULL DEFAULT 0.0,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    subtotal REAL NOT NULL,
                    total_cost REAL NOT NULL DEFAULT 0.0,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
                );
            """)

            # ---------------------------------------------------------
            # MIGRATION: Auto-add new columns if upgrading existing DB
            # ---------------------------------------------------------
            self._ensure_column(cursor, "products", "cost_price", "REAL NOT NULL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "subtotal_amount", "REAL NOT NULL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "fee_type", "TEXT DEFAULT 'none'")
            self._ensure_column(cursor, "transactions", "fee_value", "REAL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "fee_amount", "REAL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "total_cost", "REAL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "net_profit", "REAL DEFAULT 0.0")
            self._ensure_column(cursor, "transactions", "rating", "INTEGER DEFAULT 0")
            self._ensure_column(cursor, "transactions", "rating_comment", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "transaction_items", "cost_price", "REAL NOT NULL DEFAULT 0.0")
            self._ensure_column(cursor, "transaction_items", "total_cost", "REAL NOT NULL DEFAULT 0.0")

            conn.commit()

    def _ensure_column(self, cursor: sqlite3.Cursor, table: str, column: str, col_type: str):
        """Adds column to table if it doesn't already exist."""
        cursor.execute(f"PRAGMA table_info({table});")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if column not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
            except Exception:
                pass

    # -------------------------------------------------------------
    # USER OPERATIONS
    # -------------------------------------------------------------
    def add_user(self, name: str, username: str, password_hash: str, salt: str, role: str) -> int:
        """Inserts a new user into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, username, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?);
            """, (name.strip(), username.strip().lower(), password_hash, salt, role))
            conn.commit()
            return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Finds a user by username (case-insensitive)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, username, password_hash, salt, role, created_at
                FROM users
                WHERE lower(username) = lower(?);
            """, (username.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Finds a user by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, username, password_hash, salt, role, created_at
                FROM users
                WHERE id = ?;
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Returns list of all users."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, username, role, created_at
                FROM users
                ORDER BY id ASC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Updates a user's role."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE id = ?;", (new_role, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        """Updates a user's password hash and salt."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password_hash = ?, salt = ?
                WHERE id = ?;
            """, (password_hash, salt, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_details(self, user_id: int, name: str, role: str) -> bool:
        """Updates a user's name and role."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET name = ?, role = ?
                WHERE id = ?;
            """, (name.strip(), role, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_profile(
        self,
        user_id: int,
        name: str,
        role: str,
        password_hash: Optional[str] = None,
        salt: Optional[str] = None
    ) -> bool:
        """Updates user profile including optional password hash and salt."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if password_hash and salt:
                cursor.execute("""
                    UPDATE users
                    SET name = ?, role = ?, password_hash = ?, salt = ?
                    WHERE id = ?;
                """, (name.strip(), role, password_hash, salt, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET name = ?, role = ?
                    WHERE id = ?;
                """, (name.strip(), role, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def count_users(self) -> int:
        """Returns total user count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users;")
            row = cursor.fetchone()
            return row[0] if row else 0

    def delete_user(self, user_id: int) -> bool:
        """Deletes a user by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # CATEGORY OPERATIONS
    # -------------------------------------------------------------
    def add_category(self, name: str) -> int:
        """Adds a new category."""
        clean_name = name.strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name) VALUES (?);", (clean_name,))
            conn.commit()
            return cursor.lastrowid

    def update_category(self, category_id: int, name: str) -> bool:
        """Updates an existing category name."""
        clean_name = name.strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE categories SET name = ? WHERE id = ?;", (clean_name, category_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_category(self, category_id: int) -> bool:
        """Deletes a category and unlinks associated products."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id = ?;", (category_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Returns all categories along with their respective product counts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.created_at, COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id
                GROUP BY c.id
                ORDER BY c.name ASC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single category by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM categories WHERE id = ?;", (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # -------------------------------------------------------------
    # PRODUCT OPERATIONS (WITH HPP / COST PRICE)
    # -------------------------------------------------------------
    def add_product(
        self,
        name: str,
        category_id: Optional[int],
        price: float,
        cost_price: float = 0.0,
        stock: int = 0,
        image_path: Optional[str] = None
    ) -> int:
        """Inserts a new product into the database including HPP (cost_price)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, category_id, price, cost_price, stock, image_path)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (name.strip(), category_id, price, cost_price, stock, image_path))
            conn.commit()
            return cursor.lastrowid

    def update_product(
        self,
        product_id: int,
        name: str,
        category_id: Optional[int],
        price: float,
        cost_price: float = 0.0,
        stock: int = 0,
        image_path: Optional[str] = None
    ) -> bool:
        """Updates an existing product."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET name = ?, category_id = ?, price = ?, cost_price = ?, stock = ?, image_path = ?
                WHERE id = ?;
            """, (name.strip(), category_id, price, cost_price, stock, image_path, product_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_product(self, product_id: int) -> bool:
        """Deletes a product by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?;", (product_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_products(
        self,
        category_id: Optional[int] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns filtered or full list of products with HPP and category names."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT p.id, p.name, p.category_id, c.name as category_name,
                       p.price, COALESCE(p.cost_price, 0.0) as cost_price,
                       p.stock, p.image_path, p.created_at
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE 1=1
            """
            params: List[Any] = []

            if category_id is not None and category_id > 0:
                query += " AND p.category_id = ?"
                params.append(category_id)

            if search_query:
                query += " AND (lower(p.name) LIKE ? OR lower(coalesce(c.name, '')) LIKE ?)"
                like_term = f"%{search_query.strip().lower()}%"
                params.extend([like_term, like_term])

            query += " ORDER BY p.id DESC;"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single product by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.name, p.category_id, c.name as category_name,
                       p.price, COALESCE(p.cost_price, 0.0) as cost_price,
                       p.stock, p.image_path, p.created_at
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?;
            """, (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def count_products(self) -> int:
        """Returns total product count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products;")
            row = cursor.fetchone()
            return row[0] if row else 0

    # -------------------------------------------------------------
    # POS TRANSACTIONS, FEES & PROFIT OPERATIONS
    # -------------------------------------------------------------
    def create_transaction(
        self,
        user_id: Optional[int],
        items: List[Dict[str, Any]],
        total_amount: float,
        paid_amount: float,
        change_amount: float,
        payment_method: str = "Cash",
        subtotal_amount: Optional[float] = None,
        fee_type: str = "none",
        fee_value: float = 0.0,
        fee_amount: float = 0.0
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Records a completed transaction, decrements product inventory,
        and calculates total HPP and net profit.
        """
        if not items:
            return False, "Order cart is empty.", None

        import time
        invoice_no = f"INV-{int(time.time())}-{os.urandom(2).hex().upper()}"
        subtotal = subtotal_amount if subtotal_amount is not None else sum(it.get("price", 0) * it.get("quantity", 1) for it in items)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 1. Fetch current cost prices (HPP) for products in order
                total_tx_cost = 0.0
                processed_items = []

                for item in items:
                    prod_id = item.get("product_id") or item.get("id")
                    prod_name = item.get("name", "Item")
                    price = float(item.get("price", 0))
                    qty = int(item.get("quantity", 1))
                    item_subtotal = price * qty

                    cost_price = 0.0
                    if prod_id:
                        cursor.execute("SELECT cost_price FROM products WHERE id = ?;", (prod_id,))
                        c_row = cursor.fetchone()
                        if c_row and c_row[0] is not None:
                            cost_price = float(c_row[0])
                        elif "cost_price" in item:
                            cost_price = float(item["cost_price"])

                    item_total_cost = cost_price * qty
                    total_tx_cost += item_total_cost

                    processed_items.append({
                        "prod_id": prod_id,
                        "prod_name": prod_name,
                        "price": price,
                        "cost_price": cost_price,
                        "qty": qty,
                        "subtotal": item_subtotal,
                        "total_cost": item_total_cost
                    })

                # Net Profit = Total Revenue (including fee if considered revenue) - Total HPP
                net_profit = total_amount - total_tx_cost

                # 2. Insert Transaction Header
                cursor.execute("""
                    INSERT INTO transactions (
                        invoice_no, user_id, subtotal_amount, fee_type, fee_value, fee_amount,
                        total_amount, total_cost, net_profit, paid_amount, change_amount, payment_method
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    invoice_no, user_id, subtotal, fee_type, fee_value, fee_amount,
                    total_amount, total_tx_cost, net_profit, paid_amount, change_amount, payment_method
                ))
                transaction_id = cursor.lastrowid

                # 3. Insert Transaction Items and Decrement Stock
                for p_item in processed_items:
                    cursor.execute("""
                        INSERT INTO transaction_items (
                            transaction_id, product_id, product_name, price, cost_price, quantity, subtotal, total_cost
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        transaction_id, p_item["prod_id"], p_item["prod_name"],
                        p_item["price"], p_item["cost_price"], p_item["qty"],
                        p_item["subtotal"], p_item["total_cost"]
                    ))

                    if p_item["prod_id"]:
                        cursor.execute("""
                            UPDATE products
                            SET stock = max(0, stock - ?)
                            WHERE id = ?;
                        """, (p_item["qty"], p_item["prod_id"]))

                conn.commit()
                return True, invoice_no, transaction_id
            except Exception as e:
                conn.rollback()
                return False, str(e), None

    def record_transaction_rating(self, invoice_no: str, rating: int, comment: str = "") -> bool:
        """Records 1-5 star customer satisfaction rating for a transaction."""
        rating_clean = max(1, min(5, rating))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE transactions
                SET rating = ?, rating_comment = ?
                WHERE invoice_no = ?;
            """, (rating_clean, comment.strip(), invoice_no))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # SALES ANALYTICS, NET/GROSS PROFIT & CASHIER RATIOS
    # -------------------------------------------------------------
    def get_sales_kpis(self) -> Dict[str, Any]:
        """Calculates comprehensive sales summary KPIs (Gross Revenue, Total HPP, Net Profit, Ratings)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Today's stats
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0.0),
                       COALESCE(SUM(total_cost), 0.0),
                       COALESCE(SUM(net_profit), 0.0),
                       COUNT(*)
                FROM transactions
                WHERE date(created_at, 'localtime') = date('now', 'localtime');
            """)
            row_today = cursor.fetchone()
            today_gross = float(row_today[0]) if row_today else 0.0
            today_cost = float(row_today[1]) if row_today else 0.0
            today_net = float(row_today[2]) if row_today else 0.0
            today_orders = int(row_today[3]) if row_today else 0

            # 2. This month's stats
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0.0),
                       COALESCE(SUM(total_cost), 0.0),
                       COALESCE(SUM(net_profit), 0.0),
                       COUNT(*)
                FROM transactions
                WHERE strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime');
            """)
            row_month = cursor.fetchone()
            month_gross = float(row_month[0]) if row_month else 0.0
            month_cost = float(row_month[1]) if row_month else 0.0
            month_net = float(row_month[2]) if row_month else 0.0
            month_orders = int(row_month[3]) if row_month else 0

            # 3. All time totals
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0.0),
                       COALESCE(SUM(total_cost), 0.0),
                       COALESCE(SUM(net_profit), 0.0),
                       COUNT(*)
                FROM transactions;
            """)
            row_all = cursor.fetchone()
            total_gross = float(row_all[0]) if row_all else 0.0
            total_cost = float(row_all[1]) if row_all else 0.0
            total_net = float(row_all[2]) if row_all else 0.0
            total_orders = int(row_all[3]) if row_all else 0

            # 4. Overall Star Rating
            cursor.execute("""
                SELECT COALESCE(AVG(rating), 0.0), COUNT(*)
                FROM transactions
                WHERE rating > 0;
            """)
            row_rating = cursor.fetchone()
            avg_rating = float(row_rating[0]) if row_rating else 0.0
            total_reviews = int(row_rating[1]) if row_rating else 0

            avg_basket = (total_gross / total_orders) if total_orders > 0 else 0.0
            profit_margin = ((total_net / total_gross) * 100.0) if total_gross > 0 else 0.0

            return {
                "today_sales": today_gross,
                "today_cost": today_cost,
                "today_net": today_net,
                "today_orders": today_orders,
                "month_sales": month_gross,
                "month_cost": month_cost,
                "month_net": month_net,
                "month_orders": month_orders,
                "total_sales": total_gross,
                "total_cost": total_cost,
                "total_net": total_net,
                "total_orders": total_orders,
                "avg_basket": avg_basket,
                "profit_margin": profit_margin,
                "avg_rating": avg_rating,
                "total_reviews": total_reviews
            }

    def get_average_rating(self) -> Dict[str, Any]:
        """Returns overall store average rating and total review count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(AVG(rating), 0.0), COUNT(*)
                FROM transactions
                WHERE rating > 0;
            """)
            row = cursor.fetchone()
            return {
                "avg_rating": float(row[0]) if row else 0.0,
                "total_ratings": int(row[1]) if row else 0
            }

    def get_cashier_rating_stats(self) -> List[Dict[str, Any]]:
        """Returns cashier performance ratio and star rating distribution."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.name, u.username, u.role,
                       COUNT(t.id) as total_tx,
                       COALESCE(SUM(t.total_amount), 0.0) as total_sales,
                       COALESCE(SUM(t.net_profit), 0.0) as total_net,
                       COUNT(CASE WHEN t.rating > 0 THEN 1 END) as review_count,
                       COALESCE(AVG(CASE WHEN t.rating > 0 THEN t.rating END), 0.0) as avg_rating,
                       SUM(CASE WHEN t.rating = 5 THEN 1 ELSE 0 END) as star_5,
                       SUM(CASE WHEN t.rating = 4 THEN 1 ELSE 0 END) as star_4,
                       SUM(CASE WHEN t.rating = 3 THEN 1 ELSE 0 END) as star_3,
                       SUM(CASE WHEN t.rating = 2 THEN 1 ELSE 0 END) as star_2,
                       SUM(CASE WHEN t.rating = 1 THEN 1 ELSE 0 END) as star_1
                FROM users u
                LEFT JOIN transactions t ON t.user_id = u.id
                GROUP BY u.id
                ORDER BY total_sales DESC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    # Alias for cashier performance and ratings
    get_cashier_performance = get_cashier_rating_stats

    def get_daily_sales_chart_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Returns daily gross sales, net profit, and order count for the last N days."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                WITH RECURSIVE dates(d) AS (
                    SELECT date('now', 'localtime', '-' || (? - 1) || ' days')
                    UNION ALL
                    SELECT date(d, '+1 day')
                    FROM dates
                    WHERE d < date('now', 'localtime')
                )
                SELECT dates.d as date_str,
                       COALESCE(SUM(t.total_amount), 0.0) as total_sales,
                       COALESCE(SUM(t.net_profit), 0.0) as net_profit,
                       COUNT(t.id) as order_count
                FROM dates
                LEFT JOIN transactions t ON date(t.created_at, 'localtime') = dates.d
                GROUP BY dates.d
                ORDER BY dates.d ASC;
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def get_top_selling_products(self, limit: int = 8) -> List[Dict[str, Any]]:
        """Returns best-selling products ranked by quantity sold, revenue, and gross profit."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ti.product_name,
                       SUM(ti.quantity) as total_qty,
                       SUM(ti.subtotal) as total_revenue,
                       SUM(ti.subtotal - COALESCE(ti.total_cost, 0.0)) as total_profit
                FROM transaction_items ti
                GROUP BY ti.product_name
                ORDER BY total_qty DESC
                LIMIT ?;
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_filtered_transactions(
        self,
        period: str = "all",
        search: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Returns filtered transaction records with net profit and ratings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = []
            params: List[Any] = []

            if period == "today":
                where_clauses.append("date(t.created_at, 'localtime') = date('now', 'localtime')")
            elif period == "week":
                where_clauses.append("date(t.created_at, 'localtime') >= date('now', 'localtime', '-7 days')")
            elif period == "month":
                where_clauses.append("strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')")

            if search.strip():
                where_clauses.append("(t.invoice_no LIKE ? OR u.name LIKE ?)")
                q = f"%{search.strip()}%"
                params.extend([q, q])

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"""
                SELECT t.id, t.invoice_no, t.user_id, u.name as cashier_name,
                       t.subtotal_amount, t.fee_type, t.fee_value, t.fee_amount,
                       t.total_amount, t.total_cost, t.net_profit, t.paid_amount,
                       t.change_amount, t.payment_method, t.rating, t.rating_comment, t.created_at
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                {where_sql}
                ORDER BY t.id DESC LIMIT ?;
            """
            params.append(limit)
            cursor.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns recent transactions."""
        return self.get_filtered_transactions(period="all", limit=limit)

    def wipe_transactions(self) -> bool:
        """Purges all transaction items and transaction records from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transaction_items;")
            cursor.execute("DELETE FROM transactions;")
            conn.commit()
            return True


# Default singleton instance
db = DatabaseManager()
db_manager = db
