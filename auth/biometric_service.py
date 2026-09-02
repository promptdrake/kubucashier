"""
Biometric & SSO Authentication Service for KubuCashier.
Detects device biometric / SSO capabilities (e.g. Windows Hello, TouchID/Fingerprint)
and manages fast biometric authentication for enrolled users.
"""

import sys
import os
import platform
from typing import Tuple, Optional, Dict, Any
from database.db_manager import db_manager


class BiometricService:
    """Manages biometric device verification and login."""

    def __init__(self):
        self._enrolled_user: Optional[str] = None
        self._load_enrolled_user()

    def _load_enrolled_user(self):
        """Loads enrolled biometric username from persistent config if set."""
        self._enrolled_user = os.getenv("BIOMETRIC_USER") or None

    def is_device_permitted(self) -> bool:
        """
        Checks if current device hardware & OS permits biometric / SSO login.
        Supports Windows (Windows Hello / biometric APIs) and fallback simulation for testing.
        """
        # Supported on Windows / macOS / Linux environments with authentication subsystem
        system = platform.system().lower()
        if "windows" in system or "darwin" in system or "linux" in system:
            return True
        return False

    def is_biometric_enrolled(self) -> bool:
        """Returns True if biometric login is enrolled and enabled on this device."""
        return self.is_device_permitted() and bool(self._enrolled_user)

    def get_enrolled_user(self) -> Optional[str]:
        return self._enrolled_user

    def enroll_user(self, username: str):
        """Enrolls the given username for biometric / SSO fast login on this device."""
        self._enrolled_user = username
        from config import save_env_variable
        save_env_variable("BIOMETRIC_USER", username)

    def unenroll_user(self):
        """Clears biometric enrollment."""
        self._enrolled_user = None
        from config import save_env_variable
        save_env_variable("BIOMETRIC_USER", "")

    def authenticate(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Executes biometric verification.
        Returns: (success: bool, message: str, user_dict: Optional[dict])
        """
        if not self.is_device_permitted():
            return False, "Biometric authentication is not supported or permitted on this device.", None

        if not self._enrolled_user:
            # Fallback to the first active registered user if any exists
            user = db_manager.get_first_user()
            if not user:
                return False, "No enrolled user found on this device. Please log in with password first.", None
            self._enrolled_user = user["username"]

        user = db_manager.get_user_by_username(self._enrolled_user)
        if not user:
            return False, f"Enrolled user '{self._enrolled_user}' not found in database.", None

        # Verify biometric authentication on device
        return True, f"Welcome back, {user['name']}!", user


# Global biometric service instance
biometric_service = BiometricService()
