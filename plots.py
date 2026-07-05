# ============================================================
# Figure builders for the cognitive profile.
#
# Matplotlib is the single source of truth for every figure. The same
# builders feed both the on-screen display (base64 PNG handed to the
# web UI) and the Word export (300 DPI PNG embedded by report.py), so a
# figure always looks identical on screen and on paper.
#
# Design choices:
# - Colorblind-safe, muted, professional palette. Low scores are NOT
#   marked in red; the band shading is a calm light-to-deeper blue/teal
#   sequential ramp, which is also distinguishable in grayscale.
# - Honest radial scale: by default the radius is the z score, so equal
#   visual steps are equal standardized steps. The rings are still
#   LABELLED in percentiles so the clinician reads percentiles.
# - No chart junk. One restrained accent color for the patient polygon.
# ============================================================

from __future__ import annotations

import base64
import io
import math
import textwrap
from typing import Optional

import matplotlib

# Use the non-interactive Agg backend: figures are rendered to bytes,
# never shown in a window. This is thread-safe inside the webview and
# needs no display server.
matplotlib.use("Agg")

import matplotlib.pyplot as plt          # noqa: E402  (after use())
import matplotlib.patheffects as pe      # noqa: E402
import numpy as np                       # noqa: E402

from engine import (                      # noqa: E402
    BANDS,
    ProfileResult,
    _pctl_phrase,
    format_percentile,
    phi_inverse,
    z_to_percentile,
)

# Global quality defaults: Arial first (a universal system font on macOS
# and Windows, so still fully offline), falling back to DejaVu Sans which
# ships with matplotlib. Crisp anti-aliasing and white backgrounds.
matplotlib.rcParams.update({
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 10.5,
    "axes.linewidth": 0.8,
    "lines.antialiased": True,
    "patch.antialiased": True,
    "text.antialiased": True,
    "svg.fonttype": "path",   # self-contained SVG, no font lookups
})

# --- 0. Shared palette ---------------------------------------

# Preset color themes for the radar plots (and, for consistency, the band
# cells and the legend). Each theme is a 7-step band ramp from the lowest
# band to the highest (light -> deeper, so equal-lightness steps keep it
# colorblind-friendly and never alarmist: low scores are the palest, not
# red), plus an accent for the patient polygon and a deeper accent for
# titles. The user switches themes at runtime; "teal" is the default.
THEMES = {
    "teal": {
        "name_fr": "Sarcelle", "name_en": "Teal",
        "bands": ["#eef4f5", "#e5eff1", "#dbe9ed", "#cfe2e7",
                  "#c2dbe1", "#b3d2da", "#a3cad4"],
        "accent": "#2c6e8f", "accent_deep": "#1f5269",
    },
    "ocean": {
        "name_fr": "Océan", "name_en": "Ocean",
        "bands": ["#eef2fa", "#e2e9f6", "#d4dff1", "#c4d4ec",
                  "#b0c5e6", "#9ab5df", "#82a4d8"],
        "accent": "#3a5fa8", "accent_deep": "#28447d",
    },
    "lavender": {
        "name_fr": "Lavande", "name_en": "Lavender",
        "bands": ["#f3eff8", "#ebe3f3", "#e1d5ed", "#d5c6e5",
                  "#c7b4dc", "#b7a1d1", "#a78ac6"],
        "accent": "#6f57a8", "accent_deep": "#503d80",
    },
    "sage": {
        "name_fr": "Sauge", "name_en": "Sage",
        "bands": ["#eef5ef", "#e3efe5", "#d6e8da", "#c8e0ce",
                  "#b6d6be", "#a3caac", "#8dbd98"],
        "accent": "#3f8a5f", "accent_deep": "#2c6444",
    },
    "amber": {
        "name_fr": "Ambre", "name_en": "Amber",
        "bands": ["#fbf3e8", "#f7ecda", "#f2e2c8", "#ecd6b1",
                  "#e5c997", "#dcba77", "#d0aa53"],
        "accent": "#b07a2a", "accent_deep": "#8a5d18",
    },
    "mono": {
        "name_fr": "Niveaux de gris", "name_en": "Grayscale",
        "bands": ["#f2f3f4", "#e8eaeb", "#dcdee0", "#cfd2d5",
                  "#bfc4c7", "#acb2b6", "#969ca2"],
        "accent": "#3a4750", "accent_deep": "#262f35",
    },
    # Clinical convention used in Quebec neuropsychology: the AACN
    # classification table adapted by the AQNP (2022, after Guilmette
    # et al., 2020). From the lowest band to the highest: red, orange,
    # amber, green (average), clear blue (high average), periwinkle
    # (above average) and rose (extremely high). Tints follow the
    # published table, slightly softened so dark text stays readable.
    # Unlike the other presets this ramp is multi-hue by design; it
    # follows the clinical convention rather than monotonic lightness.
    "aqnp": {
        "name_fr": "AQNP (clinique)", "name_en": "AQNP (clinical)",
        "bands": ["#e85c5c", "#f0913a", "#f5bc53", "#a3cd92",
                  "#4faedd", "#98abd6", "#f18da1"],
        "accent": "#2f6699", "accent_deep": "#24507a",
    },
}
DEFAULT_THEME = "teal"

# Default module-level palette (the default theme), used when no theme is
# given. Kept as module constants for backward compatibility.
BAND_COLORS = THEMES[DEFAULT_THEME]["bands"]
ACCENT = THEMES[DEFAULT_THEME]["accent"]
ACCENT_DEEP = THEMES[DEFAULT_THEME]["accent_deep"]

# Second series (test-retest overlay): a neutral dark slate with a dashed
# line and square markers, so the two series stay distinguishable in any
# theme, for colorblind readers and in grayscale printing.
SERIES2_COLOR = "#4c5660"
SERIES2_DASH = (0, (4, 2))
# Dark neutral for text that must read on top of any band.
INK = "#26343c"
MUTED = "#5b676e"
# Neutral gray for the 50th-percentile reference ring and bar guides.
GUIDE = "#6f7d84"
# Hairline color for separators and pill borders.
HAIRLINE = "#d3dce0"

# Ring percentiles that are drawn and labelled on every radar.
RING_PCTLS = (2, 9, 25, 50, 75, 91, 98)
# Band cut percentiles (the six boundaries between the seven bands).
CUT_PCTLS = (2, 9, 25, 75, 91, 98)

# Radial extent of the z-scale axis and the clamp applied to data.
# Capped just beyond the outer band boundary (z ~= 2.05 for the 98th
# percentile) so the extreme bands read as thin context rims instead of
# dominating the figure with a large dark outer annulus.
Z_AXIS_MIN = -2.75
Z_AXIS_MAX = 2.75
Z_DATA_CLAMP = 2.6


# --- 1. Small helpers ----------------------------------------

def band_index(percentile: float) -> int:
    """Return the 0..6 band index for a percentile (mirrors the engine)."""
    for i, (cutoff, _fr, _en) in enumerate(BANDS):
        if percentile < cutoff:
            return i
    return len(BANDS) - 1


def resolve_theme(theme=None):
    """Return (bands, accent, accent_deep) for a theme key, a custom theme
    dict ({"bands": [...7], "accent": ..., "accent_deep": ...}), or None
    (the default theme). Invalid input falls back to the default."""
    default = THEMES[DEFAULT_THEME]
    if isinstance(theme, dict) and theme.get("bands"):
        bands = list(theme["bands"])
        accent = theme.get("accent", default["accent"])
        accent_deep = theme.get("accent_deep", accent)
    else:
        chosen = THEMES.get(theme, default) if isinstance(theme, str) else default
        bands = list(chosen["bands"])
        accent, accent_deep = chosen["accent"], chosen["accent_deep"]
    if len(bands) != 7:
        bands = list(default["bands"])
    return bands, accent, accent_deep


def palette(theme=None) -> dict:
    """Expose the resolved palette so the UI, the table and the plots all
    use exactly the same band colors (single source of truth)."""
    bands, accent, accent_deep = resolve_theme(theme)
    return {
        "bands": bands,
        "accent": accent,
        "accent_deep": accent_deep,
        "ink": INK,
        "labels_fr": [b[1] for b in BANDS],
        "labels_en": [b[2] for b in BANDS],
        "ring_pctls": list(RING_PCTLS),
    }


def theme_list() -> list:
    """The preset themes for the UI picker (key, bilingual name, swatch)."""
    return [
        {"key": k, "name_fr": v["name_fr"], "name_en": v["name_en"],
         "bands": list(v["bands"]), "accent": v["accent"]}
        for k, v in THEMES.items()
    ]


def _wrap(label: str, width: int = 14) -> str:
    """Wrap a long axis label onto a couple of lines."""
    return textwrap.fill(label, width=width, break_long_words=False)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _axis_params(mode: str):
    """Return (axis_min, axis_max, region_edges, rings, ref_pos) for the
    requested radial mode.

    region_edges has 8 entries (7 bands). rings is a list of
    (position, percentile_label). ref_pos is the position of the 50th
    percentile reference ring.
    """
    if mode == "percentile":
        edges = [0.0] + [float(p) for p in CUT_PCTLS] + [100.0]
        rings = [(float(p), p) for p in RING_PCTLS]
        return 0.0, 100.0, edges, rings, 50.0
    # Default: honest z scale.
    edges = [Z_AXIS_MIN] + [phi_inverse(p / 100.0) for p in CUT_PCTLS] + [Z_AXIS_MAX]
    rings = [(phi_inverse(p / 100.0), p) for p in RING_PCTLS]
    return Z_AXIS_MIN, Z_AXIS_MAX, edges, rings, 0.0


def _pos_of_z(z: float, mode: str) -> float:
    """Map a z score to its radial position for the requested mode."""
    if mode == "percentile":
        return z_to_percentile(z)
    return _clamp(z, -Z_DATA_CLAMP, Z_DATA_CLAMP)


# --- 2. Radar core -------------------------------------------

def _series_style(index: int, accent: str, accent_deep: str) -> dict:
    """Visual style for series index (0 = theme accent, 1 = slate dashed)."""
    if index == 0:
        return {"color": accent, "deep": accent_deep, "ls": "-",
                "marker": "o", "fill": True}
    return {"color": SERIES2_COLOR, "deep": SERIES2_COLOR, "ls": SERIES2_DASH,
            "marker": "s", "fill": False}


def _draw_radar(ax, labels: list[str], series: list[dict],
                personal_mean_z: Optional[float],
                lang: str = "fr", radial_mode: str = "z",
                compact: bool = False, theme=None) -> None:
    """Draw a report-grade radar onto a provided polar Axes.

    series is a list of dicts {"label", "z": [float|None per axis],
    "disp": [str|None per axis]}; one entry per data series (a second
    series overlays the first for test-retest comparison). A None value
    means "not administered in this series": the vertex is skipped and
    the polygon edge is broken there rather than interpolated.

    Sets no title and creates no figure, so the same drawing serves a
    full single figure and a small panel inside the composite page.
    """
    bands, accent, accent_deep = resolve_theme(theme)
    mode = radial_mode if radial_mode in ("z", "percentile") else "z"
    axis_min, axis_max, edges, rings, ref_pos = _axis_params(mode)
    span = axis_max - axis_min
    n = len(labels)
    angles = [2.0 * math.pi * i / n for i in range(n)]
    theta = np.linspace(0.0, 2.0 * math.pi, 721)

    # Size set: smaller and decluttered for compact composite panels.
    if compact:
        marker_s, poly_lw, halo_lw, edge_lw = 22, 1.6, 3.0, 1.3
        vtx_fs, name_fs, name_w, name_rf = 7.0, 7.0, 12, 1.05
        show_ring_labels = False
    else:
        marker_s, poly_lw, halo_lw, edge_lw = 58, 2.4, 4.4, 1.8
        vtx_fs, name_fs, name_w, name_rf = 8.8, 10.0, 20, 1.05
        show_ring_labels = True

    # For compact panels, rotate by half a sector so the very top is a
    # gap between two spokes, leaving clean room for the panel title.
    theta_off = math.pi / 2.0 + (math.pi / n if compact else 0.0)
    ax.set_theta_offset(theta_off)
    ax.set_theta_direction(-1)           # clockwise
    ax.set_ylim(0.0, span)
    ax.set_facecolor("white")
    ax.grid(False)
    ax.spines["polar"].set_visible(False)
    ax.set_xticks([])
    ax.set_yticklabels([])

    # Shade the seven band zones as concentric regions.
    for i in range(len(edges) - 1):
        ax.fill_between(theta, np.full_like(theta, edges[i] - axis_min),
                        np.full_like(theta, edges[i + 1] - axis_min),
                        color=bands[i], linewidth=0.0, zorder=0)

    # Faint radial spokes give the plot structure.
    for a in angles:
        ax.plot([a, a], [0.0, span], color="white", lw=0.9, alpha=0.7, zorder=1)

    # Crisp white separators between bands.
    for pos, _p in rings:
        if abs(pos - ref_pos) < 1e-9:
            continue
        ax.plot(theta, np.full_like(theta, pos - axis_min),
                color="white", lw=0.8, alpha=0.8, zorder=2)

    # Finished outer boundary and the 50th-percentile reference ring.
    ax.plot(theta, np.full_like(theta, span), color=HAIRLINE, lw=1.0, zorder=2)
    ax.plot(theta, np.full_like(theta, ref_pos - axis_min),
            color=GUIDE, lw=1.4, alpha=0.9, zorder=2)

    # Faint ring at the patient's personal mean (single series only:
    # with two overlaid series it would be ambiguous which mean it is).
    if personal_mean_z is not None and len(series) == 1:
        mpos = _clamp(_pos_of_z(personal_mean_z, mode), axis_min, axis_max)
        ax.plot(theta, np.full_like(theta, mpos - axis_min),
                color=accent, lw=1.1, ls=(0, (3, 3)), alpha=0.55, zorder=3)

    # One polygon per series. Vertices missing in a series break the
    # outline there (edges are drawn only between adjacent administered
    # vertices); the translucent fill is drawn only for a complete
    # first series, so nothing is visually interpolated.
    for si, ser in enumerate(series):
        st = _series_style(si, accent, accent_deep)
        rv = [None if z is None else _pos_of_z(z, mode) - axis_min
              for z in ser["z"]]
        present = [i for i, r in enumerate(rv) if r is not None]
        if not present:
            continue
        complete = len(present) == n
        if complete and st["fill"] and n >= 3:
            ax.fill(angles + [angles[0]], [rv[i] for i in range(n)] + [rv[0]],
                    color=st["color"], alpha=0.13, zorder=4)
        # Edges between adjacent administered vertices (wrap included).
        for i in range(n):
            j = (i + 1) % n
            if n > 1 and rv[i] is not None and rv[j] is not None:
                if n == 2 and i == 1:
                    break  # avoid drawing the same edge twice
                ax.plot([angles[i], angles[j]], [rv[i], rv[j]],
                        color=st["color"], lw=poly_lw, ls=st["ls"],
                        solid_joinstyle="round", solid_capstyle="round",
                        zorder=5,
                        path_effects=[pe.Stroke(linewidth=halo_lw,
                                                foreground="white"),
                                      pe.Normal()])
        ax.scatter([angles[i] for i in present], [rv[i] for i in present],
                   s=marker_s, color=st["color"], marker=st["marker"],
                   edgecolors="white", linewidths=edge_lw, zorder=6)

    # Percentile labels for the rings, in subtle white pills (full only).
    if show_ring_labels:
        label_ang = math.pi / n
        ring_bbox = dict(boxstyle="round,pad=0.22", fc="white", ec=HAIRLINE,
                         lw=0.5, alpha=0.92)
        for pos, p in rings:
            ax.text(label_ang, pos - axis_min, str(p), fontsize=7.5, color=MUTED,
                    ha="center", va="center", zorder=7, bbox=ring_bbox)

    # Percentile value at each vertex, in a crisp white pill. With one
    # series the pill sits outward of the point; with two, series 1 sits
    # outward and series 2 inward so they never collide. In compact
    # two-series panels the pills are dropped (markers plus the shared
    # legend stay), keeping small panels readable.
    if not (compact and len(series) > 1):
        vtx_bbox = dict(boxstyle="round,pad=0.26", fc="white", ec="#c6d1d6",
                        lw=0.6, alpha=0.97)
        for si, ser in enumerate(series):
            st = _series_style(si, accent, accent_deep)
            fs = vtx_fs if len(series) == 1 else max(6.4, vtx_fs - 1.4)
            for i, (z, disp) in enumerate(zip(ser["z"], ser["disp"])):
                if z is None or disp is None:
                    continue
                r = _pos_of_z(z, mode) - axis_min
                off = 0.1 * span
                if si == 0:
                    lr = r + off if (r + off) <= span * 0.965 else r - off
                else:
                    lr = r - off if (r - off) >= span * 0.04 else r + off
                ax.text(angles[i], lr, disp, fontsize=fs, fontweight="bold",
                        color=st["deep"], ha="center", va="center", zorder=8,
                        bbox=vtx_bbox)

    # Sub-function names just outside the ring, aligned by direction.
    name_r = span * name_rf
    for a, lab in zip(angles, labels):
        v = theta_off - a   # on-screen angle (clockwise direction)
        vx, vy = math.cos(v), math.sin(v)
        ha = "left" if vx > 0.25 else "right" if vx < -0.25 else "center"
        va = "bottom" if vy > 0.25 else "top" if vy < -0.25 else "center"
        ax.text(a, name_r, _wrap(lab, name_w), fontsize=name_fs, color=INK,
                ha=ha, va=va, zorder=7, clip_on=False)


def _series_legend_handles(series_labels: list[str], accent: str,
                           accent_deep: str) -> list:
    """Proxy line handles for the series legend."""
    from matplotlib.lines import Line2D
    handles = []
    for si, lab in enumerate(series_labels):
        st = _series_style(si, accent, accent_deep)
        handles.append(Line2D([0], [0], color=st["color"], lw=2.0,
                              ls=st["ls"], marker=st["marker"],
                              markerfacecolor=st["color"],
                              markeredgecolor="white", markersize=7,
                              label=lab))
    return handles


def _radar_figure(labels: list[str],
                  series: list[dict],
                  personal_mean_z: Optional[float],
                  title: str,
                  lang: str = "fr",
                  radial_mode: str = "z",
                  subtitle: Optional[str] = None,
                  theme=None) -> plt.Figure:
    """Build a single, report-grade radar figure (on-screen and exports)."""
    _bands, accent, accent_deep = resolve_theme(theme)
    fig = plt.figure(figsize=(7.0, 7.3))
    ax = fig.add_subplot(111, projection="polar")
    fig.subplots_adjust(top=0.80, bottom=0.07, left=0.08, right=0.92)
    _draw_radar(ax, labels, series, personal_mean_z,
                lang, radial_mode, compact=False, theme=theme)
    # A clean, prominent title in the theme accent; muted subtitle beneath.
    fig.suptitle(title, y=0.972, fontsize=18, fontweight="bold",
                 color=accent_deep)
    if subtitle:
        fig.text(0.5, 0.926, subtitle, ha="center", va="center",
                 fontsize=10.5, color=MUTED)
    if len(series) > 1:
        fig.legend(handles=_series_legend_handles(
                       [s["label"] for s in series], accent, accent_deep),
                   loc="lower center", ncol=len(series), frameon=False,
                   fontsize=9.5, bbox_to_anchor=(0.5, 0.005))
    return fig


# --- 4. Panel specs and public figure builders ----------------

def build_panels(profiles: list[ProfileResult],
                 lang: str = "fr",
                 show_summary: bool = True) -> list[dict]:
    """Build radar panel specs from one profile per series.

    Domains are aligned by index (every series comes from the same
    battery). Within a domain, the axes are the union of the measures
    administered in at least one series, in battery order; a series
    missing a measure gets None at that axis. Panels need at least
    three axes; smaller domains carry no figure (their scores stay in
    the table).

    Returns dicts: {"title", "labels", "series": [{"label","z","disp"}]}.
    The series label is filled in by the caller (see figure builders).
    """
    if not profiles:
        return []
    panels: list[dict] = []

    # Summary panel: each axis is a domain with data in >= 1 series.
    if show_summary:
        keys: list[tuple[str, str]] = []
        for prof in profiles:
            for d in prof.domains:
                if d.mean_z is not None and (d.name_fr, d.name_en) not in keys:
                    keys.append((d.name_fr, d.name_en))
        if len(keys) >= 3:
            sers = []
            for prof in profiles:
                by_key = {(d.name_fr, d.name_en): d for d in prof.domains}
                zs, disp = [], []
                for k in keys:
                    d = by_key.get(k)
                    if d is not None and d.mean_z is not None:
                        zs.append(d.mean_z)
                        disp.append(format_percentile(d.mean_percentile))
                    else:
                        zs.append(None)
                        disp.append(None)
                sers.append({"z": zs, "disp": disp})
            labels = [k[0] if lang == "fr" else k[1] for k in keys]
            title = "Synthèse" if lang == "fr" else "Summary"
            panels.append({"title": title, "labels": labels, "series": sers})

    # One panel per domain (aligned by index across series).
    ndom = max(len(p.domains) for p in profiles)
    for di in range(ndom):
        variants = [p.domains[di] if di < len(p.domains) else None
                    for p in profiles]
        mkeys: list[tuple[str, str]] = []
        for v in variants:
            if v is None:
                continue
            for m in v.measures:
                if (m.name_fr, m.name_en) not in mkeys:
                    mkeys.append((m.name_fr, m.name_en))
        if len(mkeys) < 3:
            continue
        sers = []
        for v in variants:
            by_key = {} if v is None else {(m.name_fr, m.name_en): m
                                           for m in v.measures}
            zs, disp = [], []
            for k in mkeys:
                m = by_key.get(k)
                if m is not None:
                    zs.append(m.z)
                    disp.append(m.percentile_display)
                else:
                    zs.append(None)
                    disp.append(None)
            sers.append({"z": zs, "disp": disp})
        first = next(v for v in variants if v is not None)
        labels = [k[0] if lang == "fr" else k[1] for k in mkeys]
        panels.append({"title": first.name(lang), "labels": labels,
                       "series": sers, "domain_index": di})
    return panels


def _mean_subtitle(profiles: list[ProfileResult], series_labels: list[str],
                   domain_index: Optional[int], lang: str) -> Optional[str]:
    """Subtitle giving the domain (or overall) mean per series."""
    parts = []
    for prof, lab in zip(profiles, series_labels):
        if domain_index is None:
            mz = prof.personal_mean_z
            pct = None if mz is None else z_to_percentile(mz)
        else:
            dom = (prof.domains[domain_index]
                   if domain_index < len(prof.domains) else None)
            pct = None if dom is None else dom.mean_percentile
        if pct is None:
            continue
        phrase = _pctl_phrase(format_percentile(pct), lang)
        parts.append(phrase if len(profiles) == 1 else f"{lab}: {phrase}")
    if not parts:
        return None
    joined = ", ".join(parts)
    if domain_index is None:
        return (f"Moyenne globale : {joined}" if lang == "fr"
                else f"Overall mean: {joined}")
    return (f"Moyenne du domaine : {joined}" if lang == "fr"
            else f"Domain mean: {joined}")


def _attach_labels(panel: dict, series_labels: list[str]) -> list[dict]:
    """Attach series labels to a panel's series dicts."""
    out = []
    for si, ser in enumerate(panel["series"]):
        lab = series_labels[si] if si < len(series_labels) else f"S{si + 1}"
        out.append({"label": lab, "z": ser["z"], "disp": ser["disp"]})
    return out


def domain_figure(profiles: list[ProfileResult],
                  series_labels: list[str],
                  domain_index: int,
                  lang: str = "fr",
                  radial_mode: str = "z",
                  theme=None) -> tuple[Optional[plt.Figure], str]:
    """Radar for one domain, overlaying every series. Returns
    (figure, kind); kind 'none' when fewer than three axes have data."""
    panels = build_panels(profiles, lang, show_summary=False)
    panel = next((p for p in panels if p.get("domain_index") == domain_index),
                 None)
    if panel is None:
        return None, "none"
    pmz = profiles[0].personal_mean_z if len(profiles) == 1 else None
    subtitle = _mean_subtitle(profiles, series_labels, domain_index, lang)
    fig = _radar_figure(panel["labels"], _attach_labels(panel, series_labels),
                        pmz, panel["title"], lang, radial_mode, subtitle,
                        theme)
    return fig, "radar"


def summary_figure(profiles: list[ProfileResult],
                   series_labels: list[str],
                   lang: str = "fr",
                   radial_mode: str = "z",
                   theme=None) -> tuple[Optional[plt.Figure], str]:
    """Cross-domain summary radar (domain means), overlaying series."""
    panels = build_panels(profiles, lang, show_summary=True)
    panel = next((p for p in panels if "domain_index" not in p), None)
    if panel is None:
        return None, "none"
    pmz = profiles[0].personal_mean_z if len(profiles) == 1 else None
    title = "Synthèse par domaine" if lang == "fr" else "Domain summary"
    subtitle = _mean_subtitle(profiles, series_labels, None, lang)
    fig = _radar_figure(panel["labels"], _attach_labels(panel, series_labels),
                        pmz, title, lang, radial_mode, subtitle, theme)
    return fig, "radar"


def composite_figure(profiles: list[ProfileResult],
                     series_labels: list[str],
                     lang: str = "fr",
                     radial_mode: str = "z",
                     show_summary: bool = True,
                     theme=None) -> plt.Figure:
    """Every radar (summary first, then domains) as one compact grid of
    at most two rows, for the top of the Word report."""
    panels = build_panels(profiles, lang, show_summary)
    npan = len(panels)
    if npan == 0:
        return plt.figure(figsize=(7.2, 1.6))

    _bands, accent, accent_deep = resolve_theme(theme)
    # Never more than two rows: grow columns instead.
    cols = max(1, math.ceil(npan / 2))
    rows = math.ceil(npan / cols)
    multi = len(profiles) > 1
    legend_pad = 0.5 if multi else 0.0
    fig = plt.figure(figsize=(7.2, 0.3 + rows * 2.55 + legend_pad))

    for idx, panel in enumerate(panels):
        ax = fig.add_subplot(rows, cols, idx + 1, projection="polar")
        pmz = profiles[0].personal_mean_z if len(profiles) == 1 else None
        _draw_radar(ax, panel["labels"], _attach_labels(panel, series_labels),
                    pmz, lang, radial_mode, compact=True, theme=theme)
        ax.set_title(panel["title"], fontsize=10.5, fontweight="bold",
                     color=accent_deep, pad=9)

    bottom = 0.10 if multi else 0.04
    fig.subplots_adjust(top=0.94, bottom=bottom, left=0.05, right=0.95,
                        hspace=0.50, wspace=0.30)
    if multi:
        fig.legend(handles=_series_legend_handles(series_labels, accent,
                                                  accent_deep),
                   loc="lower center", ncol=len(series_labels), frameon=False,
                   fontsize=9)
    return fig


# --- 5. Rendering to bytes -----------------------------------

def fig_to_base64_png(fig: plt.Figure, dpi: int = 300) -> str:
    """Render a figure to a base64-encoded PNG string (300 DPI default).

    Used for on-screen display (the web UI builds an <img> from it) and,
    at the same resolution, for the Word export.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def fig_to_png_bytes(fig: plt.Figure, dpi: int = 300) -> bytes:
    """Render a figure to raw PNG bytes (for embedding in the .docx)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white")
    return buf.getvalue()


def fig_to_svg_text(fig: plt.Figure) -> str:
    """Render a figure to SVG markup (for the download button)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    return buf.getvalue().decode("utf-8")


def close_fig(fig: plt.Figure) -> None:
    """Release a figure once it has been rendered to bytes."""
    plt.close(fig)


# --- 6. Manual smoke test ------------------------------------

if __name__ == "__main__":
    # Build figures from the engine demo and write them next to this file
    # so the output can be eyeballed. No network, no persistence of PHI.
    from engine import DomainInput, MeasureInput, process_profile

    demo = [
        DomainInput("Attention / Vitesse", "Attention / Speed", [
            MeasureInput("Soutenue", "Sustained", 8, "scaled"),
            MeasureInput("Sélective", "Selective", 50, "t"),
            MeasureInput("Divisée", "Divided", 5, "percentile"),
            MeasureInput("Vigilance", "Vigilance", -0.5, "z"),
            MeasureInput("Vitesse de traitement", "Processing speed", 115, "standard"),
        ]),
        DomainInput("Mémoire", "Memory", [
            MeasureInput("À court terme", "Short-term", 25, "percentile"),
            MeasureInput("À long terme", "Long-term", 1.5, "z"),
        ]),
    ]
    result = process_profile(demo, "DEMO-01", 1.0)

    # Single series composite.
    fig_c = composite_figure([result], ["T1"], "fr")
    with open("smoke_composite.png", "wb") as fh:
        fh.write(fig_to_png_bytes(fig_c, dpi=150))
    close_fig(fig_c)
    print("composite written")

    # Two-series overlay (second series slightly shifted, one gap).
    demo2 = [DomainInput(d.name_fr, d.name_en, [
        MeasureInput(m.name_fr, m.name_en, m.value, m.metric)
        for m in d.measures[:-1]]) for d in demo]
    result2 = process_profile(demo2, "DEMO-01", 1.0)
    fig_o, kind_o = domain_figure([result, result2], ["T1", "T2"], 0, "fr")
    if fig_o is not None:
        with open("smoke_overlay.png", "wb") as fh:
            fh.write(fig_to_png_bytes(fig_o, dpi=150))
        close_fig(fig_o)
    print("overlay:", kind_o)

    print("Smoke figures written.")
