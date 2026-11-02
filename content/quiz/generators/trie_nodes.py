"""Trie insertion: how many nodes (not counting the root) the words create.

Shared prefixes share nodes, and a word that is a prefix of another adds nothing new.
Wrong answers count every letter, count words or distinct letters, or count the root.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

DESCEND = lines("x = child[x][ch]", "x = child[x][c];", "x = child.get(x)[c];")


def program(v: dict) -> dict[str, str]:
    py = ", ".join(f'"{w}"' for w in v["words"])
    return {
        "python": (
            f"words = [{py}]\n"
            "child = [{}]  # child[node][letter] = node; node 0 is the root\n"
            "for w in words:\n"
            "    x = 0\n"
            "    for ch in w:\n"
            "        if ch not in child[x]:\n"
            "            child[x][ch] = len(child)\n"
            "            child.append({})\n"
            "        x = child[x][ch]\n"
            "print(len(child) - 1)"
        ),
        "cpp": (
            f"vector<string> words = {{{py}}};\n"
            "vector<array<int, 26>> child(1);  // child[node][letter] = node, 0 = none; node 0 is the root\n"
            "for (auto& w : words) {\n"
            "    int x = 0;\n"
            "    for (char ch : w) {\n"
            "        int c = ch - 'a';\n"
            "        if (child[x][c] == 0) {\n"
            "            child[x][c] = child.size();\n"
            "            child.push_back({});\n"
            "        }\n"
            "        x = child[x][c];\n"
            "    }\n"
            "}\n"
            'cout << child.size() - 1 << "\\n";'
        ),
        "java": (
            f"String[] words = {{{py}}};\n"
            "List<int[]> child = new ArrayList<>();  // child.get(node)[letter] = node, 0 = none\n"
            "child.add(new int[26]);\n"
            "for (String w : words) {\n"
            "    int x = 0;\n"
            "    for (char ch : w.toCharArray()) {\n"
            "        int c = ch - 'a';\n"
            "        if (child.get(x)[c] == 0) {\n"
            "            child.get(x)[c] = child.size();\n"
            "            child.add(new int[26]);\n"
            "        }\n"
            "        x = child.get(x)[c];\n"
            "    }\n"
            "}\n"
            "System.out.println(child.size() - 1);"
        ),
    }


def nodes(words: list) -> int:
    """Independent check: one node per distinct non-empty prefix."""
    return len({w[:i] for w in words for i in range(1, len(w) + 1)})


def wrong(v):
    words = v["words"]
    right = nodes(words)
    return [
        (str(sum(len(w) for w in words)), "trie-node-per-letter"),
        (str(len({ch for w in words for ch in w})), "trie-distinct-letters"),
        (str(right + 1), "trie-count-root"),
        (str(len(words)), "trie-node-per-word"),
    ]


def sample(rng, params):
    letters = "abcd"[: params["letters"][0]]
    words: list[str] = []
    while len(words) < rng.randint(*params["n"]):
        if words and rng.random() < 0.5:  # extend or cut an earlier word: shared prefixes
            base = rng.choice(words)
            w = base[: rng.randint(1, len(base))] + "".join(
                rng.choice(letters) for _ in range(rng.randint(0, 2))
            )
        else:
            w = "".join(rng.choice(letters) for _ in range(rng.randint(2, 4)))
        if w not in words:
            words.append(w)
    return {"words": words}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(nodes(v["words"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should insert every word into a trie and print how many nodes it created "
        "(the root not counted). Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "Each node is one distinct prefix. A word walks down existing nodes as long as its "
        "prefix is already there and creates nodes only for the new tail, so the words "
        f"{', '.join(v['words'])} need {answer} nodes."
    ),
    blanks=[
        Blank(
            DESCEND,
            [
                (lines("x = 0", "x = 0;"), "trie-restart-at-root"),
                (lines("x = len(child) - 1", "x = child.size() - 1;"), "confuse-index-value"),
                (lines("x = child[x][ch] - 1", "x = child[x][c] - 1;", "x = child.get(x)[c] - 1;"),
                 "off-by-one-output"),
            ],
        ),
    ],
    bands=(3, 4, 5),
)
HELPERS = {"nodes": nodes}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
