"""Read models for the learner UI: today, plan, concepts, problems, progress, export."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import practice
from socrat.catalog.registry import Catalog
from socrat.learn import achievements, resources
from socrat.learn import service as learn
from socrat.library import service as library
from socrat.mastery.model import ConceptState, band
from socrat.models import (
    ActivityRecord,
    AIUsage,
    AssistantMessage,
    AssistantThread,
    CompanySprint,
    ContentIssue,
    DailyActivity,
    Draft,
    Enrollment,
    Evidence,
    LearningSession,
    LinkedAccount,
    PlanProposal,
    PracticeMark,
    ResourceEvent,
    SkillPassport,
    Submission,
    User,
    WeeklyAssessment,
)
from socrat.models import now as now_seconds
from socrat.planner.engine import Plan

LANGUAGES = {"python": "Python", "cpp": "C++", "java": "Java"}


def course_card(catalog: Catalog, course_id: str) -> dict:
    course = catalog.course(course_id)
    return dict(
        id=course.id,
        title=course.title,
        tagline=course.tagline,
        description=course.description,
        languages=course.languages,
        levels=[dict(id=x.id, label=x.label, description=x.description) for x in course.levels],
        modules=[
            dict(id=m.id, title=m.title, summary=m.summary, concepts=len(m.concepts))
            for m in course.modules
        ],
        concept_count=len(course.concepts),
        problem_count=len(course.problems),
    )


def lock_info(
    db: Session, catalog: Catalog, enrollment: Enrollment | None, concept: str
) -> dict | None:
    """Which checkpoint must be passed before this concept can be practised, if any."""
    if enrollment is None or enrollment.status != "active":
        return None
    gate = learn.locked_concepts(db, catalog, enrollment, now_seconds()).get(concept)
    if gate is None:
        return None
    module_key = gate.removeprefix("checkpoint:")
    course_id, module_id = module_key.split(":", 1)
    title = next(m.title for m in catalog.course(course_id).modules if m.id == module_id)
    return dict(gate=gate, module=title)


def describe(catalog: Catalog, activity_id: str) -> dict:
    kind, _, target = activity_id.partition(":")
    if kind == "problem":
        course_id, problem = catalog.problems[target]
        return dict(kind=kind, title=problem.title, concept=f"{course_id}:{problem.concepts[0]}")
    if kind == "checkpoint":
        course_id, module_id = target.split(":", 1)
        module = next(m for m in catalog.course(course_id).modules if m.id == module_id)
        return dict(kind=kind, title=f"Checkpoint: {module.title}", concept=target)
    if kind == "moduletest":
        course_id, module_id = target.split(":", 1)
        module = next(m for m in catalog.course(course_id).modules if m.id == module_id)
        return dict(kind=kind, title=f"Test out: {module.title}", concept=target)
    concept = catalog.concept(target)
    titles = {
        "lesson": concept.title,
        "quiz": f"{concept.title} check",
        "review": f"Review: {concept.title}",
        "remedial": f"Refresh: {concept.title}",
        "probe": f"Quick check: {concept.title} and its foundations",
        "testout": f"Test out: {concept.title}",
        "example": f"Worked example: {concept.title}",
        "explain": f"{concept.title}, explained another way",
        "checkin": f"Talk it through: {concept.title}",
        "stretch": f"Stretch: a harder {concept.title} problem",
    }
    return dict(kind=kind, title=titles.get(kind, concept.title), concept=target)


def today_view(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int) -> dict:
    from socrat.adaptive import proposals as adaptive_proposals
    from socrat.adaptive import views as adaptive_views

    plan = learn.plan_for(db, catalog, user, enrollment, now)
    done_ids = learn.completed_today(db, user, enrollment, now)
    done = [dict(id=a, status="done", **describe(catalog, a)) for a in done_ids]
    pending = [
        dict(item, status="pending") for item in (plan.days[0]["items"] if plan.days else [])
    ]
    pending = [p for p in pending if p["id"] not in done_ids]
    budget = enrollment.minutes_per_day
    day = next(
        (
            d
            for d in [db.get(DailyActivity, (user.id, learn.local_day(user, now).isoformat()))]
            if d
        ),
        None,
    )
    revisions = learn.latest_revisions(db, enrollment, limit=1)
    course = catalog.course(enrollment.course_id)
    hour = learn.local_now(user, now).hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return dict(
        greeting=f"{greeting}, {user.display_name.split(' ')[0] if user.display_name else 'there'}",
        course=dict(id=course.id, title=course.title),
        language=enrollment.language,
        date=learn.local_day(user, now).isoformat(),
        study_day=learn.local_day(user, now).weekday() in set(enrollment.weekdays),
        streak=learn.streak(db, user, enrollment, now),
        days_away=learn.days_away(db, user, enrollment, now),
        minutes=dict(done=day.minutes if day else 0, goal=budget),
        done=done,
        next=pending[0] if pending else None,
        queue=pending[1:],
        pace=plan.pace,
        pace_reason=plan.pace_reason,
        latest_update=revisions[0] if revisions else None,
        reviews_due=sum(1 for p in pending if p["kind"] == "review"),
        progress=progress_numbers(plan),
        projected_finish=plan.projected_finish,
        forecast=plan.forecast,
        checkin=adaptive_views.checkin(db, catalog, user, enrollment, plan, now),
        nudges=adaptive_views.nudges(db, catalog, user, enrollment, plan, now),
        proposals=[adaptive_proposals.view(p) for p in adaptive_proposals.pending(db, enrollment)],
        milestone=plan.milestones[0] if plan.milestones else None,
    )


def progress_numbers(plan: Plan) -> dict:
    total = len(plan.roadmap)
    # Assumed-from-placement skills are not evidence, so they stay out of "finished".
    finished = sum(1 for r in plan.roadmap if r["status"] in {"mastered", "practiced"})
    assumed = sum(1 for r in plan.roadmap if r["status"] == "assumed")
    return dict(
        total=total,
        finished=finished,
        assumed=assumed,
        percent=round(100 * finished / total) if total else 0,
    )


def plan_view(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int) -> dict:
    plan = learn.plan_for(db, catalog, user, enrollment, now)
    completed = learn.completed_for(db, enrollment)
    states = learn.states_for(db, enrollment)
    modules: list[dict] = []
    index: dict[str, dict] = {}
    for item in plan.roadmap:
        module_key = item["module"]
        if module_key not in index:
            course_id, module_id = module_key.split(":", 1)
            module = next(m for m in catalog.course(course_id).modules if m.id == module_id)
            index[module_key] = dict(
                id=module_key,
                title=module.title,
                summary=module.summary,
                course=catalog.course(course_id).title,
                bridge=course_id != enrollment.course_id,
                concepts=[],
                locked_by=None,
            )
            modules.append(index[module_key])
        index[module_key]["concepts"].append(
            dict(
                item,
                lesson_done=f"lesson:{item['concept']}" in completed,
                quiz_done=f"quiz:{item['concept']}" in completed,
                review_due=states.get(item["concept"], ConceptState()).due(now),
                roadmap_resources=resources.selected(
                    item["concept"], enrollment.language, "roadmap"
                ),
            )
        )
        if item.get("locked_by"):
            gate_module = item["locked_by"].removeprefix("checkpoint:")
            gate_course, gate_id = gate_module.split(":", 1)
            index[module_key]["locked_by"] = dict(
                gate=item["locked_by"],
                module=next(
                    m.title for m in catalog.course(gate_course).modules if m.id == gate_id
                ),
            )
    from socrat.adaptive import views as adaptive_views

    target = enrollment.goal.get("target_date")
    on_track = plan.forecast.get("on_track")
    current = next((r for r in plan.roadmap if r["status"] in {"in_progress", "upcoming"}), None)
    return dict(
        style=plan.style,
        focus=plan.focus,
        forecast=plan.forecast,
        milestones=plan.milestones,
        proposals=adaptive_views.proposals_view(db, enrollment),
        weekly_review_ready=adaptive_views.weekly_ready(user, enrollment, now),
        pace=plan.pace,
        pace_reason=plan.pace_reason,
        projected_finish=plan.projected_finish,
        remaining_minutes=plan.remaining_minutes,
        target_date=target,
        on_track=on_track,
        current_concept=current["concept"] if current else None,
        modules=modules,
        days=plan.days,
        reasons=plan.reasons,
        revisions=learn.latest_revisions(db, enrollment),
        progress=progress_numbers(plan),
    )


def concept_view(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment | None,
    qualified: str,
    now: int,
) -> dict:
    concept = catalog.concept(qualified)
    course_id = catalog.owner[qualified]
    language = enrollment.language if enrollment else "python"
    states = learn.states_for(db, enrollment) if enrollment else {}
    state = states.get(qualified, ConceptState())
    completed = learn.completed_for(db, enrollment) if enrollment else set()
    solved = solved_problems(db, user.id)
    index = practice.default_index()
    current_band = band(state, now)
    return dict(
        id=qualified,
        course=course_id,
        title=concept.title,
        summary=concept.summary,
        module=catalog.module_of(qualified),
        lesson=concept.lesson,
        exercises=resources.selected(qualified, language, "exercises"),
        key_points=concept.key_points,
        pitfalls=concept.pitfalls,
        resources=resources.personalised(db, user.id, qualified, concept, language, current_band),
        # Authored links that are in the library become library rows (with status);
        # the rest stay plain links.
        practice_links=[
            p.model_dump(mode="json")
            for p in concept.practice_links
            if index.find_url(str(p.url)) is None
            and qualified in learn.practice_topics(db, catalog, enrollment, now)
        ],
        more_practice=library.concept_practice(
            db,
            catalog,
            user,
            enrollment,
            qualified,
            now,
            [str(p.url) for p in concept.practice_links],
        ),
        implementations=index.implementations_for(qualified, language),
        handbook=index.book_for(qualified),
        problems=[
            dict(
                id=p,
                title=catalog.problem(p).title,
                difficulty=catalog.problem(p).difficulty,
                solved=p in solved,
            )
            for p in concept.problems
        ],
        prerequisites=[
            dict(
                id=p, title=catalog.concept(p).title, band=band(states.get(p, ConceptState()), now)
            )
            for p in catalog.prerequisites[qualified]
        ],
        band=current_band,
        locked=lock_info(db, catalog, enrollment, qualified),
        lesson_done=f"lesson:{qualified}" in completed,
        quiz_done=f"quiz:{qualified}" in completed,
        language=language,
    )


def solved_problems(db: Session, user_id: str) -> set[str]:
    return library.native_solved(db, user_id)


STARTERS = {
    "python": "import sys\n\n\ndef main():\n    data = sys.stdin.read().split()\n    # Your solution here\n\n\nmain()\n",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // Your solution here\n    return 0;\n}\n",
    "java": "import java.io.*;\nimport java.util.*;\n\npublic class Solution {\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        // Your solution here\n    }\n}\n",
}
# Programming from Zero uses only what its first lessons teach: line-by-line input and print (Z-1).
ZERO_STARTERS = {
    "python": "# Read each input line with input().\n# Show your answer with print().\n",
    "cpp": "#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {\n    // Read input with cin >> (or getline(cin, line) for a whole line).\n    // Show your answer with cout.\n    return 0;\n}\n",
    "java": "import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        // Read input with in.nextLine() or in.nextInt().\n        // Show your answer with System.out.println.\n    }\n}\n",
}


def problem_view(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment | None,
    problem_id: str,
    language: str,
) -> dict:
    course_id, problem = catalog.problems[problem_id]
    draft = db.get(Draft, (user.id, problem_id, language))
    recent = db.scalars(
        select(Submission)
        .where(Submission.user_id == user.id, Submission.problem_id == problem_id)
        .order_by(Submission.created_at.desc())
        .limit(10)
    )
    concept = f"{course_id}:{problem.concepts[0]}"
    return dict(
        id=problem.id,
        title=problem.title,
        difficulty=problem.difficulty,
        concept=dict(id=concept, title=catalog.concept(concept).title),
        statement=problem.statement,
        input_format=problem.input_format,
        output_format=problem.output_format,
        constraints=problem.constraints,
        examples=[e.model_dump() for e in problem.examples],
        language=language,
        starter=problem.starter.get(language)  # type: ignore[call-overload]
        or (ZERO_STARTERS if course_id == "zero" else STARTERS)[language],
        draft=draft.source if draft else None,
        solved=problem_id in solved_problems(db, user.id),
        locked=lock_info(db, catalog, enrollment, concept),
        history=[
            dict(
                id=s.id,
                mode=s.mode,
                verdict=s.verdict,
                status=s.status,
                passed=s.passed,
                total=s.total,
                at=s.created_at,
            )
            for s in recent
        ],
        hint_count=len(problem.hints),
    )


def progress_view(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> dict:
    plan = learn.plan_for(db, catalog, user, enrollment, now)
    states = learn.states_for(db, enrollment)
    modules: dict[str, dict] = {}
    for item in plan.roadmap:
        state = states.get(item["concept"], ConceptState())
        entry = modules.setdefault(item["module"], dict(id=item["module"], title="", concepts=[]))
        if not entry["title"]:
            course_id, module_id = item["module"].split(":", 1)
            entry["title"] = next(
                m.title for m in catalog.course(course_id).modules if m.id == module_id
            )
        entry["concepts"].append(
            dict(
                id=item["concept"],
                title=item["title"],
                band=band(state, now),
                mastery=round(state.effective(now), 3),
                confidence=round(state.confidence, 3),
                evidence=state.evidence_count,
                next_review=state.next_review_at or None,
            )
        )
    today = learn.local_day(user, now)
    start = today - timedelta(days=7 * 26 - 1)
    days = {
        row.day: row
        for row in db.scalars(
            select(DailyActivity).where(
                DailyActivity.user_id == user.id, DailyActivity.day >= start.isoformat()
            )
        )
    }
    heatmap = []
    cursor = start
    while cursor <= today:
        row = days.get(cursor.isoformat())
        heatmap.append(
            dict(
                day=cursor.isoformat(),
                minutes=row.minutes if row else 0,
                activities=row.activities if row else 0,
            )
        )
        cursor += timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    week_minutes = sum(r.minutes for d, r in days.items() if date.fromisoformat(d) >= week_start)
    recent = db.scalars(
        select(Evidence)
        .where(Evidence.enrollment_id == enrollment.id)
        .order_by(Evidence.created_at.desc())
        .limit(15)
    )
    streak = learn.streak(db, user, enrollment, now)
    return dict(
        modules=list(modules.values()),
        progress=progress_numbers(plan),
        streak=streak,
        achievements=achievements.for_learner(db, catalog, user, enrollment, streak["longest"]),
        heatmap=heatmap,
        week=dict(minutes=week_minutes, goal=enrollment.minutes_per_day * len(enrollment.weekdays)),
        solves=learn.evidence_counts(db, enrollment),
        total_minutes=sum(r.minutes for r in days.values()),
        revisions=learn.latest_revisions(db, enrollment, limit=10),
        recent=[
            dict(
                concept=catalog.concept(e.concept).title
                if e.concept in catalog.concepts
                else e.concept,
                kind=e.kind,
                score=e.score,
                assisted=e.assistance > 0,
                at=e.created_at,
            )
            for e in recent
        ],
        pace=plan.pace,
        projected_finish=plan.projected_finish,
    )


def export(db: Session, user: User) -> dict:
    enrollments = list(db.scalars(select(Enrollment).where(Enrollment.user_id == user.id)))
    ids = [e.id for e in enrollments]
    threads = list(db.scalars(select(AssistantThread).where(AssistantThread.user_id == user.id)))
    return dict(
        profile=dict(
            id=user.id,
            display_name=user.display_name,
            birth_year=user.birth_year,
            timezone=user.timezone,
            created_at=user.created_at,
        ),
        enrollments=[
            dict(
                id=e.id,
                course=e.course_id,
                language=e.language,
                level=e.level_id,
                goal=e.goal,
                minutes_per_day=e.minutes_per_day,
                weekdays=e.weekdays,
                created_at=e.created_at,
                adaptive=e.adaptive,
            )
            for e in enrollments
        ],
        ai_usage=[
            dict(
                feature=u.feature,
                model=u.model,
                input_tokens=u.input_tokens,
                output_tokens=u.output_tokens,
                at=u.created_at,
            )
            for u in db.scalars(select(AIUsage).where(AIUsage.user_id == user.id))
        ],
        plan_proposals=[
            dict(
                id=p.id,
                kind=p.kind,
                title=p.title,
                reason=p.reason,
                payload=p.payload,
                source=p.source,
                status=p.status,
                created_at=p.created_at,
                decided_at=p.decided_at,
            )
            for p in db.scalars(select(PlanProposal).where(PlanProposal.enrollment_id.in_(ids)))
        ],
        evidence=[
            dict(
                id=x.id,
                concept=x.concept,
                kind=x.kind,
                score=x.score,
                assistance=x.assistance,
                activity=x.activity_id,
                at=x.created_at,
                details=x.details,
            )
            for x in db.scalars(select(Evidence).where(Evidence.enrollment_id.in_(ids)))
        ],
        activities=[
            dict(
                activity=x.activity_id,
                started=x.started_at,
                completed=x.completed_at,
                outcome=x.outcome,
            )
            for x in db.scalars(select(ActivityRecord).where(ActivityRecord.enrollment_id.in_(ids)))
        ],
        learning_sessions=[
            dict(
                id=s.id,
                day=s.day,
                started_at=s.created_at,
                finished_at=s.finished_at,
                concept=s.payload["concept"],
                minutes=s.payload["minutes"],
                reflection=s.payload.get("reflection"),
                checks=s.payload["answers"],
                outcomes=s.payload["outcomes"],
                summary=s.payload.get("summary"),
            )
            for s in db.scalars(
                select(LearningSession).where(LearningSession.enrollment_id.in_(ids))
            )
        ],
        skill_passport=next(
            (
                dict(slug=p.slug, public=p.public, created_at=p.created_at, updated_at=p.updated_at)
                for p in db.scalars(select(SkillPassport).where(SkillPassport.user_id == user.id))
            ),
            None,
        ),
        company_sprints=[
            dict(
                company=c.company_name,
                role=c.role,
                weeks=c.weeks,
                started_on=c.started_on,
                ends_on=c.ends_on,
                plan=c.plan,
                finished_at=c.finished_at,
            )
            for c in db.scalars(select(CompanySprint).where(CompanySprint.enrollment_id.in_(ids)))
        ],
        content_issues=[
            dict(
                concept=i.concept,
                atom=i.atom_id,
                version=i.version,
                reason=i.reason,
                note=i.note,
                at=i.created_at,
            )
            for i in db.scalars(select(ContentIssue).where(ContentIssue.user_id == user.id))
        ],
        submissions=[
            dict(
                problem=s.problem_id,
                language=s.language,
                mode=s.mode,
                verdict=s.verdict,
                source=s.source,
                at=s.created_at,
            )
            for s in db.scalars(select(Submission).where(Submission.user_id == user.id))
        ],
        assistant=[
            dict(
                scope=t.scope,
                messages=[
                    dict(role=m.role, content=m.content, at=m.created_at, rating=m.rating)
                    for m in db.scalars(
                        select(AssistantMessage)
                        .where(AssistantMessage.thread_id == t.id)
                        .order_by(AssistantMessage.seq)
                    )
                ],
            )
            for t in threads
        ],
        resource_feedback=[
            dict(concept=e.concept, url=e.url, opened_at=e.opened_at, helpful=e.helpful)
            for e in db.scalars(select(ResourceEvent).where(ResourceEvent.user_id == user.id))
        ],
        daily=[
            dict(day=d.day, minutes=d.minutes, activities=d.activities, solved=d.solved)
            for d in db.scalars(select(DailyActivity).where(DailyActivity.user_id == user.id))
        ],
        practice_marks=[
            dict(
                problem=m.problem_id,
                status=m.status,
                bookmarked=m.bookmarked,
                opened_at=m.opened_at,
                solved_at=m.solved_at,
            )
            for m in db.scalars(select(PracticeMark).where(PracticeMark.user_id == user.id))
        ],
        weekly_assessments=[
            dict(
                week=a.iso_week,
                score=a.score,
                started_at=a.started_at,
                finished_at=a.finished_at,
                report=a.report,
            )
            for a in db.scalars(
                select(WeeklyAssessment).where(WeeklyAssessment.enrollment_id.in_(ids))
            )
        ],
        linked_accounts=[
            dict(platform=a.platform, handle=a.handle, rating=a.rating, synced_at=a.synced_at)
            for a in db.scalars(select(LinkedAccount).where(LinkedAccount.user_id == user.id))
        ],
    )
