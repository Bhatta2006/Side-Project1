"""Supported locales. A locale is a BCP-47 tag; country (currency, tax, privacy rules) is a
separate concern. English is the source of truth: every other locale falls back to it, never
to an empty string."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Locale:
    tag: str
    name: str  # English name
    native: str  # shown in the language switcher
    script: str  # latin | devanagari | telugu | tamil | bengali | arabic
    rtl: bool = False
    engine: str = "gateway"  # which translation backend suits it: gateway | sarvam
    preview: bool = False  # machine-only quality not yet benchmarked: shown as "preview"


LOCALES: dict[str, Locale] = {
    loc.tag: loc
    for loc in (
        Locale("en", "English", "English", "latin"),
        Locale("hi", "Hindi", "हिन्दी", "devanagari", engine="sarvam"),
        Locale("te", "Telugu", "తెలుగు", "telugu", engine="sarvam"),
        Locale("ta", "Tamil", "தமிழ்", "tamil", engine="sarvam"),
        Locale("bn", "Bengali", "বাংলা", "bengali", engine="sarvam"),
        Locale("mr", "Marathi", "मराठी", "devanagari", engine="sarvam", preview=True),
        Locale("es", "Spanish", "Español", "latin", preview=True),
        Locale("pt-BR", "Brazilian Portuguese", "Português (Brasil)", "latin", preview=True),
        Locale("id", "Indonesian", "Bahasa Indonesia", "latin", preview=True),
        Locale("ar", "Arabic", "العربية", "arabic", rtl=True, preview=True),
    )
}
DEFAULT = "en"

# Unicode ranges used to check that a translation is really in the target script.
SCRIPT_RANGES = {
    "devanagari": [(0x0900, 0x097F)],
    "telugu": [(0x0C00, 0x0C7F)],
    "tamil": [(0x0B80, 0x0BFF)],
    "bengali": [(0x0980, 0x09FF)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F)],
}


def get(tag: str) -> Locale:
    """The locale for ``tag``; unknown tags fall back to English."""
    return LOCALES.get(tag) or DEFAULT_LOCALE


def supported(tag: str) -> bool:
    return tag in LOCALES


def negotiate(accept_language: str) -> str:
    """Best supported locale from an Accept-Language header; English if none match."""
    best, best_q = DEFAULT, -1.0
    for part in accept_language.split(","):
        piece = part.strip()
        if not piece:
            continue
        tag, _, q = piece.partition(";q=")
        try:
            weight = float(q) if q else 1.0
        except ValueError:
            continue
        candidates = [tag, tag.split("-")[0]]
        for cand in candidates:
            match = next((t for t in LOCALES if t.lower() == cand.lower()), None)
            if match and weight > best_q:
                best, best_q = match, weight
                break
    return best


DEFAULT_LOCALE = LOCALES[DEFAULT]


def script_share(text: str, script: str) -> float:
    """Fraction of letters in ``text`` that belong to ``script`` (1.0 for Latin: not checked)."""
    ranges = SCRIPT_RANGES.get(script)
    if not ranges:
        return 1.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    inside = sum(any(a <= ord(c) <= b for a, b in ranges) for c in letters)
    return inside / len(letters)
