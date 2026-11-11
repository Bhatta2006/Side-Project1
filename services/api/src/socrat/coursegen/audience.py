"""Tell the tutor how a learner asked to be taught, in the learner's own course.

When a learner builds a course with "teach me X", their picks (age or register, approach, theory
or practice balance, minutes a day) shape how the lessons were written. The tutor ("Ask Soc")
must talk the same way, otherwise a six-year-old gets a university reply in the chat beside a
kid-friendly lesson.

Only the intent's validated enum fields are used, never its free text, and only for the learner
who made the request, in the course made from it. Someone else's shared course, or free text in
a brief, never reaches a learner's tutor through here. The block changes wording only; the help
ladder, the rule against handing over solutions and the facts are untouched (the tutor prompt
says so, and the directive repeats it).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.coursegen.intent import Intent
from socrat.models import Enrollment, GeneratedCourse, LearningRequest, User

REGISTER = {
    "little-kid": (
        "The learner is a young child (about 5 to 7). Use very short, simple sentences, "
        "everyday objects as examples, one small idea per message, a warm playful tone and no "
        "jargon. Ask one tiny question at a time."
    ),
    "kid": (
        "The learner is a child (about 8 to 12). Use plain words, friendly examples from games "
        "and school, short replies, and define any new word the first time."
    ),
    "teen": (
        "The learner is a teenager. Be direct and respectful, not childish; use relatable "
        "examples, keep replies short, and explain why something matters."
    ),
    "university": (
        "The learner studies at university level. Use precise terminology, state assumptions, "
        "and connect ideas to the underlying theory."
    ),
    "professional": (
        "The learner is a working professional. Be concise and practical, assume general "
        "workplace context, and tie explanations to real use."
    ),
}
APPROACH = {
    "gamified": "Make practice feel like a game: small challenges, clear goals, quick feedback.",
    "bite-sized": "Keep every reply to a few sentences; offer the next small step.",
    "theory-first": "Explain the idea and the why before examples.",
    "practice-first": "Start from a small task or example, then explain what it showed.",
    "projects": "Tie explanations to the learner's project work where possible.",
    "visual": "Prefer a picture, diagram or concrete image to describe an idea when you can.",
}
BALANCE = {
    "theory-heavy": "Lean towards explanation and reasoning over drills.",
    "practice-heavy": "Lean towards doing and trying over long explanation.",
}
GUARD = (
    "This changes wording and pacing only. The help ladder, the rule against revealing a "
    "solution early and accuracy apply exactly as before."
)


def block(intent: Intent) -> str:
    """The tutor text for one intent; empty when it asks for nothing beyond the default."""
    lines = []
    if intent.age and intent.age < 18:
        # A validated number, never free text: the exact age beats the age group below.
        lines.append(
            f"The learner is {intent.age} years old. Pitch every reply at exactly that age."
        )
    if intent.register in REGISTER:
        lines.append(REGISTER[intent.register])
    lines += [APPROACH[a] for a in intent.approach if a in APPROACH]
    if intent.balance in BALANCE:
        lines.append(BALANCE[intent.balance])
    if intent.minutes_per_day and intent.minutes_per_day <= 10:
        lines.append("The learner has only a few minutes a day: keep each reply short.")
    return "\n".join([*lines, GUARD]) if lines else ""


def tutor_block(db: Session, user: User, enrollment: Enrollment | None) -> str:
    """The block for the learner's active course if they made it themselves, else empty."""
    if enrollment is None:
        return ""
    course = db.get(GeneratedCourse, enrollment.course_id)
    if course is None:
        return ""
    framed = frame_line(course.brief)
    if course.owner_id != user.id:
        return "\n".join([framed, GUARD]) if framed else ""
    mine = _own_block(db, user, course)
    return "\n".join(x for x in (framed, mine) if x)


def frame_line(brief: dict | None) -> str:
    """How the course is taught, for the tutor of anyone taking it: the frame's name and its
    words for a lesson and a module. These are pattern-checked plain words (style/spec.py);
    the frame's free-text method stays with the lesson writers."""
    from socrat.style import spec as styles

    frame = styles.course_frame(brief)
    if frame is None:
        return ""
    return (
        f"This course is taught as: {frame.name}. In it a lesson is called a "
        f'"{frame.lesson_word}" and a module a "{frame.module_word}". Keep that framing in '
        "your replies, and step out of it whenever the learner is confused: a clear answer "
        "comes first. Never invent rewards, scores or progress."
    )


def _own_block(db: Session, user: User, course: GeneratedCourse) -> str:
    """How the learner who made this course asked to be taught (their validated picks)."""
    request = db.scalars(
        select(LearningRequest)
        .where(LearningRequest.user_id == user.id, LearningRequest.course_id == course.id)
        .order_by(LearningRequest.created_at.desc())
        .limit(1)
    ).first()
    if request is None:
        return ""
    try:
        return block(Intent.model_validate(request.intent))
    except ValueError:
        return ""  # a stored intent that no longer validates is ignored, never half-used
