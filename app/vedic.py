"""Vedic (Jyotish) chart construction from sidereal longitudes."""

from __future__ import annotations

from datetime import date

from .ephemeris import (
    calc_houses,
    calc_planets,
    configure,
    ephemeris_label,
    julian_day_ut,
    local_to_ut_hours,
)
from .jhd import ChartEvent

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_LORDS = [
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
]

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_LORDS = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
] * 3

VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

EXALTATION = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 3,
    "Venus": 11,
    "Saturn": 6,
}
DEBILITATION = {k: (v + 6) % 12 for k, v in EXALTATION.items()}
OWN_SIGNS = {
    "Sun": {4},
    "Moon": {3},
    "Mars": {0, 7},
    "Mercury": {2, 5},
    "Jupiter": {8, 11},
    "Venus": {1, 6},
    "Saturn": {9, 10},
}

CORE_PLANETS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Rahu",
    "Ketu",
]

NAK_SPAN = 360.0 / 27.0


def sign_index(lon: float) -> int:
    return int((lon % 360) / 30.0)


def sign_degree(lon: float) -> float:
    return (lon % 360) % 30.0


def nakshatra_of(lon: float) -> dict:
    lon = lon % 360
    idx = int(lon / NAK_SPAN)
    within = lon - idx * NAK_SPAN
    pada = int(within / (NAK_SPAN / 4.0)) + 1
    return {
        "index": idx,
        "name": NAKSHATRAS[idx],
        "lord": NAKSHATRA_LORDS[idx],
        "pada": min(pada, 4),
        "remainder_pct": 100.0 * (1.0 - within / NAK_SPAN),
    }


def format_dms(lon_in_sign: float) -> str:
    d = int(lon_in_sign)
    m_float = (lon_in_sign - d) * 60.0
    m = int(m_float)
    s = int(round((m_float - m) * 60.0))
    if s == 60:
        m += 1
        s = 0
    if m == 60:
        d += 1
        m = 0
    return f"{d}°{m:02d}'{s:02d}\""


def whole_sign_house(planet_sign: int, lagna_sign: int) -> int:
    return (planet_sign - lagna_sign) % 12 + 1


def dignity(planet: str, sign: int) -> str:
    if planet in EXALTATION and EXALTATION[planet] == sign:
        return "exalted"
    if planet in DEBILITATION and DEBILITATION[planet] == sign:
        return "debilitated"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]:
        return "own"
    return "neutral"


def vedic_aspects(from_house: int, planet: str) -> list[int]:
    """Houses aspected, whole-sign, from the planet's house."""
    special = {
        "Mars": {4, 7, 8},
        "Jupiter": {5, 7, 9},
        "Saturn": {3, 7, 10},
    }
    offsets = special.get(planet, {7})
    return [((from_house - 1 + (o - 1)) % 12) + 1 for o in sorted(offsets)]


def conjunctions(positions: dict[str, dict], orb: float = 8.0) -> list[dict]:
    names = list(positions)
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            d = abs(positions[a]["longitude"] - positions[b]["longitude"]) % 360
            d = min(d, 360 - d)
            if d <= orb:
                found.append({"a": a, "b": b, "orb": round(d, 2)})
    found.sort(key=lambda x: x["orb"])
    return found


def yogas(chart: dict) -> list[str]:
    bodies = chart["bodies"]
    flags: list[str] = []
    moon_house = bodies["Moon"]["house"]
    jup_house = bodies["Jupiter"]["house"]
    if (jup_house - moon_house) % 12 in {0, 3, 6, 9}:
        flags.append("Gaja-Kesari (Jupiter in kendra from Moon)")

    sun_sign = bodies["Sun"]["sign_index"]
    moon_sign = bodies["Moon"]["sign_index"]
    rahu_sign = bodies["Rahu"]["sign_index"]
    if sun_sign == moon_sign:
        flags.append("Amavasya / Sun-Moon conjunction (new Moon)")
    if (sun_sign - moon_sign) % 12 == 6:
        flags.append("Purnima / Sun-Moon opposition (full Moon)")
    if sun_sign == rahu_sign or moon_sign == rahu_sign:
        flags.append("Node on luminaries (eclipse-family alignment)")
    if bodies["Jupiter"]["sign_index"] == rahu_sign:
        flags.append("Guru-Chandala (Jupiter with Rahu)")
    if bodies["Mars"]["sign"] == bodies["Rahu"]["sign"]:
        flags.append("Mars-Rahu conjunction")
    if bodies["Saturn"]["sign"] == bodies["Rahu"]["sign"]:
        flags.append("Saturn-Rahu conjunction")
    if bodies["Mars"]["sign"] == bodies["Saturn"]["sign"]:
        flags.append("Mars-Saturn conjunction")
    # Kemadruma: no planets in 2nd or 12th from Moon (excluding Sun)
    occupied = {bodies[p]["house"] for p in CORE_PLANETS if p not in {"Moon", "Sun"}}
    second = (moon_house % 12) + 1
    twelfth = ((moon_house - 2) % 12) + 1
    if second not in occupied and twelfth not in occupied:
        flags.append("Kemadruma-like (empty 2nd/12th from Moon)")
    return flags


def vimshottari_at_event(moon_lon: float) -> dict:
    nak = nakshatra_of(moon_lon)
    lord = nak["lord"]
    years = VIMSHOTTARI_YEARS[lord]
    elapsed_frac = 1.0 - nak["remainder_pct"] / 100.0
    balance_years = years * (1.0 - elapsed_frac)
    order = list(VIMSHOTTARI_YEARS.keys())
    start = order.index(lord)
    sequence = order[start:] + order[:start]
    return {
        "mahadasha": lord,
        "nakshatra": nak["name"],
        "balance_years": round(balance_years, 3),
        "sequence": sequence,
    }


def build_chart(event: ChartEvent | dict) -> dict:
    if isinstance(event, dict):
        event = ChartEvent(**{k: event[k] for k in ChartEvent.__dataclass_fields__ if k in event})
    configure()
    local_h = event.hour + event.minute / 60.0 + event.second / 3600.0
    ut_h, shift = local_to_ut_hours(local_h, event.tz_offset_hours)
    y, m, d = event.year, event.month, event.day
    if shift:
        from .ephemeris import _shift_date

        y, m, d = _shift_date(y, m, d, shift)
    jd = julian_day_ut(y, m, d, ut_h)
    planets = calc_planets(jd)
    houses = calc_houses(jd, event.latitude, event.longitude)
    lagna_lon = houses["ascendant"]
    lagna_sign = sign_index(lagna_lon)

    bodies: dict[str, dict] = {}
    all_names = list(CORE_PLANETS) + ["Uranus", "Neptune", "Pluto"]
    for name in all_names:
        pos = planets[name]
        sidx = sign_index(pos["longitude"])
        deg = sign_degree(pos["longitude"])
        nak = nakshatra_of(pos["longitude"])
        house = whole_sign_house(sidx, lagna_sign)
        bodies[name] = {
            "longitude": round(pos["longitude"], 4),
            "sign": SIGNS[sidx],
            "sign_index": sidx,
            "degree": round(deg, 4),
            "dms": format_dms(deg),
            "nakshatra": nak["name"],
            "nakshatra_lord": nak["lord"],
            "pada": nak["pada"],
            "house": house,
            "lord": SIGN_LORDS[sidx],
            "dignity": dignity(name, sidx),
            "retrograde": pos["retrograde"],
            "speed": round(pos["speed"], 4),
        }

    lagna = {
        "longitude": round(lagna_lon, 4),
        "sign": SIGNS[lagna_sign],
        "sign_index": lagna_sign,
        "degree": round(sign_degree(lagna_lon), 4),
        "dms": format_dms(sign_degree(lagna_lon)),
        "nakshatra": nakshatra_of(lagna_lon)["name"],
        "house": 1,
    }

    aspects = []
    for name in CORE_PLANETS:
        targets = vedic_aspects(bodies[name]["house"], name)
        for th in targets:
            aspects.append({"from": name, "from_house": bodies[name]["house"], "to_house": th})

    chart = {
        "event": event.to_dict(),
        "jd_ut": jd,
        "weekday": date(event.year, event.month, event.day).strftime("%A"),
        "ephemeris": ephemeris_label(),
        "ayanamsa": round(houses["ayanamsa"], 4),
        "lagna": lagna,
        "mc": {
            "longitude": round(houses["mc"], 4),
            "sign": SIGNS[sign_index(houses["mc"])],
        },
        "bodies": bodies,
        "cusps": houses["cusps"],
        "conjunctions": conjunctions({n: planets[n] for n in CORE_PLANETS}),
        "aspects": aspects,
        "dasha": vimshottari_at_event(planets["Moon"]["longitude"]),
    }
    chart["yogas"] = yogas(chart)
    return chart
