"""Earthquake event lists for a concordance study.

The active set is the latest 20 magnitude 6+ earthquakes from USGS.
Times in that file are UTC, so the timezone offset is 0.
"""

from __future__ import annotations

import json
from pathlib import Path

from .jhd import ChartEvent

RECENT_QUAKES = Path(__file__).resolve().parent.parent / "recent-m6-earthquakes.json"

EARTHQUAKES: list[ChartEvent] = [
    ChartEvent("San Francisco 1906", 1906, 4, 18, 5, 12, 0, -8.0, -122.55, 37.75, "San Francisco", "USA", "M7.9", "sample"),
    ChartEvent("Great Kanto 1923", 1923, 9, 1, 11, 58, 32, 9.0, 139.14, 35.33, "Kanto", "Japan", "M7.9", "sample"),
    ChartEvent("Valdivia 1960", 1960, 5, 22, 15, 11, 14, -4.0, -73.05, -38.24, "Valdivia", "Chile", "M9.5", "sample"),
    ChartEvent("Alaska 1964", 1964, 3, 27, 17, 36, 14, -9.0, -147.73, 61.04, "Prince William Sound", "USA", "M9.2", "sample"),
    ChartEvent("Tangshan 1976", 1976, 7, 28, 3, 42, 53, 8.0, 118.40, 39.66, "Tangshan", "China", "M7.6", "sample"),
    ChartEvent("Mexico City 1985", 1985, 9, 19, 7, 17, 50, -5.0, -102.53, 18.19, "Michoacan", "Mexico", "M8.0", "sample"),
    ChartEvent("Spitak 1988", 1988, 12, 7, 11, 41, 24, 4.0, 44.19, 40.99, "Spitak", "Armenia", "M6.8", "sample"),
    ChartEvent("Loma Prieta 1989", 1989, 10, 17, 17, 4, 15, -7.0, -121.88, 37.04, "Loma Prieta", "USA", "M6.9", "sample"),
    ChartEvent("Northridge 1994", 1994, 1, 17, 4, 30, 55, -8.0, -118.54, 34.21, "Northridge", "USA", "M6.7", "sample"),
    ChartEvent("Kobe 1995", 1995, 1, 17, 5, 46, 52, 9.0, 135.00, 34.60, "Kobe", "Japan", "M6.9", "sample"),
    ChartEvent("Izmit 1999", 1999, 8, 17, 3, 1, 40, 3.0, 29.86, 40.75, "Izmit", "Turkey", "M7.6", "sample"),
    ChartEvent("Bhuj 2001", 2001, 1, 26, 8, 46, 40, 5.5, 70.23, 23.42, "Bhuj", "India", "M7.7", "sample"),
    ChartEvent("Sumatra 2004", 2004, 12, 26, 7, 58, 53, 7.0, 95.85, 3.32, "Aceh", "Indonesia", "M9.1", "sample"),
    ChartEvent("Kashmir 2005", 2005, 10, 8, 8, 50, 38, 5.0, 73.63, 34.49, "Muzaffarabad", "Pakistan", "M7.6", "sample"),
    ChartEvent("Wenchuan 2008", 2008, 5, 12, 14, 28, 1, 8.0, 103.37, 31.00, "Wenchuan", "China", "M7.9", "sample"),
    ChartEvent("Haiti 2010", 2010, 1, 12, 16, 53, 10, -5.0, -72.53, 18.46, "Léogâne", "Haiti", "M7.0", "sample"),
    ChartEvent("Tohoku 2011", 2011, 3, 11, 14, 46, 24, 9.0, 142.37, 38.30, "Tohoku", "Japan", "M9.1", "sample"),
    ChartEvent("Gorkha 2015", 2015, 4, 25, 11, 56, 26, 5.75, 84.73, 28.23, "Gorkha", "Nepal", "M7.8", "sample"),
    ChartEvent("Puebla 2017", 2017, 9, 19, 13, 14, 39, -5.0, -98.49, 18.55, "Puebla", "Mexico", "M7.1", "sample"),
    ChartEvent("Turkey–Syria 2023", 2023, 2, 6, 4, 17, 34, 3.0, 37.03, 37.17, "Pazarcık", "Turkey", "M7.8", "sample"),
]


def recent_quake_events() -> list[dict]:
    rows = json.loads(RECENT_QUAKES.read_text(encoding="utf-8"))
    events = []
    for row in rows:
        year, month, day = [int(part) for part in row["time_utc"][:10].split("-")]
        hour, minute, second = [int(part) for part in row["time_utc"][11:19].split(":")]
        place = row["place"]
        region = place.split(",")[-1].strip() if "," in place else place
        magnitude = row["magnitude"]
        events.append(
            ChartEvent(
                name=f"M{magnitude} {region}",
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
                tz_offset_hours=0.0,
                longitude=float(row["longitude"]),
                latitude=float(row["latitude"]),
                city=place,
                country="",
                notes=f"M{magnitude}, depth {row['depth_km']} km, UTC",
                source="usgs",
            ).to_dict()
        )
    return events


def sample_events() -> list[dict]:
    return recent_quake_events()
