"""Questions written in one language's syntax never reach learners of another."""

from socrat.catalog import dialect
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import QuizItem


def mcq(prompt, options=("a", "b"), explanation="Because it is."):
    return QuizItem(
        id="x",
        prompt=prompt,
        options=list(options),
        answer=0,
        explanation=explanation,
        difficulty=3,
    )


def test_python_prose_is_not_served_to_cpp_or_java():
    for text in (
        "Why can int(math.sqrt(n)) be wrong for n near 10^16?",
        "A program reads a = input() and b = input() and prints a + b.",
        "What is (7 + 2 - 1) // 2?",
    ):
        item = mcq(text)
        assert item.fits("python") and not item.fits("cpp") and not item.fits("java"), text


def test_cpp_and_java_prose_stay_in_their_language():
    assert mcq("What does std::cout << 7 / 2 print?").fits("cpp")
    assert not mcq("What does std::cout << 7 / 2 print?").fits("python")
    assert mcq("What does System.out.println(7 / 2) print?").fits("java")
    assert not mcq("What does System.out.println(7 / 2) print?").fits("cpp")


def test_neutral_prose_and_explicit_tags_still_work():
    assert all(
        mcq("How many times does a loop over 5 items run?").fits(x)
        for x in ("python", "cpp", "java")
    )
    # "In C++, ..." names the language; that wins over any marker.
    assert mcq("In C++, what does a[-1] do?").fits("cpp")
    assert dialect.spoken("plain words about a list and a string") == set()


def test_the_reported_question_no_longer_reaches_cpp_learners():
    concept = default_catalog().concept("zero:operators-and-expressions")
    wrap = next(q for q in concept.quiz if q.id == "backwards-wrap-python")
    assert not wrap.fits("cpp") and not wrap.fits("java") and wrap.fits("python")
