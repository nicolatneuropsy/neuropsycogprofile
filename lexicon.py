# ============================================================
# Bilingual lexicon of cognitive functions.
#
# Short, original clinical definitions (FR and EN) for the functions of
# the default battery and the optional add-on domains. Written in-house
# in generic clinical wording so the app can ship them without copyright
# concerns; every definition is editable in the UI before export, so a
# clinician can substitute preferred wording (for example from their own
# institutional references) for personal use.
#
# Terms are matched to battery sub-functions by name (case-insensitive,
# FR or EN). Renamed or custom sub-functions simply have no built-in
# definition; the UI hides them from the lexicon checklist.
# ============================================================

from __future__ import annotations

import unicodedata

# Each entry: key, name_fr, name_en, def_fr, def_en.
TERMS = [
    # --- Attention / speed ---
    {"key": "sustained",
     "name_fr": "Soutenue", "name_en": "Sustained",
     "def_fr": "Capacite a maintenir l'attention sur une tache pendant une periode prolongee, sans decrement marque du rendement.",
     "def_en": "Ability to maintain attention on a task over an extended period without a marked decline in performance."},
    {"key": "selective",
     "name_fr": "Sélective", "name_en": "Selective",
     "def_fr": "Capacite a diriger l'attention vers l'information pertinente tout en resistant a la distraction.",
     "def_en": "Ability to direct attention toward relevant information while resisting distraction."},
    {"key": "divided",
     "name_fr": "Divisée", "name_en": "Divided",
     "def_fr": "Capacite a traiter simultanement plusieurs sources d'information ou a mener deux taches de front.",
     "def_en": "Ability to process several sources of information at once or to carry out two tasks simultaneously."},
    {"key": "vigilance",
     "name_fr": "Vigilance", "name_en": "Vigilance",
     "def_fr": "Capacite a detecter des stimulus rares ou imprevisibles au fil du temps, en maintenant un etat d'alerte.",
     "def_en": "Ability to detect rare or unpredictable stimuli over time while maintaining an alert state."},
    {"key": "processing-speed",
     "name_fr": "Vitesse de traitement", "name_en": "Processing speed",
     "def_fr": "Rapidite avec laquelle l'information est percue, traitee et une reponse est produite.",
     "def_en": "Speed at which information is perceived and processed and a response is produced."},

    # --- Executive functions ---
    {"key": "inhibition",
     "name_fr": "Inhibition", "name_en": "Inhibition",
     "def_fr": "Capacite a supprimer une reponse automatique ou dominante au profit d'une reponse plus adaptee au contexte.",
     "def_en": "Ability to suppress an automatic or dominant response in favour of one better suited to the context."},
    {"key": "flexibility",
     "name_fr": "Flexibilité", "name_en": "Flexibility",
     "def_fr": "Capacite a alterner entre des taches, des regles ou des strategies selon les exigences changeantes.",
     "def_en": "Ability to shift between tasks, rules or strategies as demands change."},
    {"key": "planning",
     "name_fr": "Planification/organisation", "name_en": "Planning, organization",
     "def_fr": "Capacite a anticiper les etapes d'une tache, a organiser les moyens et a sequencer les actions vers un but.",
     "def_en": "Ability to anticipate the steps of a task, organize resources and sequence actions toward a goal."},
    {"key": "emotional-regulation",
     "name_fr": "Régulation émotionnelle", "name_en": "Emotional regulation",
     "def_fr": "Capacite a moduler l'intensite et l'expression des emotions en fonction du contexte et des buts.",
     "def_en": "Ability to modulate the intensity and expression of emotions according to context and goals."},

    # --- Memory ---
    {"key": "short-term",
     "name_fr": "À court terme", "name_en": "Short-term",
     "def_fr": "Maintien temporaire d'une quantite limitee d'information pendant quelques secondes, sans manipulation.",
     "def_en": "Temporary retention of a limited amount of information for several seconds, without manipulation."},
    {"key": "long-term",
     "name_fr": "À long terme", "name_en": "Long-term",
     "def_fr": "Encodage, consolidation et recuperation d'informations au-dela de l'empan immediat (minutes a annees).",
     "def_en": "Encoding, consolidation and retrieval of information beyond the immediate span (minutes to years)."},
    {"key": "visuospatial-wm",
     "name_fr": "MdeT visuospatiale", "name_en": "Visuospatial working memory",
     "def_fr": "Maintien et manipulation mentale d'informations visuelles et spatiales sur une courte periode.",
     "def_en": "Short-term maintenance and mental manipulation of visual and spatial information."},
    {"key": "auditory-wm",
     "name_fr": "MdeT auditive", "name_en": "Auditory working memory",
     "def_fr": "Maintien et manipulation mentale d'informations verbales ou auditives sur une courte periode.",
     "def_en": "Short-term maintenance and mental manipulation of verbal or auditory information."},

    # --- Visuospatial skills ---
    {"key": "visual-perception",
     "name_fr": "Perception visuelle", "name_en": "Visual perception",
     "def_fr": "Analyse et interpretation des caracteristiques visuelles telles que les formes, les objets et les visages.",
     "def_en": "Analysis and interpretation of visual features such as shapes, objects and faces."},
    {"key": "visuoconstruction",
     "name_fr": "Visuoconstruction", "name_en": "Visuoconstruction",
     "def_fr": "Capacite a assembler des elements pour reproduire ou construire une configuration (dessin, blocs).",
     "def_en": "Ability to assemble elements to reproduce or build a configuration (drawing, blocks)."},
    {"key": "visuospatial-organization",
     "name_fr": "Organisation visuospatiale", "name_en": "Visuospatial organization",
     "def_fr": "Structuration des relations spatiales entre les elements d'une scene ou d'un ensemble complexe.",
     "def_en": "Structuring of spatial relations among the elements of a scene or complex array."},
    {"key": "mental-rotation",
     "name_fr": "Rotation mentale", "name_en": "Mental rotation",
     "def_fr": "Capacite a imaginer le deplacement ou la rotation d'objets dans l'espace sans manipulation physique.",
     "def_en": "Ability to imagine the movement or rotation of objects in space without physical manipulation."},

    # --- Language ---
    {"key": "naming",
     "name_fr": "Dénomination", "name_en": "Naming",
     "def_fr": "Capacite a retrouver et a produire le mot correspondant a un objet, une image ou un concept.",
     "def_en": "Ability to retrieve and produce the word corresponding to an object, picture or concept."},
    {"key": "comprehension",
     "name_fr": "Compréhension", "name_en": "Comprehension",
     "def_fr": "Capacite a saisir le sens du langage oral ou ecrit, du mot isole jusqu'aux consignes complexes.",
     "def_en": "Ability to grasp the meaning of spoken or written language, from single words to complex instructions."},
    {"key": "verbal-fluency",
     "name_fr": "Fluence verbale", "name_en": "Verbal fluency",
     "def_fr": "Production rapide de mots selon une contrainte donnee (categorie semantique ou lettre initiale).",
     "def_en": "Rapid production of words under a given constraint (semantic category or initial letter)."},
    {"key": "repetition",
     "name_fr": "Répétition", "name_en": "Repetition",
     "def_fr": "Capacite a reproduire verbalement des mots, des phrases ou des sequences entendues.",
     "def_en": "Ability to verbally reproduce heard words, sentences or sequences."},

    # --- Optional add-on domains ---
    {"key": "fine-motor-speed",
     "name_fr": "Vitesse motrice fine", "name_en": "Fine motor speed",
     "def_fr": "Rapidite d'execution de mouvements precis de la main et des doigts.",
     "def_en": "Speed of execution of precise hand and finger movements."},
    {"key": "dexterity",
     "name_fr": "Dextérité", "name_en": "Dexterity",
     "def_fr": "Precision et coordination des mouvements fins, notamment dans la manipulation d'objets.",
     "def_en": "Precision and coordination of fine movements, particularly when manipulating objects."},
    {"key": "theory-of-mind",
     "name_fr": "Théorie de l'esprit", "name_en": "Theory of mind",
     "def_fr": "Capacite a inferer les etats mentaux d'autrui, comme les croyances, les intentions et les emotions.",
     "def_en": "Ability to infer the mental states of others, such as beliefs, intentions and emotions."},
    {"key": "emotion-recognition",
     "name_fr": "Reconnaissance des émotions", "name_en": "Emotion recognition",
     "def_fr": "Identification des emotions a partir d'indices faciaux, vocaux ou contextuels.",
     "def_en": "Identification of emotions from facial, vocal or contextual cues."},
    {"key": "full-scale-iq",
     "name_fr": "QI global", "name_en": "Full-scale IQ",
     "def_fr": "Estimation generale du fonctionnement intellectuel derivee d'un ensemble d'epreuves standardisees.",
     "def_en": "General estimate of intellectual functioning derived from a set of standardized tasks."},
    {"key": "reasoning",
     "name_fr": "Raisonnement", "name_en": "Reasoning",
     "def_fr": "Capacite a resoudre des problemes nouveaux, a degager des regles et a manipuler des concepts.",
     "def_en": "Ability to solve novel problems, extract rules and manipulate concepts."},
]


def _norm(name: str) -> str:
    """Accent-insensitive, case-insensitive key for name matching."""
    text = unicodedata.normalize("NFD", str(name or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


# Lookup by normalized FR or EN name.
_BY_NAME: dict[str, dict] = {}
for _t in TERMS:
    _BY_NAME[_norm(_t["name_fr"])] = _t
    _BY_NAME[_norm(_t["name_en"])] = _t


def find(name_fr: str, name_en: str) -> dict | None:
    """Return the lexicon entry matching either name, or None."""
    return _BY_NAME.get(_norm(name_fr)) or _BY_NAME.get(_norm(name_en))


def all_terms() -> list[dict]:
    """All entries (for the API bridge)."""
    return [dict(t) for t in TERMS]
