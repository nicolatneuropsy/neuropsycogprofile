/* ============================================================
   NeuroCogProfile frontend logic (vanilla JS, no framework, no CDN).

   Talks to Python through window.pywebview.api. All UI strings are
   bilingual via the T dictionary; the generated draft text is bilingual
   via the engine. Nothing is persisted unless the user explicitly saves
   a template or a session through a native file dialog.

   Data model notes:
   - Up to two data series (test-retest, with/without medication...):
     state.seriesLabels holds the labels, and every measure carries
     entries[si] = {value, metric} aligned with them.
   - Each domain carries an optional clinical note; a global note and
     the clinician name (report watermark) live at the top level.
   - The lexicon checklist matches administered sub-functions against
     the built-in bilingual definitions; each entry is editable and
     can be unchecked, and the whole section can be disabled.
   ============================================================ */

"use strict";

/* ---------- 0. Bilingual UI strings ------------------------- */

const T = {
  fr: {
    tagline: "Profil cognitif local et hors ligne",
    threshold_label: "Seuil force / faiblesse",
    tab_battery: "Batterie", tab_entry: "Saisie", tab_results: "Resultats",
    battery_title: "Composition de la batterie",
    battery_help: "Ajoutez, renommez et reordonnez les domaines et les sous-fonctions. Chaque nom possede une etiquette FR et EN; la langue affichee suit le bouton FR / EN.",
    load_template: "Charger un modele", save_template: "Enregistrer le modele",
    add_domain: "+ Ajouter un domaine", addon_label: "Domaines optionnels",
    add_addon: "Inserer", add_measure: "+ Sous-fonction",
    new_domain: "Nouveau domaine", new_measure: "Nouvelle sous-fonction",
    entry_title: "Saisie des scores",
    load_session: "Charger une session", save_session: "Enregistrer la session",
    pid_label: "Identifiant", pid_ph: "ex. AB-001",
    clinician_label: "Clinicien(ne)", clinician_ph: "ex. Nicola Thibault, PhD.",
    pid_warning: "N'inscrivez pas le nom complet ni d'autres renseignements identifiants. Rien n'est enregistre tant que vous n'enregistrez pas explicitement une session. Le nom du clinicien apparait en bas du rapport.",
    series_title: "Series",
    series_add: "+ Ajouter une serie (retest)",
    series_remove: "Retirer la serie 2",
    series_help: "Deux series se superposent sur les memes graphiques (ex. avec / sans medication).",
    series_t1: "T1", series_t2: "T2",
    col_measure: "Sous-fonction", col_value: "Score", col_metric: "Type",
    compute: "Calculer le profil",
    results_title: "Profil et figures",
    mode_z: "Echelle z", mode_pct: "Percentile", summary_toggle: "Radar de synthese",
    copy_table: "Copier le tableau", export: "Exporter vers Word (.docx)",
    results_empty: "Aucun resultat. Saisissez des scores puis cliquez sur Calculer le profil.",
    col_series: "Serie",
    col_score: "Score saisi", col_pct: "Percentile", col_band: "Bande", col_marker: "Marqueur",
    domain_mean: "Moyenne du domaine",
    strength: "Force relative", weakness: "Faiblesse relative", within: "Dans la moyenne",
    note_label: "Notes cliniques (domaine)",
    note_ph: "Observations, justification des resultats...",
    global_note_title: "Note generale (facultative)",
    lexicon_title: "Lexique des fonctions evaluees",
    lexicon_help: "Cochez les definitions a inclure dans le rapport; le texte est modifiable.",
    lexicon_empty: "Aucune definition integree ne correspond aux fonctions administrees.",
    draft_title: "Texte interpretatif (brouillon, modifiable)",
    copy_image: "Copier l'image", download_svg: "SVG", theme_label: "Theme de couleur",
    saved_template: "Modele enregistre", loaded_template: "Modele charge",
    saved_session: "Session enregistree", loaded_session: "Session chargee",
    exported: "Rapport Word enregistre", copied_image: "Image copiee",
    copied_table: "Tableau copie", copy_failed: "Copie impossible dans cet environnement",
    compute_error: "Erreur de calcul", load_error: "Echec du chargement",
    confirm_del: "Supprimer ce domaine et ses donnees saisies ?",
  },
  en: {
    tagline: "Local, offline cognitive profile",
    threshold_label: "Strength / weakness threshold",
    tab_battery: "Battery", tab_entry: "Data entry", tab_results: "Results",
    battery_title: "Battery composition",
    battery_help: "Add, rename and reorder domains and sub-functions. Each name has an FR and an EN label; the one shown follows the FR / EN button.",
    load_template: "Load template", save_template: "Save template",
    add_domain: "+ Add domain", addon_label: "Optional domains",
    add_addon: "Insert", add_measure: "+ Sub-function",
    new_domain: "New domain", new_measure: "New sub-function",
    entry_title: "Score entry",
    load_session: "Load session", save_session: "Save session",
    pid_label: "Identifier", pid_ph: "e.g. AB-001",
    clinician_label: "Clinician", clinician_ph: "e.g. Nicola Thibault, PhD.",
    pid_warning: "Do not enter the full name or other identifying information. Nothing is saved unless you explicitly save a session. The clinician name appears at the bottom of the report.",
    series_title: "Series",
    series_add: "+ Add a series (retest)",
    series_remove: "Remove series 2",
    series_help: "Two series overlay on the same figures (e.g. with / without medication).",
    series_t1: "T1", series_t2: "T2",
    col_measure: "Sub-function", col_value: "Score", col_metric: "Metric",
    compute: "Compute profile",
    results_title: "Profile and figures",
    mode_z: "z scale", mode_pct: "Percentile", summary_toggle: "Summary radar",
    copy_table: "Copy table", export: "Export to Word (.docx)",
    results_empty: "No results yet. Enter scores then click Compute profile.",
    col_series: "Series",
    col_score: "Entered score", col_pct: "Percentile", col_band: "Band", col_marker: "Marker",
    domain_mean: "Domain mean",
    strength: "Relative strength", weakness: "Relative weakness", within: "Within average",
    note_label: "Clinical notes (domain)",
    note_ph: "Observations, rationale for the results...",
    global_note_title: "General note (optional)",
    lexicon_title: "Lexicon of assessed functions",
    lexicon_help: "Check the definitions to include in the report; the text is editable.",
    lexicon_empty: "No built-in definition matches the administered functions.",
    draft_title: "Interpretive text (draft, editable)",
    copy_image: "Copy image", download_svg: "SVG", theme_label: "Color theme",
    saved_template: "Template saved", loaded_template: "Template loaded",
    saved_session: "Session saved", loaded_session: "Session loaded",
    exported: "Word report saved", copied_image: "Image copied",
    copied_table: "Table copied", copy_failed: "Clipboard not available in this environment",
    compute_error: "Compute error", load_error: "Load failed",
    confirm_del: "Delete this domain and its entered data?",
  },
};

const METRICS = [
  { v: "z", fr: "z", en: "z" },
  { v: "percentile", fr: "centile", en: "percentile" },
  { v: "scaled", fr: "scaled", en: "scaled" },
  { v: "standard", fr: "standard", en: "standard" },
  { v: "t", fr: "T", en: "T" },
];

const MAX_SERIES = 2;

/* ---------- 1. State ---------------------------------------- */

const state = {
  lang: "fr",
  threshold: 1.0,
  patientId: "",
  clinician: "",
  seriesLabels: ["T1"],
  battery: { name: "Default battery", domains: [] },
  globalNote: "",
  result: null,
  palette: null,
  addons: [],
  theme: "teal",
  themes: [],
  lex: { enabled: true, terms: [], checks: {}, edits: {} },
  options: { radialMode: "z", showSummary: true },
};

/* ---------- 2. Tiny helpers --------------------------------- */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const t = (key) => (T[state.lang][key] !== undefined ? T[state.lang][key] : key);

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

function nameOf(obj) { return state.lang === "fr" ? (obj.name_fr || "") : (obj.name_en || ""); }
function setName(obj, value) { if (state.lang === "fr") obj.name_fr = value; else obj.name_en = value; }
function metricLabel(v) { const m = METRICS.find((x) => x.v === v); return m ? m[state.lang] : v; }
function normName(s) {
  return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim().replace(/\s+/g, " ");
}

let toastTimer = null;
function toast(msg) {
  const node = $("#toast");
  node.textContent = msg;
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 2600);
}

/* Runs cb once the pywebview bridge can actually round-trip a call.
   The window.pywebview.api object can appear before its calls resolve,
   so we poll ping() until it truly answers. */
async function whenReady(cb) {
  for (let i = 0; i < 250; i++) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.ping) {
      try {
        const r = await Promise.race([
          Promise.resolve(window.pywebview.api.ping()),
          new Promise((res) => setTimeout(() => res(null), 250)),
        ]);
        if (r && r.ok) { cb(); return; }
      } catch (e) { /* bridge not answering yet */ }
    }
    await new Promise((res) => setTimeout(res, 80));
  }
  cb();
}

const api = new Proxy({}, {
  get: (_t, name) => (...args) => {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api[name]) {
      return Promise.resolve({ ok: false, error: "bridge unavailable" });
    }
    return Promise.resolve(window.pywebview.api[name](...args));
  },
});

/* ---------- 3. Battery normalisation ------------------------ */

function blankEntry() { return { value: "", metric: "scaled" }; }

function normaliseBattery(tpl, nSeries) {
  // Ensure every measure carries one {value, metric} entry per series.
  // Accepts the template shape (no values), the legacy session shape
  // (measure.value/metric) and the current one (measure.values array).
  const n = Math.max(1, Math.min(MAX_SERIES, nSeries || 1));
  const domains = (tpl.domains || []).map((d) => ({
    name_fr: d.name_fr || "", name_en: d.name_en || "",
    note: typeof d.note === "string" ? d.note : "",
    measures: (d.measures || []).map((m) => {
      let entries = [];
      if (Array.isArray(m.values)) {
        entries = m.values.map((v) => ({
          value: v && v.value !== undefined && v.value !== null ? String(v.value) : "",
          metric: v && v.metric ? String(v.metric).toLowerCase() : "scaled",
        }));
      } else if (m.value !== undefined || m.metric !== undefined) {
        entries = [{
          value: m.value !== undefined && m.value !== null ? String(m.value) : "",
          metric: m.metric ? String(m.metric).toLowerCase() : "scaled",
        }];
      }
      while (entries.length < n) entries.push(blankEntry());
      return { name_fr: m.name_fr || "", name_en: m.name_en || "",
               entries: entries.slice(0, n) };
    }),
  }));
  return { name: tpl.name || "Battery", domains };
}

function batteryToTemplate() {
  const tpl = {
    name: state.battery.name || "Custom battery",
    threshold_sd: state.threshold,
    domains: state.battery.domains.map((d) => ({
      name_fr: d.name_fr, name_en: d.name_en,
      measures: d.measures.map((m) => ({ name_fr: m.name_fr, name_en: m.name_en })),
    })),
  };
  if (state.clinician.trim()) tpl.clinician = state.clinician.trim();
  return tpl;
}

function lexiconState() {
  const unchecked = Object.keys(state.lex.checks).filter((k) => state.lex.checks[k] === false);
  return { enabled: state.lex.enabled, unchecked, edits: state.lex.edits };
}

function batteryToSession() {
  return {
    name: state.battery.name || "Custom battery",
    threshold_sd: state.threshold,
    patient_id: state.patientId,
    clinician: state.clinician,
    language: state.lang,
    theme: state.theme,
    series_labels: state.seriesLabels.slice(),
    global_note: state.globalNote,
    lexicon: lexiconState(),
    domains: state.battery.domains.map((d) => ({
      name_fr: d.name_fr, name_en: d.name_en, note: d.note || "",
      measures: d.measures.map((m) => ({
        name_fr: m.name_fr, name_en: m.name_en,
        values: m.entries.map((e) => ({ value: e.value, metric: e.metric })),
      })),
    })),
  };
}

/* ---------- 4. Static strings & navigation ------------------ */

function applyStaticStrings() {
  $("#app-tagline").textContent = t("tagline");
  $("#threshold-label").textContent = t("threshold_label");
  $("#tab-battery").textContent = t("tab_battery");
  $("#tab-entry").textContent = t("tab_entry");
  $("#tab-results").textContent = t("tab_results");

  $("#battery-title").textContent = t("battery_title");
  $("#battery-help").textContent = t("battery_help");
  $("#btn-load-template").textContent = t("load_template");
  $("#btn-save-template").textContent = t("save_template");
  $("#btn-add-domain").textContent = t("add_domain");
  $("#addon-label").textContent = t("addon_label");
  $("#btn-add-addon").textContent = t("add_addon");

  $("#entry-title").textContent = t("entry_title");
  $("#btn-load-session").textContent = t("load_session");
  $("#btn-save-session").textContent = t("save_session");
  $("#pid-label").textContent = t("pid_label");
  $("#patient-id").placeholder = t("pid_ph");
  $("#clinician-label").textContent = t("clinician_label");
  $("#clinician-input").placeholder = t("clinician_ph");
  $("#pid-warning").textContent = t("pid_warning");
  $("#btn-compute").textContent = t("compute");

  $("#results-title").textContent = t("results_title");
  $("#radial-toggle").querySelector('[data-mode="z"]').textContent = t("mode_z");
  $("#radial-toggle").querySelector('[data-mode="percentile"]').textContent = t("mode_pct");
  $("#summary-toggle-label").textContent = t("summary_toggle");
  $("#btn-copy-table").textContent = t("copy_table");
  $("#btn-export").textContent = t("export");
  $("#results-empty").textContent = t("results_empty");
  $("#theme-label").textContent = t("theme_label");
  $("#lexicon-title").textContent = t("lexicon_title");
  $("#lexicon-help").textContent = t("lexicon_help");
  $("#global-note-title").textContent = t("global_note_title");
  $("#draft-title").textContent = t("draft_title");
}

function switchView(name) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
  // Refresh the target view so renamed/added/removed items are current
  // without re-rendering on every keystroke (which would drop focus).
  if (name === "battery") renderBattery();
  else if (name === "entry") renderEntry();
}

/* ---------- 5. Battery view --------------------------------- */

function move(arr, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= arr.length) return;
  [arr[i], arr[j]] = [arr[j], arr[i]];
}

function renderBattery() {
  const list = $("#domain-list");
  list.innerHTML = "";
  state.battery.domains.forEach((dom, di) => list.appendChild(domainCard(dom, di)));
}

// Any change to the battery STRUCTURE must also refresh the data-entry
// grid so the two views never drift out of sync.
function syncBattery() {
  renderBattery();
  renderEntry();
}

function domainCard(dom, di) {
  const head = el("div", { class: "domain-card-head" }, [
    el("input", {
      type: "text", value: nameOf(dom),
      oninput: (e) => setName(dom, e.target.value),
    }),
    iconBtn("▲", () => { move(state.battery.domains, di, -1); syncBattery(); }),
    iconBtn("▼", () => { move(state.battery.domains, di, 1); syncBattery(); }),
    iconBtn("✕", () => {
      if (window.confirm(t("confirm_del"))) {
        state.battery.domains.splice(di, 1); syncBattery();
      }
    }, "danger"),
  ]);

  const card = el("div", { class: "card" }, [head]);
  dom.measures.forEach((m, mi) => card.appendChild(measureRow(dom, m, di, mi)));

  card.appendChild(el("button", {
    class: "btn tiny measure-add", text: t("add_measure"),
    onclick: () => {
      dom.measures.push({
        name_fr: t("new_measure"), name_en: T.en.new_measure,
        entries: state.seriesLabels.map(() => blankEntry()),
      });
      syncBattery();
    },
  }));
  return card;
}

function measureRow(dom, m, di, mi) {
  return el("div", { class: "measure-row" }, [
    el("span", { class: "handle", text: String(mi + 1) }),
    el("input", { type: "text", value: nameOf(m), oninput: (e) => setName(m, e.target.value) }),
    iconBtn("▲", () => { move(dom.measures, mi, -1); syncBattery(); }),
    iconBtn("▼", () => { move(dom.measures, mi, 1); syncBattery(); }),
    iconBtn("✕", () => { dom.measures.splice(mi, 1); syncBattery(); }, "danger"),
  ]);
}

function iconBtn(label, onclick, extra) {
  return el("button", { class: "icon-btn" + (extra ? " " + extra : ""), text: label, onclick });
}

function populateAddons() {
  const sel = $("#addon-select");
  sel.innerHTML = "";
  state.addons.forEach((d, i) => sel.appendChild(el("option", { value: String(i), text: nameOf(d) })));
}

/* ---------- 6. Series management ----------------------------- */

function addSeries() {
  if (state.seriesLabels.length >= MAX_SERIES) return;
  state.seriesLabels.push(t("series_t2"));
  state.battery.domains.forEach((d) => d.measures.forEach((m) => {
    while (m.entries.length < state.seriesLabels.length) {
      m.entries.push({ value: "", metric: m.entries[0] ? m.entries[0].metric : "scaled" });
    }
  }));
  renderEntry();
}

function removeSeries() {
  if (state.seriesLabels.length <= 1) return;
  state.seriesLabels.pop();
  state.battery.domains.forEach((d) => d.measures.forEach((m) => {
    m.entries = m.entries.slice(0, state.seriesLabels.length);
  }));
  renderEntry();
}

function renderSeriesBar() {
  const bar = $("#series-bar");
  bar.innerHTML = "";
  bar.appendChild(el("span", { class: "series-title", text: t("series_title") }));
  state.seriesLabels.forEach((lab, si) => {
    bar.appendChild(el("span", { class: "series-tag s" + (si + 1) }));
    bar.appendChild(el("input", {
      type: "text", value: lab,
      oninput: (e) => { state.seriesLabels[si] = e.target.value; },
    }));
  });
  if (state.seriesLabels.length < MAX_SERIES) {
    bar.appendChild(el("button", { class: "btn tiny", text: t("series_add"), onclick: addSeries }));
  } else {
    bar.appendChild(el("button", { class: "btn tiny", text: t("series_remove"), onclick: removeSeries }));
  }
  bar.appendChild(el("span", { class: "muted", text: t("series_help") }));
}

/* ---------- 7. Data entry view ------------------------------ */

function metricSelect(entry) {
  const select = el("select", { onchange: (e) => { entry.metric = e.target.value; } });
  METRICS.forEach((opt) => {
    const o = el("option", { value: opt.v, text: opt[state.lang] });
    if (opt.v === entry.metric) o.selected = true;
    select.appendChild(o);
  });
  return select;
}

function renderEntry() {
  $("#patient-id").value = state.patientId;
  $("#clinician-input").value = state.clinician;
  renderSeriesBar();

  const grid = $("#entry-grid");
  grid.innerHTML = "";
  const nser = state.seriesLabels.length;

  state.battery.domains.forEach((dom) => {
    const table = el("table", { class: "entry-table" });
    const head = [el("th", { text: t("col_measure") })];
    for (let si = 0; si < nser; si++) {
      const tag = nser > 1 ? state.seriesLabels[si] + " · " : "";
      head.push(el("th", { text: tag + t("col_value") }));
      head.push(el("th", { text: t("col_metric") }));
    }
    table.appendChild(el("tr", {}, head));

    dom.measures.forEach((m) => {
      while (m.entries.length < nser) m.entries.push(blankEntry());
      const cells = [el("td", { class: "name", text: nameOf(m) })];
      for (let si = 0; si < nser; si++) {
        const entry = m.entries[si];
        cells.push(el("td", {}, [el("input", {
          type: "text", inputmode: "decimal", value: entry.value,
          oninput: (e) => { entry.value = e.target.value; },
        })]));
        cells.push(el("td", {}, [metricSelect(entry)]));
      }
      table.appendChild(el("tr", {}, cells));
    });
    grid.appendChild(el("div", { class: "card" }, [el("h3", { text: nameOf(dom) }), table]));
  });
}

function buildPayload() {
  return {
    patient_id: state.patientId,
    threshold: state.threshold,
    series_labels: state.seriesLabels.slice(),
    domains: state.battery.domains.map((d) => ({
      name_fr: d.name_fr, name_en: d.name_en,
      measures: d.measures.map((m) => ({
        name_fr: m.name_fr, name_en: m.name_en,
        values: m.entries.map((e) => ({ value: e.value, metric: e.metric })),
      })),
    })),
  };
}

async function onCompute() {
  state.patientId = $("#patient-id").value.trim();
  state.clinician = $("#clinician-input").value.trim();
  const res = await api.compute(buildPayload());
  if (!res.ok) { toast(t("compute_error") + (res.error ? ": " + res.error : "")); return; }
  state.result = res.result;
  switchView("results");
  await renderResults();
}

/* ---------- 8. Results view --------------------------------- */

function renderThemeChips() {
  const box = $("#theme-chips");
  if (!box) return;
  box.innerHTML = "";
  state.themes.forEach((th) => {
    const name = state.lang === "fr" ? th.name_fr : th.name_en;
    const grad = `linear-gradient(to right, ${th.bands.join(",")})`;
    box.appendChild(el("button", {
      class: "theme-chip" + (th.key === state.theme ? " active" : ""),
      title: name, onclick: () => setTheme(th.key),
    }, [
      el("span", { class: "swatch", style: `background:${grad}` }),
      el("span", { class: "chip-name", text: name }),
    ]));
  });
}

async function setTheme(key) {
  if (key === state.theme) return;
  state.theme = key;
  const pal = await api.get_palette(key);
  if (pal && pal.ok) state.palette = pal;
  renderThemeChips();
  if (state.result) { renderLegend(); renderTables(); await renderPlots(); }
}

function renderLegend() {
  const box = $("#band-legend");
  box.innerHTML = "";
  if (!state.palette) return;
  const labels = state.lang === "fr" ? state.palette.labels_fr : state.palette.labels_en;
  state.palette.bands.forEach((color, i) => {
    box.appendChild(el("span", { class: "legend-item" }, [
      el("span", { class: "legend-swatch", style: `background:${color}` }),
      el("span", { text: labels[i] }),
    ]));
  });
}

function markCell(flag) {
  const map = {
    strength: ["mark-strength", "▲ " + t("strength")],
    weakness: ["mark-weakness", "▼ " + t("weakness")],
    within: ["mark-within", "-"],
  };
  const [cls, text] = map[flag] || map.within;
  const td = el("td", {}, [el("span", { class: "mark " + cls, text })]);
  if (flag === "within") td.querySelector("span").title = t("within");
  return td;
}

function bandColor(idx) {
  return state.palette ? state.palette.bands[idx] : "#eef4f5";
}

// Rows of the results table for one domain, aligned per series.
function domainTableRows(dom) {
  const multi = (state.result.series_labels || []).length > 1;
  const rows = [];
  dom.measures.forEach((m) => {
    let first = true;
    (m.series || []).forEach((cell, si) => {
      if (!cell) return;
      rows.push({ kind: "measure", m, cell, si, showName: first, multi });
      first = false;
    });
  });
  (dom.mean || []).forEach((mean, si) => {
    if (mean) rows.push({ kind: "mean", mean, si, multi });
  });
  return rows;
}

function renderTables() {
  const box = $("#results-tables");
  box.innerHTML = "";
  if (!state.result) return;
  const labels = state.result.series_labels || [];

  state.result.domains.forEach((dom, di) => {
    const rows = domainTableRows(dom);
    if (!rows.length) return;
    const table = el("table", { class: "result-table" });
    table.appendChild(el("tr", {}, [
      el("th", { text: t("col_measure") }),
      el("th", { text: t("col_score") }),
      el("th", { text: t("col_pct") }),
      el("th", { text: t("col_band") }),
      el("th", { text: t("col_marker") }),
    ]));
    rows.forEach((row) => {
      if (row.kind === "measure") {
        const { m, cell, si } = row;
        let score = `${cell.value} (${metricLabel(cell.metric)})`;
        if (row.multi) score = `${labels[si]} · ${score}`;
        const bandLabel = state.lang === "fr" ? cell.band_fr : cell.band_en;
        table.appendChild(el("tr", {}, [
          el("td", { text: row.showName ? nameOf(m) : "" }),
          el("td", { class: "num" + (row.multi ? " series-cell" : ""), text: score }),
          el("td", { class: "num", text: cell.percentile_display }),
          el("td", { class: "band-cell", style: `background:${bandColor(cell.band_index)}`, text: bandLabel }),
          markCell(cell.flag),
        ]));
      } else {
        const { mean, si } = row;
        let label = t("domain_mean");
        if (row.multi) label = `${label} (${labels[si]})`;
        const bandLabel = state.lang === "fr" ? mean.band_fr : mean.band_en;
        table.appendChild(el("tr", { class: "mean-row" }, [
          el("td", { text: label }),
          el("td", { class: "num", text: "" }),
          el("td", { class: "num", text: mean.percentile_display }),
          el("td", { class: "band-cell", style: `background:${bandColor(mean.band_index)}`, text: bandLabel }),
          el("td", { text: "" }),
        ]));
      }
    });

    // Per-domain clinical note, kept next to the results and figures.
    const batDom = state.battery.domains[di];
    const note = el("div", { class: "note-block" }, [
      el("label", { text: t("note_label") }),
      el("textarea", {
        rows: "2", placeholder: t("note_ph"), spellcheck: "false",
        oninput: (e) => { if (batDom) batDom.note = e.target.value; },
      }),
    ]);
    note.querySelector("textarea").value = (batDom && batDom.note) || "";

    box.appendChild(el("div", { class: "domain-block" }, [
      el("h3", { text: nameOf(dom) }), table, note,
    ]));
  });
}

function plotCard(title, png, svg, svgName) {
  const img = el("img", { src: "data:image/png;base64," + png, alt: title });
  const actions = el("div", { class: "plot-actions" }, [
    el("button", { class: "btn tiny", text: t("copy_image"), onclick: () => copyImage(png) }),
    el("button", { class: "btn tiny", text: t("download_svg"), onclick: () => downloadSVG(svg, svgName) }),
  ]);
  return el("div", { class: "plot-card" }, [img, actions]);
}

async function renderPlots() {
  const box = $("#results-plots");
  box.innerHTML = "";
  if (!state.result) return;
  const opts = { lang: state.lang, radial_mode: state.options.radialMode, theme: state.theme };

  if (state.options.showSummary) {
    const s = await api.render_summary_plot(opts);
    if (s.ok) box.appendChild(plotCard("summary", s.png, s.svg, "summary.svg"));
  }
  for (let di = 0; di < state.result.domains.length; di++) {
    const dom = state.result.domains[di];
    const any = dom.measures.some((m) => (m.series || []).some((c) => c));
    if (!any) continue;
    const r = await api.render_domain_plot(di, opts);
    if (r.ok) {
      const name = nameOf(dom) || ("domain" + di);
      box.appendChild(plotCard(name, r.png, r.svg, name.replace(/\W+/g, "_") + ".svg"));
    }
  }
}

/* ---------- 9. Lexicon --------------------------------------- */

// Lexicon entries matching the administered sub-functions (any series).
function matchedLexTerms() {
  if (!state.result) return [];
  const byName = {};
  state.lex.terms.forEach((term) => {
    byName[normName(term.name_fr)] = term;
    byName[normName(term.name_en)] = term;
  });
  const out = [];
  const seen = {};
  state.result.domains.forEach((dom) => {
    dom.measures.forEach((m) => {
      if (!(m.series || []).some((c) => c)) return;
      const term = byName[normName(m.name_fr)] || byName[normName(m.name_en)];
      if (term && !seen[term.key]) { seen[term.key] = true; out.push(term); }
    });
  });
  return out;
}

function lexText(term) {
  const edits = state.lex.edits[term.key] || {};
  if (state.lang === "fr") return edits.fr !== undefined ? edits.fr : term.def_fr;
  return edits.en !== undefined ? edits.en : term.def_en;
}

function renderLexicon() {
  const panel = $("#lexicon-panel");
  const items = $("#lexicon-items");
  const toggle = $("#lexicon-toggle");
  items.innerHTML = "";
  if (!state.result) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  toggle.checked = state.lex.enabled;
  items.classList.toggle("open", state.lex.enabled);

  const terms = matchedLexTerms();
  if (!terms.length) {
    items.appendChild(el("p", { class: "muted", text: t("lexicon_empty") }));
    return;
  }
  terms.forEach((term) => {
    const checked = state.lex.checks[term.key] !== false;
    const row = el("div", { class: "lex-item" + (checked ? "" : " unchecked") });
    const cb = el("input", { type: "checkbox" });
    cb.checked = checked;
    cb.addEventListener("change", () => {
      state.lex.checks[term.key] = cb.checked;
      row.classList.toggle("unchecked", !cb.checked);
    });
    const ta = el("textarea", { rows: "2", spellcheck: "false" });
    ta.value = lexText(term);
    ta.addEventListener("input", () => {
      if (!state.lex.edits[term.key]) state.lex.edits[term.key] = {};
      state.lex.edits[term.key][state.lang] = ta.value;
    });
    row.appendChild(cb);
    row.appendChild(el("span", { class: "lex-name",
                                 text: state.lang === "fr" ? term.name_fr : term.name_en }));
    row.appendChild(ta);
    items.appendChild(row);
  });
}

function lexiconForExport() {
  if (!state.lex.enabled) return [];
  return matchedLexTerms()
    .filter((term) => state.lex.checks[term.key] !== false)
    .map((term) => ({
      term: state.lang === "fr" ? term.name_fr : term.name_en,
      definition: lexText(term),
    }));
}

/* ---------- 10. Draft & full results render ------------------ */

async function refreshDraft() {
  const r = await api.get_report_text(state.lang);
  $("#draft-text").value = r.ok ? r.text : "";
}

async function renderResults() {
  const empty = $("#results-empty");
  renderThemeChips();
  const hasResult = !!state.result;
  empty.style.display = hasResult ? "none" : "block";
  $("#lexicon-panel").style.display = hasResult ? "block" : "none";
  if (!hasResult) return;
  $("#global-note").value = state.globalNote;
  renderLegend();
  renderTables();
  renderLexicon();
  await renderPlots();
  await refreshDraft();
}

/* ---------- 11. Clipboard & downloads ------------------------ */

function b64ToBlob(b64, type) {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type });
}

async function copyImage(png) {
  try {
    if (!navigator.clipboard || !window.ClipboardItem) throw new Error("no clipboard");
    const blob = b64ToBlob(png, "image/png");
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    toast(t("copied_image"));
  } catch (e) {
    toast(t("copy_failed"));
  }
}

function downloadSVG(svg, filename) {
  const blob = new Blob([svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function buildTableExport() {
  const labels = state.result.series_labels || [];
  let html = '<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse">';
  let text = "";
  const cols = [t("col_measure"), t("col_score"), t("col_pct"), t("col_band"), t("col_marker")];
  state.result.domains.forEach((dom) => {
    const rows = domainTableRows(dom);
    if (!rows.length) return;
    const dname = nameOf(dom);
    html += `<tr><td colspan="5" style="font-weight:bold;background:#f0f2f4">${escapeHtml(dname)}</td></tr>`;
    text += `\n${dname}\n` + cols.join("\t") + "\n";
    html += "<tr>" + cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("") + "</tr>";
    rows.forEach((row) => {
      if (row.kind === "measure") {
        const { m, cell, si } = row;
        let score = `${cell.value} (${metricLabel(cell.metric)})`;
        if (row.multi) score = `${labels[si]} · ${score}`;
        const band = state.lang === "fr" ? cell.band_fr : cell.band_en;
        const mark = cell.flag === "strength" ? t("strength") : cell.flag === "weakness" ? t("weakness") : "";
        const name = row.showName ? nameOf(m) : "";
        html += `<tr><td>${escapeHtml(name)}</td><td>${escapeHtml(score)}</td>`
          + `<td>${escapeHtml(cell.percentile_display)}</td>`
          + `<td style="background:${bandColor(cell.band_index)}">${escapeHtml(band)}</td>`
          + `<td>${escapeHtml(mark)}</td></tr>`;
        text += [name, score, cell.percentile_display, band, mark].join("\t") + "\n";
      } else {
        const { mean, si } = row;
        let label = t("domain_mean");
        if (row.multi) label = `${label} (${labels[si]})`;
        const band = state.lang === "fr" ? mean.band_fr : mean.band_en;
        html += `<tr><td style="font-weight:bold">${escapeHtml(label)}</td><td></td>`
          + `<td style="font-weight:bold">${escapeHtml(mean.percentile_display)}</td>`
          + `<td style="background:${bandColor(mean.band_index)}">${escapeHtml(band)}</td><td></td></tr>`;
        text += [label, "", mean.percentile_display, band, ""].join("\t") + "\n";
      }
    });
  });
  html += "</table>";
  return { html, text };
}

async function copyTable() {
  if (!state.result) return;
  const { html, text } = buildTableExport();
  try {
    if (navigator.clipboard && window.ClipboardItem) {
      await navigator.clipboard.write([new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      })]);
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
    } else {
      throw new Error("no clipboard");
    }
    toast(t("copied_table"));
  } catch (e) {
    toast(t("copy_failed"));
  }
}

/* ---------- 12. Language & threshold ------------------------- */

async function setLang(lang) {
  if (lang !== "fr" && lang !== "en") return;
  state.lang = lang;
  document.documentElement.lang = lang;
  $$(".lang-btn").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  applyStaticStrings();
  populateAddons();
  renderThemeChips();
  renderBattery();
  renderEntry();
  if (state.result) await renderResults();
}

async function onThresholdChange(e) {
  let v = parseFloat(e.target.value);
  if (isNaN(v) || v < 0) v = 1.0;
  state.threshold = v;
  e.target.value = v;
  if (state.result) {
    const res = await api.compute(buildPayload());
    if (res.ok) { state.result = res.result; await renderResults(); }
  }
}

/* ---------- 13. Template / session actions ------------------- */

async function onLoadTemplate() {
  const res = await api.load_template();
  if (res.cancelled) return;
  if (!res.ok) { toast(t("load_error") + (res.error ? ": " + res.error : "")); return; }
  // A template redefines the battery: entries reset to a single series.
  state.seriesLabels = [t("series_t1")];
  state.battery = normaliseBattery(res.template, 1);
  if (res.template.threshold_sd != null) {
    state.threshold = res.template.threshold_sd;
    $("#threshold-input").value = state.threshold;
  }
  if (typeof res.template.clinician === "string" && res.template.clinician.trim()) {
    state.clinician = res.template.clinician.trim();
  }
  renderBattery();
  renderEntry();
  toast(t("loaded_template"));
}

async function onSaveTemplate() {
  state.clinician = $("#clinician-input") ? $("#clinician-input").value.trim() : state.clinician;
  const res = await api.save_template(batteryToTemplate());
  if (res.ok) toast(t("saved_template"));
  else if (res.error) toast(res.error);
}

async function onSaveSession() {
  state.patientId = $("#patient-id").value.trim();
  state.clinician = $("#clinician-input").value.trim();
  const res = await api.save_session(batteryToSession());
  if (res.ok) toast(t("saved_session"));
  else if (res.error) toast(res.error);
}

async function onLoadSession() {
  const res = await api.load_session();
  if (res.cancelled) return;
  if (!res.ok) { toast(t("load_error") + (res.error ? ": " + res.error : "")); return; }
  const s = res.session;
  const labels = Array.isArray(s.series_labels) && s.series_labels.length
    ? s.series_labels.slice(0, MAX_SERIES).map(String) : [t("series_t1")];
  state.seriesLabels = labels;
  state.battery = normaliseBattery(s, labels.length);
  state.patientId = s.patient_id || "";
  state.clinician = s.clinician || "";
  state.globalNote = s.global_note || "";
  if (s.threshold_sd != null) { state.threshold = s.threshold_sd; $("#threshold-input").value = s.threshold_sd; }
  if (s.theme && state.themes.some((th) => th.key === s.theme)) {
    state.theme = s.theme;
    const pal = await api.get_palette(s.theme);
    if (pal && pal.ok) state.palette = pal;
  }
  if (s.lexicon && typeof s.lexicon === "object") {
    state.lex.enabled = s.lexicon.enabled !== false;
    state.lex.checks = {};
    (s.lexicon.unchecked || []).forEach((k) => { state.lex.checks[k] = false; });
    state.lex.edits = s.lexicon.edits && typeof s.lexicon.edits === "object" ? s.lexicon.edits : {};
  }
  state.result = null;
  await setLang(s.language === "en" ? "en" : "fr");
  renderEntry();
  switchView("entry");
  toast(t("loaded_session"));
}

async function onExport() {
  if (!state.result) return;
  state.globalNote = $("#global-note").value;
  const opts = {
    radial_mode: state.options.radialMode,
    show_summary: state.options.showSummary,
    theme: state.theme,
    clinician: state.clinician,
    notes: {
      domains: state.battery.domains.map((d) => d.note || ""),
      global: state.globalNote,
    },
    lexicon: lexiconForExport(),
  };
  const res = await api.export_docx($("#draft-text").value, state.lang, opts);
  if (res.ok) toast(t("exported"));
  else if (res.error) toast(res.error);
}

/* ---------- 14. Wiring --------------------------------------- */

function wireEvents() {
  $$(".lang-btn").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
  $$(".tab").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));
  $("#threshold-input").addEventListener("change", onThresholdChange);

  $("#btn-load-template").addEventListener("click", onLoadTemplate);
  $("#btn-save-template").addEventListener("click", onSaveTemplate);
  $("#btn-add-domain").addEventListener("click", () => {
    state.battery.domains.push({ name_fr: T.fr.new_domain, name_en: T.en.new_domain, note: "", measures: [] });
    syncBattery();
  });
  $("#btn-add-addon").addEventListener("click", () => {
    const idx = parseInt($("#addon-select").value, 10);
    const src = state.addons[idx];
    if (!src) return;
    state.battery.domains.push(
      normaliseBattery({ domains: [src] }, state.seriesLabels.length).domains[0]);
    syncBattery();
  });

  $("#patient-id").addEventListener("input", (e) => { state.patientId = e.target.value; });
  $("#clinician-input").addEventListener("input", (e) => { state.clinician = e.target.value; });
  $("#btn-compute").addEventListener("click", onCompute);
  $("#btn-save-session").addEventListener("click", onSaveSession);
  $("#btn-load-session").addEventListener("click", onLoadSession);

  $("#radial-toggle").querySelectorAll(".seg-btn").forEach((b) => b.addEventListener("click", async () => {
    state.options.radialMode = b.dataset.mode;
    $("#radial-toggle").querySelectorAll(".seg-btn").forEach((x) => x.classList.toggle("active", x === b));
    if (state.result) await renderPlots();
  }));
  $("#summary-toggle").addEventListener("change", async (e) => {
    state.options.showSummary = e.target.checked;
    if (state.result) await renderPlots();
  });
  $("#lexicon-toggle").addEventListener("change", (e) => {
    state.lex.enabled = e.target.checked;
    $("#lexicon-items").classList.toggle("open", state.lex.enabled);
  });
  $("#global-note").addEventListener("input", (e) => { state.globalNote = e.target.value; });
  $("#btn-copy-table").addEventListener("click", copyTable);
  $("#btn-export").addEventListener("click", onExport);
}

/* ---------- 15. Startup -------------------------------------- */

async function init() {
  try {
    const themes = await api.get_themes();
    if (themes && themes.ok) {
      state.themes = themes.themes;
      if (themes.default) state.theme = themes.default;
      renderThemeChips();
    }

    const pal = await api.get_palette(state.theme);
    if (pal && pal.ok) state.palette = pal;

    const lex = await api.get_lexicon();
    if (lex && lex.ok) state.lex.terms = lex.terms;

    const addons = await api.get_addon_domains();
    if (addons && addons.ok) { state.addons = addons.domains; populateAddons(); }

    const dt = await api.get_default_template();
    if (dt && dt.ok) {
      state.battery = normaliseBattery(dt.template, state.seriesLabels.length);
      if (dt.template.threshold_sd != null) {
        state.threshold = dt.template.threshold_sd;
        $("#threshold-input").value = state.threshold;
      }
      if (typeof dt.template.clinician === "string") {
        state.clinician = dt.template.clinician;
      }
    }
    renderBattery();
    renderEntry();
  } catch (e) {
    window.__lastError = String(e && e.message ? e.message : e);
    toast(t("load_error") + ": " + window.__lastError);
  }
}

// Surface any uncaught error instead of failing silently.
window.addEventListener("error", (e) => {
  window.__lastError = e.message || String(e.error || e);
});

function boot() {
  applyStaticStrings();
  wireEvents();
  whenReady(init);
}

// This script is the last element in <body>, so every element boot()
// touches has already been parsed. Boot synchronously and do not depend
// on the DOMContentLoaded event firing, because some webview backends
// attach the page only after that event has already passed.
boot();
