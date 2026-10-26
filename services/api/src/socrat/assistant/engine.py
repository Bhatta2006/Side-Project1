"""Soc's teaching engine: the server decides the teaching move, the model only words it.

Each turn the engine reads the learner's message and the thread's teaching state, picks one
move (probe, explain-then-check, switch style, check understanding, give feedback, encourage),
injects it as a binding instruction, and afterwards makes sure the reply keeps the move's
promise (a move that must end by checking understanding always does). State lives in the
thread's JSON so it survives across turns without a schema change.
"""

import re
from dataclasses import dataclass

from socrat.assistant import socratic

# Explanation styles, tried in order when the learner stays confused.
STYLES = (
    "an everyday analogy, then map each part of the analogy back to the real idea",
    "one tiny worked example traced by hand, step by step, with the state written out",
    "a picture: a small ASCII diagram or a step table showing how the state changes",
    "the prerequisite underneath: check the simpler idea this one depends on first",
)

_WORDS = re.compile(r"[A-Za-z0-9']+")
_GREETING = re.compile(
    r"^\s*(hi|hey|hello|hii+|yo|good (morning|afternoon|evening)|namaste)\b", re.I
)
_FRUSTRATED = re.compile(
    r"\b(give up|giving up|i quit|so hard|too hard|i'?m (so )?(dumb|stupid|slow|bad at)|"
    r"frustrat\w*|hate (this|it)|never get (this|it)|can'?t do (this|it))\b",
    re.I,
)
_CONFUSED = re.compile(
    r"\b(don'?t (get|understand|follow)|didn'?t (get|understand)|confus\w*|lost|"
    r"makes? no sense|what do you mean|still (not|don'?t)|not clear|unclear|huh)\b|^\s*\?+\s*$",
    re.I,
)
_UNDERSTOOD = re.compile(
    r"\b(got it|makes sense|i (see|understand|get it)|understood|clear now|that helps|"
    r"ok(ay)? thanks?|thanks?,? (got|that)|ahh?+ ?ok)\b",
    re.I,
)
_PLANNING = re.compile(
    r"\b(plan|schedule|roadmap|this week|next week|what should i (study|do|learn|focus)|"
    r"interview|deadline|weak(est)?|focus on|recommend|pick \d+ problems?)\b",
    re.I,
)
_QUESTION = re.compile(
    r"\?\s*$|^\s*(what|why|how|when|where|which|can|could|is|are|does|do|should|explain)\b", re.I
)


@dataclass(frozen=True)
class Move:
    name: str
    label: str  # shown to the learner while Soc works
    instruction: str  # binding for this reply
    check: bool  # the reply must end by asking the learner something


def classify(message: str, new_attempt: bool = False) -> str:
    """The learner's intent this turn, from their words alone. Order is priority."""
    text = message.strip()
    words = len(_WORDS.findall(text))
    if _FRUSTRATED.search(text):
        return "frustrated"
    if _CONFUSED.search(text):
        return "confused"
    if socratic._PRESSURE.search(text):
        return "answer_seeking"
    if _UNDERSTOOD.search(text) and words <= 12:
        return "understood"
    if _GREETING.match(text) and words <= 4:
        return "greeting"
    if new_attempt or (
        socratic.genuine(text, False) and not _QUESTION.search(text) and words >= 12
    ):
        return "attempt"
    if _PLANNING.search(text):
        return "planning"
    if _QUESTION.search(text):
        return "question"
    return "attempt" if words >= 6 else "question"


@dataclass(frozen=True)
class State:
    turn: int = 0
    last_move: str = ""
    confused_streak: int = 0
    style: int = 0
    pending_check: bool = False

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value: dict | None) -> "State":
        known = {k: v for k, v in (value or {}).items() if k in cls.__dataclass_fields__}
        return cls(**known)


def _move(name: str, state: State) -> Move:
    # state.style counts style switches so far; the latest one picks the style.
    style = STYLES[(state.style - 1) % len(STYLES)]
    moves = {
        "warm_open": Move(
            "warm_open",
            "Saying hello",
            "Greet them by name in one short line, name the one most useful next step from "
            "their context, and ask what they want to work on.",
            True,
        ),
        "encourage": Move(
            "encourage",
            "Making the next step smaller",
            "They are frustrated. Acknowledge it in one honest sentence (struggle is normal and "
            "says nothing about ability), then shrink the task to the smallest next step they "
            "can surely do, and ask one easy question about it. Under 80 words. No new concepts.",
            True,
        ),
        "switch_style": Move(
            "switch_style",
            "Trying a different explanation",
            f"They are still confused, so the previous explanation did not land. Explain it "
            f"again using {style}. Do not repeat earlier wording. Keep it under 150 words, then "
            f"ask one question that shows whether it clicked.",
            True,
        ),
        "check": Move(
            "check",
            "Checking your understanding",
            "They say they understand. Do not take it on trust and do not re-explain: ask ONE "
            "short question that makes them apply the idea (predict an output, change one "
            "input, spot the bug, or say why). Under 50 words.",
            True,
        ),
        "evaluate": Move(
            "evaluate",
            "Reading your answer",
            "They are answering your understanding check. Say plainly whether it is right. If "
            "right, name exactly what they got right and give the next small step. If wrong, "
            "point to the first wrong part, explain only that, and ask them to try again.",
            True,
        ),
        "feedback": Move(
            "feedback",
            "Reading your attempt",
            "They shared their own reasoning or code. Start with what is right, specifically. "
            "Then point at the first thing that is wrong or missing, without fixing it for "
            "them, and ask one question that leads them to see it.",
            True,
        ),
        "explain": Move(
            "explain",
            "Explaining",
            "Answer the question directly and concretely at their level: the idea in one or "
            "two sentences, then one small example. End with one short question that checks "
            "they can use it.",
            True,
        ),
        "guide": Move(
            "guide",
            "Thinking of the right question",
            "Do not explain yet. Ask one focused question that moves them one step forward "
            "from where they are.",
            True,
        ),
        "hold": Move(
            "hold",
            "Finding where you're stuck",
            "They want the answer before the help level allows it. Say kindly that they are "
            "closer than it feels, say what unlocks more help (a real attempt, or naming the "
            "exact line or case that breaks), and ask one guiding question.",
            True,
        ),
        "coach": Move(
            "coach",
            "Looking at your plan",
            "This is about their plan or what to do next. Ground the answer in their context "
            "or a tool result, give at most three concrete next steps, and ask which they "
            "want to start with.",
            True,
        ),
    }
    return moves[name]


def decide(state: State, intent: str, scope: str, intent_hint: str = "chat") -> tuple[Move, State]:
    """Pick this turn's move and the state after it. Pure: no I/O, easy to test."""
    problem = scope.startswith("problem:")
    if intent_hint in {"hint", "reveal", "reveal_confirmed"}:
        name = "guide"
    elif intent == "frustrated":
        name = "encourage"
    elif intent == "confused":
        # Confused right after Soc explained: that explanation did not land, so change style.
        name = (
            "switch_style"
            if state.last_move in {"explain", "switch_style", "evaluate"}
            else "explain"
        )
    elif state.pending_check and intent in {"attempt", "question", "answer_seeking"}:
        name = "evaluate"
    elif intent == "understood":
        name = (
            "check"
            if state.last_move in {"explain", "switch_style", "feedback", "evaluate"}
            else "guide"
        )
    elif intent == "greeting":
        name = "warm_open"
    elif intent == "answer_seeking":
        name = "hold" if problem else "explain"
    elif intent == "attempt":
        name = "feedback"
    elif intent == "planning" and not problem:
        name = "coach"
    else:
        name = "guide" if problem else "explain"
    after = State(
        turn=state.turn + 1,
        last_move=name,
        confused_streak=state.confused_streak + 1 if intent == "confused" else 0,
        style=state.style + 1 if name == "switch_style" else state.style,
        pending_check=name == "check",
    )
    return _move(name, after), after


def instruction(move: Move) -> str:
    return f"MOVE: {move.name}\n{move.instruction}\nFollow this move for this reply only."


_CLOSERS = {
    "explain": "**Quick check:** how would you explain this to a friend in one sentence?",
    "switch_style": "Does it click this way? Tell me the part that still feels fuzzy, if any.",
    "check": "**Quick check:** what would change if the input were empty?",
    "evaluate": "Want to try the next step, or go over this part once more?",
    "feedback": "What do you think happens on the smallest input?",
    "encourage": "What's the very first line you'd write?",
    "warm_open": "What would you like to work on?",
    "coach": "Which one do you want to start with?",
}


def closing(reply: str, move: Move | None) -> str:
    """Text to append so the reply keeps the move's promise; empty when it already does."""
    if move is None or not move.check or "?" in reply.strip()[-300:]:
        return ""
    return "\n\n" + _CLOSERS.get(move.name, "What's your next step?")


def describe(state: State) -> str:
    """The engine's state in words, for the learner-visible context panel."""
    if not state.turn:
        return "No teaching moves yet in this chat."
    parts = [f"Turns so far: {state.turn}", f"Last move: {state.last_move.replace('_', ' ')}"]
    if state.style:
        parts.append(f"Explaining with {STYLES[(state.style - 1) % len(STYLES)].split(',')[0]}")
    if state.pending_check:
        parts.append("Waiting for your answer to a quick check")
    return ". ".join(parts) + "."
