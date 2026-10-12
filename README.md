# FARS — Event Chart Concordance

FARS compares many event charts and ranks what they have in common: signs, nakshatras, whole-sign houses, yogas, the Rahu–Ketu axis, weekdays, and conjunctions.

It does not calculate the sky itself. For each event it opens **Jagannatha Hora 7.66** on this Windows PC, types the date, time, and place into JHora’s Birthdata window, and reads the chart text that JHora copies to the clipboard. Those printed positions are the source of truth. The report then counts which factors repeat.

This is a concordance tool. It does not claim that planets cause earthquakes or markets. Lift in the report is a ranking against a uniform baseline, not a proof.

A saved project can be opened on another machine as a finished report. Casting new dates still needs Jagannatha Hora 7.66 on Windows.

## What a teammate needs

- Windows, with the desktop unlocked while a new study is running.
- [Jagannatha Hora 7.66](https://www.vedicastrologer.org/jh/) installed. Do not upgrade it. If an update dialog appears, choose No or Cancel. Never run `jh_update_auto.exe`.
- Python 3.12.
- The launch shortcut in `app/jhora_bot.py`. On this machine it is:

  `C:\Users\ychuk\Documents\Jagannath hora\3. Launch\Jagannatha Hora.lnk`

  That shortcut starts `C:\Program Files (x86)\Jagannatha Hora\bin\jhora.exe`. On another PC, change `SHORTCUT` to that PC’s shortcut. If JHora is already open, FARS attaches to that window and does not use the shortcut.

JHora’s own settings are kept. This copy prints the ayanamsa it is configured for (currently the Galaxy-center ayanamsa, about 22°54′) and draws the report as a South Indian chart. FARS does not rewrite `jhora.ini`.

## Run

```bat
python -m pip install -r requirements.txt
python -m pip install pywinauto pywin32
python run.py
```

Or double-click `run.bat` after those packages are installed.

Then open [http://127.0.0.1:8787](http://127.0.0.1:8787).

Leave the JHora window alone while **Analyze similarities** is running. Twenty charts takes several minutes. Covering or closing JHora mid-run can spoil the chart being typed.

## Using the screen

1. Name the study.
2. Load events. **Load 20 recent M6+ quakes** uses USGS times in UTC. You can also add one event, import a CSV, open `.jhd` files, or scan a folder of saved JHora charts.
3. Click **Analyze similarities**. FARS types each event into JHora and ranks the repeats. The highlight threshold defaults to 25%.
4. Click **Save project** to store the events and, when a report is already on screen, the JHora charts. **Open a saved project** brings that file back without recasting.
5. **Export as .jhd** writes date, time, and place files that JHora can open. Those files do not contain planet positions.
6. **Print / PDF report** prints the page. The side panel is hidden in print.

CSV columns: `name,date,time,tz,lat,lon,city,country,notes`. Timezone is hours from UTC (India is `5.5`, UTC is `0`). Latitude is north-positive. Longitude is east-positive.

## Sections of the code

| Path | What it does |
| --- | --- |
| `run.py`, `run.bat` | Start the local server at `http://127.0.0.1:8787`. |
| `app/main.py` | The HTTP API: health, analyze, import `.jhd` and CSV, export `.jhd`, scan folders, and save or open a project. |
| `app/jhora_bot.py` | The engine. Launches JHora 7.66, fills Birthdata, copies “basic calculations,” and parses Lagna, planets, nakshatras, weekday, and the ayanamsa text. It refuses an update dialog. |
| `app/analysis.py` | Counts repeats across the charts JHora returned. Builds the narrative, heatmaps, yoga flags, node axis, and weekday totals. |
| `app/vedic.py` | Classifies positions that are already known: signs, nakshatras, whole-sign houses, dignity, conjunctions, aspects, and yogas. Whole-sign house is taken from JHora’s Lagna sign. |
| `app/jhd.py` | Reads and writes Jagannatha Hora `.jhd` files. A `.jhd` file is only a name, date, time, timezone, and place. |
| `app/samples.py` | The event lists. `sample_events()` returns the 20 recent magnitude 6+ quakes. An older century list, `EARTHQUAKES`, is still in the file and is not what the button loads. |
| `static/index.html`, `static/app.js`, `static/styles.css` | The research page. Charts are drawn as a South Indian grid: signs stay fixed, and the box marked As is Lagna. |
| `projects/` | Saved studies. One JSON file per study name. Saving the same name again updates that file. |
| `recent-m6-earthquakes.json` | The USGS rows used as input: time in UTC, magnitude, latitude, longitude, depth, and place. |
| `recent-quake-study.json` | The 20-chart report already read from JHora. **Show saved JHora report** loads this file. |
| `run_recent_study.py` | The one-off script that typed those 20 quakes into JHora and wrote `recent-quake-study.json`. |

`app/ephemeris.py` is an older sky calculator (Astronomy Engine and a Sri Surya Siddhanta ayanamsa). **Analyze** does not call it. Do not use it as a second source of planet positions.

Vimshottari mahadasha is not in JHora’s “Copy basic calculations” text, so the dasha section of a new report stays empty.

## Saved example

`projects/Recent-magnitude-6-earthquakes.json` is the study of 20 magnitude 6+ earthquakes from 24 July 2026 through 25 September 2026. Open it from **Open a saved project**. Jupiter, Saturn, and Ketu repeat in every chart because those bodies barely move across two months. Faster bodies, and the houses, vary with the Lagna.
