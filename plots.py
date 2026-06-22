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
    DomainResult,
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
}
DEFAULT_THEME = "teal"

# Default module-level palette (the default theme), used when no theme is
# given. Kept as module constants for backward compatibility.
BAND_COLORS = THEMES[DEFAULT_THEME]["bands"]
ACCENT = THEMES[DEFAULT_THEME]["accent"]
ACCENT_DEEP = THEMES[DEFAULT_THEME]["accent_deep"]
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

def _draw_radar(ax, labels: list[str], z_values: list[float],
                pctl_displays: list[str], personal_mean_z: Optional[float],
                lang: str = "fr", radial_mode: str = "z",
                compact: bool = False, theme=None) -> None:
    """Draw a report-grade radar onto a provided polar Axes.

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

    # Faint ring at the patient's personal mean.
    if personal_mean_z is not None:
        mpos = _clamp(_pos_of_z(personal_mean_z, mode), axis_min, axis_max)
        ax.plot(theta, np.full_like(theta, mpos - axis_min),
                color=accent, lw=1.1, ls=(0, (3, 3)), alpha=0.55, zorder=3)

    # Patient polygon: subtle fill, white-haloed line, clean markers.
    rvals = [_pos_of_z(z, mode) - axis_min for z in z_values]
    ang_c = angles + [angles[0]]
    r_c = rvals + [rvals[0]]
    ax.fill(ang_c, r_c, color=accent, alpha=0.13, zorder=4)
    ax.plot(ang_c, r_c, color=accent, lw=poly_lw, solid_joinstyle="round",
            solid_capstyle="round", zorder=5,
            path_effects=[pe.Stroke(linewidth=halo_lw, foreground="white"),
                          pe.Normal()])
    ax.scatter(angles, rvals, s=marker_s, color=accent, edgecolors="white",
               linewidths=edge_lw, zorder=6)

    # Percentile labels for the rings, in subtle white pills (full only).
    if show_ring_labels:
        label_ang = math.pi / n
        ring_bbox = dict(boxstyle="round,pad=0.22", fc="white", ec=HAIRLINE,
                         lw=0.5, alpha=0.92)
        for pos, p in rings:
            ax.text(label_ang, pos - axis_min, str(p), fontsize=7.5, color=MUTED,
                    ha="center", va="center", zorder=7, bbox=ring_bbox)

    # Percentile value at each vertex, in a crisp white pill.
    vtx_bbox = dict(boxstyle="round,pad=0.26", fc="white", ec="#c6d1d6",
                    lw=0.6, alpha=0.97)
    for ang, r, disp in zip(angles, rvals, pctl_displays):
        off = 0.1 * span
        lr = r + off if (r + off) <= span * 0.965 else r - off
        ax.text(ang, lr, disp, fontsize=vtx_fs, fontweight="bold",
                color=accent_deep, ha="center", va="center", zorder=8,
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


def _radar_figure(labels: list[str],
                  z_values: list[float],
                  pctl_displays: list[str],
                  personal_mean_z: Optional[float],
                  title: str,
                  lang: str = "fr",
                  radial_mode: str = "z",
                  subtitle: Optional[str] = None,
                  theme=None) -> plt.Figure:
    """Build a single, report-grade radar figure (on-screen and exports)."""
    _bands, _accent, accent_deep = resolve_theme(theme)
    fig = plt.figure(figsize=(7.0, 7.3))
    ax = fig.add_subplot(111, projection="polar")
    fig.subplots_adjust(top=0.80, bottom=0.05, left=0.08, right=0.92)
    _draw_radar(ax, labels, z_values, pctl_displays, personal_mean_z,
                lang, radial_mode, compact=False, theme=theme)
    # A clean, prominent title in the theme accent; muted subtitle beneath.
    fig.suptitle(title, y=0.972, fontsize=18, fontweight="bold",
                 color=accent_deep)
    if subtitle:
        fig.text(0.5, 0.926, subtitle, ha="center", va="center",
                 fontsize=10.5, color=MUTED)
    return fig


# --- 4. Public figure builders -------------------------------

def domain_figure(domain: DomainResult,
                  personal_mean_z: Optional[float] = None,
                  lang: str = "fr",
                  radial_mode: str = "z",
                  theme=None) -> tuple[Optional[plt.Figure], str]:
    """Return (figure, kind) for one domain.

    A radar needs at least three sub-functions to be meaningful. With
    fewer, no figure is produced (kind 'none'); the table still carries
    those scores.
    """
    measures = domain.measures
    if len(measures) < 3:
        return None, "none"
    labels = [m.name(lang) for m in measures]
    zs = [m.z for m in measures]
    disp = [m.percentile_display for m in measures]
    subtitle = None
    if domain.mean_percentile is not None:
        phrase = _pctl_phrase(format_percentile(domain.mean_percentile), lang)
        subtitle = (f"Moyenne du domaine : {phrase}" if lang == "fr"
                    else f"Domain mean: {phrase}")
    fig = _radar_figure(labels, zs, disp, personal_mean_z,
                        domain.name(lang), lang, radial_mode, subtitle, theme)
    return fig, "radar"


def summary_figure(profile: ProfileResult,
                   lang: str = "fr",
                   radial_mode: str = "z",
                   theme=None) -> tuple[Optional[plt.Figure], str]:
    """Return (figure, kind) for the cross-domain summary, using each
    domain's mean. A radar needs at least three domains; with fewer, no
    figure is produced (kind 'none')."""
    doms = [d for d in profile.domains if d.mean_z is not None]
    if len(doms) < 3:
        return None, "none"
    labels = [d.name(lang) for d in doms]
    title = "Synthèse par domaine" if lang == "fr" else "Domain summary"
    subtitle = None
    if profile.personal_mean_z is not None:
        phrase = _pctl_phrase(
            format_percentile(z_to_percentile(profile.personal_mean_z)), lang)
        subtitle = (f"Moyenne globale : {phrase}" if lang == "fr"
                    else f"Overall mean: {phrase}")
    zs = [d.mean_z for d in doms]
    disp = [format_percentile(d.mean_percentile) for d in doms]
    fig = _radar_figure(labels, zs, disp, profile.personal_mean_z,
                        title, lang, radial_mode, subtitle, theme)
    return fig, "radar"


def composite_figure(profile: ProfileResult,
                     lang: str = "fr",
                     radial_mode: str = "z",
                     show_summary: bool = True,
                     theme=None) -> plt.Figure:
    """Lay every figure (summary first, then each domain) onto a single
    page as a tidy grid, for the visual page of the Word report."""
    pmz = profile.personal_mean_z

    # Build the ordered list of radar panels (summary first, then each
    # domain with at least three sub-functions). Smaller domains carry no
    # figure; their scores remain in the table.
    panels: list[dict] = []
    sdoms = [d for d in profile.domains if d.mean_z is not None]
    if show_summary and len(sdoms) >= 3:
        panels.append({"title": "Synthèse" if lang == "fr" else "Summary",
                       "labels": [d.name(lang) for d in sdoms],
                       "z": [d.mean_z for d in sdoms],
                       "disp": [format_percentile(d.mean_percentile) for d in sdoms]})
    for d in profile.domains:
        if len(d.measures) >= 3:
            panels.append({"title": d.name(lang),
                           "labels": [m.name(lang) for m in d.measures],
                           "z": [m.z for m in d.measures],
                           "disp": [m.percentile_display for m in d.measures]})

    npan = len(panels)
    if npan == 0:
        return plt.figure(figsize=(7.2, 2.0))

    _bands, _accent, accent_deep = resolve_theme(theme)
    cols = 1 if npan == 1 else (2 if npan <= 6 else 3)
    rows = math.ceil(npan / cols)
    fig = plt.figure(figsize=(7.4, 0.3 + rows * 3.2))

    for idx, panel in enumerate(panels):
        ax = fig.add_subplot(rows, cols, idx + 1, projection="polar")
        _draw_radar(ax, panel["labels"], panel["z"], panel["disp"], pmz,
                    lang, radial_mode, compact=True, theme=theme)
        ax.set_title(panel["title"], fontsize=13, fontweight="bold",
                     color=accent_deep, pad=11)

    fig.subplots_adjust(top=0.955, bottom=0.035, left=0.05, right=0.95,
                        hspace=0.46, wspace=0.28)
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

    fig_c = composite_figure(result, "fr")
    with open("smoke_composite.png", "wb") as fh:
        fh.write(fig_to_png_bytes(fig_c, dpi=150))
    close_fig(fig_c)
    print("composite written")

    for idx, dom in enumerate(result.domains):
        fig_d, kind_d = domain_figure(dom, result.personal_mean_z, "fr")
        if fig_d is None:
            print(f"domain {idx} ({dom.name_en}): {kind_d} (no figure)")
            continue
        with open(f"smoke_domain_{idx}.png", "wb") as fh:
            fh.write(fig_to_png_bytes(fig_d, dpi=150))
        close_fig(fig_d)
        print(f"domain {idx} ({dom.name_en}): {kind_d}")

    print("Smoke figures written.")
