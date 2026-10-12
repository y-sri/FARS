# FARS — Event Chart Concordance

Research desk for comparing Vedic event charts across many dates. It reads the date, time, and place from Jagannatha Hora `.jhd` files, casts South Indian charts with the Sri Surya Siddhanta ayanamsa, and ranks repeating factors: signs, houses, nakshatras, yogas, nodes, and dashas.

This is a concordance tool. It does not claim that planets cause earthquakes or markets.

## Run

Jagannatha Hora is expected at `C:\Program Files (x86)\Jagannatha Hora`.

```bat
run.bat
```

Or:

```bat
python -m pip install -r requirements.txt
python run.py
```

Then open [http://127.0.0.1:8787](http://127.0.0.1:8787).

## Typical study

1. Click **Load 20 earthquake dates** (or import your own `.jhd` / CSV).
2. Optionally **Scan JHora folders** to pull charts already saved in JHora.
3. Set the repeat threshold and click **Analyze similarities**.
4. Print the report, or **Export as .jhd** to inspect the same events inside Jagannatha Hora.

CSV columns: `name,date,time,tz,lat,lon,city,country,notes`. Timezone is hours from UTC (IST = `5.5`).

## Chart settings

- Chart drawing: South Indian. Signs are fixed; the box marked As is Lagna.
- Ayanamsa: Sri Surya Siddhanta (zero near 21 March 499 CE).
- Planet longitudes: modern geocentric positions, then the ayanamsa is subtracted.
- A `.jhd` file holds date, time, and place only. Vinay Jha's generalized Makaranda longitudes are calculated inside Jagannatha Hora and are not written into that file.

JHora remains the place for Vargas, ashtakavarga, and custom ayanamsa experiments.
