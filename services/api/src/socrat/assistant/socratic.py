"""Server-enforced Socratic escalation.

The model chooses its wording; the server chooses how much it may reveal. Help rises
one level at a time and only after the learner does real work, and the full answer
needs both demonstrated struggle and an explicit, confirmed request.
"""

import re
from dataclasses import dataclass

LEVELS = {
    0: "Ask what they tried and where it stopped making sense. Do not hint yet.",
    1: "Ask one guiding question that points at the key observation. No method names.",
    2: "Give a conceptual nudge: name the relevant idea or property, not the algorithm steps.",
    3: "Suggest the approach or technique and why it fits; no code, no full steps.",
    4: "Give a partial plan in plain-language pseudocode with the core step left for them.",
    5: "Walk through the complete solution with code and explain every decision.",
}
REVEAL_MIN_FAILED_SUBMITS = 2
REVEAL_MIN_TURNS_AT_FOUR = 3
_CODE_FENCE = re.compile(r"```([a-zA-Z+#]*)\n(.*?)```", re.S)
_CODE_LANGS = {"python", "py", "cpp", "c++", "java", "c", "javascript", "js"}
# Asking for the answer, or saying you're lost, is not work (X1): it must not raise the level.
_PRESSURE = re.compile(
    r"\b(give|send|show|tell|write)\s+(me\s+)?(the\s+)?(full\s+|whole\s+|complete\s+)?"
    r"(code|answer|solution)\b|\bjust\s+(give|tell|show)\b|\b(full|whole|complete)\s+(code|solution)\b"
    r"|\bdon'?t\s+(know|get|understand)\b|\bno\s+idea\b",
    re.I,
)


@dataclass(frozen=True)
class Ladder:
    ceiling: int = 0  # highest level the tutor may use on its next reply
    turns_at_ceiling: int = 0
    revealed: bool = False

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value: dict | None) -> "Ladder":
        return cls(**value) if value else cls()


def genuine(message: str, new_attempt: bool) -> bool:
    """A real learner effort: a new Run/Submit, code, or a substantive explanation."""
    if new_attempt:
        return True
    text = message.strip()
    if "\n" in text and any(ch in text for ch in "=();{}[]:"):
        return True
    if _PRESSURE.search(text):
        return False
    return len(re.findall(r"[A-Za-z0-9]+", text)) >= 6


def advance(ladder: Ladder, message: str, new_attempt: bool) -> Ladder:
    if ladder.revealed:
        return ladder
    if not genuine(message, new_attempt):
        return Ladder(ladder.ceiling, ladder.turns_at_ceiling, False)
    if ladder.ceiling < 4:
        return Ladder(ladder.ceiling + 1, 0, False)
    return Ladder(4, ladder.turns_at_ceiling + 1, False)


def reveal_eligibility(ladder: Ladder, failed_submits: int) -> tuple[bool, str]:
    if ladder.revealed:
        return True, "already_revealed"
    if failed_submits >= REVEAL_MIN_FAILED_SUBMITS and ladder.ceiling >= 3:
        return True, "struggled_after_attempts"
    if ladder.ceiling >= 4 and ladder.turns_at_ceiling >= REVEAL_MIN_TURNS_AT_FOUR:
        return True, "struggled_after_hints"
    needed = []
    if failed_submits < REVEAL_MIN_FAILED_SUBMITS:
        left = REVEAL_MIN_FAILED_SUBMITS - failed_submits
        needed.append(f"submit {left} more attempt{'' if left == 1 else 's'}")
    if ladder.ceiling < 4:
        needed.append("work through a few more hints with Socrat")
    return False, " or ".join(needed)


def _normalized_lines(code: str) -> set[str]:
    lines = set()
    for raw in code.splitlines():
        line = re.sub(r"\s+", "", raw)
        if len(line) >= 12 and not line.startswith(("#", "//", "import", "using", "from")):
            lines.add(line)
    return lines


def leaks(message: str, level: int, reference: str = "") -> bool:
    """True when a reply reveals more than the level allows."""
    if level >= 5:
        return False
    for language, body in _CODE_FENCE.findall(message):
        lang = language.lower()
        lines = [x for x in body.splitlines() if x.strip()]
        if lang in _CODE_LANGS and len(lines) >= 2:
            return True
        if level < 4 and len(lines) >= 3:
            return True
    if reference:
        compact = re.sub(r"\s+", "", message)
        if sum(line in compact for line in _normalized_lines(reference)) >= 2:
            return True
    return False


def parse_level(text: str) -> tuple[int | None, str]:
    """Models open each reply with <level>n</level>; strip it from the visible text."""
    match = re.match(r"\s*<level>\s*([0-5])\s*</level>\s*", text)
    if not match:
        return None, text
    return int(match.group(1)), text[match.end() :]
