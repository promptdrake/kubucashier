"""
Configuration module for KubuCashier.
Handles command-line arguments, environment variables, .env files, and application constants.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Paths
if getattr(sys, "frozen", False):
    # Running as compiled PyInstaller executable
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    # Running from source
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

BASE_DIR = APP_DIR
ASSETS_DIR = BUNDLE_DIR / "assets"
DATABASE_DIR = APP_DIR / "database"
DEFAULT_DB_PATH = APP_DIR / "kubucashier.db"
ENV_FILE_PATH = APP_DIR / ".env"

# Available Roles
ROLES = ["Cashier", "Owner", "Admin", "Sales"]

# Default Credential Token fallback
DEFAULT_CREDENTIAL_TOKEN = "admin"

DEFAULT_ENV_TEMPLATE = """# KubuCashier Application Settings
PASSWORD=admin
FULLSCREEN=false
OPEN_IN_MONITOR=1
BLACK_OTHER_MONITORS=false
CUSTOMER_DISPLAY_ENABLED=true
CUSTOMER_DISPLAY_MONITOR=2
LANGUAGE=id
PAYMENT_CASH=true
PAYMENT_QRIS=true
"""


def is_admin_or_owner(role: str) -> bool:
    """Check if the given role has administrator privileges."""
    if not role:
        return False
    return role.strip().lower() in ("admin", "owner", "administrator")


def get_env_case_insensitive(var_name: str) -> Optional[str]:
    """Retrieve environment variable case-insensitively."""
    target = var_name.upper()
    for k, v in os.environ.items():
        if k.upper() == target:
            return v
    return None


def load_dotenv(path: Path = ENV_FILE_PATH):
    """Simple parser for .env file if present. Automatically creates default .env if missing."""
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_ENV_TEMPLATE.strip() + "\n")
        except Exception:
            pass

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and get_env_case_insensitive(key) is None:
                    os.environ[key] = val
    except Exception:
        pass


def save_env_variable(key: str, value: str, path: Path = ENV_FILE_PATH):
    """Persist or update an environment variable in the .env file."""
    lines = []
    key_found = False
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            if k.strip().upper() == key.upper():
                new_lines.append(f"{key}={value}\n")
                key_found = True
                continue
        new_lines.append(line)

    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass


# Preload .env on import
load_dotenv()


class Config:
    """Application configuration container."""

    def __init__(self):
        self.app_name = "KubuCashier"
        self.version = "1.0.0"
        self.db_path = str(DEFAULT_DB_PATH)
        self.credential_token = self._resolve_credential_token()
        self.fullscreen = self._resolve_fullscreen()
        self.monitor: Optional[int] = self._resolve_monitor()
        self.black_other_monitors = self._resolve_black_other_monitors()
        self.cloud_sync = self._resolve_cloud_sync()
        self.language = self._resolve_language()
        self.roles = ROLES

        # Payment Methods Configuration
        self.payment_cash_enabled = self._resolve_bool("PAYMENT_CASH", default=True)
        self.payment_qris_enabled = self._resolve_bool("PAYMENT_QRIS", default=True)
        self.payment_debit_enabled = self._resolve_bool("PAYMENT_DEBIT", default=True)
        self.payment_debt_enabled = self._resolve_bool("PAYMENT_DEBT", default=True)
        self.qris_static_payload = get_env_case_insensitive("QRIS_STATIC_PAYLOAD") or ""
        self.qris_image_path = get_env_case_insensitive("QRIS_IMAGE_PATH") or ""

        # Customer Second Display Monitor Configuration
        self.customer_display_enabled = self._resolve_bool("CUSTOMER_DISPLAY_ENABLED", default=False)
        self.customer_display_monitor = self._resolve_customer_display_monitor()

        # Default Persistent Fee Configuration
        self.default_fee_enabled = self._resolve_bool("DEFAULT_FEE_ENABLED", default=False)
        self.default_fee_type = (get_env_case_insensitive("DEFAULT_FEE_TYPE") or "percent").strip().lower()
        self.default_fee_value = float(get_env_case_insensitive("DEFAULT_FEE_VALUE") or 0.0)

    def _resolve_customer_display_monitor(self) -> int:
        val = get_env_case_insensitive("CUSTOMER_DISPLAY_MONITOR")
        if val is not None:
            try:
                num = int(val.strip())
                if num >= 1:
                    return num
            except ValueError:
                pass
        return 2

    def _resolve_bool(self, key: str, default: bool = True) -> bool:
        val = get_env_case_insensitive(key)
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on")
        return default

    def _resolve_credential_token(self) -> str:
        """
        Resolves credential token from:
        1. Environment variables / .env: 'password', 'credential_token'
        2. Fallback default: 'testing'
        """
        env_token = (
            get_env_case_insensitive("password")
            or get_env_case_insensitive("credential_token")
        )
        if env_token:
            return env_token

        return DEFAULT_CREDENTIAL_TOKEN

    def _resolve_fullscreen(self) -> bool:
        """Resolves fullscreen setting from environment variables / .env."""
        val = get_env_case_insensitive("FULLSCREEN") or get_env_case_insensitive("FULL_SCREEN")
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on")
        return False

    def _resolve_monitor(self) -> Optional[int]:
        """Resolves target monitor (1, 2, 3...) from environment variables / .env."""
        val = (
            get_env_case_insensitive("OPEN_IN_MONITOR")
            or get_env_case_insensitive("MONITOR")
            or get_env_case_insensitive("TARGET_MONITOR")
        )
        if val is not None:
            try:
                num = int(val.strip())
                if num >= 1:
                    return num
            except ValueError:
                pass
        return 1

    def _resolve_black_other_monitors(self) -> bool:
        """Resolves black other monitors setting from environment variables / .env."""
        val = (
            get_env_case_insensitive("BLACK_OTHER_MONITORS")
            or get_env_case_insensitive("black_other_monitors")
            or get_env_case_insensitive("BLACKOUT_OTHER_MONITORS")
        )
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on")
        return False

    def _resolve_cloud_sync(self) -> bool:
        """Resolves cloud sync setting from environment variables / .env."""
        val = get_env_case_insensitive("CLOUD_SYNC")
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on")
        return False

    def _resolve_language(self) -> str:
        """Resolves language setting ('en' or 'id') from environment variables / .env."""
        val = get_env_case_insensitive("LANGUAGE") or get_env_case_insensitive("LANG")
        if val is not None:
            val_clean = val.strip().lower()
            if val_clean in ("id", "indonesia", "indonesian"):
                return "id"
        return "en"

    def set_fullscreen(self, enabled: bool, persist: bool = True):
        self.fullscreen = enabled
        if persist:
            save_env_variable("FULLSCREEN", "true" if enabled else "false")

    def set_monitor(self, monitor_num: int, persist: bool = True):
        self.monitor = monitor_num
        if persist:
            save_env_variable("OPEN_IN_MONITOR", str(monitor_num))

    def set_black_other_monitors(self, enabled: bool, persist: bool = True):
        self.black_other_monitors = enabled
        if persist:
            save_env_variable("BLACK_OTHER_MONITORS", "true" if enabled else "false")

    def set_credential_token(self, token: str, persist: bool = True):
        self.credential_token = token
        if persist:
            save_env_variable("password", token)

    def set_cloud_sync(self, enabled: bool, persist: bool = True):
        self.cloud_sync = enabled
        if persist:
            save_env_variable("CLOUD_SYNC", "true" if enabled else "false")

    def set_language(self, lang_code: str, persist: bool = True):
        self.language = lang_code
        try:
            from ui.i18n import set_language as i18n_set_language
            i18n_set_language(lang_code)
        except Exception:
            pass
        if persist:
            save_env_variable("LANGUAGE", lang_code)

    def set_payment_option(self, option: str, enabled: bool, persist: bool = True):
        env_map = {
            "cash": ("payment_cash_enabled", "PAYMENT_CASH"),
            "qris": ("payment_qris_enabled", "PAYMENT_QRIS"),
            "debit": ("payment_debit_enabled", "PAYMENT_DEBIT"),
            "debt": ("payment_debt_enabled", "PAYMENT_DEBT"),
        }
        if option.lower() in env_map:
            attr_name, env_key = env_map[option.lower()]
            setattr(self, attr_name, enabled)
            if persist:
                save_env_variable(env_key, "true" if enabled else "false")

    def set_qris_config(self, static_payload: str, image_path: Optional[str] = None, persist: bool = True):
        self.qris_static_payload = static_payload.strip()
        if image_path is not None:
            self.qris_image_path = image_path
        if persist:
            save_env_variable("QRIS_STATIC_PAYLOAD", self.qris_static_payload)
            if image_path is not None:
                save_env_variable("QRIS_IMAGE_PATH", self.qris_image_path)

    def set_customer_display(self, enabled: bool, monitor: Optional[int] = None, persist: bool = True):
        self.customer_display_enabled = enabled
        if monitor is not None:
            self.customer_display_monitor = monitor
        if persist:
            save_env_variable("CUSTOMER_DISPLAY_ENABLED", "true" if enabled else "false")
            if monitor is not None:
                save_env_variable("CUSTOMER_DISPLAY_MONITOR", str(monitor))

    def set_default_fee(self, enabled: bool, fee_type: str = "percent", fee_value: float = 0.0, persist: bool = True):
        self.default_fee_enabled = enabled
        self.default_fee_type = fee_type
        self.default_fee_value = fee_value
        if persist:
            save_env_variable("DEFAULT_FEE_ENABLED", "true" if enabled else "false")
            save_env_variable("DEFAULT_FEE_TYPE", fee_type)
            save_env_variable("DEFAULT_FEE_VALUE", str(fee_value))

    def parse_cli_args(self, args=None):
        """Parse CLI arguments and override config values."""
        parser = argparse.ArgumentParser(
            description="KubuCashier POS & Management Software",
            add_help=False
        )
        parser.add_argument(
            "--password",
            "--credential-token",
            "-p",
            dest="credential_token",
            type=str,
            default=None,
            help="Set the required registration credential token."
        )
        parser.add_argument(
            "--fullscreen",
            "-f",
            dest="fullscreen",
            nargs="?",
            const="true",
            type=str,
            default=None,
            help="Run in locked fullscreen kiosk mode (true/false)."
        )
        parser.add_argument(
            "--open-in-monitor",
            "--monitor",
            "-m",
            dest="monitor",
            type=int,
            default=None,
            help="Target monitor to open window on (1, 2, 3...)."
        )
        parser.add_argument(
            "--black-other-monitors",
            "-b",
            dest="black_other_monitors",
            nargs="?",
            const="true",
            type=str,
            default=None,
            help="Black out all secondary/other monitors in Fullscreen mode (true/false)."
        )
        parser.add_argument(
            "--language",
            "--lang",
            "-l",
            dest="language",
            type=str,
            default=None,
            help="Application interface language ('en' or 'id')."
        )
        parser.add_argument(
            "--cloud-sync",
            dest="cloud_sync",
            nargs="?",
            const="true",
            type=str,
            default=None,
            help="Enable cloud synchronization (true/false)."
        )
        parser.add_argument(
            "--db",
            dest="db_path",
            type=str,
            default=None,
            help="Custom SQLite database file path."
        )

        parsed, _ = parser.parse_known_args(args if args is not None else sys.argv[1:])

        if parsed.credential_token is not None:
            self.credential_token = parsed.credential_token
        if parsed.fullscreen is not None:
            self.fullscreen = parsed.fullscreen.strip().lower() in ("true", "1", "yes", "on")
        if parsed.monitor is not None:
            self.monitor = parsed.monitor
        if parsed.black_other_monitors is not None:
            self.black_other_monitors = parsed.black_other_monitors.strip().lower() in ("true", "1", "yes", "on")
        if parsed.language is not None:
            self.set_language(parsed.language, persist=False)
        if parsed.cloud_sync is not None:
            self.cloud_sync = parsed.cloud_sync.strip().lower() in ("true", "1", "yes", "on")
        if parsed.db_path is not None:
            self.db_path = parsed.db_path


# Global config instance
config = Config()
