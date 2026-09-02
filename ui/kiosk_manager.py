"""
Kiosk Security and Multi-Monitor Manager for KubuCashier.
Provides:
1. Low-level Windows Keyboard Hook to block Alt+Tab, Windows Keys, Alt+Esc, Alt+F4, Ctrl+Esc in Fullscreen Kiosk Mode.
2. Blackout Screen Windows to blank out secondary/other monitors when Fullscreen Kiosk Mode is active.
"""

import sys
import platform
from typing import List, Optional
import ctypes
from ctypes import wintypes

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

# Windows Hook Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F4 = 0x73
VK_CONTROL = 0x11
VK_SHIFT = 0x10

LLKHF_ALTDOWN = 0x20

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p)
    ]


class KioskKeyboardBlocker:
    """Low-level Windows keyboard hook that blocks task switching shortcuts in Fullscreen Kiosk Mode."""

    def __init__(self):
        self._hook = None
        self._hook_proc = None
        self._is_windows = platform.system().lower().startswith("win")
        self._ctrl_pressed = False

    def enable(self):
        """Installs the low-level keyboard hook."""
        if not self._is_windows or self._hook:
            return

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            def _low_level_keyboard_proc(nCode, wParam, lParam):
                if nCode >= 0:
                    kb = KBDLLHOOKSTRUCT.from_address(lParam)
                    vk = kb.vkCode
                    is_alt = bool(kb.flags & LLKHF_ALTDOWN)

                    # Track Ctrl state
                    if vk in (0x11, 0xA2, 0xA3):  # VK_CONTROL, VK_LCONTROL, VK_RCONTROL
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._ctrl_pressed = True
                        elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                            self._ctrl_pressed = False

                    # 1. Block Windows Keys (Start Menu / Win+Tab / Win+D / Win+R)
                    if vk in (VK_LWIN, VK_RWIN):
                        return 1

                    # 2. Block Alt + Tab
                    if is_alt and vk == VK_TAB:
                        return 1

                    # 3. Block Alt + Esc
                    if is_alt and vk == VK_ESCAPE:
                        return 1

                    # 4. Block Alt + Space (Window System Menu)
                    if is_alt and vk == VK_SPACE:
                        return 1

                    # 5. Block Alt + F4
                    if is_alt and vk == VK_F4:
                        return 1

                    # 6. Block Ctrl + Esc (Start Menu)
                    if self._ctrl_pressed and vk == VK_ESCAPE:
                        return 1

                    # 7. Block standalone Escape or F11 in kiosk mode
                    if vk in (VK_ESCAPE, 0x7A):  # VK_ESCAPE, VK_F11
                        return 1

                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            self._hook_proc = HOOKPROC(_low_level_keyboard_proc)
            h_mod = kernel32.GetModuleHandleW(None)
            self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, h_mod, 0)
        except Exception:
            self._hook = None

    def disable(self):
        """Removes the keyboard hook."""
        if not self._is_windows or not self._hook:
            return
        try:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
        except Exception:
            pass
        self._hook = None
        self._hook_proc = None


class BlackoutWindow(QWidget):
    """Frameless, solid black window used to black out other monitors in Kiosk mode."""

    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background-color: #000000;")
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setGeometry(screen.geometry())

    def keyPressEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        event.ignore()


class BlackoutScreensManager:
    """Manages blackout windows across secondary/other monitors."""

    def __init__(self):
        self._windows: List[BlackoutWindow] = []

    def show_blackouts(self, active_screen):
        """Creates blackout windows for all screens except the active_screen."""
        self.hide_blackouts()
        screens = QApplication.screens()
        for screen in screens:
            if screen != active_screen:
                win = BlackoutWindow(screen)
                win.show()
                self._windows.append(win)

    def hide_blackouts(self):
        """Closes all blackout windows."""
        for win in self._windows:
            try:
                win.close()
                win.deleteLater()
            except Exception:
                pass
        self._windows.clear()


# Global singletons
kiosk_keyboard_blocker = KioskKeyboardBlocker()
blackout_manager = BlackoutScreensManager()
