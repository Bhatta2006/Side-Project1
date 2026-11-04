"""The tutor's general and plan chats belong to one course: switching courses never carries a
conversation (or its teaching state) from one course into the other's tutor context."""

# ruff: noqa: F811
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant import service as assistant
from socrat.models import AssistantMessage, Enrollment, User


def _switch_to(db: Session, user_id: str, course: str) -> None:
    """Pause the active course and make ``course`` active (as /enrollments/switch does)."""
    db.execute(update(Enrollment).where(Enrollment.user_id == user_id).values(active=False))
    row = db.scalar(
        select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course)
    )
    if row is None:
        db.add(
            Enrollment(
                user_id=user_id,
                course_id=course,
                language="python",
                level_id="new-to-programming",
                minutes_per_day=30,
                weekdays=[0, 1, 2],
                status="active",
                active=True,
            )
        )
    else:
        row.active = True
    db.flush()


def _say(db: Session, user_id: str, scope: str, text: str) -> str:
    thread = assistant.thread_for(db, user_id, scope)
    db.add(AssistantMessage(thread_id=thread.id, role="user", content=text, seq=1))
    db.flush()
    return thread.id


def test_general_and_plan_chats_stay_with_their_course(client):
    headers = login(client, subject="kira", name="Kira")
    onboard(client, headers)  # zero
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == "kira"))
        zero_general = _say(db, user.id, "general", "zero: how do loops work")
        _say(db, user.id, "plan", "zero: plan for loops")

        _switch_to(db, user.id, "dsa")
        # The other course's chats are not this course's history or context.
        assert assistant.thread_view(db, user.id, "general")["messages"] == []
        assert assistant.thread_view(db, user.id, "plan")["messages"] == []
        assert assistant.list_chats(db, user.id, "general")["items"] == []
        assert assistant.thread_for(db, user.id, "general").id != zero_general
        try:
            assistant.chat_view(db, user.id, zero_general)
            raise AssertionError("another course's chat was readable")
        except assistant.HTTPException as exc:
            assert exc.status_code == 404
        dsa_general = _say(db, user.id, "general", "dsa: two pointers")
        assert [
            m["content"] for m in assistant.thread_view(db, user.id, "general")["messages"]
        ] == ["dsa: two pointers"]

        _switch_to(db, user.id, "zero")
        # Back in the first course, its own conversation is still there, and only it.
        view = assistant.thread_view(db, user.id, "general")
        assert view["scope"] == "general"
        assert [m["content"] for m in view["messages"]] == ["zero: how do loops work"]
        assert assistant.thread_for(db, user.id, "general").id == zero_general != dsa_general
        archived = assistant.new_chat(db, user.id, "general", 1)
        assert archived["scope"] == "general" and archived["archived"] == zero_general
        chats = assistant.list_chats(db, user.id, "general")["items"]
        assert [c["id"] for c in chats] == [zero_general]
        assert assistant.resume_chat(db, user.id, zero_general, 2)["scope"] == "general"


def test_problem_and_concept_chats_keep_their_scope_names(client):
    headers = login(client, subject="omar", name="Omar")
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == "omar"))
        assert assistant.stored_scope(db, user.id, "problem:greeting") == "problem:greeting"
        assert (
            assistant.stored_scope(db, user.id, "concept:zero:programs-and-output")
            == "concept:zero:programs-and-output"
        )
        assert assistant.stored_scope(db, user.id, "general") == "general@zero"
        assert assistant.public_scope("general@zero#abc") == "general"


def test_non_tutor_scopes_pass_through_unchanged(client):
    """The Playground stores its visuals under its own scope through thread_for."""
    headers = login(client, subject="pia", name="Pia")
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == "pia"))
        assert assistant.stored_scope(db, user.id, "playground:visual") == "playground:visual"
        assert assistant.thread_for(db, user.id, "playground:visual").scope == "playground:visual"
