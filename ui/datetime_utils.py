"""
Date and Time Formatting Utilities for KubuCashier.
Provides Asia/Jakarta (WIB) time conversions, locale formatting, and time greetings.
"""

from datetime import datetime, timezone, timedelta
from ui.i18n import t

ID_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
ID_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def get_jakarta_now() -> datetime:
    """Returns current datetime in Asia/Jakarta (WIB, UTC+7)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Jakarta"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=7)))


def get_greeting(name: str) -> str:
    """Returns clean time-appropriate greeting with trailing emoji in current language for Asia/Jakarta time."""
    now = get_jakarta_now()
    hour = now.hour
    if 5 <= hour < 12:
        salutation = t("greeting_morning")
        emoji = "🌅"
    elif 12 <= hour < 17:
        salutation = t("greeting_afternoon")
        emoji = "🌆"
    elif 17 <= hour < 21:
        salutation = t("greeting_evening")
        emoji = "🌇"
    else:
        salutation = t("greeting_night")
        emoji = "🌙"

    if name:
        return f"{salutation}, {name}! {emoji}"
    return f"{salutation}! {emoji}"


def get_formatted_clock(lang: str = "en") -> str:
    """Formats live clock using Asia/Jakarta (WIB) and locale-specific format."""
    now = get_jakarta_now()
    if lang == "id":
        day_name = ID_DAYS[now.weekday()]
        month_name = ID_MONTHS[now.month - 1]
        time_str = now.strftime("%H:%M:%S WIB")
        date_str = f"{day_name}, {now.day:02d} {month_name} {now.year}"
        return f"{time_str}  •  {date_str}"
    else:
        time_str = now.strftime("%I:%M:%S %p WIB")
        date_str = now.strftime("%a, %b %d, %Y")
        return f"{time_str}  •  {date_str}"
