"""Drive the installed Jagannatha Hora 7.66 UI and read its charts.

The shortcut in the user's Launch folder starts jhora.exe. This module types
birth data into that program and copies the chart text JHora itself produces.
It never runs jh_update_auto.exe and never accepts an update dialog.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

SHORTCUT = Path(r"C:\Users\ychuk\Documents\Jagannath hora\3. Launch\Jagannatha Hora.lnk")
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

_app: Application | None = None


def _dismiss_update() -> None:
    """Close an update offer. Never press Yes."""
    for title in ("Ready to install update", "Update Error", "Jagannatha Hora"):
        try:
            dlg = Desktop(backend="win32").window(title=title, class_name="#32770")
            if not dlg.exists(timeout=0.2):
                continue
            text = dlg.window_text() + " " + " ".join(
                c.window_text() for c in dlg.children() if c.window_text()
            )
            if "update" not in text.lower() and title != "Ready to install update":
                continue
            for label in ("No", "&No", "Cancel", "OK"):
                btn = dlg.child_window(title=label, class_name="Button")
                if btn.exists(timeout=0.2):
                    btn.click()
                    return
            dlg.close()
        except Exception:
            continue


def launch() -> Application:
    global _app
    _dismiss_update()
    if _app is not None:
        try:
            if _app.top_window().exists(timeout=0.5):
                return _app
        except Exception:
            _app = None
    existing = Desktop(backend="win32").windows(title_re=".*Jagannatha Hora.*", class_name_re="Afx:.*")
    if existing:
        _app = Application(backend="win32").connect(handle=existing[0].handle)
        _dismiss_update()
        return _app
    if not SHORTCUT.exists():
        raise FileNotFoundError(f"JHora shortcut not found: {SHORTCUT}")
    import os

    os.startfile(str(SHORTCUT))
    deadline = time.time() + 25
    while time.time() < deadline:
        _dismiss_update()
        wins = Desktop(backend="win32").windows(title_re=".*Jagannatha Hora.*", class_name_re="Afx:.*")
        if wins:
            _app = Application(backend="win32").connect(handle=wins[0].handle)
            _dismiss_update()
            return _app
        time.sleep(0.4)
    raise RuntimeError("Jagannatha Hora did not open from the Launch shortcut.")


def main_window():
    app = launch()
    win = app.window(title_re=".*Jagannatha Hora.*", class_name_re="Afx:.*")
    win.wait("visible", timeout=10)
    return win


def _set_edit(dlg, **kwargs) -> None:
    edit = dlg.child_window(**kwargs)
    edit.set_edit_text("")
    edit.set_edit_text(kwargs.get("text_value", ""))


def _fill(dlg, ident: dict, value: str) -> None:
    edit = dlg.child_window(**ident)
    edit.set_focus()
    edit.set_edit_text(str(value))


def _dms(value: float) -> tuple[int, str, int, int]:
    sign = "E" if value >= 0 else "W"
    # Latitude uses N/S; caller overrides the hemisphere letter.
    mag = abs(value)
    degrees = int(mag)
    minutes_f = (mag - degrees) * 60
    minutes = int(minutes_f)
    seconds = int(round((minutes_f - minutes) * 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        degrees += 1
        minutes = 0
    return degrees, sign, minutes, seconds


def enter_event(event: dict) -> str:
    """Type one event into JHora and return the basic-calculation text."""
    win = main_window()
    win.set_focus()
    win.menu_select("Edit->Birthdata")
    dlg = Desktop(backend="win32").window(title="Enter Birthdata", class_name="#32770")
    dlg.wait("visible", timeout=8)

    month = MONTHS[int(event["month"]) - 1]
    dlg.child_window(class_name="ComboBox", found_index=0).select(month)
    _fill(dlg, {"class_name": "Edit", "found_index": 0}, str(int(event["day"])))
    _fill(dlg, {"class_name": "Edit", "found_index": 1}, str(int(event["year"])))
    _fill(dlg, {"class_name": "Edit", "found_index": 2}, str(int(event["hour"])))
    _fill(dlg, {"class_name": "Edit", "found_index": 3}, str(int(event["minute"])))
    _fill(dlg, {"class_name": "Edit", "found_index": 4}, str(int(event.get("second") or 0)))

    place = event.get("city") or event.get("name") or "Event"
    _fill(dlg, {"class_name": "Edit", "found_index": 5}, place)

    tz = float(event["tz_offset_hours"])
    tz_hours = int(abs(tz))
    tz_minutes = int(round((abs(tz) - tz_hours) * 60))
    _fill(dlg, {"class_name": "Edit", "found_index": 6}, str(tz_hours))
    _fill(dlg, {"class_name": "Edit", "found_index": 7}, str(tz_minutes))
    side = dlg.child_window(class_name="ComboBox", found_index=7)
    side.select("East of GMT" if tz >= 0 else "West of GMT")

    lon_d, _, lon_m, lon_s = _dms(float(event["longitude"]))
    lat_d, _, lat_m, lat_s = _dms(float(event["latitude"]))
    lon_hem = "E" if float(event["longitude"]) >= 0 else "W"
    lat_hem = "N" if float(event["latitude"]) >= 0 else "S"

    _fill(dlg, {"class_name": "Edit", "found_index": 8}, str(lon_d))
    dlg.child_window(class_name="ComboBox", found_index=8).select(lon_hem)
    _fill(dlg, {"class_name": "Edit", "found_index": 9}, str(lon_m))
    _fill(dlg, {"class_name": "Edit", "found_index": 10}, str(lon_s))
    _fill(dlg, {"class_name": "Edit", "found_index": 11}, str(lat_d))
    dlg.child_window(class_name="ComboBox", found_index=9).select(lat_hem)
    _fill(dlg, {"class_name": "Edit", "found_index": 12}, str(lat_m))
    _fill(dlg, {"class_name": "Edit", "found_index": 13}, str(lat_s))

    dlg.child_window(title="OK", class_name="Button").click()
    time.sleep(0.8)
    _dismiss_message_boxes()

    win = main_window()
    win.set_focus()
    win.menu_select("Edit->Copy basic calculations")
    time.sleep(0.4)
    _dismiss_message_boxes()
    return _clipboard()


def _dismiss_message_boxes() -> None:
    for _ in range(4):
        _dismiss_update()
        found = False
        for w in Desktop(backend="win32").windows(class_name="#32770"):
            title = w.window_text()
            if title in {"Enter Birthdata", "Jagannatha Hora"}:
                continue
            if not title:
                continue
            blob = title.lower()
            try:
                blob += " " + " ".join(c.window_text().lower() for c in w.children())
            except Exception:
                pass
            if "update" in blob and "yes" in blob:
                for label in ("No", "&No", "Cancel"):
                    btn = w.child_window(title=label, class_name="Button")
                    if btn.exists(timeout=0.1):
                        btn.click()
                        found = True
                        break
                continue
            if "copied" in blob or "success" in blob:
                w.set_focus()
                send_keys("{ENTER}")
                found = True
        if not found:
            break
        time.sleep(0.2)


def _clipboard() -> str:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    return data


_SIGN = {
    "Ar": "Aries",
    "Ta": "Taurus",
    "Ge": "Gemini",
    "Cn": "Cancer",
    "Le": "Leo",
    "Vi": "Virgo",
    "Li": "Libra",
    "Sc": "Scorpio",
    "Sg": "Sagittarius",
    "Cp": "Capricorn",
    "Aq": "Aquarius",
    "Pi": "Pisces",
}
_SIGNS = list(_SIGN.values())
_NAK = {
    "Aswi": "Ashwini",
    "Bhar": "Bharani",
    "Krit": "Krittika",
    "Rohi": "Rohini",
    "Mrig": "Mrigashira",
    "Ardr": "Ardra",
    "Puna": "Punarvasu",
    "Push": "Pushya",
    "Asre": "Ashlesha",
    "Magh": "Magha",
    "PPha": "Purva Phalguni",
    "UPha": "Uttara Phalguni",
    "Hast": "Hasta",
    "Chit": "Chitra",
    "Swat": "Swati",
    "Visa": "Vishakha",
    "Anur": "Anuradha",
    "Jyes": "Jyeshtha",
    "Mool": "Mula",
    "PSha": "Purva Ashadha",
    "USha": "Uttara Ashadha",
    "Srav": "Shravana",
    "Dhan": "Dhanishta",
    "Sata": "Shatabhisha",
    "PBha": "Purva Bhadrapada",
    "UBha": "Uttara Bhadrapada",
    "Reva": "Revati",
}
_BODY_LINE = re.compile(
    r"^(Lagna|Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b.*?"
    r"(\d+)\s+([A-Za-z]{2})\s+(\d+)'\s+([\d.]+)\"\s+([A-Za-z]+)"
)


def parse_basic_chart(text: str, event: dict) -> dict:
    """Turn JHora's copied basic-calculation text into the chart the report draws."""
    from .vedic import conjunctions, dignity, vedic_aspects, yogas

    found = {}
    for line in text.splitlines():
        match = _BODY_LINE.search(line.strip())
        if not match:
            continue
        name, deg, abbr, minute, sec, nak = match.groups()
        sign = _SIGN[abbr]
        degree = int(deg) + int(minute) / 60 + float(sec) / 3600
        found[name] = {
            "sign": sign,
            "sign_index": _SIGNS.index(sign),
            "dms": f"{int(deg)}°{int(minute):02d}'{int(float(sec)):02d}\"",
            "degree": round(degree, 4),
            "longitude": round(_SIGNS.index(sign) * 30 + degree, 4),
            "nakshatra": _NAK.get(nak, nak),
            "retrograde": "(R)" in line,
            "house": 1,
            "dignity": "neutral",
        }
    if "Lagna" not in found:
        raise RuntimeError("JHora chart text did not include Lagna.")
    lagna = found.pop("Lagna")
    for name, body in found.items():
        body["house"] = (body["sign_index"] - lagna["sign_index"]) % 12 + 1
        body["dignity"] = dignity(name, body["sign_index"])
    weekday = ""
    week = re.search(r"Vedic Weekday:\s+([A-Za-z]+)", text)
    if week:
        weekday = week.group(1)
    ayanamsa = ""
    ayan = re.search(r"Ayanamsa:\s+([0-9\- .]+)", text)
    if ayan:
        ayanamsa = ayan.group(1).strip()
    chart = {
        "event": event,
        "source": "Jagannatha Hora 7.66",
        "lagna": {
            "sign": lagna["sign"],
            "sign_index": lagna["sign_index"],
            "dms": lagna["dms"],
            "nakshatra": lagna["nakshatra"],
            "house": 1,
        },
        "bodies": found,
        "ephemeris": "Jagannatha Hora 7.66",
        "ayanamsa_text": ayanamsa,
        "weekday": weekday,
        "dasha": {"mahadasha": ""},
        "conjunctions": conjunctions(found),
        "aspects": [],
    }
    for name, body in found.items():
        for house in vedic_aspects(body["house"], name):
            chart["aspects"].append({"from": name, "from_house": body["house"], "to_house": house})
    chart["yogas"] = yogas(chart)
    return chart


def read_chart(event: dict) -> dict:
    text = enter_event(event)
    if "Natal Chart" not in text or "Lagna" not in text:
        raise RuntimeError("Jagannatha Hora did not copy a natal chart.")
    return parse_basic_chart(text, event)
