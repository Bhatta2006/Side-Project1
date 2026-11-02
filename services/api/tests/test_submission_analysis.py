"""Hidden-test diagnosis and complexity estimates read from a finished submission."""

from socrat.judge import analysis
from socrat.models import Submission

CPP_INT = (
    "#include <iostream>\nint main(){ int n; std::cin >> n; int s = 0; s = n * n; std::cout << s; }"
)


def job(source="", language="cpp", verdict="wrong_answer", cases=None, tests=None, mode="submit"):
    return Submission(
        source=source,
        language=language,
        mode=mode,
        status="done",
        verdict=verdict,
        cases=cases or [],
        tests=tests or [],
    )


def failing_hidden(expected: str):
    cases = [
        {"status": "passed", "public": True},
        {"status": "wrong_answer", "public": False},
    ]
    tests = [{"expected": "1"}, {"expected": expected}]
    return cases, tests


def test_int_overflow_on_a_hidden_case_is_named():
    cases, tests = failing_hidden("4999999950000000")
    found = analysis.diagnosis(job(CPP_INT, cases=cases, tests=tests))
    assert found and "long long" in found and "1LL" in found


def test_java_is_told_to_use_long():
    cases, tests = failing_hidden("9999999999")
    found = analysis.diagnosis(job("class A { int s; }", "java", cases=cases, tests=tests))
    assert found and "`long`" in found


def test_no_diagnosis_when_the_value_fits_or_the_type_is_already_wide():
    cases, tests = failing_hidden("42")
    assert analysis.diagnosis(job(CPP_INT, cases=cases, tests=tests)) is None
    cases, tests = failing_hidden("9999999999")
    assert analysis.diagnosis(job("long long s;", cases=cases, tests=tests)) is None


def test_no_diagnosis_when_a_visible_case_fails_or_python():
    cases, tests = failing_hidden("9999999999")
    cases[0]["status"] = "wrong_answer"
    assert analysis.diagnosis(job(CPP_INT, cases=cases, tests=tests)) is None
    cases, tests = failing_hidden("9999999999")
    assert analysis.diagnosis(job("print(1)", "python", cases=cases, tests=tests)) is None


def test_complexity_follows_loop_nesting_and_sorting():
    def est(source, language="python"):
        return analysis.complexity(job(source, language, verdict="accepted"))

    assert est("print(1)") == {**est("print(1)"), "time": "O(1)", "space": "O(1)"}
    assert est("for i in range(n):\n    pass")["time"] == "O(n)"
    assert est("for i in range(n):\n    for j in range(n):\n        pass")["time"] == "O(n²)"
    assert est("a = sorted(xs)")["time"] == "O(n log n)"
    assert est("a = [x for x in xs]")["space"] == "O(n)"
    cpp = "int main(){ for(int i=0;i<n;i++){ for(int j=0;j<n;j++) s+=1; } }"
    assert est(cpp, "cpp")["time"] == "O(n²)"
    assert (
        est("int main(){ vector<int> v; sort(v.begin(), v.end()); }", "cpp")["time"] == "O(n log n)"
    )


def test_complexity_is_only_for_accepted_code():
    assert analysis.complexity(job("print(1)", "python", verdict="wrong_answer")) is None
