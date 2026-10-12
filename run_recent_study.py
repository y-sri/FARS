"""Type the 20 recent USGS earthquakes into Jagannatha Hora and save the report."""

import json
from pathlib import Path

from app.analysis import analyze_charts
from app.jhora_bot import read_chart
from app.samples import sample_events

OUT = Path(__file__).resolve().parent / "recent-quake-study.json"


def main() -> None:
    events = sample_events()
    charts = []
    for index, event in enumerate(events, start=1):
        print(f"[{index}/20] {event['name']}", flush=True)
        chart = read_chart(event)
        charts.append(chart)
        lagna = chart["lagna"]
        print(
            f"    Lagna {lagna['sign']} {lagna['dms']}  {chart['weekday']}  ayanamsa {chart['ayanamsa_text']}",
            flush=True,
        )
    result = {"charts": charts, "analysis": analyze_charts(charts, min_share=0.25)}
    OUT.write_text(json.dumps(result), encoding="utf-8")
    print("SAVED", OUT, flush=True)
    for line in result["analysis"]["narrative"]:
        print(line, flush=True)


if __name__ == "__main__":
    main()
