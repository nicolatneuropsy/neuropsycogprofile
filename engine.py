# ============================================================
# Cognitive profile scoring engine
# Converts neuropsychological scores to percentiles, classifies
# them into clinical bands, and flags relative strengths and
# weaknesses (descriptive, non-inferential).
# Author: [your name]
# Date: 2026-06-21
# ============================================================
#
# Design notes:
# - Every supported input metric (z, percentile, scaled, standard,
#   T) is first converted to a z score, then to an output percentile
#   via the normal CDF. The table is therefore always in percentiles.
# - Strength/weakness flagging is DESCRIPTIVE, not inferential: a
#   measure is flagged only by how far its z sits from the patient's
#   own mean z. No claim of statistical significance is made anywhere.
#   The flag logic is isolated so a reliable-difference test (SEM
#   based) can be added later without touching the rest of the code.
# - No third-party dependencies: the normal CDF uses math.erf and the
#   inverse normal CDF uses Acklam's rational approximation, accurate
#   to roughly 1e-9, which keeps packaging small and avoids scipy.

from __future__ import annotations

from dataclasses import dataclass, field
from math import erf, sqrt, log
from typing import Optional

# --- 0. Constants --------------------------------------------

# Supported input metrics and their (mean, sd) on the standard scale.
# "z" and "percentile" are handled separately (percentile needs the
# inverse normal CDF, z is the identity).
METRIC_PARAMS = {
    "scaled": (10.0, 3.0),     # subtest scaled scores
    "standard": (100.0, 15.0), # index / standard / IQ scores
    "t": (50.0, 10.0),         # T scores
}
SUPPORTED_METRICS = ("z", "percentile", "scaled", "standard", "t")

# Default threshold (in z units) for flagging a measure as a relative
# strength or weakness versus the patient's own mean. Configurable.
DEFAULT_FLAG_THRESHOLD = 1.0

# Clinical descriptive bands, keyed by an upper-exclusive percentile
# cutoff, following the conventional Wechsler-style classification.
# Each entry: (upper_cutoff_exclusive, label_fr, label_en).
BANDS = [
    (2.0,   "Extrêmement bas",   "Extremely low"),
    (9.0,   "Limite",            "Borderline"),
    (25.0,  "Moyenne inférieure","Low average"),
    (75.0,  "Moyenne",           "Average"),
    (91.0,  "Moyenne supérieure","High average"),
    (98.0,  "Supérieur",         "Superior"),
    (100.01,"Très supérieur",    "Very superior"),
]

# Percentiles are clamped away from 0 and 100 so that conversions to
# and from z never produce infinities. 0.05 / 99.95 corresponds to
# roughly +/- 3.29 z, which covers any realistic clinical score.
PCTL_MIN = 0.05
PCTL_MAX = 99.95


# --- 1. Normal distribution helpers --------------------------

def phi(z: float) -> float:
    """Standard normal CDF. Returns P(Z <= z)."""
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def phi_inverse(p: float) -> float:
    """Inverse standard normal CDF (probit) for p in (0, 1).

    Acklam's rational approximation. Absolute error < ~1.15e-9.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("phi_inverse requires 0 < p < 1")

    # Coefficients for the rational approximation.
    a = (-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00)

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        # Lower tail.
        q = sqrt(-2.0 * log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    elif p <= p_high:
        # Central region.
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        # Upper tail.
        q = sqrt(-2.0 * log(1.0 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)


# --- 2. Metric conversion ------------------------------------

def to_z(value: float, metric: str) -> float:
    """Convert a score on any supported metric to a z score."""
    metric = metric.lower()
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"Unsupported metric '{metric}'. "
                         f"Use one of {SUPPORTED_METRICS}.")
    if metric == "z":
        return float(value)
    if metric == "percentile":
        p = min(max(float(value), PCTL_MIN), PCTL_MAX)  # clamp to (0,100)
        return phi_inverse(p / 100.0)
    mean, sd = METRIC_PARAMS[metric]
    return (float(value) - mean) / sd


def z_to_percentile(z: float) -> float:
    """Convert a z score to a percentile in (0, 100)."""
    return min(max(phi(z) * 100.0, PCTL_MIN), PCTL_MAX)


def format_percentile(p: float) -> str:
    """Human-readable percentile for the report table."""
    if p < 1.0:
        return "<1"
    if p > 99.0:
        return ">99"
    return str(round(p))


def classify_band(p: float) -> tuple[str, str]:
    """Return (label_fr, label_en) for a given percentile."""
    for cutoff, label_fr, label_en in BANDS:
        if p < cutoff:
            return label_fr, label_en
    return BANDS[-1][1], BANDS[-1][2]  # safety fallback


# --- 3. Data model -------------------------------------------

@dataclass
class MeasureInput:
    """A single sub-function as entered by the clinician."""
    name_fr: str
    name_en: str
    value: float
    metric: str  # one of SUPPORTED_METRICS


@dataclass
class MeasureResult:
    """A single sub-function after processing."""
    name_fr: str
    name_en: str
    z: float
    percentile: float
    percentile_display: str
    band_fr: str
    band_en: str
    flag: str  # "strength" | "weakness" | "within"

    def name(self, lang: str) -> str:
        return self.name_fr if lang == "fr" else self.name_en

    def band(self, lang: str) -> str:
        return self.band_fr if lang == "fr" else self.band_en


@dataclass
class DomainInput:
    name_fr: str
    name_en: str
    measures: list[MeasureInput] = field(default_factory=list)


@dataclass
class DomainResult:
    name_fr: str
    name_en: str
    measures: list[MeasureResult]
    mean_z: Optional[float]
    mean_percentile: Optional[float]

    def name(self, lang: str) -> str:
        return self.name_fr if lang == "fr" else self.name_en


@dataclass
class ProfileResult:
    patient_id: str
    domains: list[DomainResult]
    personal_mean_z: Optional[float]
    threshold: float


# --- 4. Profile processing -----------------------------------

def process_profile(domains: list[DomainInput],
                    patient_id: str = "",
                    threshold: float = DEFAULT_FLAG_THRESHOLD) -> ProfileResult:
    """Convert every measure, classify bands, and flag strengths and
    weaknesses relative to the patient's own mean z.

    Missing measures (value is None) are skipped, never imputed.
    """
    # First pass: convert every measure to z and percentile.
    converted: list[tuple[DomainInput, list[MeasureResult]]] = []
    all_z: list[float] = []
    for dom in domains:
        rows: list[MeasureResult] = []
        for m in dom.measures:
            if m.value is None:
                continue  # not administered
            z = to_z(m.value, m.metric)
            p = z_to_percentile(z)
            band_fr, band_en = classify_band(p)
            rows.append(MeasureResult(
                name_fr=m.name_fr, name_en=m.name_en,
                z=z, percentile=p, percentile_display=format_percentile(p),
                band_fr=band_fr, band_en=band_en,
                flag="within",  # set in second pass
            ))
            all_z.append(z)
        converted.append((dom, rows))

    # Patient's own mean z across all administered measures.
    personal_mean_z = sum(all_z) / len(all_z) if all_z else None

    # Second pass: descriptive flag relative to the personal mean.
    domain_results: list[DomainResult] = []
    for dom, rows in converted:
        for r in rows:
            if personal_mean_z is None:
                r.flag = "within"
            elif r.z - personal_mean_z >= threshold:
                r.flag = "strength"
            elif r.z - personal_mean_z <= -threshold:
                r.flag = "weakness"
            else:
                r.flag = "within"
        if rows:
            dmean_z = sum(r.z for r in rows) / len(rows)
            dmean_p = z_to_percentile(dmean_z)
        else:
            dmean_z, dmean_p = None, None
        domain_results.append(DomainResult(
            name_fr=dom.name_fr, name_en=dom.name_en,
            measures=rows, mean_z=dmean_z, mean_percentile=dmean_p,
        ))

    return ProfileResult(
        patient_id=patient_id, domains=domain_results,
        personal_mean_z=personal_mean_z, threshold=threshold,
    )


# --- 5. Draft interpretive text (template-based, local) ------

def _join(items: list[str], lang: str) -> str:
    """Grammatical list join in the chosen language."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conj = " et " if lang == "fr" else " and "
    return ", ".join(items[:-1]) + conj + items[-1]


def _pctl_phrase(display: str, lang: str) -> str:
    """Format a percentile with the correct ordinal/wording per language.

    Non-numeric displays such as '<1' and '>99' are kept verbatim.
    """
    if not display.isdigit():
        return f"{display} percentile"
    n = int(display)
    if lang == "fr":
        suffix = "er" if n == 1 else "e"
        return f"{n}{suffix} percentile"
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix} percentile"


def generate_report_text(profile: ProfileResult, lang: str = "fr") -> str:
    """Build a hedged, clinician-reviewable draft paragraph.

    The text is generated entirely from the numbers on this machine.
    It never uses the word 'significant', because the flagging is
    descriptive (relative to the patient's own average), not the
    result of an inferential test. Measure names keep the casing the
    clinician chose, so acronyms such as 'MdeT' are preserved.
    """
    strengths = [r for d in profile.domains for r in d.measures if r.flag == "strength"]
    weaknesses = [r for d in profile.domains for r in d.measures if r.flag == "weakness"]

    def describe(r: MeasureResult) -> str:
        # Keep the name as written; only the band label is lowercased.
        name = r.name_fr if lang == "fr" else r.name_en
        band = (r.band_fr if lang == "fr" else r.band_en).lower()
        return f"{name} ({_pctl_phrase(r.percentile_display, lang)}, {band})"

    if lang == "fr":
        header = ("Brouillon généré automatiquement à partir des percentiles et "
                  "d'une comparaison descriptive à la moyenne propre du patient. "
                  "À réviser et à valider selon le jugement clinique.")
        if profile.personal_mean_z is None:
            return header + "\n\nAucune donnée disponible."
        parts = [header, ""]
        if strengths:
            parts.append("Forces relatives : le profil se distingue par "
                         + _join([describe(r) for r in strengths], lang)
                         + ", au-dessus de la moyenne propre du patient.")
        if weaknesses:
            verb = "se situe" if len(weaknesses) == 1 else "se situent"
            parts.append("Faiblesses relatives : "
                         + _join([describe(r) for r in weaknesses], lang)
                         + f" {verb} sous la moyenne propre du patient.")
        if not strengths and not weaknesses:
            parts.append("Aucune force ni faiblesse relative ne ressort selon le "
                         f"seuil retenu (écart de {profile.threshold:g} écart-type "
                         "par rapport à la moyenne du patient). Le profil apparaît "
                         "relativement homogène.")
        return "\n".join(parts).strip()

    # English
    header = ("Automatically generated draft based on percentiles and a descriptive "
              "comparison to the patient's own average. To be reviewed and validated "
              "with clinical judgement.")
    if profile.personal_mean_z is None:
        return header + "\n\nNo data available."
    parts = [header, ""]
    if strengths:
        parts.append("Relative strengths: the profile stands out on "
                     + _join([describe(r) for r in strengths], lang)
                     + ", above the patient's own average.")
    if weaknesses:
        verb = "falls" if len(weaknesses) == 1 else "fall"
        parts.append("Relative weaknesses: "
                     + _join([describe(r) for r in weaknesses], lang)
                     + f" {verb} below the patient's own average.")
    if not strengths and not weaknesses:
        parts.append("No relative strength or weakness emerges at the chosen "
                     f"threshold ({profile.threshold:g} standard deviation from the "
                     "patient's average). The profile appears relatively even.")
    return "\n".join(parts).strip()


# --- 6. Self-test / demonstration ----------------------------

if __name__ == "__main__":
    # Sanity checks on the conversions.
    assert format_percentile(z_to_percentile(0.0)) == "50"
    assert to_z(100, "standard") == 0.0
    assert to_z(10, "scaled") == 0.0
    assert to_z(50, "t") == 0.0
    assert abs(to_z(50, "percentile")) < 1e-6      # 50th pct -> z 0
    assert abs(to_z(84.13, "percentile") - 1.0) < 1e-3  # ~84th -> z 1
    assert round(z_to_percentile(1.0)) == 84
    assert round(z_to_percentile(-2.0)) == 2
    print("Conversion self-tests passed.\n")

    # A worked example mixing input metrics, using the default template.
    demo = [
        DomainInput("Attention / Vitesse", "Attention / Speed", [
            MeasureInput("Soutenue", "Sustained", 8, "scaled"),        # ~25th
            MeasureInput("Sélective", "Selective", 50, "t"),           # 50th
            MeasureInput("Divisée", "Divided", 5, "percentile"),       # ~5th
            MeasureInput("Vigilance", "Vigilance", -0.5, "z"),         # ~31st
        ]),
        DomainInput("Fonctions exécutives", "Executive functions", [
            MeasureInput("Inhibition", "Inhibition", 115, "standard"), # ~84th
            MeasureInput("Flexibilité", "Flexibility", 50, "percentile"),
            MeasureInput("Planification/organisation", "Planning", 9, "scaled"),
            MeasureInput("Régulation émotionnelle", "Emotional regulation", 40, "t"),
        ]),
        DomainInput("Mémoire", "Memory", [
            MeasureInput("À court terme", "Short-term", 25, "percentile"),
            MeasureInput("À long terme", "Long-term", 1.5, "z"),       # ~93rd
            MeasureInput("MdeT visuospatiale", "Visuospatial WM", 11, "scaled"),
            MeasureInput("MdeT auditive", "Auditory WM", 60, "t"),     # ~84th
        ]),
    ]

    result = process_profile(demo, patient_id="DEMO-01", threshold=1.0)
    print(f"Patient: {result.patient_id}   "
          f"personal mean z = {result.personal_mean_z:+.2f}\n")

    for d in result.domains:
        print(f"== {d.name_en}  (domain mean pctl "
              f"{format_percentile(d.mean_percentile)}) ==")
        for r in d.measures:
            tag = {"strength": "  <-- relative strength",
                   "weakness": "  <-- relative weakness",
                   "within": ""}[r.flag]
            print(f"  {r.name_en:<22} z={r.z:+.2f}  "
                  f"pctl={r.percentile_display:>3}  "
                  f"{r.band_en}{tag}")
        print()

    print("------ Draft text (EN) ------")
    print(generate_report_text(result, "en"))
    print("\n------ Draft text (FR) ------")
    print(generate_report_text(result, "fr"))
