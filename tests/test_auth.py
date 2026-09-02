"""Unit tests for authentication service and credential tokens."""
import os
import unittest
import tempfile

from config import config
from database.db_manager import DatabaseManager
from auth.auth_service import AuthService


class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = DatabaseManager(self.temp_db_path)
        self.auth = AuthService(self.db)
        config.credential_token = "secret123"

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_password_hashing_and_verification(self):
        pwd = "mypassword!99"
        pwd_hash, salt = AuthService.hash_password(pwd)
        self.assertTrue(AuthService.verify_password(pwd, pwd_hash, salt))
        self.assertFalse(AuthService.verify_password("wrongpassword", pwd_hash, salt))

    def test_registration_with_valid_token(self):
        success, msg, user = self.auth.register(
            name="Bob Builder",
            username="bob",
            password="securepassword",
            role="Owner",
            credential_token="secret123"
        )
        self.assertTrue(success, msg)
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Bob Builder")
        self.assertEqual(user["username"], "bob")
        self.assertEqual(user["role"], "Owner")

    def test_registration_with_invalid_token(self):
        success, msg, user = self.auth.register(
            name="Eve Hacker",
            username="evehacker",
            password="password",
            role="Cashier",
            credential_token="wrong_token"
        )
        self.assertFalse(success)
        self.assertIn("Invalid Credential Token", msg)
        self.assertIsNone(user)

    def test_registration_validation(self):
        # Empty name
        success, msg, _ = self.auth.register("", "user1", "pass", "Cashier", "secret123")
        self.assertFalse(success)

        # Short username
        success, msg, _ = self.auth.register("User", "ab", "pass", "Cashier", "secret123")
        self.assertFalse(success)

        # Invalid role
        success, msg, _ = self.auth.register("User", "userlong", "pass", "SuperAdmin", "secret123")
        self.assertFalse(success)

    def test_duplicate_registration(self):
        self.auth.register("User One", "testuser", "pass123", "Cashier", "secret123")
        success, msg, _ = self.auth.register("User Two", "testuser", "pass456", "Sales", "secret123")
        self.assertFalse(success)
        self.assertIn("already taken", msg)

    def test_login_flow(self):
        self.auth.register("Charlie Day", "charlie", "greenman123", "Sales", "secret123")

        # Wrong password
        success, msg, user = self.auth.login("charlie", "wrong")
        self.assertFalse(success)
        self.assertIsNone(user)

        # Correct password
        success, msg, user = self.auth.login("charlie", "greenman123")
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertTrue(self.auth.is_logged_in())
        self.assertEqual(self.auth.current_user["username"], "charlie")

        # Logout
        self.auth.logout()
        self.assertFalse(self.auth.is_logged_in())

    def test_admin_user_management(self):
        # 1. Admin creates user
        success, msg, user = self.auth.admin_create_user(
            name="Staff Member",
            username="staff1",
            password="oldpassword123",
            role="Cashier"
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        user_id = user["id"]

        # 2. Update role and reset password
        success, msg = self.auth.update_user_account(
            user_id=user_id,
            name="Staff Member Updated",
            role="Sales",
            new_password="newsecretpassword"
        )
        self.assertTrue(success)

        # 3. Verify login works with new password
        success, msg, logged_user = self.auth.login("staff1", "newsecretpassword")
        self.assertTrue(success)
        self.assertEqual(logged_user["role"], "Sales")
        self.assertEqual(logged_user["name"], "Staff Member Updated")

        # 4. Old password fails
        self.auth.logout()
        success, _, _ = self.auth.login("staff1", "oldpassword123")
        self.assertFalse(success)

        # 5. Delete user
        success, msg = self.auth.delete_user_account(user_id=user_id, current_user_id=999)
        self.assertTrue(success)
        self.assertIsNone(self.db.get_user_by_id(user_id))

        # 6. Cannot delete self
        self.assertFalse(self.auth.delete_user_account(user_id=1, current_user_id=1)[0])


if __name__ == "__main__":
    unittest.main()
