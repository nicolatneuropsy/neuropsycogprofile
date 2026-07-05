# ============================================================
# js_api bridge.
#
# A single Api instance is exposed to the web UI as
# window.pywebview.api. Every method is callable from JavaScript and
# returns a JSON-serializable dict (always with an "ok" flag).
#
# The engine results of the last compute are cached on the instance so
# the plot and export methods can rebuild figures without shipping large
# structures back and forth across the bridge. Nothing is written to
# disk except through an explicit native file dialog chosen by the user.
# ============================================================

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import engine
import lexicon
import plots
import report

# Optional add-on domains the clinician can insert from the Battery view.
# The two domains without sub-functions in the spec are given sensible,
# fully editable starter sub-functions (noted in the README).
ADDON_DOMAINS = [
    {
        "name_fr": "Habiletés motrices",
        "name_en": "Motor skills",
        "measures": [
            {"name_fr": "Vitesse motrice fine", "name_en": "Fine motor speed"},
            {"name_fr": "Dextérité", "name_en": "Dexterity"},
        ],
    },
    {
        "name_fr": "Cognition sociale",
        "name_en": "Social cognition",
        "measures": [
            {"name_fr": "Théorie de l'esprit", "name_en": "Theory of mind"},
            {"name_fr": "Reconnaissance des émotions", "name_en": "Emotion recognition"},
        ],
    },
    {
        "name_fr": "Fonctionnement intellectuel général",
        "name_en": "General intellectual functioning",
        "measures": [
            {"name_fr": "QI global", "name_en": "Full-scale IQ"},
            {"name_fr": "Raisonnement", "name_en": "Reasoning"},
        ],
    },
]


def resource_path(relative: str) -> str:
    """Resolve a bundled resource both in development and inside a
    PyInstaller one-file build (which unpacks to sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class Api:
    """Methods exposed to the web UI through window.pywebview.api."""

    def __init__(self) -> None:
        self._window = None
        # Cache of the most recent computation (single open window).
        # One engine profile per data series (test-retest support).
        self._profiles: list[engine.ProfileResult] = []
        self._series_labels: list[str] = []
        # inputs_aligned[domain][measure][series] -> {value, metric} | None
        self._inputs: list[list[list[Optional[dict]]]] = []
        self._patient_id: str = ""

    # -- wiring ------------------------------------------------

    def set_window(self, window) -> None:
        """Called once by app.py after the window is created."""
        self._window = window

    def ping(self) -> dict:
        """Trivial readiness check for the frontend."""
        return {"ok": True}

    # -- native file dialogs (lazy import so api.py is importable
    #    without a display, e.g. for tests) ---------------------

    def _save_dialog(self, default_name: str, file_types) -> Optional[str]:
        import webview
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default_name, file_types=file_types)
        if not result:
            return None
        return result if isinstance(result, str) else result[0]

    def _open_dialog(self, file_types) -> Optional[str]:
        import webview
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else result

    # -- templates and palette --------------------------------

    def get_default_template(self) -> dict:
        """Return the bundled default battery template."""
        try:
            path = resource_path(os.path.join("templates", "default_template.json"))
            with open(path, "r", encoding="utf-8") as fh:
                template = json.load(fh)
            return {"ok": True, "template": template}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_addon_domains(self) -> dict:
        """Return the optional add-on domains for the Battery view."""
        return {"ok": True, "domains": ADDON_DOMAINS}

    def get_palette(self, theme=None) -> dict:
        """Return the resolved band palette and labels for a theme (single
        source of truth shared by the table, the legend and the plots)."""
        pal = plots.palette(theme)
        pal["ok"] = True
        return pal

    def get_themes(self) -> dict:
        """Return the preset color themes for the radar plots."""
        return {"ok": True, "themes": plots.theme_list(),
                "default": plots.DEFAULT_THEME}

    def get_lexicon(self) -> dict:
        """Return the built-in bilingual lexicon of cognitive functions."""
        return {"ok": True, "terms": lexicon.all_terms()}

    def load_template(self) -> dict:
        """Open a JSON template chosen by the user."""
        path = self._open_dialog(("JSON (*.json)", "All files (*.*)"))
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                template = json.load(fh)
            if "domains" not in template:
                return {"ok": False, "error": "Not a valid battery template."}
            return {"ok": True, "template": template}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def save_template(self, template: dict) -> dict:
        """Save the current battery as a JSON template (no patient data)."""
        path = self._save_dialog("battery_template.json",
                                 ("JSON (*.json)",))
        if not path:
            return {"ok": False, "cancelled": True}
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(template, fh, ensure_ascii=False, indent=2)
            return {"ok": True, "path": path}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # -- computation ------------------------------------------

    @staticmethod
    def _parse_value(raw) -> Optional[float]:
        """Parse a cell value. Blank means 'not administered' (None)."""
        if raw is None:
            return None
        text = str(raw).strip()
        if text == "":
            return None
        return float(text.replace(",", "."))  # accept comma decimals

    def compute(self, payload: dict) -> dict:
        """Convert the entered battery (one or two data series), classify
        and flag each series independently, and return a JSON-serializable
        result aligned per measure and per series for the table. The
        engine results are cached for plotting and export.

        payload.series_labels names the series; each measure carries
        values[si] = {"value", "metric"} aligned with those labels. The
        legacy single-series shape (measure.value / measure.metric) is
        also accepted.
        """
        try:
            patient_id = str(payload.get("patient_id", "")).strip()
            threshold = float(payload.get("threshold", engine.DEFAULT_FLAG_THRESHOLD))
            labels = [str(x).strip() or f"S{i + 1}" for i, x in
                      enumerate(payload.get("series_labels") or ["S1"])][:2]
            nser = len(labels)

            # Parse every cell first: parsed[di][mi][si] -> float | None,
            # echo[di][mi][si] -> {"value","metric"} | None.
            parsed: list[list[list[Optional[float]]]] = []
            echo: list[list[list[Optional[dict]]]] = []
            for dom in payload.get("domains", []):
                dp, de = [], []
                for m in dom.get("measures", []):
                    cells = m.get("values")
                    if cells is None:  # legacy single-series shape
                        cells = [{"value": m.get("value"),
                                  "metric": m.get("metric", "scaled")}]
                    mp, me = [], []
                    for si in range(nser):
                        cell = cells[si] if si < len(cells) else {}
                        metric = str((cell or {}).get("metric", "scaled")).lower()
                        if metric not in engine.SUPPORTED_METRICS:
                            return {"ok": False,
                                    "error": f"Unsupported metric '{metric}'."}
                        try:
                            value = self._parse_value((cell or {}).get("value"))
                        except ValueError:
                            name = m.get("name_fr") or m.get("name_en") or "?"
                            return {"ok": False,
                                    "error": f"Non-numeric value for '{name}'."}
                        mp.append(value)
                        me.append(None if value is None else
                                  {"value": str(cell.get("value")).strip(),
                                   "metric": metric})
                    dp.append(mp)
                    de.append(me)
                parsed.append(dp)
                echo.append(de)

            # Drop trailing series with no data at all (a second series
            # left entirely blank behaves as a single-series profile).
            used = nser
            while used > 1 and not any(mp[used - 1] is not None
                                       for dp in parsed for mp in dp):
                used -= 1
            labels = labels[:used]

            # One engine pass per series (the engine is untouched; each
            # series gets its own personal mean and descriptive flags).
            profiles: list[engine.ProfileResult] = []
            for si in range(used):
                domain_inputs = []
                for di, dom in enumerate(payload.get("domains", [])):
                    measures = []
                    for mi, m in enumerate(dom.get("measures", [])):
                        value = parsed[di][mi][si]
                        if value is None:
                            continue  # not administered, never imputed
                        measures.append(engine.MeasureInput(
                            name_fr=m.get("name_fr", ""),
                            name_en=m.get("name_en", ""),
                            value=value,
                            metric=echo[di][mi][si]["metric"]))
                    domain_inputs.append(engine.DomainInput(
                        name_fr=dom.get("name_fr", ""),
                        name_en=dom.get("name_en", ""),
                        measures=measures))
                profiles.append(engine.process_profile(domain_inputs,
                                                       patient_id, threshold))

            self._profiles = profiles
            self._series_labels = labels
            self._inputs = [[[me[si] for si in range(used)] for me in de]
                            for de in echo]
            self._patient_id = patient_id

            return {"ok": True,
                    "result": self._serialize(payload, profiles, labels,
                                              parsed, echo)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _serialize(payload: dict, profiles: list[engine.ProfileResult],
                   labels: list[str],
                   parsed: list, echo: list) -> dict:
        """Aligned, JSON-serializable result: every payload measure keeps
        one slot per series (None when not administered in that series)."""
        used = len(labels)
        # Per-series cursors into the engine results (which keep only the
        # administered measures, in payload order).
        cursors = [[0] * len(profiles[si].domains) for si in range(used)]

        domains = []
        for di, dom in enumerate(payload.get("domains", [])):
            measures = []
            for mi, m in enumerate(dom.get("measures", [])):
                per_series = []
                for si in range(used):
                    if parsed[di][mi][si] is None:
                        per_series.append(None)
                        continue
                    r = profiles[si].domains[di].measures[cursors[si][di]]
                    cursors[si][di] += 1
                    per_series.append({
                        "value": echo[di][mi][si]["value"],
                        "metric": echo[di][mi][si]["metric"],
                        "z": round(r.z, 4),
                        "percentile": round(r.percentile, 2),
                        "percentile_display": r.percentile_display,
                        "band_fr": r.band_fr, "band_en": r.band_en,
                        "band_index": plots.band_index(r.percentile),
                        "flag": r.flag,
                    })
                measures.append({"name_fr": m.get("name_fr", ""),
                                 "name_en": m.get("name_en", ""),
                                 "series": per_series})
            mean_per_series = []
            for si in range(used):
                d = profiles[si].domains[di]
                if d.mean_percentile is None:
                    mean_per_series.append(None)
                else:
                    band_fr, band_en = engine.classify_band(d.mean_percentile)
                    mean_per_series.append({
                        "z": round(d.mean_z, 4),
                        "percentile": round(d.mean_percentile, 2),
                        "percentile_display":
                            engine.format_percentile(d.mean_percentile),
                        "band_fr": band_fr, "band_en": band_en,
                        "band_index": plots.band_index(d.mean_percentile),
                    })
            domains.append({"name_fr": dom.get("name_fr", ""),
                            "name_en": dom.get("name_en", ""),
                            "mean": mean_per_series,
                            "measures": measures})

        return {
            "patient_id": profiles[0].patient_id,
            "threshold": profiles[0].threshold,
            "series_labels": labels,
            "personal_mean_z": [
                None if p.personal_mean_z is None
                else round(p.personal_mean_z, 4) for p in profiles],
            "domains": domains,
        }

    def get_report_text(self, lang: str = "fr") -> dict:
        """Draft interpretive text for the cached result. With two series
        the drafts are concatenated under their series labels."""
        if not self._profiles:
            return {"ok": False, "error": "Nothing computed yet."}
        lang = "fr" if lang == "fr" else "en"
        if len(self._profiles) == 1:
            return {"ok": True,
                    "text": engine.generate_report_text(self._profiles[0], lang)}
        parts = []
        for prof, lab in zip(self._profiles, self._series_labels):
            parts.append(f"[{lab}]")
            parts.append(engine.generate_report_text(prof, lang))
            parts.append("")
        return {"ok": True, "text": "\n".join(parts).strip()}

    # -- plots ------------------------------------------------

    def render_summary_plot(self, options: Optional[dict] = None) -> dict:
        """Render the cross-domain summary figure for display."""
        if not self._profiles:
            return {"ok": False, "error": "Nothing computed yet."}
        options = options or {}
        lang = "fr" if options.get("lang", "fr") == "fr" else "en"
        mode = options.get("radial_mode", "z")
        try:
            fig, kind = plots.summary_figure(self._profiles,
                                             self._series_labels, lang, mode,
                                             theme=options.get("theme"))
            if fig is None:
                return {"ok": False, "skip": True}
            png = plots.fig_to_base64_png(fig, dpi=options.get("dpi", 200))
            svg = plots.fig_to_svg_text(fig)
            plots.close_fig(fig)
            return {"ok": True, "png": png, "svg": svg, "kind": kind}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def render_domain_plot(self, domain_index: int,
                           options: Optional[dict] = None) -> dict:
        """Render one domain radar (all series overlaid). Domains with
        fewer than three measured axes carry no figure (skip)."""
        if not self._profiles:
            return {"ok": False, "error": "Nothing computed yet."}
        options = options or {}
        lang = "fr" if options.get("lang", "fr") == "fr" else "en"
        mode = options.get("radial_mode", "z")
        try:
            di = int(domain_index)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Unknown domain index."}
        try:
            fig, kind = plots.domain_figure(self._profiles,
                                            self._series_labels, di, lang,
                                            mode, theme=options.get("theme"))
            if fig is None:
                return {"ok": False, "skip": True}
            png = plots.fig_to_base64_png(fig, dpi=options.get("dpi", 200))
            svg = plots.fig_to_svg_text(fig)
            plots.close_fig(fig)
            return {"ok": True, "png": png, "svg": svg, "kind": kind}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # -- Word export ------------------------------------------

    def export_docx(self, draft_text: str, lang: str = "fr",
                    options: Optional[dict] = None) -> dict:
        """Build the full Word report and save it to a chosen path.

        options may carry: radial_mode, show_summary, theme, clinician,
        notes ({"domains": [str per domain], "global": str}) and
        lexicon (list of {"term", "definition"} already in the export
        language, assembled by the UI from the checklist).
        """
        if not self._profiles:
            return {"ok": False, "error": "Nothing computed yet."}
        lang = "fr" if lang == "fr" else "en"
        options = options or {}
        safe_id = (self._patient_id or "profile").replace(" ", "_")
        path = self._save_dialog(f"{safe_id}_cognitive_profile.docx",
                                 ("Word document (*.docx)",))
        if not path:
            return {"ok": False, "cancelled": True}
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            report.export_report(path, self._profiles, self._series_labels,
                                 self._inputs, draft_text, self._patient_id,
                                 lang, options)
            return {"ok": True, "path": path}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # -- sessions ---------------------------------------------

    def save_session(self, session: dict) -> dict:
        """Save the full session (battery + entries + meta) to a chosen
        path. This is the only way patient-related data reaches disk."""
        path = self._save_dialog("session.json", ("JSON (*.json)",))
        if not path:
            return {"ok": False, "cancelled": True}
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(session, fh, ensure_ascii=False, indent=2)
            return {"ok": True, "path": path}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def load_session(self) -> dict:
        """Load a previously saved session from a chosen path."""
        path = self._open_dialog(("JSON (*.json)", "All files (*.*)"))
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                session = json.load(fh)
            return {"ok": True, "session": session}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
