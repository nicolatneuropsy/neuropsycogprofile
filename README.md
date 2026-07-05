# NeuroCogProfile

A fully local, offline desktop application for neuropsychologists. Enter
a patient's cognitive test scores and get back a percentile table, one
radar plot per cognitive domain, an optional cross-domain summary radar,
and an auto-generated draft interpretive paragraph. Copy any plot to the
clipboard and export the whole thing to a clean Word document to drop
into a clinical report.

Bilingual French / English throughout, toggleable at runtime. Default
language: French.

---

## 1. Install

Requires Python 3.10 or newer.

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The runtime dependencies are intentionally minimal: `pywebview` (native
window), `matplotlib` (every figure), `python-docx` (Word export), and
`numpy` (only to simplify the plot geometry). The scoring engine
(`engine.py`) is dependency-free.

Windows also needs the Microsoft Edge WebView2 runtime (ships with
current Windows 10 / 11). macOS uses the system WebKit through pyobjc.

## 2. Run in development

```
python app.py
```

The native window opens with the default battery loaded.

You can also run the modules on their own:

```
python engine.py     # self-tests + worked example (no GUI)
python plots.py      # writes sample figures next to the file
python report.py     # writes a sample .docx to a temp path
```

## 3. Build a standalone app

See [build/BUILD.md](build/BUILD.md) for the exact PyInstaller commands
for Windows (`.exe`) and macOS (`.app`), including the `--add-data`
separators (`;` on Windows, `:` on macOS / Linux). Code signing and
notarization are out of scope; the build steps are unsigned.

## 4. How to use it

1. **Battery** tab: review or edit the battery. Add, remove, rename and
   reorder domains and sub-functions. Each name has a French and an
   English label; the one shown for editing follows the FR / EN toggle,
   and both are stored. Insert optional add-on domains, or load and save
   battery templates as JSON.
2. **Data entry** tab: set a non-identifying patient identifier, then
   enter a score and pick a metric for each sub-function. Leave a row
   blank to mean "not administered" (it is skipped, never imputed).
   Supported metrics: z, percentile, scaled (M=10, SD=3), standard
   (M=100, SD=15), and T (M=50, SD=10). Press **Compute profile**.
3. **Results** tab: read the percentile table (band color-coded, with a
   domain-mean row and relative strength / weakness markers), the
   summary radar and one plot per domain, and an editable draft
   paragraph. Copy any plot image, download an SVG, copy the table, or
   export the full report to Word.

The strength / weakness threshold (default 1.0 SD) is in the header and
applies live. The radial scale of the radars can be switched between the
honest z scale (default) and raw percentile in the Results tab.

A color-theme picker in the Results tab offers preset palettes (Teal,
Ocean, Lavender, Sage, Amber, Grayscale, plus an AQNP clinical
convention with warm low bands and blue high bands) that recolor the
radars, the band cells and the legend together (and the Word export),
and is saved with the session. The sequential presets keep the
colorblind-friendly, non-alarmist design (low scores stay the palest);
the AQNP preset follows the Quebec clinical color convention instead.

Additional clinical features:

- **Two data series (test-retest).** "Add a series" in Data entry
  creates a second value column (e.g. with / without medication, T1 /
  T2). The two series overlay on the same radars (theme color and solid
  circles vs slate dashed squares, readable in grayscale), the table
  carries one row per series with per-series domain means, and the
  draft text is generated per series. The engine is untouched: each
  series gets its own independent pass and personal mean.
- **Clinical notes.** A notes field under each domain in Results plus a
  global note; they print in a "Clinical notes" section of the report
  and are saved with the session.
- **Lexicon.** Built-in bilingual definitions (written originally, in
  generic clinical wording) are matched to the administered
  sub-functions and offered as a checklist with editable text; a master
  toggle removes the whole section. Checked entries print at the end of
  the report.
- **Clinician watermark.** The clinician name field (Data entry) prints
  at the bottom left of every report page. Save it in your own battery
  template once and it comes back on every launch; the shipped default
  template leaves it empty so distributed copies stay neutral.
- **Report layout.** The Word report shows all radars as one compact
  grid (at most two rows) at the top, then the band legend, the
  percentile table, notes, the interpretation and the lexicon.

## 5. Privacy model

Patient data is PHI and never leaves the machine.

- **Zero runtime network access.** No telemetry, update checks,
  analytics, CDNs, external fonts, or LLM calls. The UI is loaded from
  bundled local files and Python is reached only through the in-process
  `js_api` bridge. No HTTP server is started and no port is opened.
- **No automatic persistence.** Default state is in memory only. Nothing
  about a patient is written to disk unless you explicitly save a session
  or export a report to a path you choose in a native file dialog. There
  is no background logging of patient data.
- **Non-identifying identifier.** The patient identifier field is for an
  initials or code style value, and the UI warns against entering a full
  name or other identifying information.
- **Templates vs sessions.** A *template* stores only the battery
  structure (domain and sub-function names). A *session* additionally
  stores the entered values, the patient identifier, the language and
  the threshold. Both are written only where you choose.

## 6. Statistical notes (integrity guardrails)

These are deliberate and should not be "improved" without clinical and
statistical review:

- **Strength / weakness flagging is descriptive, not inferential.** A
  measure is flagged only when its z sits at least the threshold (in SD)
  above or below the patient's own pooled mean z across administered
  measures. This is not a reliable-difference or significance test, and
  the word "significant" is never used. A proper reliable-difference
  test could be added later as an explicit, separate mode.
- **Percentiles are never averaged or tested directly.** All math is in
  z space. Each input metric is converted to z, then to an output
  percentile via the normal CDF, so the table is always in percentiles
  while the averaging and the radar geometry stay on the standardized
  scale.
- **Normal-distribution conversions are fixed.** The engine uses
  `math.erf` for the normal CDF and Acklam's rational approximation for
  its inverse (accurate to ~1e-9), with no substitute norm assumptions.
- **Bands and threshold are configurable with the specified defaults.**
  Seven Wechsler-style bands at percentile cutoffs 2 / 9 / 25 / 75 / 91 /
  98, and a 1.0 SD flag threshold.

The radar uses an honest radial scale by default: the radius is the z
score (so equal visual steps are equal standardized steps), while the
rings are labelled in percentiles (2, 9, 25, 50, 75, 91, 98) so the
clinician still reads percentiles. A reference ring marks the 50th
percentile and a faint ring marks the patient's personal mean.

## 7. Notes on simple defaults chosen where the spec was open

- **Fonts.** The UI uses a local system font stack so that no webfont is
  ever fetched (the strongest guarantee of no network access). A font
  binary cannot be fetched at build time without network access, so this
  was the simplest sensible default. `web/fonts/` is reserved and
  documented for bundling a consistent typeface if desired. The figures
  use matplotlib's own bundled DejaVu Sans, which is local.
- **Add-on sub-functions.** The spec names the *Motor skills* add-on with
  two sub-functions but leaves *Social cognition* and *General
  intellectual functioning* without any. Each is shipped with a couple
  of sensible, fully editable starter sub-functions.
- **On-screen vs export resolution.** Figures are rendered at 200 DPI for
  a crisp on-screen display and re-rendered at 300 DPI for the Word
  export and the offered PNG. SVG is always vector.
- **Patient identifier default.** The field starts empty with an example
  placeholder (`AB-001`) rather than a pre-filled value, to avoid
  injecting a code the clinician must clear.
- **Clipboard image copy.** Implemented with
  `navigator.clipboard.write([new ClipboardItem(...)])` as specified.
  Where a webview does not grant it (some macOS WebKit configurations),
  the app shows a notice and the SVG download and Word export still work.
- **Threshold changes** recompute the cached profile live so the markers
  and draft text stay in sync.

## 8. Project layout

```
neurocogprofile/
  engine.py     scoring engine (dependency-free, used verbatim)
  plots.py      matplotlib figure builders + render helpers
  report.py     Word (.docx) export via python-docx
  api.py        js_api class wiring engine/plots/report to the UI
  app.py        entry point: native window + start
  web/          local HTML, CSS, JS and fonts (no CDN)
  templates/    default_template.json (preloaded on first launch)
  build/        BUILD.md (PyInstaller instructions)
  requirements.txt
  README.md
```

## 9. Acceptance checklist

- `python engine.py` runs its self-tests and worked example.
- `python app.py` opens the window with the default battery loaded.
- A mix of metrics then Compute shows the table, the summary radar and
  one plot per domain, with correct bands and markers.
- The FR / EN toggle updates every label and the draft text.
- Copy image places a PNG on the clipboard; Export to Word produces a
  `.docx` that opens cleanly in Word with the table and all images.
- No network requests are made at runtime.
