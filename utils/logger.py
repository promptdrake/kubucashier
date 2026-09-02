"""
Unified Console Logging Utility for KubuCashier.
Logs all cashier POS actions, dual-screen customer display sync events,
checkout flows, and configuration updates to the terminal in real-time.
"""

import sys
from datetime import datetime


def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log_info(tag: str, message: str):
    """Prints formatted info log message with timestamp."""
    print(f"[{get_timestamp()}] [{tag.upper()}] {message}", flush=True)


def log_pos(action: str, details: str):
    """Prints POS register cashier action log."""
    print(f"[{get_timestamp()}] [POS:{action.upper()}] {details}", flush=True)


def log_cfd(state: str, details: str):
    """Prints Customer Facing Display state change log."""
    print(f"[{get_timestamp()}] [CFD:{state.upper()}] {details}", flush=True)


def log_checkout(action: str, details: str):
    """Prints Checkout and Payment process log."""
    print(f"[{get_timestamp()}] [CHECKOUT:{action.upper()}] {details}", flush=True)


def log_auth(action: str, details: str):
    """Prints Authentication action log."""
    print(f"[{get_timestamp()}] [AUTH:{action.upper()}] {details}", flush=True)


def log_settings(action: str, details: str):
    """Prints Settings update action log."""
    print(f"[{get_timestamp()}] [SETTINGS:{action.upper()}] {details}", flush=True)
