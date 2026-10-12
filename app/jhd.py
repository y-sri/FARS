"""Jagannatha Hora .jhd chart-file reader and writer.

JHora stores one chart per file as line-oriented text.
Longitude and timezone are East-negative (opposite of ISO).
Timezone on line 5 is H.MM (hours.minutes), not decimal hours.
The chart name is the file stem, not a field inside the file.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ChartEvent:
    name: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    tz_offset_hours: float
    longitude: float
    latitude: float
    city: str = ""
    country: str = ""
    notes: str = ""
    source: str = "jhd"
    path: str = ""

    def local_time_decimal(self) -> float:
        return self.hour + self.minute / 60.0 + self.second / 3600.0

    def to_dict(self) -> dict:
        return asdict(self)


class JhdError(ValueError):
    pass


def _hmm_to_decimal_hours(value: float) -> float:
    """Convert signed H.MM (e.g. -5.30) to signed decimal hours (-5.5)."""
    sign = -1.0 if value < 0 else 1.0
    mag = abs(value)
    hours = int(mag)
    minutes = (mag - hours) * 100.0
    return sign * (hours + minutes / 60.0)


def _decimal_hours_to_hmm(value: float) -> float:
    """Convert signed decimal hours to signed H.MM."""
    sign = -1.0 if value < 0 else 1.0
    mag = abs(value)
    hours = int(mag)
    minutes = round((mag - hours) * 60.0)
    if minutes >= 60:
        hours += 1
        minutes = 0
    return sign * (hours + minutes / 100.0)


def parse_jhd_text(text: str, name: str = "", path: str = "") -> ChartEvent:
    lines = [line.rstrip("\r").strip() for line in text.splitlines()]
    lines = [line for line in lines if True]
    if len(lines) < 7:
        raise JhdError(f"Expected at least 7 lines in .jhd, found {len(lines)}")

    def num(idx: int) -> float:
        raw = lines[idx - 1]
        try:
            return float(raw)
        except ValueError as exc:
            raise JhdError(f"Line {idx}: expected a number, found {raw!r}") from exc

    month = int(num(1))
    day = int(num(2))
    year = int(num(3))
    t = num(4)
    hour = int(t)
    rem_min = (t - hour) * 60.0
    minute = int(rem_min)
    second = int(round((rem_min - minute) * 60.0))
    if second >= 60:
        minute += 1
        second = 0
    if minute >= 60:
        hour += 1
        minute = 0

    tz_east_neg = _hmm_to_decimal_hours(num(5))
    tz_offset_hours = -tz_east_neg
    longitude = -num(6)
    latitude = num(7)

    city, country = "", ""
    if len(lines) >= 13:
        line13 = lines[12]
        try:
            float(line13)
        except ValueError:
            if line13 and line13 != "Unknown":
                city = line13
            if len(lines) >= 14 and lines[13] and lines[13] != "Unknown":
                try:
                    float(lines[13])
                except ValueError:
                    country = lines[13]

    return ChartEvent(
        name=name or "Untitled",
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=min(second, 59),
        tz_offset_hours=tz_offset_hours,
        longitude=longitude,
        latitude=latitude,
        city=city,
        country=country,
        source="jhd",
        path=path,
    )


def parse_jhd_file(path: str | Path) -> ChartEvent:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    return parse_jhd_text(text, name=p.stem, path=str(p))


def scan_jhd_folder(folder: str | Path, recursive: bool = True) -> list[ChartEvent]:
    root = Path(folder)
    if not root.exists():
        raise JhdError(f"Folder not found: {root}")
    pattern = "**/*.jhd" if recursive else "*.jhd"
    events: list[ChartEvent] = []
    errors: list[str] = []
    for file in sorted(root.glob(pattern)):
        try:
            events.append(parse_jhd_file(file))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{file}: {exc}")
    if not events and errors:
        raise JhdError("; ".join(errors[:5]))
    return events


def write_jhd(event: ChartEvent) -> str:
    t = event.local_time_decimal()
    tz = _decimal_hours_to_hmm(-event.tz_offset_hours)
    lon = -event.longitude
    lines = [
        str(event.month),
        str(event.day),
        str(event.year),
        f"{t:.15f}",
        f"{tz:.6f}",
        f"{lon:.6f}",
        f"{event.latitude:.6f}",
        "0.000000",
        f"{tz:.6f}",
        f"{tz:.6f}",
        "0",
        "105",
        event.city or "Unknown",
        event.country or "Unknown",
        "1",
        "1013.250000",
        "20.000000",
        "0",
    ]
    return "\n".join(lines) + "\n"
