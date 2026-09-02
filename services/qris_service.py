"""
QRIS (Quick Response Code Indonesian Standard) Dynamic Generator & Parser.
EMVCo QR standard implementation with CRC-16 CCITT for dynamic amount injection.
Ported from standard Indonesian QRIS dynamic conversion algorithms.
"""

import re
import importlib
from typing import Optional, Dict, Any, Tuple
from io import BytesIO
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage


def to_crc16(input_str: str) -> str:
    """
    Computes CRC-16 CCITT (0xFFFF initial, 0x1021 polynomial) in uppercase 4-digit hex.
    Matching the exact JS algorithm provided.
    """
    crc = 0xFFFF
    for ch in input_str:
        crc ^= (ord(ch) << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    hex_str = f"{crc & 0xFFFF:04X}"
    return hex_str


def get_between(text: str, start: str, end: str) -> str:
    """Extracts substring between two markers."""
    start_idx = text.find(start)
    if start_idx == -1:
        return ""
    start_idx += len(start)
    end_idx = text.find(end, start_idx)
    if end_idx == -1:
        return text[start_idx:]
    return text[start_idx:end_idx]


def parse_qris_data(qris_str: str) -> Dict[str, Any]:
    """
    Parses metadata from QRIS payload (NMID, Merchant Name, ID, Printer, CRC validity).
    Exact port of dataQris() algorithm.
    """
    qris = qris_str.strip()
    if len(qris) < 10:
        return {
            "nmid": "",
            "id": "01",
            "merchant_name": "UNKNOWN",
            "printer": "UNKNOWN",
            "nns": "UNKNOWN",
            "crc_is_valid": False,
            "raw": qris
        }

    nmid = "ID" + get_between(qris, "15ID", "0303")
    id_tag = "A01" if "A01" in qris else "01"
    merchant_name = get_between(qris, "ID59", "60")[2:].strip().upper() if "ID59" in qris else "MERCHANT"

    crc_input = qris[:-4]
    crc_from_qris = qris[-4:].upper()
    crc_computed = to_crc16(crc_input)

    return {
        "nmid": nmid,
        "id": id_tag,
        "merchant_name": merchant_name or "MERCHANT",
        "crc_is_valid": crc_from_qris == crc_computed,
        "raw": qris
    }


def convert_to_dynamic_qris(static_qris: str, amount: int) -> str:
    """
    Converts a static QRIS payload (010211) into a dynamic QRIS payload (010212)
    with injected transaction amount (Tag 54) and re-calculated CRC16 checksum.
    """
    raw = static_qris.strip()
    if not raw:
        return ""

    # 1. Strip existing CRC (Tag 63: '6304' + 4 chars = last 8 chars)
    if raw.endswith("6304") or "6304" in raw[-8:]:
        idx_63 = raw.rfind("6304")
        payload = raw[:idx_63]
    elif len(raw) > 4:
        payload = raw[:-4]
    else:
        payload = raw

    # 2. Change Point of Initiation Method from Static (010211) to Dynamic (010212)
    if "010211" in payload:
        payload = payload.replace("010211", "010212", 1)

    # 3. Format Amount in EMVCo TLV format: Tag 54, length (2 digits), amount string
    amt_str = str(int(amount))
    amt_len = f"{len(amt_str):02d}"
    amt_tlv = f"54{amt_len}{amt_str}"

    # 4. If Tag 54 already exists, strip it
    if "54" in payload and "5802ID" in payload:
        # Check if 54 is right before 5802ID
        match = re.search(r"54\d{2}\d+(?=5802ID)", payload)
        if match:
            payload = payload[:match.start()] + payload[match.end():]

    # 5. Insert Tag 54 right before Country Code (Tag 58: '5802ID')
    if "5802ID" in payload:
        parts = payload.split("5802ID", 1)
        payload = f"{parts[0]}{amt_tlv}5802ID{parts[1]}"
    elif "5802" in payload:
        idx_58 = payload.find("5802")
        payload = f"{payload[:idx_58]}{amt_tlv}{payload[idx_58:]}"
    else:
        payload = f"{payload}{amt_tlv}"

    # 6. Append Tag 6304 and compute CRC16
    payload_to_crc = f"{payload}6304"
    crc_hex = to_crc16(payload_to_crc)

    return f"{payload_to_crc}{crc_hex}"


def generate_qr_pixmap(data_str: str, size: int = 220) -> Optional[QPixmap]:
    """
    Renders QR code data into a high-quality QPixmap for display.
    Uses 'qrcode' library with Pillow backend.
    """
    if not data_str:
        return None
    try:
        import qrcode
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data_str)
        qr.make(fit=True)

        try:
            from qrcode.image.pil import PilImage
            img = qr.make_image(image_factory=PilImage, fill_color="#0f172a", back_color="#ffffff")
        except Exception:
            img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")

        buffer = BytesIO()
        if hasattr(img, "save"):
            try:
                img.save(buffer, format="PNG")
            except TypeError:
                img.save(buffer)
        buffer.seek(0)

        qimage = QImage.fromData(buffer.getvalue())
        pix = QPixmap.fromImage(qimage)
        return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    except Exception:
        return None


def decode_qr_from_image(image_path: str) -> Optional[str]:
    """
    Attempts to read and decode QRIS payload string from an uploaded image file.
    Tries cv2 QRCodeDetector, pyzbar, and pure-python fallbacks.
    """
    if not image_path:
        return None

    # Try cv2 QRCodeDetector dynamically
    try:
        cv2_mod = importlib.import_module("cv2")
        img = cv2_mod.imread(image_path)
        if img is not None:
            detector = cv2_mod.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(img)
            if data:
                return str(data).strip()
    except Exception:
        pass

    # Try pyzbar dynamically
    try:
        pyzbar_mod = importlib.import_module("pyzbar.pyzbar")
        from PIL import Image
        img = Image.open(image_path)
        decoded = pyzbar_mod.decode(img)
        if decoded:
            return decoded[0].data.decode("utf-8").strip()
    except Exception:
        pass

    return None
