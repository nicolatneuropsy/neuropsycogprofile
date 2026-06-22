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
        self._profile: Optional[engine.ProfileResult] = None
        self._inputs: list[list[dict]] = []
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

    def get_palette(self) -> dict:
        """Return the canonical band palette and labels (single source
        of truth shared by the table, the legend and the plots)."""
        pal = plots.palette()
        pal["ok"] = True
        return pal

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
        """Convert the entered battery, classify and flag, then return a
        JSON-serializable result for the table and store the engine
        result for plotting and export."""
        try:
            patient_id = str(payload.get("patient_id", "")).strip()
            threshold = float(payload.get("threshold", engine.DEFAULT_FLAG_THRESHOLD))

            domain_inputs: list[engine.DomainInput] = []
            inputs_aligned: list[list[dict]] = []

            for dom in payload.get("domains", []):
                measures: list[engine.MeasureInput] = []
                aligned: list[dict] = []
                for m in dom.get("measures", []):
                    metric = str(m.get("metric", "scaled")).lower()
                    if metric not in engine.SUPPORTED_METRICS:
                        return {"ok": False,
                                "error": f"Unsupported metric '{metric}'."}
                    try:
                        value = self._parse_value(m.get("value"))
                    except ValueError:
                        name = m.get("name_fr") or m.get("name_en") or "?"
                        return {"ok": False,
                                "error": f"Non-numeric value for '{name}'."}
                    if value is None:
                        continue  # not administered, skipped (never imputed)
                    measures.append(engine.MeasureInput(
                        name_fr=m.get("name_fr", ""), name_en=m.get("name_en", ""),
                        value=value, metric=metric))
                    aligned.append({"value": str(m.get("value")).strip(),
                                    "metric": metric})
                domain_inputs.append(engine.DomainInput(
                    name_fr=dom.get("name_fr", ""), name_en=dom.get("name_en", ""),
                    measures=measures))
                inputs_aligned.append(aligned)

            result = engine.process_profile(domain_inputs, patient_id, threshold)

            # Cache for plotting and export.
            self._profile = result
            self._inputs = inputs_aligned
            self._patient_id = patient_id

            return {"ok": True, "result": self._serialize(result, inputs_aligned)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _serialize(result: engine.ProfileResult,
                   inputs: list[list[dict]]) -> dict:
        """Turn the engine result into a JSON-serializable dict, echoing
        the raw value+metric so the table can show the score as entered."""
        domains = []
        for di, d in enumerate(result.domains):
            measures = []
            for mi, m in enumerate(d.measures):
                raw = inputs[di][mi] if di < len(inputs) and mi < len(inputs[di]) else {}
                measures.append({
                    "name_fr": m.name_fr, "name_en": m.name_en,
                    "value": raw.get("value", ""), "metric": raw.get("metric", ""),
                    "z": round(m.z, 4),
                    "percentile": round(m.percentile, 2),
                    "percentile_display": m.percentile_display,
                    "band_fr": m.band_fr, "band_en": m.band_en,
                    "band_index": plots.band_index(m.percentile),
                    "flag": m.flag,
                })
            domains.append({
                "name_fr": d.name_fr, "name_en": d.name_en,
                "mean_z": None if d.mean_z is None else round(d.mean_z, 4),
                "mean_percentile": (None if d.mean_percentile is None
                                    else round(d.mean_percentile, 2)),
                "mean_percentile_display": (None if d.mean_percentile is None
                                            else engine.format_percentile(d.mean_percentile)),
                "mean_band_index": (None if d.mean_percentile is None
                                    else plots.band_index(d.mean_percentile)),
                "measures": measures,
            })
        return {
            "patient_id": result.patient_id,
            "threshold": result.threshold,
            "personal_mean_z": (None if result.personal_mean_z is None
                                else round(result.personal_mean_z, 4)),
            "domains": domains,
        }

    def get_report_text(self, lang: str = "fr") -> dict:
        """Return the draft interpretive paragraph for the cached result."""
        if self._profile is None:
            return {"ok": False, "error": "Nothing computed yet."}
        lang = "fr" if lang == "fr" else "en"
        return {"ok": True,
                "text": engine.generate_report_text(self._profile, lang)}

    # -- plots ------------------------------------------------

    def render_summary_plot(self, options: Optional[dict] = None) -> dict:
        """Render the cross-domain summary figure for display."""
        if self._profile is None:
            return {"ok": False, "error": "Nothing computed yet."}
        options = options or {}
        lang = "fr" if options.get("lang", "fr") == "fr" else "en"
        mode = options.get("radial_mode", "z")
        try:
            fig, kind = plots.summary_figure(self._profile, lang, mode)
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
        """Render one domain radar for display. Domains with fewer than
        three sub-functions carry no figure (skip)."""
        if self._profile is None:
            return {"ok": False, "error": "Nothing computed yet."}
        options = options or {}
        lang = "fr" if options.get("lang", "fr") == "fr" else "en"
        mode = options.get("radial_mode", "z")
        try:
            domain = self._profile.domains[int(domain_index)]
        except (IndexError, ValueError, TypeError):
            return {"ok": False, "error": "Unknown domain index."}
        if len(domain.measures) < 3:
            return {"ok": False, "skip": True}
        try:
            fig, kind = plots.domain_figure(domain, self._profile.personal_mean_z,
                                            lang, mode)
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
        """Build the full Word report and save it to a chosen path."""
        if self._profile is None:
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
            report.export_report(path, self._profile, self._inputs, draft_text,
                                 self._patient_id, lang, options)
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
