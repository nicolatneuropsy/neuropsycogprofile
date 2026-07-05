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
# name_fr / name_en match the battery sub-function names (short, since
# they sit under a domain heading). display_fr / display_en are the full
# standalone names shown in the lexicon itself and in the report (for
# example "Attention soutenue" rather than "Soutenue").
#
# Terms are matched to battery sub-functions by name (case-insensitive,
# accent-insensitive, FR or EN). Renamed or custom sub-functions simply
# have no built-in definition; the UI hides them from the checklist.
# ============================================================

from __future__ import annotations

import unicodedata

# Each entry: key, name_fr/en (battery match), display_fr/en, def_fr/en.
TERMS = [
    # --- Attention / speed ---
    {"key": "sustained",
     "phrase_fr": "l'attention soutenue", "phrase_en": 'sustained attention',
     "name_fr": "Soutenue", "name_en": "Sustained",
     "display_fr": "Attention soutenue", "display_en": "Sustained attention",
     "def_fr": "Capacité à maintenir l'attention sur une tâche pendant une période prolongée, sans déclin marqué du rendement.",
     "def_en": "Ability to maintain attention on a task over an extended period without a marked decline in performance."},
    {"key": "selective",
     "phrase_fr": "l'attention sélective", "phrase_en": 'selective attention',
     "name_fr": "Sélective", "name_en": "Selective",
     "display_fr": "Attention sélective", "display_en": "Selective attention",
     "def_fr": "Capacité à diriger l'attention vers l'information pertinente tout en résistant à la distraction.",
     "def_en": "Ability to direct attention toward relevant information while resisting distraction."},
    {"key": "divided",
     "phrase_fr": "l'attention divisée", "phrase_en": 'divided attention',
     "name_fr": "Divisée", "name_en": "Divided",
     "display_fr": "Attention divisée", "display_en": "Divided attention",
     "def_fr": "Capacité à traiter simultanément plusieurs sources d'information ou à mener deux tâches de front.",
     "def_en": "Ability to process several sources of information at once or to carry out two tasks simultaneously."},
    {"key": "vigilance",
     "phrase_fr": 'la vigilance', "phrase_en": 'vigilance',
     "name_fr": "Vigilance", "name_en": "Vigilance",
     "display_fr": "Vigilance", "display_en": "Vigilance",
     "def_fr": "Capacité à détecter des stimulus rares ou imprévisibles au fil du temps, en maintenant un état d'alerte.",
     "def_en": "Ability to detect rare or unpredictable stimuli over time while maintaining an alert state."},
    {"key": "processing-speed",
     "phrase_fr": 'la vitesse de traitement', "phrase_en": 'processing speed',
     "name_fr": "Vitesse de traitement", "name_en": "Processing speed",
     "display_fr": "Vitesse de traitement", "display_en": "Processing speed",
     "def_fr": "Rapidité avec laquelle l'information est perçue, traitée et une réponse est produite.",
     "def_en": "Speed at which information is perceived and processed and a response is produced."},

    # --- Executive functions ---
    {"key": "inhibition",
     "phrase_fr": "l'inhibition", "phrase_en": 'inhibition',
     "name_fr": "Inhibition", "name_en": "Inhibition",
     "display_fr": "Inhibition", "display_en": "Inhibition",
     "def_fr": "Capacité à supprimer une réponse automatique ou dominante au profit d'une réponse plus adaptée au contexte.",
     "def_en": "Ability to suppress an automatic or dominant response in favour of one better suited to the context."},
    {"key": "flexibility",
     "phrase_fr": 'la flexibilité cognitive', "phrase_en": 'cognitive flexibility',
     "name_fr": "Flexibilité", "name_en": "Flexibility",
     "display_fr": "Flexibilité cognitive", "display_en": "Cognitive flexibility",
     "def_fr": "Capacité à alterner entre des tâches, des règles ou des stratégies selon les exigences changeantes.",
     "def_en": "Ability to shift between tasks, rules or strategies as demands change."},
    {"key": "planning",
     "phrase_fr": "la planification et l'organisation", "phrase_en": 'planning and organization',
     "name_fr": "Planification/organisation", "name_en": "Planning, organization",
     "display_fr": "Planification et organisation", "display_en": "Planning and organization",
     "def_fr": "Capacité à anticiper les étapes d'une tâche, à organiser les moyens et à séquencer les actions vers un but.",
     "def_en": "Ability to anticipate the steps of a task, organize resources and sequence actions toward a goal."},
    {"key": "emotional-regulation",
     "phrase_fr": 'la régulation émotionnelle', "phrase_en": 'emotional regulation',
     "name_fr": "Régulation émotionnelle", "name_en": "Emotional regulation",
     "display_fr": "Régulation émotionnelle", "display_en": "Emotional regulation",
     "def_fr": "Capacité à moduler l'intensité et l'expression des émotions en fonction du contexte et des buts.",
     "def_en": "Ability to modulate the intensity and expression of emotions according to context and goals."},

    # --- Memory ---
    {"key": "short-term",
     "phrase_fr": 'la mémoire à court terme', "phrase_en": 'short-term memory',
     "name_fr": "À court terme", "name_en": "Short-term",
     "display_fr": "Mémoire à court terme", "display_en": "Short-term memory",
     "def_fr": "Maintien temporaire d'une quantité limitée d'information pendant quelques secondes, sans manipulation.",
     "def_en": "Temporary retention of a limited amount of information for several seconds, without manipulation."},
    {"key": "long-term",
     "phrase_fr": 'la mémoire à long terme', "phrase_en": 'long-term memory',
     "name_fr": "À long terme", "name_en": "Long-term",
     "display_fr": "Mémoire à long terme", "display_en": "Long-term memory",
     "def_fr": "Encodage, consolidation et récupération d'informations au-delà de l'empan immédiat (de quelques minutes à plusieurs années).",
     "def_en": "Encoding, consolidation and retrieval of information beyond the immediate span (minutes to years)."},
    {"key": "visuospatial-wm",
     "phrase_fr": 'la mémoire de travail visuospatiale', "phrase_en": 'visuospatial working memory',
     "name_fr": "MdeT visuospatiale", "name_en": "Visuospatial working memory",
     "display_fr": "Mémoire de travail visuospatiale", "display_en": "Visuospatial working memory",
     "def_fr": "Maintien et manipulation mentale d'informations visuelles et spatiales sur une courte période.",
     "def_en": "Short-term maintenance and mental manipulation of visual and spatial information."},
    {"key": "auditory-wm",
     "phrase_fr": 'la mémoire de travail auditive-verbale', "phrase_en": 'auditory-verbal working memory',
     "name_fr": "MdeT auditive", "name_en": "Auditory working memory",
     "display_fr": "Mémoire de travail auditive-verbale", "display_en": "Auditory-verbal working memory",
     "def_fr": "Maintien et manipulation mentale d'informations verbales ou auditives sur une courte période.",
     "def_en": "Short-term maintenance and mental manipulation of verbal or auditory information."},

    # --- Visuospatial skills ---
    {"key": "visual-perception",
     "phrase_fr": 'la perception visuelle', "phrase_en": 'visual perception',
     "name_fr": "Perception visuelle", "name_en": "Visual perception",
     "display_fr": "Perception visuelle", "display_en": "Visual perception",
     "def_fr": "Analyse et interprétation des caractéristiques visuelles telles que les formes, les objets et les visages.",
     "def_en": "Analysis and interpretation of visual features such as shapes, objects and faces."},
    {"key": "visuoconstruction",
     "phrase_fr": 'la visuoconstruction', "phrase_en": 'visuoconstruction',
     "name_fr": "Visuoconstruction", "name_en": "Visuoconstruction",
     "display_fr": "Visuoconstruction", "display_en": "Visuoconstruction",
     "def_fr": "Capacité à assembler des éléments pour reproduire ou construire une configuration (dessin, blocs).",
     "def_en": "Ability to assemble elements to reproduce or build a configuration (drawing, blocks)."},
    {"key": "visuospatial-organization",
     "phrase_fr": "l'organisation visuospatiale", "phrase_en": 'visuospatial organization',
     "name_fr": "Organisation visuospatiale", "name_en": "Visuospatial organization",
     "display_fr": "Organisation visuospatiale", "display_en": "Visuospatial organization",
     "def_fr": "Structuration des relations spatiales entre les éléments d'une scène ou d'un ensemble complexe.",
     "def_en": "Structuring of spatial relations among the elements of a scene or complex array."},
    {"key": "mental-rotation",
     "phrase_fr": 'la rotation mentale', "phrase_en": 'mental rotation',
     "name_fr": "Rotation mentale", "name_en": "Mental rotation",
     "display_fr": "Rotation mentale", "display_en": "Mental rotation",
     "def_fr": "Capacité à imaginer le déplacement ou la rotation d'objets dans l'espace sans manipulation physique.",
     "def_en": "Ability to imagine the movement or rotation of objects in space without physical manipulation."},

    # --- Language ---
    {"key": "naming",
     "phrase_fr": 'la dénomination', "phrase_en": 'naming',
     "name_fr": "Dénomination", "name_en": "Naming",
     "display_fr": "Dénomination", "display_en": "Naming",
     "def_fr": "Capacité à retrouver et à produire le mot correspondant à un objet, une image ou un concept.",
     "def_en": "Ability to retrieve and produce the word corresponding to an object, picture or concept."},
    {"key": "comprehension",
     "phrase_fr": 'la compréhension du langage', "phrase_en": 'language comprehension',
     "name_fr": "Compréhension", "name_en": "Comprehension",
     "display_fr": "Compréhension du langage", "display_en": "Language comprehension",
     "def_fr": "Capacité à saisir le sens du langage oral ou écrit, du mot isolé jusqu'aux consignes complexes.",
     "def_en": "Ability to grasp the meaning of spoken or written language, from single words to complex instructions."},
    {"key": "verbal-fluency",
     "phrase_fr": 'la fluence verbale', "phrase_en": 'verbal fluency',
     "name_fr": "Fluence verbale", "name_en": "Verbal fluency",
     "display_fr": "Fluence verbale", "display_en": "Verbal fluency",
     "def_fr": "Production rapide de mots selon une contrainte donnée (catégorie sémantique ou lettre initiale).",
     "def_en": "Rapid production of words under a given constraint (semantic category or initial letter)."},
    {"key": "repetition",
     "phrase_fr": 'la répétition', "phrase_en": 'repetition',
     "name_fr": "Répétition", "name_en": "Repetition",
     "display_fr": "Répétition", "display_en": "Repetition",
     "def_fr": "Capacité à reproduire verbalement des mots, des phrases ou des séquences entendus.",
     "def_en": "Ability to verbally reproduce heard words, sentences or sequences."},

    # --- Optional add-on domains ---
    {"key": "fine-motor-speed",
     "phrase_fr": 'la vitesse motrice fine', "phrase_en": 'fine motor speed',
     "name_fr": "Vitesse motrice fine", "name_en": "Fine motor speed",
     "display_fr": "Vitesse motrice fine", "display_en": "Fine motor speed",
     "def_fr": "Rapidité d'exécution de mouvements précis de la main et des doigts.",
     "def_en": "Speed of execution of precise hand and finger movements."},
    {"key": "dexterity",
     "phrase_fr": 'la dextérité manuelle', "phrase_en": 'manual dexterity',
     "name_fr": "Dextérité", "name_en": "Dexterity",
     "display_fr": "Dextérité manuelle", "display_en": "Manual dexterity",
     "def_fr": "Précision et coordination des mouvements fins, notamment dans la manipulation d'objets.",
     "def_en": "Precision and coordination of fine movements, particularly when manipulating objects."},
    {"key": "theory-of-mind",
     "phrase_fr": "la théorie de l'esprit", "phrase_en": 'theory of mind',
     "name_fr": "Théorie de l'esprit", "name_en": "Theory of mind",
     "display_fr": "Théorie de l'esprit", "display_en": "Theory of mind",
     "def_fr": "Capacité à inférer les états mentaux d'autrui, comme les croyances, les intentions et les émotions.",
     "def_en": "Ability to infer the mental states of others, such as beliefs, intentions and emotions."},
    {"key": "emotion-recognition",
     "phrase_fr": 'la reconnaissance des émotions', "phrase_en": 'emotion recognition',
     "name_fr": "Reconnaissance des émotions", "name_en": "Emotion recognition",
     "display_fr": "Reconnaissance des émotions", "display_en": "Emotion recognition",
     "def_fr": "Identification des émotions à partir d'indices faciaux, vocaux ou contextuels.",
     "def_en": "Identification of emotions from facial, vocal or contextual cues."},
    {"key": "full-scale-iq",
     "phrase_fr": 'le quotient intellectuel global', "phrase_en": 'full-scale IQ',
     "name_fr": "QI global", "name_en": "Full-scale IQ",
     "display_fr": "Quotient intellectuel global", "display_en": "Full-scale IQ",
     "def_fr": "Estimation générale du fonctionnement intellectuel dérivée d'un ensemble d'épreuves standardisées.",
     "def_en": "General estimate of intellectual functioning derived from a set of standardized tasks."},
    {"key": "reasoning",
     "phrase_fr": 'le raisonnement', "phrase_en": 'reasoning',
     "name_fr": "Raisonnement", "name_en": "Reasoning",
     "display_fr": "Raisonnement", "display_en": "Reasoning",
     "def_fr": "Capacité à résoudre des problèmes nouveaux, à dégager des règles et à manipuler des concepts.",
     "def_en": "Ability to solve novel problems, extract rules and manipulate concepts."},
]


def _norm(name: str) -> str:
    """Accent-insensitive, case-insensitive key for name matching."""
    text = unicodedata.normalize("NFD", str(name or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


# Lookup by normalized FR or EN name (short battery names and full
# display names both match, so renamed batteries using the long form
# still find their definition).
_BY_NAME: dict[str, dict] = {}
for _t in TERMS:
    for _n in (_t["name_fr"], _t["name_en"], _t["display_fr"], _t["display_en"]):
        _BY_NAME[_norm(_n)] = _t


def find(name_fr: str, name_en: str) -> dict | None:
    """Return the lexicon entry matching either name, or None."""
    return _BY_NAME.get(_norm(name_fr)) or _BY_NAME.get(_norm(name_en))


def all_terms() -> list[dict]:
    """All entries (for the API bridge)."""
    return [dict(t) for t in TERMS]
