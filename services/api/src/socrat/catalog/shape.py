"""What a course needs in order to be learned: the studio, the practice loop and the evidence.

Subjects differ in more than their topics. Programming is learned by solving problems in an
editor and proving it with tests; math by deriving on a workbench and showing the steps;
physics by predicting, observing a simulation and explaining. A course declares this shape
once; navigation, practice, evidence and the mentor read it. Courses without a shape (all
hand-authored ones) are programming courses.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Studio = Literal["code", "workbench", "lab", "reading"]
Loop = Literal["solve", "derive", "predict-observe-explain", "read-reflect"]
Evidence = Literal["tests", "derivation", "numeric", "explanation", "quiz"]
Tool = Literal["editor", "graph", "cas", "simulation"]

# What each studio supports. "reading" is the baseline for subjects with no tool yet.
STUDIOS: dict[str, dict] = {
    "code": dict(
        label="Practice",
        loops={"solve"},
        evidence={"tests", "quiz", "explanation"},
        tools={"editor"},
    ),
    "workbench": dict(
        label="Workbench",
        loops={"solve", "derive"},
        evidence={"derivation", "numeric", "quiz", "explanation"},
        tools={"graph", "cas"},
    ),
    "lab": dict(
        label="Lab",
        loops={"predict-observe-explain", "solve"},
        evidence={"numeric", "explanation", "quiz"},
        tools={"simulation", "graph"},
    ),
    "reading": dict(
        label="Notebook",
        loops={"read-reflect"},
        evidence={"quiz", "explanation"},
        tools=set(),
    ),
}


class CourseShape(BaseModel):
    model_config = ConfigDict(extra="forbid")
    studio: Studio
    loop: Loop
    evidence: list[Evidence] = Field(min_length=1, max_length=4)
    tools: list[Tool] = Field(default_factory=list, max_length=3)
    label: str = Field(default="", max_length=24)  # the nav name; the studio's own if empty

    @model_validator(mode="after")
    def fits_the_studio(self):
        allowed = STUDIOS[self.studio]
        if self.loop not in allowed["loops"]:
            raise ValueError(f"the {self.studio} studio does not support the {self.loop} loop")
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("evidence kinds must be distinct")
        if bad := set(self.evidence) - allowed["evidence"]:
            raise ValueError(f"the {self.studio} studio cannot show evidence {sorted(bad)}")
        if len(set(self.tools)) != len(self.tools):
            raise ValueError("tools must be distinct")
        if bad := set(self.tools) - allowed["tools"]:
            raise ValueError(f"the {self.studio} studio has no tools {sorted(bad)}")
        return self

    @property
    def name(self) -> str:
        return self.label or STUDIOS[self.studio]["label"]


CODE = CourseShape(studio="code", loop="solve", evidence=["tests", "quiz"], tools=["editor"])


def effective(course) -> CourseShape:
    """The course's shape; hand-authored courses without one are programming courses."""
    return course.shape or CODE


# The external practice library (LeetCode, CSES, Codeforces), focus sprints and the Codeforces
# link belong to the hand-authored programming courses; company questions to DSA alone. Every
# course, these included, practises with questions written for it (socrat.drills): one
# Practice page for all, with only the extras a course has, so a children's math course never
# shows interview banks or a programming-language choice.
LIBRARY_COURSES = frozenset({"zero", "dsa", "cp"})
COMPANY_COURSES = frozenset({"dsa"})
RATED_COURSES = frozenset({"dsa", "cp"})


def features(course_id: str | None, chosen: CourseShape | None = None) -> dict[str, bool]:
    """What the course's Practice area offers. No course (not enrolled yet) offers nothing."""
    chosen = chosen or CODE
    code = chosen.studio == "code"
    library = course_id in LIBRARY_COURSES and code
    return dict(
        code=code,  # a code editor and a programming-language choice
        library=library,  # external problems, recommendations, focus sprints
        companies=course_id in COMPANY_COURSES and code,  # company questions and sprints
        codeforces=course_id in RATED_COURSES and code,  # the rated handle link
        drills=course_id is not None,  # practice sets written for the course, for every course
    )


def features_of(catalog, course_id: str | None) -> dict[str, bool]:
    course = catalog.courses.get(course_id) if course_id else None
    return features(course_id, effective(course) if course is not None else None)


# Planned activities the authoring pipeline can only produce in one studio. An outline that
# plans a "lab" for a maths course, or a "code" assessment for a language course, hands the
# writer a contract it cannot meet, and the reviewer then fails every round for the missing
# activity (seen in the first live run). Everything else (quiz, explain, project, worked
# examples, problem sets, reflection...) can be written in every studio.
NEEDS_STUDIO = {
    ("assessment", "code"): "code",
    ("practice", "lab"): "lab",
}


def producible(studio: str, field: str, values: list[str]) -> list[str]:
    """``values`` without the activities this studio cannot produce, order kept."""
    return [v for v in values if NEEDS_STUDIO.get((field, v), studio) == studio]
