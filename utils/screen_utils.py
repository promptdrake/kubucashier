"""
Screen and Monitor Utility for detecting friendly monitor names,
EDID models, resolutions, and primary screen status.
"""

import sys
import platform
from typing import List, Dict, Any, Optional

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QScreen, QGuiApplication
except ImportError:
    pass


def _get_windows_edid_monitor_names() -> Dict[str, str]:
    """
    On Windows, extracts monitor models/names directly from EDID registry data
    and maps them to Windows display adapter names (e.g. '\\\\.\\DISPLAY1').
    """
    if platform.system() != "Windows":
        return {}

    edid_names: Dict[str, str] = {}
    try:
        import winreg

        base_path = r"SYSTEM\CurrentControlSet\Enum\DISPLAY"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as disp_key:
            num_devs = winreg.QueryInfoKey(disp_key)[0]
            for i in range(num_devs):
                dev_name = winreg.EnumKey(disp_key, i)
                dev_path = f"{base_path}\\{dev_name}"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, dev_path) as inst_key:
                        num_insts = winreg.QueryInfoKey(inst_key)[0]
                        for j in range(num_insts):
                            inst_name = winreg.EnumKey(inst_key, j)
                            param_path = f"{dev_path}\\{inst_name}\\Device Parameters"
                            try:
                                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, param_path) as param_key:
                                    try:
                                        edid, _ = winreg.QueryValueEx(param_key, "EDID")
                                        parsed_name = None
                                        # Parse 18-byte descriptor blocks at offsets 54, 72, 90, 108
                                        for offset in (54, 72, 90, 108):
                                            tag = edid[offset : offset + 4]
                                            if tag == b"\x00\x00\x00\xfc":  # Monitor Name descriptor
                                                parsed_name = edid[offset + 5 : offset + 18].decode("ascii", errors="ignore").strip("\x0a\x00 ")
                                                break
                                            elif tag == b"\x00\x00\x00\xfe" and not parsed_name:  # ASCII text / model
                                                parsed_name = edid[offset + 5 : offset + 18].decode("ascii", errors="ignore").strip("\x0a\x00 ")
                                        if parsed_name:
                                            edid_names[dev_name] = parsed_name
                                    except FileNotFoundError:
                                        pass
                            except FileNotFoundError:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # Map Windows DeviceName (e.g. \\.\DISPLAY1) to EDID DeviceID via EnumDisplayDevicesW
    adapter_to_name: Dict[str, str] = {}
    try:
        import ctypes
        from ctypes import wintypes

        class DISPLAY_DEVICE(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("DeviceName", wintypes.WCHAR * 32),
                ("DeviceString", wintypes.WCHAR * 128),
                ("StateFlags", wintypes.DWORD),
                ("DeviceID", wintypes.WCHAR * 128),
                ("DeviceKey", wintypes.WCHAR * 128),
            ]

        user32 = ctypes.windll.user32
        dev = DISPLAY_DEVICE()
        dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
        adapter_idx = 0
        while user32.EnumDisplayDevicesW(None, adapter_idx, ctypes.byref(dev), 0):
            mon_dev = DISPLAY_DEVICE()
            mon_dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
            mon_idx = 0
            while user32.EnumDisplayDevicesW(dev.DeviceName, mon_idx, ctypes.byref(mon_dev), 0):
                dev_id = mon_dev.DeviceID
                if dev_id.startswith("MONITOR\\"):
                    parts = dev_id.split("\\")
                    if len(parts) >= 2 and parts[1] in edid_names:
                        adapter_to_name[dev.DeviceName] = edid_names[parts[1]]
                mon_idx += 1
            adapter_idx += 1
    except Exception:
        pass

    return adapter_to_name


def get_detected_screens_info() -> List[Dict[str, Any]]:
    """
    Returns a list of structured monitor dictionaries with friendly names,
    resolution, primary status, and formatted dropdown display strings.
    """
    app = QApplication.instance() or QGuiApplication.instance()
    if not app:
        return [
            {
                "index": 1,
                "name": "Monitor 1",
                "resolution": "1920x1080",
                "is_primary": True,
                "display_label": "Monitor 1 (1920x1080)",
            }
        ]

    screens = app.screens()
    if not screens:
        return [
            {
                "index": 1,
                "name": "Monitor 1",
                "resolution": "1920x1080",
                "is_primary": True,
                "display_label": "Monitor 1 (1920x1080)",
            }
        ]

    edid_map = _get_windows_edid_monitor_names()
    primary_screen = app.primaryScreen()

    results: List[Dict[str, Any]] = []
    for idx, screen in enumerate(screens, 1):
        s_name = screen.name() or ""
        geom = screen.geometry()
        res_str = f"{geom.width()}x{geom.height()}"
        is_primary = (screen == primary_screen)

        # 1. Look up in EDID map
        friendly_name = edid_map.get(s_name)

        # 2. Look up in QScreen model() / manufacturer()
        if not friendly_name:
            model = getattr(screen, "model", lambda: "")() or ""
            mfg = getattr(screen, "manufacturer", lambda: "")() or ""
            if model and model not in ("", "unknown", "Generic"):
                friendly_name = model
            elif mfg and mfg not in ("", "unknown", "Generic") and len(mfg) > 2:
                friendly_name = f"{mfg} Display"
            elif s_name and not s_name.startswith(r"\\.\DISPLAY"):
                friendly_name = s_name

        # 3. Fallback to generic Monitor N
        if not friendly_name:
            friendly_name = f"Monitor {idx}"

        primary_tag = " (Primary)" if is_primary else ""
        label = f"{idx}. {friendly_name} ({res_str}){primary_tag}"

        results.append({
            "index": idx,
            "name": friendly_name,
            "device_name": s_name,
            "resolution": res_str,
            "is_primary": is_primary,
            "display_label": label,
        })

    return results
