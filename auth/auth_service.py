"""
Authentication Service for KubuCashier.
Handles credential verification, secure password hashing, registration, and session state.
"""

import os
import hashlib
import binascii
import sqlite3
from typing import Optional, Tuple, Dict, Any

from config import config
from database.db_manager import DatabaseManager, db


class AuthService:
    """Manages user authentication and registration."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or db
        self.current_user: Optional[Dict[str, Any]] = None

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hashes a password using PBKDF2-HMAC-SHA256.
        Returns (password_hash_hex, salt_hex).
        """
        if salt is None:
            salt_bytes = os.urandom(16)
            salt = binascii.hexlify(salt_bytes).decode('utf-8')
        else:
            salt_bytes = binascii.unhexlify(salt.encode('utf-8'))

        pwd_bytes = password.encode('utf-8')
        dk = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100_000)
        hash_hex = binascii.hexlify(dk).decode('utf-8')
        return hash_hex, salt

    @staticmethod
    def verify_password(password: str, stored_hash: str, salt: str) -> bool:
        """Verifies a password against the stored hash and salt."""
        computed_hash, _ = AuthService.hash_password(password, salt)
        return computed_hash == stored_hash

    def register(
        self,
        name: str,
        username: str,
        password: str,
        role: str,
        credential_token: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Registers a new user with role and credential token validation.
        """
        # Validate inputs
        name = name.strip()
        username = username.strip()
        password = password.strip()
        role = role.strip()
        credential_token = credential_token.strip()

        if not name:
            return False, "Please enter your name.", None

        if not username:
            return False, "Please enter your username.", None

        if len(username) < 3:
            return False, "Username must be at least 3 characters.", None

        if not password:
            return False, "Please enter a password.", None

        if len(password) < 4:
            return False, "Password must be at least 4 characters.", None

        if role not in config.roles:
            return False, f"Invalid role. Must be one of: {', '.join(config.roles)}", None

        # Validate Credential Token
        required_token = config.credential_token.strip()
        if credential_token != required_token:
            return False, "Invalid Credential Token! Check your security parameter/env.", None

        # Check if username exists
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            return False, "Username is already taken. Please choose another.", None

        # Hash password and store
        pwd_hash, salt = self.hash_password(password)
        try:
            user_id = self.db.add_user(name, username, pwd_hash, salt, role)
            user_data = self.db.get_user_by_id(user_id)
            return True, "Registration successful! You can now log in.", user_data
        except sqlite3.IntegrityError:
            return False, "Username is already taken.", None
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticates a user with username and password.
        """
        username = username.strip()
        password = password.strip()

        if not username:
            return False, "Please enter your username.", None

        if not password:
            return False, "Please enter your password.", None

        user = self.db.get_user_by_username(username)
        if not user:
            return False, "Invalid username or password.", None

        if not self.verify_password(password, user["password_hash"], user["salt"]):
            return False, "Invalid username or password.", None

        # Set active session
        self.current_user = user
        return True, f"Welcome back, {user['name']}!", user

    def logout(self):
        """Clears current active user session."""
        self.current_user = None

    def is_logged_in(self) -> bool:
        """Returns True if a user is currently logged in."""
        return self.current_user is not None

    def admin_create_user(
        self,
        name: str,
        username: str,
        password: str,
        role: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Creates a new user directly from Admin / Owner user management."""
        name = name.strip()
        username = username.strip()
        password = password.strip()
        role = role.strip()

        if not name:
            return False, "Please enter full name.", None
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters.", None
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters.", None
        if role not in config.roles:
            return False, f"Invalid role. Must be one of: {', '.join(config.roles)}", None

        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            return False, "Username is already taken.", None

        pwd_hash, salt = self.hash_password(password)
        try:
            user_id = self.db.add_user(name, username, pwd_hash, salt, role)
            user_data = self.db.get_user_by_id(user_id)
            return True, "User created successfully.", user_data
        except sqlite3.IntegrityError:
            return False, "Username is already taken.", None
        except Exception as e:
            return False, f"Failed to create user: {str(e)}", None

    def update_user_account(
        self,
        user_id: int,
        name: str,
        role: str,
        new_password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Updates user account details (name, role, and optional password)."""
        name = name.strip()
        role = role.strip()

        if not name:
            return False, "Please enter full name."
        if role not in config.roles:
            return False, f"Invalid role. Must be one of: {', '.join(config.roles)}"

        if new_password and len(new_password.strip()) > 0:
            clean_pwd = new_password.strip()
            if len(clean_pwd) < 4:
                return False, "New password must be at least 4 characters."
            pwd_hash, salt = self.hash_password(clean_pwd)
            success = self.db.update_user_profile(user_id, name, role, pwd_hash, salt)
        else:
            success = self.db.update_user_profile(user_id, name, role)

        if success:
            return True, "User account updated successfully."
        return False, "Failed to update user account."

    def delete_user_account(self, user_id: int, current_user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Deletes a user account with safety check against deleting own active account."""
        if current_user_id is not None and user_id == current_user_id:
            return False, "You cannot delete your own logged-in account."

        user = self.db.get_user_by_id(user_id)
        if not user:
            return False, "User not found."

        success = self.db.delete_user(user_id)
        if success:
            return True, "User account deleted successfully."
        return False, "Failed to delete user account."


# Global singleton instance
auth_service = AuthService()
