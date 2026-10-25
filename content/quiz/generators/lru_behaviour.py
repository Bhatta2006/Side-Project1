"""LRU cache behaviour: which key is evicted, and what each get returns.

The snippet keeps a last-use time per key and evicts the smallest, which is slow but makes
the policy explicit; the lesson builds the O(1) hash map + linked list. Wrong answers are the
classic slips: evicting in insertion order (FIFO), a get that does not count as a use,
evicting the most recent key, evicting on an update of an existing key, and holding one key
too many.
"""

from collections import OrderedDict

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

REFRESH = lines("used[key] = clock  # a hit counts as a use", "used[key] = clock;  // a hit counts as a use",
                "used.put(key, clock);  // a hit counts as a use")
FULL = lines("if key not in value and len(value) == cap:", "if (!value.count(key) && (int)value.size() == cap) {",
             "if (!value.containsKey(key) && value.size() == cap) {")
OLDEST = lines("old = min(sorted(used), key=used.get)", "for (auto& [k, t] : used) if (old == -1 || t < used[old]) old = k;",
               "for (int k : used.keySet()) if (old == -1 || used.get(k) < used.get(old)) old = k;")
STAMP = lines("used[key] = clock", "used[key] = clock;", "used.put(key, clock);")
TICK = lines("clock += 1", "clock += 1;")


def program(v: dict) -> dict[str, str]:
    ops, cap = v["ops"], v["cap"]
    py = ", ".join(f'("{o}", {k}, {x})' for o, k, x in ops)
    cpp = ", ".join(f'{{"{o}", {k}, {x}}}' for o, k, x in ops)
    jop = ", ".join(f'"{o}"' for o, _, _ in ops)
    jkey = ", ".join(str(k) for _, k, _ in ops)
    jval = ", ".join(str(x) for _, _, x in ops)
    return {
        "python": (
            f"ops = [{py}]\ncap = {cap}\n"
            "value = {}\n"
            "used = {}\n"
            "clock = 0\n"
            "out = []\n"
            "for op, key, val in ops:\n"
            "    clock += 1\n"
            '    if op == "get":\n'
            "        if key in value:\n"
            "            used[key] = clock  # a hit counts as a use\n"
            "            out.append(value[key])\n"
            "        else:\n"
            "            out.append(-1)\n"
            "    else:\n"
            "        if key not in value and len(value) == cap:\n"
            "            old = min(sorted(used), key=used.get)\n"
            "            del value[old]\n"
            "            del used[old]\n"
            "        value[key] = val\n"
            "        used[key] = clock\n"
            'print(" ".join(map(str, out)))'
        ),
        "cpp": (
            f"vector<tuple<string, int, int>> ops = {{{cpp}}};\nint cap = {cap};\n"
            "map<int, int> value;\n"
            "map<int, int> used;\n"
            "int clock = 0;\n"
            "vector<int> out;\n"
            "for (auto [op, key, val] : ops) {\n"
            "    clock += 1;\n"
            '    if (op == "get") {\n'
            "        if (value.count(key)) {\n"
            "            used[key] = clock;  // a hit counts as a use\n"
            "            out.push_back(value[key]);\n"
            "        } else {\n"
            "            out.push_back(-1);\n"
            "        }\n"
            "    } else {\n"
            "        if (!value.count(key) && (int)value.size() == cap) {\n"
            "            int old = -1;\n"
            "            for (auto& [k, t] : used) if (old == -1 || t < used[old]) old = k;\n"
            "            value.erase(old);\n"
            "            used.erase(old);\n"
            "        }\n"
            "        value[key] = val;\n"
            "        used[key] = clock;\n"
            "    }\n"
            "}\n"
            'for (size_t i = 0; i < out.size(); i++) cout << out[i] << (i + 1 < out.size() ? " " : "\\n");'
        ),
        "java": (
            f"String[] op = {{{jop}}};\nint[] keys = {{{jkey}}};\nint[] vals = {{{jval}}};\nint cap = {cap};\n"
            "Map<Integer, Integer> value = new TreeMap<>();\n"
            "Map<Integer, Integer> used = new TreeMap<>();\n"
            "int clock = 0;\n"
            "List<String> out = new ArrayList<>();\n"
            "for (int i = 0; i < op.length; i++) {\n"
            "    int key = keys[i], val = vals[i];\n"
            "    clock += 1;\n"
            '    if (op[i].equals("get")) {\n'
            "        if (value.containsKey(key)) {\n"
            "            used.put(key, clock);  // a hit counts as a use\n"
            "            out.add(String.valueOf(value.get(key)));\n"
            "        } else {\n"
            '            out.add("-1");\n'
            "        }\n"
            "    } else {\n"
            "        if (!value.containsKey(key) && value.size() == cap) {\n"
            "            int old = -1;\n"
            "            for (int k : used.keySet()) if (old == -1 || used.get(k) < used.get(old)) old = k;\n"
            "            value.remove(old);\n"
            "            used.remove(old);\n"
            "        }\n"
            "        value.put(key, val);\n"
            "        used.put(key, clock);\n"
            "    }\n"
            "}\n"
            'System.out.println(String.join(" ", out));'
        ),
    }


def simulate(ops, cap, refresh=True, evict="lru", update_evicts=False, room=0):
    """Independent model on an OrderedDict: front = least recently used."""
    cache, out = OrderedDict(), []
    for op, key, val in ops:
        if op == "get":
            if key in cache:
                if refresh:
                    cache.move_to_end(key)
                out.append(cache[key])
            else:
                out.append(-1)
            continue
        if (key not in cache or update_evicts) and len(cache) >= cap + room:
            if evict == "lru":
                cache.popitem(last=False)
            else:
                cache.popitem(last=True)
        if key in cache:
            cache.move_to_end(key)
        cache[key] = val
    return " ".join(map(str, out))


def fifo(ops, cap):
    cache, order, out = {}, [], []
    for op, key, val in ops:
        if op == "get":
            out.append(cache.get(key, -1))
            continue
        if key not in cache and len(cache) == cap:
            del cache[order.pop(0)]
        if key not in cache:
            order.append(key)
        cache[key] = val
    return " ".join(map(str, out))


def lru(ops, cap):
    return simulate(ops, cap)


def wrong(v):
    ops, cap = v["ops"], v["cap"]
    return [
        (fifo(ops, cap), "lru-fifo-not-lru"),
        (simulate(ops, cap, refresh=False), "lru-get-no-refresh"),
        (simulate(ops, cap, evict="mru"), "lru-evict-most-recent"),
        (simulate(ops, cap, room=1), "lru-capacity-off-by-one"),
        (simulate(ops, cap, update_evicts=True), "lru-evict-on-update"),
    ]


def sample(rng, params):
    cap = rng.randint(*params["cap"])
    keys = list(range(params["keys"][0], params["keys"][1] + 1))
    ops, stored = [], set()
    for _ in range(rng.randint(*params["ops"])):
        if stored and rng.random() < 0.45:
            ops.append(("get", rng.choice(keys), 0))
        else:
            key = rng.choice(keys)
            stored.add(key)
            ops.append(("put", key, rng.randint(1, 9) * 10 + key))
    if sum(1 for o in ops if o[0] == "get") < 3:
        ops += [("get", rng.choice(keys), 0) for _ in range(3)]
    return {"ops": ops, "cap": cap}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: lru(v["ops"], v["cap"]),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code runs an LRU cache of capacity {v['cap']}: when it is full, a new key evicts the key "
        "used least recently, and both get and put count as uses. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code runs an LRU cache of capacity {v['cap']}: when it is full, a new key evicts the key "
        "used least recently, and both get and put count as uses. It prints the wrong results. Which "
        "one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "Every put and every successful get makes its key the most recently used. A put of a new key "
        "into a full cache evicts the key whose last use is oldest; updating a key that is already "
        f"stored evicts nothing. The gets return {answer}."
    ),
    blanks=[
        Blank(
            OLDEST,
            [
                (lines("old = max(sorted(used), key=used.get)",
                       "for (auto& [k, t] : used) if (old == -1 || t > used[old]) old = k;",
                       "for (int k : used.keySet()) if (old == -1 || used.get(k) > used.get(old)) old = k;"),
                 "lru-evict-most-recent"),
                (lines("old = min(used)", "for (auto& [k, t] : used) if (old == -1 || k < old) old = k;",
                       "for (int k : used.keySet()) if (old == -1 || k < old) old = k;"), "confuse-index-value"),
                (lines("old = max(used)", "for (auto& [k, t] : used) if (old == -1 || k > old) old = k;",
                       "for (int k : used.keySet()) if (old == -1 || k > old) old = k;"), "confuse-index-value"),
            ],
        ),
        Blank(
            FULL,
            [
                (lines("if len(value) == cap:", "if ((int)value.size() == cap) {", "if (value.size() == cap) {"),
                 "lru-evict-on-update"),
                (lines("if key not in value and len(value) > cap:",
                       "if (!value.count(key) && (int)value.size() > cap) {",
                       "if (!value.containsKey(key) && value.size() > cap) {"), "lru-capacity-off-by-one"),
                (lines("if key not in value and len(value) == cap - 1:",
                       "if (!value.count(key) && (int)value.size() == cap - 1) {",
                       "if (!value.containsKey(key) && value.size() == cap - 1) {"), "loop-bound-off-by-one"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "lru-get-no-refresh",
            edit(REFRESH, lines("used[key] = used[key]  # a hit counts as a use",
                                "used[key] = used[key];  // a hit counts as a use",
                                "used.put(key, used.get(key));  // a hit counts as a use")),
            "Record the time of a successful get: used[key] = clock",
            "A get is a use, so it must make the key the most recently used.",
        ),
        Fix(
            "lru-evict-most-recent",
            edit(OLDEST, lines("old = max(sorted(used), key=used.get)",
                               "for (auto& [k, t] : used) if (old == -1 || t > used[old]) old = k;",
                               "for (int k : used.keySet()) if (old == -1 || used.get(k) > used.get(old)) old = k;")),
            "Evict the key with the smallest last-use time",
            "The largest time is the most recently used key, the one to keep.",
        ),
        Fix(
            "lru-evict-on-update",
            edit(FULL, lines("if len(value) == cap:", "if ((int)value.size() == cap) {", "if (value.size() == cap) {")),
            "Only evict when the key is new: check key not in value first",
            "Updating a stored key does not add an entry, so nothing needs to leave.",
        ),
    ],
    decoys=[
        Decoy(edit(TICK, lines("clock += 2", "clock += 2;")), "Advance the clock by 2 per operation",
              "trace-step-slip"),
        Decoy(edit(STAMP, lines("used[key] = 0", "used[key] = 0;", "used.put(key, 0);")),
              "Give a put the time 0", "lru-fifo-not-lru"),
        Decoy(edit(FULL, lines("if key not in value and len(value) > cap:",
                               "if (!value.count(key) && (int)value.size() > cap) {",
                               "if (!value.containsKey(key) && value.size() > cap) {")),
              "Evict only when the cache holds more than cap keys", "lru-capacity-off-by-one"),
        Decoy(edit(REFRESH, lines("used[key] = -clock  # a hit counts as a use",
                                  "used[key] = -clock;  // a hit counts as a use",
                                  "used.put(key, -clock);  // a hit counts as a use")),
              "Store the negative time on a get", "lru-evict-most-recent"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"lru": lru}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
