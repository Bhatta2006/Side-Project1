"""Sieve of Eratosthenes: how many primes are there up to n.

Wrong answers are the classic slips: counting 0 and 1 as prime, stopping one short of n,
counting composites instead of primes, and forgetting the only even prime.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

CHECK = lines("if is_prime[i]:", "if (is_prime[i]) {", "if (isPrime[i]) {")
START = lines("j = i * i", "int j = i * i;")
STEP = lines("j += i", "j += i;")
BOUND = lines("while i * i <= n:", "while (i * i <= n) {")
FIRST = lines("i = 2", "int i = 2;")
ZERO = lines("is_prime[0] = False", "is_prime[0] = false;", "isPrime[0] = false;")
ONE = lines("is_prime[1] = False", "is_prime[1] = false;", "isPrime[1] = false;")


def primes_up_to(n):
    """Independent check: trial division, no sieve."""
    return [p for p in range(2, n + 1) if all(p % d for d in range(2, int(p**0.5) + 1))]


def program(v: dict) -> dict[str, str]:
    n = v["n"]
    return {
        "python": (
            f"n = {n}\n"
            "is_prime = [True] * (n + 1)\n"
            "is_prime[0] = False\n"
            "is_prime[1] = False\n"
            "i = 2\n"
            "while i * i <= n:\n"
            "    if is_prime[i]:\n"
            "        j = i * i\n"
            "        while j <= n:\n"
            "            is_prime[j] = False\n"
            "            j += i\n"
            "    i += 1\n"
            "print(sum(is_prime))"
        ),
        "cpp": (
            f"int n = {n};\n"
            "vector<bool> is_prime(n + 1, true);\n"
            "is_prime[0] = false;\n"
            "is_prime[1] = false;\n"
            "int i = 2;\n"
            "while (i * i <= n) {\n"
            "    if (is_prime[i]) {\n"
            "        int j = i * i;\n"
            "        while (j <= n) {\n"
            "            is_prime[j] = false;\n"
            "            j += i;\n"
            "        }\n"
            "    }\n"
            "    i += 1;\n"
            "}\n"
            "int count = 0;\n"
            "for (int p = 0; p <= n; p++) {\n"
            "    if (is_prime[p]) count++;\n"
            "}\n"
            'cout << count << "\\n";'
        ),
        "java": (
            f"int n = {n};\n"
            "boolean[] isPrime = new boolean[n + 1];\n"
            "java.util.Arrays.fill(isPrime, true);\n"
            "isPrime[0] = false;\n"
            "isPrime[1] = false;\n"
            "int i = 2;\n"
            "while (i * i <= n) {\n"
            "    if (isPrime[i]) {\n"
            "        int j = i * i;\n"
            "        while (j <= n) {\n"
            "            isPrime[j] = false;\n"
            "            j += i;\n"
            "        }\n"
            "    }\n"
            "    i += 1;\n"
            "}\n"
            "int count = 0;\n"
            "for (int p = 0; p <= n; p++) {\n"
            "    if (isPrime[p]) count++;\n"
            "}\n"
            "System.out.println(count);"
        ),
    }


def sample(rng, params):
    return {"n": rng.randint(*params["n"])}


def wrong(v):
    n = v["n"]
    count = len(primes_up_to(n))
    return [
        (str(count + 2), "sieve-zero-one-prime"),
        (str(len(primes_up_to(n - 1))), "off-by-one-output"),
        (str(n - 1 - count), "sieve-count-composites"),
        (str(count - 1), "sieve-forget-two"),
        (str(count + 1), "sieve-one-prime"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(len(primes_up_to(v["n"]))),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should count the primes up to {v['n']}. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should count the primes up to {v['n']}, but it prints the wrong "
        "answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Cross out the multiples of each prime starting at its square; what survives from 2 "
        f"to {v['n']} is prime: {answer} numbers."
    ),
    blanks=[
        Blank(
            START,
            [
                (lines("j = i", "int j = i;"), "sieve-cross-out-itself"),
                (lines("j = 2", "int j = 2;"), "sieve-start-two"),
                (lines("j = i + 1", "int j = i + 1;"), "sieve-step-by-one"),
            ],
        ),
        Blank(
            STEP,
            [
                (lines("j += 1", "j += 1;"), "sieve-step-by-one"),
                (lines("j += 2", "j += 2;"), "sieve-step-by-two"),
                (lines("j *= i", "j *= i;"), "sieve-multiply-not-add"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "sieve-step",
            edit(STEP, lines("j += 1", "j += 1;")),
            "Move j on by i, so only the multiples of i are crossed out",
            "Stepping by 1 crosses out every number, prime or not.",
        ),
        Fix(
            "sieve-skip-composite",
            edit(CHECK, lines("if not is_prime[i]:", "if (!is_prime[i]) {", "if (!isPrime[i]) {")),
            "Cross out multiples only for numbers still marked prime",
            "Only a prime's multiples need crossing out; composites were already handled.",
        ),
    ],
    decoys=[
        Decoy(
            edit(START, lines("j = i", "int j = i;")),
            "Start j at i, the prime itself",
            "sieve-cross-out-itself",
        ),
        Decoy(
            edit(FIRST, lines("i = 3", "int i = 3;")),
            "Begin the outer loop at 3",
            "sieve-forget-two",
        ),
        Decoy(
            edit(ZERO, lines("is_prime[0] = True", "is_prime[0] = true;", "isPrime[0] = true;")),
            "Leave 0 marked prime",
            "sieve-zero-one-prime",
        ),
        Decoy(
            edit(STEP, lines("j += 2", "j += 2;")),
            "Move j on by 2",
            "sieve-step-by-two",
        ),
        Decoy(
            edit(ONE, lines("is_prime[1] = True", "is_prime[1] = true;", "isPrime[1] = true;")),
            "Leave 1 marked prime",
            "sieve-one-prime",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"primes_up_to": primes_up_to}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
