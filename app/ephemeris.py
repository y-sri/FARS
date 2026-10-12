"""Sidereal positions for FARS.

A .jhd file stores the event's date, time, and place. It does not store
JHora's calculated longitudes. These positions are modern geocentric
longitudes minus the Sri Surya Siddhanta ayanamsa. Vinay Jha's generalized
Makaranda model is a separate planetary theory inside Jagannatha Hora.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import astronomy as A

_LABEL = "Modern geocentric + Sri Surya Siddhanta ayanamsa"
_J2000_JD = 2451545.0
# Swiss Ephemeris SIDM_SURYASIDDHANTA: zero near the Kali-3600 equinox, 21 March 499 CE.
_SS_J2000_DEG = 20.8951
_SS_PRECESSION_ARCSEC_PER_CENTURY = 5027.8

BODIES = {
    "Sun": A.Body.Sun,
    "Moon": A.Body.Moon,
    "Mercury": A.Body.Mercury,
    "Venus": A.Body.Venus,
    "Mars": A.Body.Mars,
    "Jupiter": A.Body.Jupiter,
    "Saturn": A.Body.Saturn,
    "Uranus": A.Body.Uranus,
    "Neptune": A.Body.Neptune,
    "Pluto": A.Body.Pluto,
}


def configure(ephe_path: str | None = None) -> str:
    return _LABEL


def ephemeris_label() -> str:
    return _LABEL


def julian_day_ut(year: int, month: int, day: int, ut_hours: float) -> float:
    return _J2000_JD + _time_ut(year, month, day, ut_hours).ut


def local_to_ut_hours(local_hours: float, tz_offset_hours: float) -> tuple[float, int]:
    ut = local_hours - tz_offset_hours
    shift = 0
    if ut < 0:
        ut += 24
        shift = -1
    elif ut >= 24:
        ut -= 24
        shift = 1
    return ut, shift


def _shift_date(year: int, month: int, day: int, shift: int) -> tuple[int, int, int]:
    dt = datetime(year, month, day) + timedelta(days=shift)
    return dt.year, dt.month, dt.day


def _time_ut(year: int, month: int, day: int, ut_hours: float) -> A.Time:
    hour = int(ut_hours)
    minutes_f = (ut_hours - hour) * 60.0
    minute = int(minutes_f)
    second = (minutes_f - minute) * 60.0
    return A.Time.Make(year, month, day, hour, minute, second)


def _time_from_jd(jd: float) -> A.Time:
    return A.Time.Make(2000, 1, 1, 12, 0, 0).AddDays(jd - _J2000_JD)


def surya_siddhanta_ayanamsa(jd_ut: float) -> float:
    """Sri Surya Siddhanta ayanamsa in degrees.

    This is the published equinox-zero of 499 CE, carried by modern precession.
    It is the ayanamsa frame. It is not Vinay Jha's Makaranda planetary model.
    """
    centuries = (jd_ut - _J2000_JD) / 36525.0
    return _SS_J2000_DEG + (_SS_PRECESSION_ARCSEC_PER_CENTURY * centuries) / 3600.0


def _tropical_lon_lat(body: A.Body, time: A.Time) -> tuple[float, float]:
    vec = A.GeoVector(body, time, True)
    ecl = A.Ecliptic(vec)
    return float(ecl.elon % 360.0), float(ecl.elat)


def _mean_node_tropical(jd_ut: float) -> float:
    t = (jd_ut - _J2000_JD) / 36525.0
    omega = (
        125.0445479
        - 1934.1362891 * t
        + 0.0020754 * t * t
        + (t * t * t) / 467441.0
        - (t * t * t * t) / 60616000.0
    )
    return omega % 360.0


def _wrap_delta(a: float, b: float) -> float:
    return (b - a + 180.0) % 360.0 - 180.0


def calc_planets(jd_ut: float) -> dict[str, dict]:
    time = _time_from_jd(jd_ut)
    later = time.AddDays(1.0)
    ayan = surya_siddhanta_ayanamsa(jd_ut)
    out: dict[str, dict] = {}
    for name, body in BODIES.items():
        lon_t, lat = _tropical_lon_lat(body, time)
        lon2, _ = _tropical_lon_lat(body, later)
        speed = _wrap_delta(lon_t, lon2)
        sid = (lon_t - ayan) % 360.0
        out[name] = {
            "longitude": sid,
            "speed": speed,
            "latitude": lat,
            "retrograde": speed < 0 and name not in {"Sun", "Moon"},
        }
    node_t = _mean_node_tropical(jd_ut)
    node2 = _mean_node_tropical(jd_ut + 1.0)
    rahu = (node_t - ayan) % 360.0
    out["Rahu"] = {
        "longitude": rahu,
        "speed": _wrap_delta(node_t, node2),
        "latitude": 0.0,
        "retrograde": True,
    }
    out["Ketu"] = {
        "longitude": (rahu + 180.0) % 360.0,
        "speed": out["Rahu"]["speed"],
        "latitude": 0.0,
        "retrograde": True,
    }
    return out


def _obliquity(jd_ut: float) -> float:
    t = (jd_ut - _J2000_JD) / 36525.0
    return 23.4392911 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t * t * t


def _asc_mc(jd_ut: float, latitude: float, longitude: float) -> tuple[float, float]:
    time = _time_from_jd(jd_ut)
    gst_hours = float(A.SiderealTime(time))
    ramc = math.radians((gst_hours * 15.0 + longitude) % 360.0)
    eps = math.radians(_obliquity(jd_ut))
    phi = math.radians(latitude)
    asc = math.atan2(
        math.cos(ramc),
        -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)),
    )
    mc = math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))
    return math.degrees(asc) % 360.0, math.degrees(mc) % 360.0


def calc_houses(jd_ut: float, latitude: float, longitude: float) -> dict:
    asc_trop, mc_trop = _asc_mc(jd_ut, latitude, longitude)
    ayan = surya_siddhanta_ayanamsa(jd_ut)
    asc = (asc_trop - ayan) % 360.0
    mc = (mc_trop - ayan) % 360.0
    sign_start = math.floor(asc / 30.0) * 30.0
    cusps = [(sign_start + i * 30.0) % 360.0 for i in range(12)]
    return {
        "system": "Whole sign",
        "cusps": cusps,
        "ascendant": asc,
        "mc": mc,
        "ayanamsa": ayan,
    }


def weekday_name(jd_ut: float) -> str:
    dt = datetime(1970, 1, 1) + timedelta(seconds=(jd_ut - 2440587.5) * 86400.0)
    return dt.strftime("%A")
