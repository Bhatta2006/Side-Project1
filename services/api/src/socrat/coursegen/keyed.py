"""The answer is marked inside the item, and code derives the index.

A writer that gives ``"answer": 2`` next to a list of options can point at the wrong one, and
nothing in the item shows it. Wondering's practice items (research/wondering/2026-11-05) mark
each option ``isCorrect`` and repeat the answer text, so the key cannot drift away from the
options. Socrat's quiz items and atom checks keep their stored shape (option texts and an index),
but a writer may now say which option is right in any of these forms, all parsed here:

- ``"options": [{"text": "...", "correct": true}, {"text": "...", "correct": false}]``
  (``isCorrect`` is read as ``correct``);
- ``"answer": "<the correct option, copied>"``;
- ``"answer": 0`` (the index, as before).

When more than one form is given they must agree. Anything ambiguous is refused with a message
the writer can act on; nothing is guessed. Learners see options in a per-session order
(``learn.sessions.option_order``), so the stored position does not matter.
"""

import re

FLAGS = ("correct", "isCorrect", "is_correct")


def _plain(text: str) -> str:
    """Case, spacing and a closing full stop do not make two option texts different."""
    return re.sub(r"\s+", " ", text).strip().rstrip(".").casefold()


def settle(raw: dict) -> dict:
    """``raw`` with ``options`` as texts and ``answer`` as an index. Raises TypeError."""
    options = raw.get("options")
    if not isinstance(options, list):
        return raw  # validation reports the missing options
    texts: list[str] = []
    flagged: list[int] = []
    for index, option in enumerate(options):
        if isinstance(option, dict):
            text = option.get("text")
            if not isinstance(text, str):
                raise TypeError(f"option {index + 1} has no text")
            marks = [option[f] for f in FLAGS if f in option]
            if any(not isinstance(m, bool) for m in marks):
                raise TypeError(f"option {index + 1}: correct must be true or false")
            if any(marks):
                flagged.append(index)
            texts.append(text)
        else:
            texts.append(option if isinstance(option, str) else str(option))
    if len({_plain(t) for t in texts}) != len(texts):
        raise TypeError("two options say the same thing; every option must differ")
    if len(flagged) > 1:
        raise TypeError("mark exactly one option correct; more than one is marked")
    claims: set[int] = set(flagged)
    answer = raw.get("answer")
    if isinstance(answer, bool):
        raise TypeError("answer must be the correct option, not true or false")
    if isinstance(answer, int):
        if not 0 <= answer < len(texts):
            raise TypeError(f"answer {answer} is not one of the {len(texts)} options")
        claims.add(answer)
    elif isinstance(answer, str) and answer.strip():
        same = [i for i, t in enumerate(texts) if _plain(t) == _plain(answer)]
        if not same:
            raise TypeError("the answer text is not one of the options; copy it exactly")
        claims.update(same)
    elif answer is not None:
        raise TypeError("answer must be the correct option's text or its index")
    if not claims:
        raise TypeError("mark which option is correct")
    if len(claims) > 1:
        raise TypeError("the marked option and the answer disagree; give one correct option")
    return {**raw, "options": texts, "answer": claims.pop()}


def marked(item: dict) -> dict:
    """An index-form item (as stored) written in the marked form, for examples shown to a writer."""
    options, answer = item.get("options"), item.get("answer")
    if not isinstance(options, list) or not isinstance(answer, int):
        return item
    out = {k: v for k, v in item.items() if k != "answer"}
    out["options"] = [{"text": t, "correct": i == answer} for i, t in enumerate(options)]
    return out
