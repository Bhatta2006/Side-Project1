"""Item generators and the verifier (M4 tasks 16–19)."""

import json
import random
import shutil
import textwrap

import pytest

from socrat.catalog import atoms
from socrat.catalog.quizbank import QuizFamily
from socrat.catalog.registry import CONTENT_ROOT, default_catalog
from socrat.quiz import pools
from socrat.quiz.generate import counterexample, framework, mutate, story, trace, verify
from socrat.quiz.generate.harness import Runner, parse

TAXONOMY = atoms.load_taxonomy(CONTENT_ROOT.parent / "atoms")
PROOF = {
    "quiz:dsa:sliding-window:fixed-window-sum",
    "quiz:dsa:binary-search:boundaries",
    "quiz:zero:for-loops:accumulator",
}


def tools():
    from runner.toolchains import toolchains

    return toolchains()


def python_only():
    return Runner({"python": tools()["python"]}, timeout=10)


def family(template: str, fmt: str, reference: str = "v", languages=("python",), stop=4):
    return QuizFamily.model_validate(
        dict(
            id=f"quiz:dsa:sliding-window:{template.replace('_', '-')}",
            family=template.replace("_", "-"),
            concept="dsa:sliding-window",
            format=fmt,
            tracks=["interview"],
            languages=list(languages),
            generator=dict(
                template=template,
                reference=reference,
                seeds={
                    "practice": {"start": 0, "stop": stop - 1},
                    "assessment": {"start": stop - 1, "stop": stop},
                },
            ),
            provenance={},
        )
    )


def write_generator(root, template, body):
    (root / "generators").mkdir(parents=True, exist_ok=True)
    source = "from socrat.quiz.generate.framework import Draft, Option\n\n" + textwrap.dedent(body)
    (root / "generators" / f"{template}.py").write_text(source, encoding="utf-8")


def problems(verdicts):
    return [p for v in verdicts for p in v.problems]


# ---------------------------------------------------------------- the three proof families


@pytest.fixture(scope="module")
def catalog():
    return default_catalog()


def test_proof_families_are_deterministic_and_distinct(catalog):
    root = catalog.quiz_root
    for family_id in PROOF:
        fam = catalog.quiz_families[family_id]
        faces = set()
        for seed, _ in framework.seeds(fam):
            first = framework.draft(root, fam, seed)
            assert first == framework.draft(root, fam, seed)
            assert set(first.code) == {"python", "cpp", "java"}
            assert len(first.options) == 4
            faces.add(first.face())
        assert len(faces) == 100  # the accumulator has one spare seed for a duplicate


def test_proof_families_split_about_seventy_thirty(catalog):
    served = [i for i in pools.bank(catalog) if i.seed is not None]
    for family_id in PROOF:
        practice = sum(i.pool == "practice" for i in served if i.family == family_id)
        assert abs(practice - 70) <= 1


def test_every_proof_item_verifies_in_three_languages_and_the_manifest_is_current(catalog):
    available = tools()
    if not {"python", "cpp", "java"} <= set(available):
        pytest.skip("needs Python, C++ and Java toolchains")
    root = catalog.quiz_root
    manifest = framework.load_manifest(root)
    runner = Runner(available)
    for family_id in sorted(PROOF):
        fam = catalog.quiz_families[family_id]
        verdicts = verify.verify_family(root, fam, runner, TAXONOMY)
        assert problems(verdicts) == []
        assert sum(v.ok for v in verdicts) == 100
        assert manifest[family_id] == verify.manifest_entry(root, fam, verdicts)


def test_new_misconceptions_are_all_used(catalog):
    """D6: every specific ID added since M4 is used by a distractor, pitfall or micro-lesson."""
    used = {t for i in pools.bank(catalog) for t in i.misconceptions if t}
    for fam in catalog.quiz_families.values():
        used |= {rule.misconception for rule in fam.distractors}
    for pattern in catalog.patterns.values():
        used |= set(pattern.pitfalls)
    for pack in catalog.pattern_atoms.values():
        used |= {a.misconception for a in pack.atoms if a.misconception}
    text = (CONTENT_ROOT.parent / "atoms" / "misconceptions.yaml").read_text(encoding="utf-8")
    added = text.split("(M4, decision D6)")[1]
    new_ids = {line.strip()[2:] for line in added.splitlines() if line.strip().startswith("- ")}
    assert len(new_ids) >= 17
    assert new_ids - {"trace-step-slip"} <= used  # trace-step-slip is used by trace.options


def test_only_verified_items_reach_the_bank(catalog, tmp_path):
    served = [i for i in pools.bank(catalog) if i.seed is not None]
    manifest = framework.load_manifest(catalog.quiz_root)
    assert len(served) == sum(len(entry["items"]) for entry in manifest.values())
    assert all(not i.reviewed and i.status == "provisional" for i in served)
    by_family = {f: [i for i in served if i.family == f] for f in PROOF}
    assert {f: len(v) for f, v in by_family.items()} == {f: 100 for f in PROOF}
    assert {2, 3, 4} <= {i.band for i in served} <= {2, 3, 4, 5, 6}  # Spec.bands lifts hard traces

    # A copy of the quiz root with one tampered digest and one stale family.
    root = tmp_path / "quiz"
    shutil.copytree(catalog.quiz_root, root)
    manifest = json.loads((root / "verified.json").read_text(encoding="utf-8"))
    manifest["quiz:dsa:sliding-window:fixed-window-sum"]["items"]["0"] = "0" * 64
    manifest["quiz:zero:for-loops:accumulator"]["source"] = "stale"
    (root / "verified.json").write_text(json.dumps(manifest), encoding="utf-8")
    original = catalog.quiz_root
    try:
        catalog.quiz_root = root
        counts = {}
        for item in pools.generated_bank(catalog):
            counts[item.family] = counts.get(item.family, 0) + 1
    finally:
        catalog.quiz_root = original
    assert counts["quiz:dsa:sliding-window:fixed-window-sum"] == 99  # tampered digest
    assert "quiz:zero:for-loops:accumulator" not in counts  # stale source
    assert counts["quiz:dsa:binary-search:boundaries"] == 100  # untouched


# ---------------------------------------------------------------- verifier rejects


def test_broken_generator_is_rejected(tmp_path):
    write_generator(tmp_path, "boom", "def generate(rng, params):\n    raise RuntimeError('no')\n")
    verdicts = verify.verify_family(
        tmp_path, family("boom", "output_prediction"), python_only(), TAXONOMY
    )
    assert not any(v.ok for v in verdicts)
    assert all("generator failed: RuntimeError" in v.problems[0] for v in verdicts)


def test_wrong_answer_is_rejected(tmp_path):
    write_generator(
        tmp_path,
        "wrong",
        """
        def generate(rng, params):
            v = rng.randint(1, 9)
            return Draft(prompt="What prints?", code={"python": f"print({v} + 1)"},
                         options=[Option(text=str(v)), Option(text="0", misconception="stop-after-first")],
                         answer=0, explanation="Reads the value.", band=2, values={"v": v})
        """,
    )
    found = problems(
        verify.verify_family(
            tmp_path, family("wrong", "output_prediction"), python_only(), TAXONOMY
        )
    )
    assert found and all("shown code prints" in p for p in found)


def test_ambiguous_options_are_rejected(tmp_path):
    write_generator(
        tmp_path,
        "ambiguous",
        """
        def generate(rng, params):
            v = rng.randint(2, 9)
            fill = lambda s: {"python": s}
            return Draft(
                prompt="Which code completes it?",
                code={"python": f"total = 0\\nfor i in range({v}):\\n    ___\\nprint(total)"},
                options=[
                    Option(text="total += 1", fill=fill("total += 1")),
                    Option(text="total = total + 1", misconception="count-not-sum", fill=fill("total = total + 1")),
                    Option(text="total = i", misconception="overwrite-not-accumulate", fill=fill("total = i")),
                ],
                answer=0, explanation="Counts the passes.", band=3, values={"v": v})
        """,
    )
    found = problems(
        verify.verify_family(tmp_path, family("ambiguous", "fill_blank"), python_only(), TAXONOMY)
    )
    assert found and all("ambiguous: option 'total = total + 1'" in p for p in found)


def test_hash_order_output_is_rejected_as_unspecified(tmp_path):
    write_generator(
        tmp_path,
        "hashorder",
        """
        def generate(rng, params):
            words = sorted({f"w{rng.randint(0, 999)}" for _ in range(12)})
            first = words[0]
            return Draft(prompt="What prints?", code={"python": f"print(next(iter(set({words!r}))))"},
                         options=[Option(text=first), Option(text="none", misconception="stop-after-first")],
                         answer=0, explanation="Sets have no order.", band=2, values={"v": first})
        """,
    )
    found = problems(
        verify.verify_family(
            tmp_path, family("hashorder", "output_prediction"), python_only(), TAXONOMY
        )
    )
    assert any("unspecified behaviour" in p for p in found)


def test_languages_that_disagree_are_rejected(tmp_path):
    available = tools()
    if "cpp" not in available:
        pytest.skip("needs a C++ toolchain")
    write_generator(
        tmp_path,
        "division",
        """
        def generate(rng, params):
            v = rng.choice([7, 9, 11])
            return Draft(prompt="What prints?",
                         code={"python": f"print(-{v} // 2)", "cpp": f'cout << -{v} / 2 << "\\\\n";'},
                         options=[Option(text=str(-v // 2)), Option(text="0", misconception="stop-after-first")],
                         answer=0, explanation="Floor division.", band=2, values={"v": -v // 2})
        """,
    )
    runner = Runner({k: available[k] for k in ("python", "cpp")})
    fam = family("division", "output_prediction", languages=("python", "cpp"))
    found = problems(verify.verify_family(tmp_path, fam, runner, TAXONOMY))
    assert found and all("outputs disagree" in p for p in found)


def test_unobservable_defect_and_nondeterminism_are_rejected(tmp_path):
    write_generator(
        tmp_path,
        "hidden",
        """
        import random as _global
        def generate(rng, params):
            v = rng.randint(1, 9)
            noise = _global.random()
            code = f"print({v})"
            return Draft(prompt="Which change fixes it?", code={"python": code},
                         options=[Option(text="Leave it", variant={"python": code}),
                                  Option(text=f"Print {noise}", misconception="off-by-one-output",
                                         variant={"python": "print(0)"})],
                         answer=0, explanation="Nothing to fix.", band=4, values={"v": v})
        """,
    )
    found = problems(
        verify.verify_family(tmp_path, family("hidden", "bug_spot"), python_only(), TAXONOMY)
    )
    assert any("not observable" in p for p in found)
    assert any("not deterministic" in p for p in found)


def test_draft_contract_and_taxonomy_are_enforced(tmp_path):
    write_generator(
        tmp_path,
        "untagged",
        """
        def generate(rng, params):
            return Draft(prompt="What prints?", code={"python": "print(1)"},
                         options=[Option(text="1"), Option(text="2")], answer=0,
                         explanation="Prints one.", band=2, values={"v": 1})
        """,
    )
    found = problems(
        verify.verify_family(
            tmp_path, family("untagged", "output_prediction", "1"), python_only(), TAXONOMY
        )
    )
    assert found and all("needs a misconception" in p for p in found)
    write_generator(
        tmp_path,
        "unknown_tag",
        """
        def generate(rng, params):
            return Draft(prompt="What prints?", code={"python": "print(1)"},
                         options=[Option(text="1"), Option(text="2", misconception="not-a-real-id")],
                         answer=0, explanation="Prints one.", band=2, values={"v": 1})
        """,
    )
    found = problems(
        verify.verify_family(
            tmp_path, family("unknown_tag", "output_prediction", "1"), python_only(), TAXONOMY
        )
    )
    assert any("unknown misconception not-a-real-id" in p for p in found)
    assert any("duplicate of seed" not in p for p in found)


def test_duplicates_are_excluded_but_not_errors(tmp_path):
    write_generator(
        tmp_path,
        "same",
        """
        def generate(rng, params):
            return Draft(prompt="What prints?", code={"python": "print(1)"},
                         options=[Option(text="1"), Option(text="2", misconception="stop-after-first")],
                         answer=0, explanation="Prints one.", band=2, values={"v": 1})
        """,
    )
    verdicts = verify.verify_family(
        tmp_path, family("same", "output_prediction", "1"), python_only(), TAXONOMY
    )
    assert [v.ok for v in verdicts] == [True, False, False, False]
    entry = verify.manifest_entry(tmp_path, family("same", "output_prediction", "1"), verdicts)
    assert entry["duplicates"] == {"1": 0, "2": 0, "3": 0} and entry["rejected"] == {}


# ---------------------------------------------------------------- harness


def test_harness_isolates_failures_per_snippet():
    runner = python_only()
    results = runner.run(
        "python", ["print(2)", "print([][1])", "while True: pass", "print('a')\nprint('b')"]
    )
    assert [r.output for r in results] == ["2", None, None, "a\nb"]
    assert results[1].error.startswith("ERR IndexError") and results[2].error == "timeout"
    assert runner.run("cpp", ["cout << 1;"])[0].error == "cpp toolchain unavailable"
    assert runner.run("python", []) == []


def test_harness_finds_snippets_that_do_not_compile():
    available = tools()
    if "cpp" not in available:
        pytest.skip("needs a C++ toolchain")
    runner = Runner({"cpp": available["cpp"]})
    results = runner.run("cpp", ["cout << 1;", "this is not c++;", "cout << 3;"])
    assert results[0].output == "1" and results[2].output == "3"
    assert results[1].output is None and "compile failed" in results[1].error


def test_parse_keeps_the_open_block_separate():
    found, last, tail = parse("\x1e0\nhello\n\x1e1\nwor")
    assert found[0].output == "hello" and last == 1 and tail == "wor"


# ---------------------------------------------------------------- building blocks


def test_mutation_edits_exactly_one_whole_line():
    code = {"python": "lo = 0\nif a < x:\n    hi = mid\nhi = mid - 1"}
    edit = {"python": ("hi = mid", "hi = mid + 7")}
    assert mutate.apply(code, edit)["python"] == "lo = 0\nif a < x:\n    hi = mid + 7\nhi = mid - 1"
    assert mutate.applicable(code, edit)
    assert not mutate.applicable(code, {"python": ("missing", "x")})
    with pytest.raises(ValueError, match="exactly one line"):
        mutate.apply_line("a\na", "a", "b")
    with pytest.raises(ValueError, match="no rewrite"):
        mutate.apply({"python": "a", "cpp": "a"}, {"python": ("a", "b")})
    assert mutate.reverse(edit) == {"python": ("hi = mid + 7", "hi = mid")}


def test_defect_catalogue_is_checked_against_the_taxonomy(tmp_path):
    catalogue = mutate.load(CONTENT_ROOT.parent / "quiz", TAXONOMY)
    assert catalogue.get("bs-skip-mid").misconception == "exclude-candidate-mid"
    with pytest.raises(KeyError):
        catalogue.get("nope")
    (tmp_path / "defects.yaml").write_text(
        "defects:\n  - {id: x, kind: off-by-one, misconception: nope, description: a long enough text}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown misconception nope"):
        mutate.load(tmp_path, TAXONOMY)


def test_binary_search_generator_declares_catalogued_defects(catalog):
    fam = catalog.quiz_families["quiz:dsa:binary-search:boundaries"]
    declared = framework.module(catalog.quiz_root, fam.generator).DEFECTS
    catalogue = mutate.load(catalog.quiz_root, TAXONOMY)
    assert {catalogue.get(d).id for d in declared} == set(declared)


def test_trace_options_use_neighbouring_steps():
    def steps():
        lo, hi = 0, 8
        while lo < hi:
            mid = (lo + hi) // 2
            lo, hi = (mid + 1, hi) if mid < 5 else (lo, mid)
            yield lo, hi

    lines = trace.states(steps)
    assert lines[:2] == ["5 8", "5 6"]
    options = trace.options(lines, 2, [("0 8", "lo-hi-confusion"), ("5 6", "x")])
    assert options[0] == ("5 6", None)
    assert ("5 8", "trace-step-slip") in options and ("0 8", "lo-hi-confusion") in options
    assert len({t for t, _ in options}) == len(options)


def test_story_fills_every_slot():
    text, chosen = story.fill(
        "{who} ships parcels in {n} trucks.", {"who": ["Ana", "Ravi"], "n": ["3"]}, random.Random(1)
    )
    assert "{" not in text and chosen["n"] == "3" and chosen["who"] in text
    with pytest.raises(ValueError, match="no values for"):
        story.fill("{missing}", {}, random.Random(1))


def test_counterexample_search_for_greedy_coin_change():
    def greedy(coins, amount):
        count = 0
        for c in sorted(coins, reverse=True):
            count += amount // c
            amount %= c
        return count if amount == 0 else -1

    def brute(coins, amount):
        best = [0] + [10**9] * amount
        for a in range(1, amount + 1):
            best[a] = min([best[a - c] + 1 for c in coins if c <= a] or [10**9])
        return best[amount] if best[amount] < 10**9 else -1

    inputs = [((1, 3, 4), n) for n in range(1, 10)]
    assert counterexample.find(greedy, brute, inputs) == ((1, 3, 4), 6)
    assert counterexample.find(brute, brute, inputs) is None
    bad, good = counterexample.split(greedy, brute, inputs)
    assert ((1, 3, 4), 6) in bad and ((1, 3, 4), 4) in good
    assert counterexample.breaks(lambda *a: 1 / 0, brute, ((1,), 1))


# ---------------------------------------------------------------- kit


def test_kit_stops_endless_variants_and_flags_missing_lines():
    from socrat.quiz.generate import kit

    assert kit.prints("print(1 + 1)") == "2"
    assert kit.prints("while True: pass") is None  # step limit, not a hang
    assert kit.prints("print([][1])") is None

    spec = kit.Spec(
        sample=lambda rng, params: {"v": rng.randint(1, 9)},
        program=lambda v: {"python": f"x = {v['v']}  # a comment hides the line\nprint(x)"},
        answer=lambda v: str(v["v"]),
        wrong=lambda v: [],
        predict="What prints?",
        fill=lambda v: "Fill it.",
        fix=lambda v: "Fix it.",
        explain=lambda v, a: "It prints x.",
        blanks=[kit.Blank(kit.lines("x = 1"), [])],
    )
    messages = set()
    for seed in range(12):  # each seed picks predict (no distractors) or the blank
        with pytest.raises(ValueError) as failure:
            kit.generate(spec, random.Random(seed), {})
        messages.add(str(failure.value).split(" after")[0].split(" is not")[0])
    assert "blank line 'x = 1'" in messages  # failed at once, not after 200 tries
    assert "no predict item for 'predict'" in messages
