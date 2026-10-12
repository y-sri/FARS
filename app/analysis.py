"""Concordance analysis across a set of Vedic event charts."""

from __future__ import annotations

from collections import Counter, defaultdict
from math import log

from .vedic import CORE_PLANETS, SIGNS

RESEARCH_BODIES = CORE_PLANETS + ["Lagna"]


def _chi_square(observed: list[int], expected_p: list[float] | None = None) -> dict:
    n = sum(observed)
    k = len(observed)
    if n == 0:
        return {"chi2": 0.0, "df": k - 1, "lift_max": 0.0}
    if expected_p is None:
        expected_p = [1.0 / k] * k
    chi2 = 0.0
    lifts = []
    for o, p in zip(observed, expected_p):
        e = n * p
        if e > 0:
            chi2 += (o - e) ** 2 / e
            lifts.append(o / e)
        else:
            lifts.append(0.0)
    return {
        "chi2": round(chi2, 3),
        "df": k - 1,
        "lift_max": round(max(lifts) if lifts else 0.0, 3),
        "n": n,
    }


def _factor_label(kind: str, subject: str, key) -> str:
    if kind == "house":
        return f"{subject} in house {key}"
    if kind in {"sign", "nakshatra"}:
        return f"{subject} in {key}"
    return f"{subject} {kind} {key}"


def _pct(count: int, n: int) -> float:
    return round(100.0 * count / n, 1) if n else 0.0


def _entropy(counts: list[int]) -> float:
    n = sum(counts)
    if n == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c:
            p = c / n
            h -= p * log(p, 2)
    return round(h, 3)


def analyze_charts(charts: list[dict], min_share: float = 0.35) -> dict:
    n = len(charts)
    if n == 0:
        raise ValueError("No charts to analyze")

    sign_counts: dict[str, Counter] = defaultdict(Counter)
    house_counts: dict[str, Counter] = defaultdict(Counter)
    nak_counts: dict[str, Counter] = defaultdict(Counter)
    dignity_counts: dict[str, Counter] = defaultdict(Counter)
    yoga_counts: Counter = Counter()
    dasha_counts: Counter = Counter()
    weekday_counts: Counter = Counter()
    retro_counts: Counter = Counter()
    conj_counts: Counter = Counter()
    aspect_to_lagna: Counter = Counter()
    planet_in_dusthana: Counter = Counter()
    planet_in_kendra: Counter = Counter()
    node_axis: Counter = Counter()

    for ch in charts:
        weekday_counts[ch["weekday"]] += 1
        if ch["dasha"].get("mahadasha"):
            dasha_counts[ch["dasha"]["mahadasha"]] += 1
        for y in ch["yogas"]:
            yoga_counts[y] += 1
        lagna_sign = ch["lagna"]["sign"]
        sign_counts["Lagna"][lagna_sign] += 1
        nak_counts["Lagna"][ch["lagna"]["nakshatra"]] += 1
        rahu_sign = ch["bodies"]["Rahu"]["sign"]
        ketu_sign = ch["bodies"]["Ketu"]["sign"]
        node_axis[f"{rahu_sign} — {ketu_sign}"] += 1
        for name in CORE_PLANETS:
            b = ch["bodies"][name]
            sign_counts[name][b["sign"]] += 1
            house_counts[name][b["house"]] += 1
            nak_counts[name][b["nakshatra"]] += 1
            dignity_counts[name][b["dignity"]] += 1
            if b["retrograde"]:
                retro_counts[name] += 1
            if b["house"] in {6, 8, 12}:
                planet_in_dusthana[name] += 1
            if b["house"] in {1, 4, 7, 10}:
                planet_in_kendra[name] += 1
        for c in ch["conjunctions"]:
            pair = "–".join(sorted([c["a"], c["b"]]))
            conj_counts[pair] += 1
        for asp in ch["aspects"]:
            if asp["to_house"] == 1:
                aspect_to_lagna[asp["from"]] += 1

    def ranked_factor(kind: str, subject: str, counter: Counter, universe: int) -> list[dict]:
        rows = []
        for key, count in counter.most_common():
            share = count / n
            expected = n / universe
            lift = count / expected if expected else 0
            rows.append(
                {
                    "kind": kind,
                    "subject": subject,
                    "value": str(key),
                    "count": count,
                    "share": round(share * 100, 1),
                    "lift": round(lift, 2),
                    "label": _factor_label(kind, subject, key),
                }
            )
        return rows

    findings: list[dict] = []
    for body in RESEARCH_BODIES:
        findings.extend(ranked_factor("sign", body, sign_counts[body], 12))
        if body != "Lagna":
            findings.extend(ranked_factor("house", body, house_counts[body], 12))
        findings.extend(ranked_factor("nakshatra", body, nak_counts[body], 27))

    for pair, count in conj_counts.most_common():
        findings.append(
            {
                "kind": "conjunction",
                "subject": pair,
                "value": "conjunction",
                "count": count,
                "share": _pct(count, n),
                "lift": round(count / max(n * 0.15, 1), 2),
                "label": f"{pair} conjunction",
            }
        )
    for yoga, count in yoga_counts.most_common():
        findings.append(
            {
                "kind": "yoga",
                "subject": yoga,
                "value": yoga,
                "count": count,
                "share": _pct(count, n),
                "lift": round(count / max(n * 0.2, 1), 2),
                "label": yoga,
            }
        )
    for lord, count in dasha_counts.most_common():
        findings.append(
            {
                "kind": "dasha",
                "subject": "Mahadasha",
                "value": lord,
                "count": count,
                "share": _pct(count, n),
                "lift": round((count / n) / (1 / 9), 2),
                "label": f"Vimshottari mahadasha of {lord}",
            }
        )

    findings.sort(key=lambda r: (-r["share"], -r["lift"], -r["count"]))
    common = [f for f in findings if f["share"] >= min_share * 100 and f["count"] >= max(2, int(n * 0.25))]

    heat_signs = []
    for body in RESEARCH_BODIES:
        row = {"body": body}
        for s in SIGNS:
            row[s] = sign_counts[body][s]
        heat_signs.append(row)

    heat_houses = []
    for body in CORE_PLANETS:
        row = {"body": body}
        for h in range(1, 13):
            row[str(h)] = house_counts[body][h]
        heat_houses.append(row)

    sign_stats = {}
    for body in RESEARCH_BODIES:
        obs = [sign_counts[body][s] for s in SIGNS]
        sign_stats[body] = {**_chi_square(obs), "entropy": _entropy(obs)}

    narrative = _narrative(n, findings, common, sign_stats, yoga_counts, dasha_counts, node_axis, min_share)

    return {
        "n": n,
        "min_share": min_share,
        "common": common[:40],
        "all_findings": findings[:200],
        "heatmap_signs": heat_signs,
        "heatmap_houses": heat_houses,
        "sign_stats": sign_stats,
        "yogas": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in yoga_counts.most_common(20)],
        "dashas": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in dasha_counts.most_common()],
        "weekdays": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in weekday_counts.most_common()],
        "retrogrades": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in retro_counts.most_common()],
        "conjunctions": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in conj_counts.most_common(15)],
        "dusthana": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in planet_in_dusthana.most_common()],
        "kendra": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in planet_in_kendra.most_common()],
        "node_axis": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in node_axis.most_common()],
        "aspect_lagna": [{"name": k, "count": v, "share": _pct(v, n)} for k, v in aspect_to_lagna.most_common()],
        "narrative": narrative,
    }


def _narrative(n, findings, common, sign_stats, yoga_counts, dasha_counts, node_axis, min_share) -> list[str]:
    lines = [
        f"Study size: {n} event charts read from Jagannatha Hora 7.66, whole-sign houses from the Lagna it calculated.",
    ]
    clustered = [b for b, st in sign_stats.items() if st["chi2"] > 18]
    if clustered:
        lines.append(
            "Sign occupancy is most uneven for "
            + ", ".join(clustered)
            + " (higher chi-square vs a uniform 12-sign baseline)."
        )
    top = [f for f in findings if f["count"] >= 2][:8]
    if top:
        bits = [f"{item['label']} ({item['share']}%)" for item in top]
        lines.append("Highest-frequency repeats: " + "; ".join(bits) + ".")
    if common:
        lines.append(f"{len(common)} factors reach the {int(min_share * 100)}% highlight threshold.")
    else:
        lines.append(
            f"No factor reached the {int(min_share * 100)}% highlight threshold. The ranking below is still the strongest repeat in this set."
        )
    if yoga_counts:
        y, c = yoga_counts.most_common(1)[0]
        lines.append(f"Most repeated yoga-like flag: {y} in {c} of {n} charts ({round(100*c/n,1)}%).")
    if dasha_counts:
        d, c = dasha_counts.most_common(1)[0]
        lines.append(f"Most common running mahadasha at the event: {d} ({round(100*c/n,1)}%).")
    if node_axis:
        axis, c = node_axis.most_common(1)[0]
        lines.append(f"Most common Rahu–Ketu axis: {axis} ({round(100*c/n,1)}%).")
    lines.append(
        "Lift is relative to a naive uniform baseline (12 signs / 12 houses / 27 nakshatras). "
        "It is a ranking aid, not a proof of causation. Earthquake geology is not claimed to be caused by planets."
    )
    return lines


def run_study(events: list[dict], min_share: float = 0.35) -> dict:
    from .jhora_bot import read_chart

    charts = [read_chart(ev) for ev in events]
    analysis = analyze_charts(charts, min_share=min_share)
    return {"charts": charts, "analysis": analysis}
