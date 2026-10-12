"""FARS local research server."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analysis import run_study
from .jhora_bot import read_chart
from .jhd import ChartEvent, parse_jhd_text, scan_jhd_folder, write_jhd
from .samples import sample_events

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

DEFAULT_JHORA_PATHS = [
    r"C:\Program Files (x86)\Jagannatha Hora\data",
    r"C:\Users\ychuk\Documents\Jagannath hora",
]

app = FastAPI(title="FARS", version="1.0.0")


class EventIn(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    second: int = 0
    tz_offset_hours: float = 0.0
    longitude: float
    latitude: float
    city: str = ""
    country: str = ""
    notes: str = ""
    source: str = "manual"
    path: str = ""


class StudyRequest(BaseModel):
    events: list[EventIn]
    min_share: float = Field(0.35, ge=0.1, le=1.0)


class ScanRequest(BaseModel):
    folder: str
    recursive: bool = True


class ExportRequest(BaseModel):
    events: list[EventIn]


class ProjectIn(BaseModel):
    name: str = "Untitled study"
    min_share: float = 0.25
    events: list[EventIn]
    charts: list[dict[str, Any]] | None = None
    analysis: dict[str, Any] | None = None


_AYANAMSA_BY_INDEX = {
    0: "True Lahiri / Chitrapaksha",
    1: "Traditional Lahiri",
    2: "Pushya-paksha",
    3: "Raman",
    4: "Krishnamurti (KP)",
    5: "Custom fixed star",
    6: "Jagannatha",
    7: "Rohini-paksha",
    8: "Sri Surya Siddhanta",
    18: "Galaxy center at 0° Sagittarius",
    21: "Tropical",
}
_SIDDHANTA_BY_INDEX = {
    0: "Drik (modern planetarium positions)",
    1: "Sri Surya Siddhanta, generalized Makaranda (Vinay Jha)",
}
_CHART_STYLE_BY_INDEX = {
    0: "South Indian regular",
    1: "South Indian irregular",
    2: "North Indian",
}
_JHORA_INI = Path(
    r"C:\Users\ychuk\AppData\Local\VirtualStore\Program Files (x86)\Jagannatha Hora\jhcore\jhora.ini"
)


def _ini_int(text: str, key: str):
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            try:
                return int(line.split("=", 1)[1].strip().split()[0])
            except ValueError:
                return None
    return None


def jhora_preferences() -> dict:
    if not _JHORA_INI.exists():
        return {"found": False}
    text = _JHORA_INI.read_text(encoding="utf-8", errors="ignore")
    ayan = _ini_int(text, "UserSelectedAyanamsa")
    siddhanta = _ini_int(text, "Siddhanta")
    style = _ini_int(text, "ChartStyle")
    return {
        "found": True,
        "path": str(_JHORA_INI),
        "ayanamsa_index": ayan,
        "ayanamsa": _AYANAMSA_BY_INDEX.get(ayan, f"index {ayan}"),
        "siddhanta_index": siddhanta,
        "siddhanta": _SIDDHANTA_BY_INDEX.get(siddhanta, f"index {siddhanta}"),
        "chart_style_index": style,
        "chart_style": _CHART_STYLE_BY_INDEX.get(style, f"index {style}"),
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "ephemeris": "Jagannatha Hora 7.66",
        "jhora_detected": Path(r"C:\Program Files (x86)\Jagannatha Hora\bin\jhora.exe").exists(),
        "jhora_preferences": jhora_preferences(),
        "fars_ayanamsa": "Whatever JHora 7.66 is set to",
        "fars_positions": "Read from Jagannatha Hora after typing the event into its Birthdata screen",
        "fars_chart": "South Indian",
    }


@app.get("/api/jhora-paths")
def jhora_paths():
    rows = []
    for p in DEFAULT_JHORA_PATHS:
        path = Path(p)
        count = len(list(path.glob("**/*.jhd"))) if path.exists() else 0
        rows.append({"path": p, "exists": path.exists(), "jhd_count": count})
    return {"paths": rows}


STUDY_FILE = ROOT / "recent-quake-study.json"
PROJECTS = ROOT / "projects"


def _project_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\- ]+", "", name).strip()
    slug = re.sub(r"\s+", "-", cleaned)[:80].strip("-")
    return slug or "project"


@app.get("/api/samples/earthquakes")
def earthquakes():
    return {"events": sample_events()}


@app.get("/api/latest-study")
def latest_study():
    if not STUDY_FILE.exists():
        raise HTTPException(404, "No Jagannatha Hora study has been saved yet.")
    return json.loads(STUDY_FILE.read_text(encoding="utf-8"))


@app.get("/api/projects")
def list_projects():
    PROJECTS.mkdir(exist_ok=True)
    rows = []
    for path in sorted(PROJECTS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "id": path.stem,
                "name": data.get("name") or path.stem,
                "saved_at": data.get("saved_at"),
                "event_count": len(data.get("events") or []),
                "has_report": bool(data.get("charts")),
            }
        )
    return {"projects": rows}


@app.post("/api/projects")
def save_project(req: ProjectIn):
    if not req.events:
        raise HTTPException(400, "Add events before saving a project.")
    PROJECTS.mkdir(exist_ok=True)
    name = req.name.strip() or "Untitled study"
    path = PROJECTS / f"{_project_slug(name)}.json"
    saved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "name": name,
        "min_share": req.min_share,
        "saved_at": saved_at,
        "events": [e.model_dump() for e in req.events],
        "charts": req.charts,
        "analysis": req.analysis,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"id": path.stem, "name": name, "saved_at": saved_at}


@app.get("/api/projects/{project_id}")
def load_project(project_id: str):
    if not re.fullmatch(r"[\w\-]+", project_id):
        raise HTTPException(400, "Unknown project.")
    path = PROJECTS / f"{project_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Project not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/scan-folder")
def scan_folder(req: ScanRequest):
    try:
        events = scan_jhd_folder(req.folder, recursive=req.recursive)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@app.post("/api/parse-jhd")
async def parse_jhd(files: list[UploadFile] = File(...)):
    events = []
    errors = []
    for f in files:
        raw = await f.read()
        try:
            text = raw.decode("utf-8", errors="ignore")
            name = Path(f.filename or "chart").stem
            events.append(parse_jhd_text(text, name=name).to_dict())
        except Exception as exc:  # noqa: BLE001
            errors.append({"file": f.filename, "error": str(exc)})
    return {"events": events, "errors": errors}


@app.post("/api/parse-csv")
async def parse_csv(file: UploadFile = File(...)):
    text = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    events = []
    for i, row in enumerate(reader, start=1):
        def g(*keys, default=""):
            for k in keys:
                if k in row and row[k] not in (None, ""):
                    return row[k]
            return default

        try:
            date = g("date", "Date")
            time = g("time", "Time", default="00:00:00")
            if date and "-" in date:
                y, mo, d = [int(x) for x in date.split("-")[:3]]
            elif date and "/" in date:
                parts = [int(x) for x in date.split("/")]
                if parts[2] > 31:
                    mo, d, y = parts[0], parts[1], parts[2]
                else:
                    d, mo, y = parts[0], parts[1], parts[2]
            else:
                y = int(g("year", "Year"))
                mo = int(g("month", "Month"))
                d = int(g("day", "Day"))
            th, tm, *rest = (time + ":0:0").split(":")
            sec = int(float(rest[0])) if rest else 0
            events.append(
                ChartEvent(
                    name=g("name", "Name", "event", default=f"Event {i}"),
                    year=y,
                    month=mo,
                    day=d,
                    hour=int(th),
                    minute=int(tm),
                    second=sec,
                    tz_offset_hours=float(g("tz", "timezone", "tz_offset_hours", default="0")),
                    longitude=float(g("lon", "longitude", "Longitude")),
                    latitude=float(g("lat", "latitude", "Latitude")),
                    city=g("city", "City"),
                    country=g("country", "Country"),
                    notes=g("notes", "Notes", "magnitude"),
                    source="csv",
                ).to_dict()
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"CSV row {i}: {exc}") from exc
    return {"events": events, "count": len(events)}


@app.post("/api/chart")
def one_chart(event: EventIn):
    return {"chart": read_chart(event.model_dump())}


@app.post("/api/analyze")
def analyze(req: StudyRequest):
    if len(req.events) < 2:
        raise HTTPException(400, "Need at least two events to compare.")
    payload = [e.model_dump() for e in req.events]
    return run_study(payload, min_share=req.min_share)


@app.post("/api/export-jhd")
def export_jhd(req: ExportRequest):
    files = []
    for e in req.events:
        ev = ChartEvent(**e.model_dump())
        files.append({"name": f"{ev.name}.jhd", "content": write_jhd(ev)})
    return {"files": files}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
