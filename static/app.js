const SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"];
const GLYPH = {Sun:"☉",Moon:"☽",Mercury:"☿",Venus:"♀",Mars:"♂",Jupiter:"♃",Saturn:"♄",Rahu:"☊",Ketu:"☋",Lagna:"As"};

const state = {
  events: [],
  result: null,
  paths: [],
};

function $(id) { return document.getElementById(id); }

function toast(msg) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.remove(), 4200);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function pad(n) { return String(n).padStart(2, "0"); }

function eventWhen(e) {
  return `${e.year}-${pad(e.month)}-${pad(e.day)} ${pad(e.hour)}:${pad(e.minute)}`;
}

function renderEvents() {
  $("eventCount").textContent = state.events.length;
  const wrap = $("eventTable");
  if (!state.events.length) {
    wrap.className = "table-wrap empty-note";
    wrap.textContent = "No events yet. Load the earthquake sample or import JHora files.";
    return;
  }
  wrap.className = "table-wrap";
  wrap.innerHTML = `<table>
    <thead><tr><th>Name</th><th>Local time</th><th>Place</th><th>Source</th><th></th></tr></thead>
    <tbody>
      ${state.events.map((e, i) => `<tr>
        <td>${esc(e.name)}</td>
        <td>${eventWhen(e)} (UTC${e.tz_offset_hours >= 0 ? "+" : ""}${e.tz_offset_hours})</td>
        <td>${esc(e.city || "")} ${e.latitude.toFixed(2)}, ${e.longitude.toFixed(2)}</td>
        <td>${esc(e.source || "")}</td>
        <td><button class="linkish" data-del="${i}">Remove</button></td>
      </tr>`).join("")}
    </tbody>
  </table>`;
  wrap.querySelectorAll("[data-del]").forEach((btn) => {
    btn.onclick = () => {
      state.events.splice(Number(btn.dataset.del), 1);
      state.result = null;
      renderEvents();
      $("report").classList.add("hidden");
    };
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function mergeEvents(incoming) {
  const key = (e) => `${e.name}|${e.year}-${e.month}-${e.day}-${e.hour}-${e.minute}|${e.latitude}|${e.longitude}`;
  const have = new Set(state.events.map(key));
  let added = 0;
  for (const e of incoming) {
    if (!have.has(key(e))) {
      state.events.push(e);
      have.add(key(e));
      added += 1;
    }
  }
  renderEvents();
  return added;
}

function heatColor(v, max) {
  if (!max || !v) return "#2a261f";
  const t = v / max;
  const r = Math.round(42 + t * 160);
  const g = Math.round(38 + t * 90);
  const b = Math.round(31 + t * 20);
  return `rgb(${r},${g},${b})`;
}

function renderHeat(rows, keys, labelKeys) {
  const max = Math.max(1, ...rows.flatMap((r) => keys.map((k) => r[k] || 0)));
  const head = `<div class="heat-row"><div class="heat-cell heat-lab"></div>${labelKeys.map((k) => `<div class="heat-cell heat-lab">${esc(k)}</div>`).join("")}</div>`;
  const body = rows.map((r) => {
    const cells = keys.map((k) => {
      const v = r[k] || 0;
      return `<div class="heat-cell" style="background:${heatColor(v, max)}" title="${v}">${v || ""}</div>`;
    }).join("");
    return `<div class="heat-row"><div class="heat-cell heat-lab">${esc(r.body)}</div>${cells}</div>`;
  }).join("");
  return `<div class="heat">${head}${body}</div>`;
}

function southIndianSvg(chart) {
  const lagna = chart.lagna.sign_index;
  const bySign = Array.from({ length: 12 }, () => []);
  for (const name of ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]) {
    bySign[chart.bodies[name].sign_index].push(GLYPH[name] || name[0]);
  }
  const cells = [
    [11, 0, 0], [0, 1, 0], [1, 2, 0], [2, 3, 0],
    [10, 0, 1], null, null, [3, 3, 1],
    [9, 0, 2], null, null, [4, 3, 2],
    [8, 0, 3], [7, 1, 3], [6, 2, 3], [5, 3, 3],
  ];
  let shapes = "";
  cells.forEach((cell) => {
    if (!cell) return;
    const [sign, col, row] = cell;
    const x = col * 100;
    const y = row * 100;
    const isLagna = sign === lagna;
    shapes += `<rect x="${x}" y="${y}" width="100" height="100" fill="${isLagna ? "#2a2418" : "#1b1814"}" stroke="#3a342b"/>`;
    shapes += `<text x="${x + 50}" y="${y + 22}" text-anchor="middle" fill="${isLagna ? "#c9a36a" : "#9c9484"}" font-size="12">${SIGNS[sign].slice(0, 3)}${isLagna ? " As" : ""}</text>`;
    shapes += `<text x="${x + 50}" y="${y + 58}" text-anchor="middle" fill="#c9a36a" font-size="14">${bySign[sign].join(" ")}</text>`;
  });
  return `<svg class="wheel" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">${shapes}</svg>`;
}

function listBlock(title, rows, nameKey = "name") {
  if (!rows || !rows.length) return "";
  return `<div class="panel"><h2>${title}</h2>${rows.map((r) =>
    `<div class="finding"><span>${esc(r[nameKey] || r.label || r.value)}</span><span>${r.share}%</span><span>${r.count}</span></div>`
  ).join("")}</div>`;
}

function renderReport() {
  const box = $("report");
  const { analysis, charts } = state.result;
  const name = $("studyName").value || "Study";
  const ranked = (analysis.all_findings || []).slice(0, 12);
  const threshold = Number($("minShare").value) * 100;
  box.classList.remove("hidden");
  box.innerHTML = `
    <div class="panel">
      <h2>${esc(name)}</h2>
      <div class="stat-row">
        <div class="stat"><div class="n">${analysis.n}</div><div class="l">Event charts</div></div>
        <div class="stat"><div class="n">${analysis.common.length}</div><div class="l">Repeating factors ≥ threshold</div></div>
        <div class="stat"><div class="n">${analysis.dashas[0] ? analysis.dashas[0].name : "—"}</div><div class="l">Most common mahadasha</div></div>
        <div class="stat"><div class="n">${charts[0].ephemeris.split("+")[0].trim()}</div><div class="l">Ephemeris</div></div>
      </div>
      <div class="narrative">${analysis.narrative.map((p) => `<p>${esc(p)}</p>`).join("")}</div>
    </div>
    <div class="findings">
      <div class="panel">
        <h2>Strongest common points</h2>
        ${ranked.map((f) => `<div>
          <div class="finding"><span class="${f.share >= threshold ? "hot" : ""}">${esc(f.label)}</span><span>${f.share}%</span><span>lift ${f.lift}</span></div>
          <div class="bar"><span style="width:${Math.min(f.share, 100)}%"></span></div>
        </div>`).join("") || "<p class='hint'>Not enough repetition to rank.</p>"}
      </div>
      ${listBlock("Yogas & flags", analysis.yogas)}
    </div>
    <div class="panel">
      <h2>Planet × sign occupancy</h2>
      <p class="hint">Cell = how many events have that body in that sidereal sign. Lagna is the first house cusp sign.</p>
      ${renderHeat(analysis.heatmap_signs, SIGNS, SIGNS.map((s) => s.slice(0, 3)))}
    </div>
    <div class="panel">
      <h2>Planet × whole-sign house</h2>
      <p class="hint">House 1 is Lagna. Traditional earthquake research often watches 4, 8, and the nodes.</p>
      ${renderHeat(analysis.heatmap_houses, [...Array(12)].map((_, i) => String(i + 1)), [...Array(12)].map((_, i) => String(i + 1)))}
    </div>
    <div class="two-col">
      ${listBlock("Rahu–Ketu axis", analysis.node_axis)}
      ${listBlock("Conjunctions (8°)", analysis.conjunctions)}
      ${listBlock("In dusthana (6/8/12)", analysis.dusthana)}
      ${listBlock("Aspecting Lagna", analysis.aspect_lagna)}
      ${listBlock("Weekday", analysis.weekdays)}
      ${listBlock("Retrograde at event", analysis.retrogrades)}
    </div>
    <div class="panel">
      <h2>Each event chart</h2>
      <div class="chart-grid">
        ${charts.map((ch) => {
          const e = ch.event;
          const core = ["Lagna","Sun","Moon","Mars","Saturn","Rahu","Ketu","Jupiter"];
          const chips = core.map((n) => {
            if (n === "Lagna") return `<span class="chip">As ${ch.lagna.sign} ${ch.lagna.dms}</span>`;
            const b = ch.bodies[n];
            return `<span class="chip">${GLYPH[n] || n} ${b.sign} H${b.house}${b.retrograde ? " R" : ""}</span>`;
          }).join("");
          return `<article class="wheel-card">
            <h3>${esc(e.name)}</h3>
            <div class="meta">${eventWhen(e)} · ${esc(e.city || "")} · ${esc(e.notes || "")}<br/>Moon dasha: ${ch.dasha.mahadasha} · ${ch.weekday}</div>
            ${southIndianSvg(ch)}
            <div class="chips">${chips}</div>
          </article>`;
        }).join("")}
      </div>
      <p class="footnote">South Indian chart. Each event was typed into Jagannatha Hora 7.66 and the positions were copied from that program. Signs stay fixed; the box marked As is Lagna.</p>
    </div>
  `;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function refreshProjects(selectId) {
  const list = $("projectList");
  if (!list) return;
  try {
    const data = await api("/api/projects");
    const projects = data.projects || [];
    list.innerHTML = projects.length
      ? projects.map((p) => `<option value="${esc(p.id)}">${esc(p.name)} (${p.event_count})</option>`).join("")
      : `<option value="">None saved yet</option>`;
    if (selectId) list.value = selectId;
  } catch (err) {
    toast(err.message);
  }
}

async function saveProject() {
  if (!state.events.length) {
    toast("Add events before saving a project.");
    return;
  }
  const name = $("studyName").value.trim() || "Untitled study";
  $("btnSave").disabled = true;
  try {
    const saved = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        min_share: Number($("minShare").value),
        events: state.events,
        charts: state.result ? state.result.charts : null,
        analysis: state.result ? state.result.analysis : null,
      }),
    });
    await refreshProjects(saved.id);
    const withReport = state.result ? " with its JHora report" : "";
    toast(`Saved “${saved.name}”${withReport}.`);
  } catch (err) {
    toast(err.message);
  } finally {
    $("btnSave").disabled = false;
  }
}

async function openProject() {
  const id = $("projectList").value;
  if (!id) {
    toast("No saved project to open.");
    return;
  }
  try {
    const data = await api("/api/projects/" + encodeURIComponent(id));
    $("studyName").value = data.name || "";
    if (data.min_share != null) {
      const share = Number(data.min_share).toFixed(2);
      if ([...$("minShare").options].some((option) => option.value === share)) {
        $("minShare").value = share;
      }
    }
    state.events = data.events || [];
    state.result = data.charts ? { charts: data.charts, analysis: data.analysis } : null;
    renderEvents();
    if (state.result) renderReport();
    else {
      $("report").classList.add("hidden");
      $("report").innerHTML = "";
    }
    toast(`Opened “${data.name}”.`);
  } catch (err) {
    toast(err.message);
  }
}

async function analyze() {
  if (state.events.length < 2) {
    toast("Add at least two events.");
    return;
  }
  $("btnAnalyze").disabled = true;
  $("btnAnalyze").textContent = "Reading Jagannatha Hora…";
  try {
    state.result = await api("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        events: state.events,
        min_share: Number($("minShare").value),
      }),
    });
    renderReport();
  } catch (err) {
    toast(err.message);
  } finally {
    $("btnAnalyze").disabled = false;
    $("btnAnalyze").textContent = "Analyze similarities";
  }
}

async function boot() {
  renderEvents();
  try {
    const h = await api("/api/health");
    const pref = h.jhora_preferences || {};
    const saved = pref.found
      ? `JHora saved setup: ${pref.siddhanta}; ayanamsa ${pref.ayanamsa}; ${pref.chart_style}`
      : "JHora preferences file not found";
    $("health").innerHTML = `${h.jhora_detected ? "Jagannatha Hora is installed" : "JHora not found"}<br/>${esc(saved)}<br/>This app: ${esc(h.fars_chart)}, ${esc(h.fars_ayanamsa)}. ${esc(h.fars_positions)}.`;
    const p = await api("/api/jhora-paths");
    state.paths = p.paths;
    const known = p.paths.find((x) => x.exists);
    if (known) $("folderPath").value = known.path;
  } catch (err) {
    $("health").textContent = "Server not ready: " + err.message;
  }

  $("btnEarthquakes").onclick = async () => {
    const data = await api("/api/samples/earthquakes");
    state.events = [];
    const n = mergeEvents(data.events);
    toast(`Loaded ${n} recent magnitude 6+ earthquakes.`);
  };
  $("btnLatest").onclick = async () => {
    try {
      const data = await api("/api/latest-study");
      state.events = data.charts.map((chart) => chart.event);
      state.result = data;
      renderEvents();
      renderReport();
    } catch (err) {
      toast(err.message);
    }
  };
  $("btnScan").onclick = async () => {
    const p = await api("/api/jhora-paths");
    let total = 0;
    for (const row of p.paths.filter((x) => x.exists && x.jhd_count)) {
      const data = await api("/api/scan-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder: row.path, recursive: true }),
      });
      total += mergeEvents(data.events);
    }
    toast(`Imported ${total} JHora charts from local folders.`);
  };
  $("btnScanCustom").onclick = async () => {
    const folder = $("folderPath").value.trim();
    if (!folder) return;
    const data = await api("/api/scan-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder, recursive: true }),
    });
    const n = mergeEvents(data.events);
    toast(`Imported ${n} charts from folder.`);
  };
  $("jhdFiles").onchange = async (ev) => {
    const files = ev.target.files;
    if (!files.length) return;
    const fd = new FormData();
    [...files].forEach((f) => fd.append("files", f));
    const data = await api("/api/parse-jhd", { method: "POST", body: fd });
    mergeEvents(data.events);
    if (data.errors?.length) toast(data.errors[0].error);
    ev.target.value = "";
  };
  $("csvFile").onchange = async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const data = await api("/api/parse-csv", { method: "POST", body: fd });
      mergeEvents(data.events);
      toast(`Imported ${data.count} CSV rows.`);
    } catch (err) {
      toast(err.message);
    }
    ev.target.value = "";
  };
  $("manualForm").onsubmit = (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const num = (k, d = 0) => Number(fd.get(k) ?? d);
    mergeEvents([{
      name: String(fd.get("name")),
      year: num("year"),
      month: num("month"),
      day: num("day"),
      hour: num("hour"),
      minute: num("minute"),
      second: 0,
      tz_offset_hours: num("tz_offset_hours", 0),
      latitude: num("latitude"),
      longitude: num("longitude"),
      city: String(fd.get("city") || ""),
      country: "",
      notes: "",
      source: "manual",
      path: "",
    }]);
    ev.target.reset();
  };
  $("btnAnalyze").onclick = analyze;
  $("btnSave").onclick = saveProject;
  $("btnOpen").onclick = openProject;
  $("btnPrint").onclick = () => window.print();
  refreshProjects();
  $("btnClear").onclick = () => {
    state.events = [];
    state.result = null;
    renderEvents();
    $("report").classList.add("hidden");
  };
  $("btnExportJhd").onclick = async () => {
    if (!state.events.length) return;
    const data = await api("/api/export-jhd", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: state.events }),
    });
    for (const f of data.files) {
      const blob = new Blob([f.content], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = f.name.replace(/[^\w.\- ]+/g, "_");
      a.click();
    }
    toast("Downloaded .jhd files you can open in Jagannatha Hora.");
  };
}

boot();
