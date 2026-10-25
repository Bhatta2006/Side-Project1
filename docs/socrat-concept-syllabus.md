# Socrat — Complete Concept Syllabus for All Three Tracks

**Purpose.** This is the "nothing missing" concept list for Programming from Zero, DSA for Interviews and Competitive Programming. It is meant to be the target the content team (human or agent) builds towards, so that a learner who finishes a track can solve *unseen* problems of that track's level, not just the handful of examples in each lesson.

**Why this exists.** The current catalog (`content/courses/*/concepts/*.yaml`) has 18 + 23 + 20 = 61 concepts. Each concept is a single lesson covering a topic "from the top" (e.g. `dp-2d` covers grid paths, LCS and knapsack in one lesson). A free YouTube playlist (Striver, Aditya Verma, NeetCode, Love Babbar, Luv, Errichto, Kunal Kushwaha) typically spends 10–60 videos on what Socrat currently covers in one YAML file. This document breaks every topic down to the level of **standard problem families** — the problems that cannot be derived intuitively on first sight and must be taught once, explicitly.

**What does NOT change.** The imported external practice index (`content/practice/problems.jsonl`, ~13.9k problems) and company metadata stay as they are. This syllabus defines what gets *taught*; practice mapping hooks into it.

---

## 0. How to read and use this file

### 0.1 Granularity levels

| Level | Meaning | Example |
| --- | --- | --- |
| **Module** | A group of concepts shown as one section in the course | Dynamic Programming |
| **Concept** | One lesson/YAML file (target: 20–60 min) | DP on Strings |
| **Pattern family** | A sub-lesson inside the concept; each one is a *named template* with its own state/transition or code skeleton | LCS family, Edit-distance family, Palindrome family |
| **Anchor problem** | The canonical problem that teaches the family (taught fully, with dry-run) | Longest Common Subsequence |
| **Variant** | A problem solved by bending the anchor (used as practice/quiz, not taught from scratch) | Shortest Common Supersequence, Min insertions/deletions |

Tags used below:

- **[CORE]** must be taught — required to solve unseen problems at the track's level.
- **[STD]** standard but secondary — teach after CORE; frequently asked.
- **[ADV]** advanced/optional — unlock for learners who want depth or a higher rating.
- **[NEW]** not covered anywhere in the current catalog.
- **[SPLIT]** currently merged inside another concept; should become its own concept.

### 0.2 "Done when" — the unseen-problem bar per concept

Every concept in this file should ship with:

1. **Recognition cues** — the words/constraints in a statement that signal this family (e.g. "contiguous", "at most K", n ≤ 20, "minimum maximum").
2. **Template** — state/transition or code skeleton, in Python, C++ and Java.
3. **Anchor problem** — solved step by step, including a wrong first attempt and why it fails.
4. **3–8 variants** — progressive difficulty, each changing exactly one thing about the anchor.
5. **Contrast pair** — a near-miss problem that *looks* like this family but isn't (Socrat already has `content/patterns/contrasts.yaml`; extend it).
6. **Unseen check** — 2+ problems not shown anywhere in the lesson, solved without hints, before the concept is marked mastered.

### 0.3 Reference roadmaps and playlists cross-checked

The lists below are the union of what these sources teach, de-duplicated and ordered by prerequisite:

| Source | Used for |
| --- | --- |
| Striver — takeUforward A2Z DSA Sheet + DP series + Graph series + Tree series | DSA ordering, DP families (1D, grids, subsequences, strings, stocks, LIS, partition/MCM, squares) |
| Aditya Verma — DP, Recursion, Sliding Window, Binary Search, Stack, Heap playlists | Pattern-first teaching (knapsack variants, LCS variants, MCM variants), "identification" approach |
| NeetCode — Roadmap / NeetCode 150 / 250 | Interview pattern coverage and grouping |
| Love Babbar / CodeHelp — DSA sheet, Supreme batch topics | Beginner-to-interview ordering, C++ fundamentals |
| Kunal Kushwaha — DSA bootcamp (Java) | Programming-from-zero depth: number systems, memory, OOP, recursion fundamentals |
| Apna College / Shradha Khapra — C++/Java DSA | Language basics, pattern printing, OOP |
| CS50x (Harvard) / CS50P | Fundamentals pedagogy: memory, abstraction, debugging, files |
| freeCodeCamp — Python / JS for beginners | Zero-level coverage: I/O, types, exceptions, files, modules |
| Grokking the Coding Interview (pattern list) | Pattern taxonomy: fast/slow pointers, merge intervals, cyclic sort, in-place reversal, two heaps, K-way merge, modified binary search, top-K |
| Tech Interview Handbook (Yangshun) / Blind 75 / Grind 169 | Interview-frequency check |
| USACO Guide (Bronze → Silver → Gold → Platinum → Advanced) | CP level structure |
| CSES Problem Set + CSES Handbook (Laaksonen) | CP concept checklist and anchor problems |
| CP-Algorithms (cp-algorithms.com) | Advanced algorithm coverage |
| AtCoder Educational DP Contest (A–Z) | DP anchor set for CP |
| Codeforces EDU section (ITMO) | Segment tree, binary search, two pointers, DSU, suffix array courses |
| Luv (YouTube) CP series, Errichto, Colin Galen, Kartik Arora (DP), Priyansh Agarwal, SecondThread | CP technique depth, contest strategy, DP on trees/digit DP |
| Pepcoding (legacy level 1/2) | Exhaustive recursion/backtracking and DP variants |

---

# TRACK 1 — Programming from Zero

**Goal.** A learner with zero experience can read a plain-English problem, design a solution, write it in one language (Python/C++/Java), debug it, and solve unseen beginner problems (LeetCode Easy "implementation" style, CodeChef/Codeforces 800, HackerRank basic). They are ready to start DSA.

**Current state:** 18 concepts. Missing: how code runs, operators in depth, pattern printing, math-on-numbers problems, basic searching/sorting, number systems, memory model, exceptions, files, modules/libraries, language-specific standard library, complexity intuition, 2D arrays beyond basics, mini-projects.

## Z1. How computers run code [NEW]
- [CORE] What a program is: source code → compiler/interpreter → machine instructions.
- [CORE] Compiled (C++), JVM bytecode (Java), interpreted (Python) — what this means for errors and speed.
- [CORE] Setting up: editor/IDE, running a file, online judges, terminal basics (`cd`, `ls`, running `python file.py` / `g++` / `javac`).
- [CORE] Types of errors: syntax error, runtime error, logic error, time limit exceeded — with examples of each.
- [STD] Flowcharts and pseudocode; writing the steps before code.

## Z2. Output, variables and data types (extend `programs-and-output`, `variables-and-types`)
- [CORE] Printing: multiple values, separators, newlines, escape characters, formatted output (f-strings / `printf` / `String.format`), printing decimals to k places.
- [CORE] Variables as named boxes; assignment vs equality; reassignment; naming rules.
- [CORE] Primitive types: int, float/double, bool, char, string; Python dynamic vs C++/Java static typing.
- [CORE] Integer ranges and **overflow** (int vs long long / long; Python big ints) — why `1e9 * 1e9` breaks in C++/Java.
- [CORE] Type conversion: implicit vs explicit casting; int ↔ string ↔ float; integer truncation.
- [STD] Floating-point precision (`0.1 + 0.2 != 0.3`), comparing floats with epsilon.
- [STD] Constants, `const`/`final`.
- [STD] ASCII/Unicode: characters as numbers (`'a' + 1`, `ord`/`chr`).

## Z3. Operators and expressions [SPLIT from `input-and-arithmetic`]
- [CORE] Arithmetic: `+ - * / // %`; integer vs float division per language; modulo with negatives (Python vs C++/Java difference).
- [CORE] Operator precedence and associativity; using parentheses.
- [CORE] Compound assignment (`+=`), increment/decrement (pre vs post in C++/Java).
- [CORE] Relational and logical operators; short-circuit evaluation.
- [STD] Bitwise operators intro: `& | ^ ~ << >>` (deeper in Z15).
- [STD] Math library: `abs, pow, sqrt, floor, ceil, round, min, max`; pitfalls of `pow` with integers.

## Z4. Input
- [CORE] Reading a single value, multiple values on one line, n values, n lines, a matrix.
- [CORE] Reading until end of file; reading strings with spaces.
- [STD] Competitive-judge input format: first line `t` test cases.
- [STD] Fast input basics (`sys.stdin`, `ios::sync_with_stdio(false)`, `BufferedReader`).

## Z5. Conditionals (extend `conditionals`, `boolean-logic`)
- [CORE] if / else if / else; nested if; ternary operator.
- [CORE] switch / match statements.
- [CORE] Combining conditions: and/or/not; De Morgan's laws; truthiness in Python.
- [CORE] Classic problems: even/odd, largest of three, leap year, grade calculator, triangle validity & type, quadrant of a point, character classification (vowel/consonant/digit/upper/lower), simple calculator, electricity-bill slabs.
- [STD] Avoiding deep nesting: early return, guard clauses.

## Z6. Loops (extend `for-loops`, `while-loops`, `nested-loops`)
- [CORE] for loop with ranges (start, stop, step, reverse); while loop; do-while (C++/Java).
- [CORE] `break`, `continue`; loop with flag variable.
- [CORE] Loop patterns: counter, accumulator (sum/product), running max/min, search-and-stop, count-matching.
- [CORE] Infinite loops and off-by-one errors; tracing a loop by hand with a table.
- [CORE] Nested loops: understanding total iterations (n × m), loop variable dependence (`j` from `i`).
- [CORE] **Pattern printing** [NEW] — the standard ~20 patterns every playlist teaches, because they train nested-loop control: solid/hollow rectangle, right triangle (stars, numbers, alphabets), inverted triangle, pyramid, inverted pyramid, diamond, hollow diamond, Floyd's triangle, Pascal's triangle, 0-1 triangle, butterfly, number crown, alphabet ramp, hollow square, spiral number square. Teach the method: rows → per-row spaces → per-row symbols as functions of row index.

## Z7. Math on numbers [NEW] — "basic maths" module
These are the Step-1 problems of Striver A2Z and every beginner playlist; they teach digit manipulation with `% 10` and `// 10`.
- [CORE] Extracting digits; count digits (loop and `log10`); sum of digits; reverse a number; palindrome number.
- [CORE] Armstrong number; perfect number; strong number.
- [CORE] Print all divisors (O(n) then O(√n)); check prime (O(√n)); primes up to n (naive).
- [CORE] GCD (brute force → Euclid's algorithm), LCM via GCD.
- [CORE] Factorial, Fibonacci (iterative), power (loop).
- [STD] Base conversion: decimal ↔ binary ↔ octal ↔ hex by hand and in code.
- [STD] Sum of series: AP/GP formulas vs loops.

## Z8. Functions (extend `functions`, `scope-and-mutation`)
- [CORE] Defining/calling; parameters vs arguments; return values; void functions.
- [CORE] Scope: local vs global; shadowing.
- [CORE] Pass by value vs pass by reference (C++ `&`), Java "pass reference by value", Python object references — what happens when a function modifies a list.
- [CORE] Default/keyword arguments (Python), function overloading (C++/Java).
- [CORE] Decomposing a problem into functions; pure functions; testing a function with examples.
- [STD] The call stack (visualised) — prerequisite for recursion.
- [STD] Lambdas / anonymous functions; passing functions as arguments (needed for custom sort).

## Z9. Arrays / lists (extend `lists`)
- [CORE] Declaring, indexing, 0-based indexing, length, out-of-bounds errors.
- [CORE] Traversal patterns: sum, max/min, second largest, count, find index, reverse in place, check sorted, linear search.
- [CORE] Insert/delete at position (and why it's O(n)); dynamic arrays (`vector`, `ArrayList`, Python list) vs fixed arrays.
- [CORE] Copying vs aliasing arrays.
- [CORE] Classic problems: left/right rotate by 1 and by k, move zeros to end, remove duplicates from sorted array, frequency of each element (nested loops then map), merge two sorted arrays, union & intersection, missing number, find max consecutive ones.
- [STD] Slicing (Python), `subList`, iterators.
- [STD] List comprehensions (Python), enhanced for (Java), range-for (C++).

## Z10. Strings (extend `strings`)
- [CORE] Strings as character arrays; indexing; immutability (Python/Java) vs mutability (C++).
- [CORE] Traversal; counting vowels/characters; changing case; reversing; palindrome check; character frequency.
- [CORE] Built-ins: split, join, strip/trim, find/indexOf, replace, substring/slicing, startswith, compare.
- [CORE] String building efficiently (`join`, `StringBuilder`) — why `+=` in a loop is slow in Java/Python.
- [CORE] Classic problems: count words, reverse words in a sentence, anagram check (sort / frequency), remove spaces/duplicates, first non-repeating character, toggle case, largest odd number in string, longest common prefix, rotate string check, isomorphic strings.
- [STD] String ↔ number conversion; parsing.

## Z11. 2D arrays / grids (extend `grids`)
- [CORE] Declaring/reading a matrix; row-major traversal; column traversal.
- [CORE] Row sums, column sums, diagonal sums, transpose, matrix addition & multiplication.
- [CORE] Rotate matrix 90° (transpose + reverse), spiral traversal, searching in matrix.
- [CORE] Neighbour checking with direction arrays (`dr, dc`) and bounds checks — prerequisite for grid BFS later.
- [STD] Jagged arrays; boundary traversal; snake/zigzag print.

## Z12. Maps and sets (extend `maps`)
- [CORE] Key–value lookup; insert/update/delete; iterate; `get` with default.
- [CORE] Sets: membership, removing duplicates, union/intersection.
- [CORE] Frequency counting with a map (the single most-used beginner technique).
- [CORE] Hashing intuition: why lookups are "O(1) average"; hashed vs ordered map (`unordered_map` vs `map`, `HashMap` vs `TreeMap`).
- [STD] Tuples/pairs as keys; grouping (e.g., group words by first letter).

## Z13. Recursion fundamentals (extend `recursion`)
- [CORE] Base case + recursive case; the call stack; tracing with a recursion tree.
- [CORE] Head vs tail recursion; parameterised vs functional recursion.
- [CORE] Classic: print 1..n and n..1, sum of first n, factorial, Fibonacci (and why naive is exponential), reverse an array, palindrome check, power(x, n), sum of digits.
- [STD] Stack overflow and recursion limits (`sys.setrecursionlimit`).

## Z14. Searching and sorting basics [NEW]
- [CORE] Linear search; binary search on a sorted array (iterative), the "halve each step" idea.
- [CORE] Selection sort, bubble sort (with early exit), insertion sort — implement and dry-run each.
- [CORE] Using built-in sort; sorting in reverse; sorting by a key/comparator (e.g., sort students by marks then name).
- [STD] Stability of a sort.
- [STD] Counting sort for small ranges.

## Z15. Number systems and bits basics [NEW]
- [CORE] Binary representation; converting; two's complement for negatives (high level).
- [CORE] Bitwise operators with truth tables; checking odd/even via `& 1`; `<<` as ×2, `>>` as ÷2.
- [STD] Check/set/clear/toggle i-th bit; count set bits; check power of two.

## Z16. Memory model and references [SPLIT from `scope-and-mutation`]
- [CORE] Stack vs heap (conceptual); values vs references; what `a = b` does for lists/objects in each language.
- [CORE] Shallow vs deep copy.
- [STD] C++ pointers & references basics: `*`, `&`, `nullptr`, arrays decaying to pointers; `new`/`delete` vs smart pointers (light).
- [STD] Java/Python garbage collection (intuition).

## Z17. Object-oriented programming (extend `classes-and-objects`)
- [CORE] Class vs object; attributes and methods; constructors; `self`/`this`.
- [CORE] Encapsulation: private fields, getters/setters.
- [CORE] Inheritance; method overriding; `super`.
- [CORE] Polymorphism: overloading vs overriding; dynamic dispatch.
- [CORE] Abstraction: abstract classes and interfaces.
- [STD] Static vs instance members; `toString`/`__str__`; equality (`equals`/`__eq__`) and hashing objects.
- [STD] Composition vs inheritance; small OOP design exercise (Bank account, Library, Parking lot lite).

## Z18. Errors, exceptions and defensive code [NEW]
- [CORE] try/except/catch/finally; raising/throwing; common exceptions (index, key, null pointer, division by zero, value/type errors).
- [CORE] Validating input; assertions.
- [STD] Custom exceptions.

## Z19. Files, modules and libraries [NEW]
- [CORE] Reading/writing text files; reading line by line; CSV basics.
- [CORE] Importing modules/packages; using the standard library (`math`, `random`, `collections`; `<algorithm>`, `<cmath>`; `java.util`).
- [STD] Writing your own module; `if __name__ == "__main__"`.

## Z20. Standard library for problem solving [NEW] — language track specific
- **Python:** list/dict/set/tuple methods, `collections` (Counter, defaultdict, deque), `heapq`, `bisect`, `itertools` (permutations, combinations, product), `sorted` with `key`, string methods.
- **C++ STL:** `vector`, `pair`, `string`, `map`/`unordered_map`, `set`/`multiset`, `stack`, `queue`, `deque`, `priority_queue`, iterators, `sort` with comparator/lambda, `lower_bound`/`upper_bound`, `accumulate`, `reverse`, `next_permutation`, `__builtin_popcount`.
- **Java:** `ArrayList`, `HashMap`, `HashSet`, `TreeMap`, `TreeSet`, `ArrayDeque`, `PriorityQueue`, `Collections`, `Arrays.sort` with `Comparator`, `StringBuilder`, wrapper classes and autoboxing pitfalls (`Integer ==`).

## Z21. Complexity intuition [NEW] (light version of DSA `complexity`)
- [CORE] Counting operations; why nested loops are n²; "10⁸ operations ≈ 1 second" rule.
- [CORE] Big-O of the beginner algorithms learnt so far; O(√n) prime check vs O(n).

## Z22. Problem-solving method and debugging (extend `problem-solving`, `debugging`)
- [CORE] Read → restate → examples → edge cases → brute force → code → test → improve.
- [CORE] Edge-case checklist: empty input, single element, all equal, negatives, zero, maximum constraints, overflow.
- [CORE] Debugging: print-debugging, reading stack traces, rubber-duck, using a debugger (breakpoints, step over/into, watch).
- [CORE] Dry-running with a trace table.
- [STD] Writing small test cases and a brute-force checker.

## Z23. Mini projects (capstones) [NEW]
Each integrates multiple concepts: number guessing game, tic-tac-toe (grids + functions), to-do CLI with file save (lists + files), student marks report (maps + sorting + OOP), bank account system (OOP + exceptions), text statistics tool (strings + maps + files), simple quiz app.

### Track 1 exit test (unseen-problem bar)
Solve without hints: 10 Codeforces 800-rated or LeetCode Easy implementation problems spanning loops, strings, arrays, maps and simple math; build one mini project from a spec.

---

# TRACK 2 — DSA for Interviews

**Goal.** A learner can walk into a product-company interview (SDE-1/intern; Samsung, Amazon, Microsoft, Google, Flipkart level) and solve unseen LeetCode Medium problems in 30–40 minutes, a fair share of Hards, and explain complexity and trade-offs.

**Current state:** 23 concepts across 7 modules. Biggest gaps: DP is 2 lessons (should be ~12), trees are 2 lessons (should be ~6), graphs are 4 lessons (should be ~8), no strings-algorithms concept, no recursion-patterns concept separate from backtracking, no matrix concept, no design-a-data-structure concept, linked lists and stacks are single lessons with many families inside, binary search lacks its variant families.

## D1. Complexity analysis (extend `complexity`)
- [CORE] Big-O, Big-Ω, Big-Θ; best/average/worst case.
- [CORE] Analysing loops: nested, dependent (`j < i`), halving (`i *= 2` → log n), √n loops.
- [CORE] Recursion complexity: recursion tree; recurrence relations; Master theorem (statement + 3 cases); T(n)=2T(n/2)+n, T(n)=T(n-1)+1, T(n)=2T(n-1)+1.
- [CORE] Space complexity incl. recursion stack and auxiliary space.
- [CORE] Amortised analysis: dynamic array push, monotonic stack (each element pushed/popped once).
- [CORE] Reading constraints → allowed complexity table (n ≤ 10 → n!, 20 → 2ⁿ, 500 → n³, 5000 → n², 10⁵–10⁶ → n log n, 10⁹+ → log n or O(1)).
- [STD] Harmonic series bound (n/1 + n/2 + … = n log n).

## D2. Arrays (extend `arrays-hashing`)
Pattern families:
- [CORE] **In-place manipulation:** remove duplicates from sorted array, move zeros, remove element, rotate array by k (reversal algorithm), merge sorted arrays from the back.
- [CORE] **Kadane's algorithm:** max subarray sum, print the subarray, max circular subarray, max product subarray (track min and max).
- [CORE] **Dutch national flag / 3-way partition:** sort 0s 1s 2s, partition around pivot.
- [CORE] **Majority element:** Boyer–Moore voting (> n/2), extended Boyer–Moore (> n/3).
- [CORE] **Next permutation** (find pivot, swap, reverse suffix).
- [CORE] **Leaders / suffix max** pattern; **best time to buy & sell stock I** (prefix min).
- [CORE] **Rearrangement:** rearrange by sign alternately, set matrix zeroes, rotate image, spiral matrix.
- [CORE] **Index-as-hash / cyclic sort:** missing number, find duplicate, find all missing/duplicates (values 1..n), first missing positive.
- [STD] Missing and repeating number (math and XOR approaches), count inversions (→ merge sort, D8), reverse pairs.
- [STD] Pascal's triangle (element, row, full triangle), longest consecutive sequence (set).
- [STD] Majority/moore variants, product of array except self (prefix × suffix).

## D3. Hashing (split from `arrays-hashing`) [SPLIT]
- [CORE] Frequency maps; two-sum (map of complements); group anagrams (sorted key / count key).
- [CORE] **Prefix sum + hashmap:** count subarrays with sum K, longest subarray with sum K (positive vs with negatives — different algorithms), subarrays with XOR K, longest subarray with equal 0s and 1s, subarray sum divisible by K.
- [CORE] Set-based: longest consecutive sequence, contains duplicate within k distance.
- [STD] Hash function intuition, collisions, load factor; why unordered_map can be hacked (CP link).
- [STD] 4-sum count (pair sums in a map), isomorphic strings, word pattern.

## D4. Two pointers (extend `two-pointers`)
- [CORE] **Opposite ends:** two-sum in sorted array, valid palindrome, container with most water, trapping rain water (two-pointer version), squares of sorted array.
- [CORE] **k-Sum reduction:** 3-sum (sort + two pointers + skip duplicates), 3-sum closest, 4-sum.
- [CORE] **Same direction (read/write pointers):** remove duplicates, partition arrays.
- [CORE] **Fast/slow pointers (Floyd):** linked-list cycle detection & start, middle of list, happy number, find duplicate number (array as linked list).
- [STD] Merge-like two pointers over two arrays: intersection of sorted arrays, merge intervals of two lists.
- [STD] Boats to save people, sort colors (3 pointers).

## D5. Sliding window (extend `sliding-window`)
- [CORE] **Fixed-size window:** max sum of size k, averages, first negative in every window (queue), count anagram occurrences, max of every window (→ monotonic deque, D11).
- [CORE] **Variable-size, "longest valid" (shrink while invalid):** longest substring without repeating characters, longest substring with at most K distinct, max consecutive ones III (flip at most k zeros), longest repeating character replacement, fruit into baskets.
- [CORE] **Variable-size, "shortest valid" (shrink while valid):** minimum size subarray sum, minimum window substring.
- [CORE] **Counting subarrays with "exactly K" = atMost(K) − atMost(K−1):** subarrays with K distinct integers, binary subarrays with sum, count nice subarrays (k odd numbers).
- [STD] Number of substrings containing all three characters; max points from cards (window on circular ends).
- [STD] When sliding window fails (negative numbers) → prefix sum + hashmap (contrast pair with D3).

## D6. Prefix sums and difference arrays (extend `prefix-sums`)
- [CORE] 1D prefix sum; range sum queries; prefix XOR.
- [CORE] 2D prefix sums (inclusion–exclusion); range sum query 2D; count submatrices with sum target.
- [CORE] Difference array for range updates (car pooling, corporate flight bookings).
- [STD] Prefix + suffix arrays (product except self, trapping rain water prefix-max version).
- [STD] Equilibrium index / pivot index.

## D7. Binary search (extend `binary-search`) — currently one lesson; split into 3 concepts
**D7a. Binary search on sorted arrays**
- [CORE] Iterative template and loop invariant; overflow-safe mid.
- [CORE] Lower bound, upper bound, search insert position, floor/ceil, first & last occurrence, count occurrences.
- [CORE] Rotated sorted array: search (distinct), search (with duplicates), find minimum, count rotations.
- [CORE] Single element in sorted array (pairs index parity), find peak element.
- [STD] Square root / n-th root by binary search.

**D7b. Binary search on answer ("minimise the maximum / maximise the minimum")**
- [CORE] Recognition: monotonic predicate over the answer space.
- [CORE] Koko eating bananas, minimum days to make M bouquets, smallest divisor given threshold, capacity to ship packages within D days, kth missing positive number.
- [CORE] Aggressive cows (maximise min distance), book allocation / split array largest sum / painter's partition (minimise max sum).
- [STD] Minimise max distance to gas station (real-valued binary search), median of two sorted arrays (partition binary search), kth element of two sorted arrays.

**D7c. Binary search in 2D**
- [CORE] Search in row & column sorted matrix (staircase), search in fully sorted matrix (treat as 1D), row with max 1s.
- [STD] Peak element in 2D, median of row-wise sorted matrix.

## D8. Sorting algorithms (extend `sorting`)
- [CORE] Merge sort (recursive, merging), quick sort (Lomuto & Hoare partition, randomised pivot, worst case).
- [CORE] Comparison-based lower bound (n log n) — intuition.
- [CORE] Counting sort, bucket sort idea, radix sort (overview).
- [CORE] Stability; custom comparators (sort by multiple keys, largest number formed from array).
- [CORE] **Merge-sort-based counting:** count inversions, reverse pairs, count of smaller numbers after self.
- [STD] Quickselect (kth largest in average O(n)); heap sort (after D13).
- [STD] Sort colors, wiggle sort, sort by frequency.

## D9. Recursion patterns [NEW concept; currently mixed into `backtracking`]
- [CORE] Thinking recursively: trust the function, define what f(n) returns, IBH (induction–base–hypothesis, Aditya Verma method).
- [CORE] **Input–output method / pick–not-pick:** generate all subsequences, subsets, print subsequences with sum K, count subsequences with sum K, check if any exists (return early).
- [CORE] Recursion on strings: reverse, palindrome, generate all binary strings without consecutive 1s, generate valid parentheses, permutations of a string, letter case permutation.
- [CORE] Recursion on stacks/arrays: sort a stack using recursion, reverse a stack using recursion, delete middle of stack.
- [CORE] Kth symbol in grammar, Tower of Hanoi, Josephus problem.
- [CORE] Fast exponentiation (pow(x, n) in O(log n)), count good numbers.
- [STD] Recursion tree to complexity; converting recursion to iteration with an explicit stack.

## D10. Backtracking (extend `backtracking`)
- [CORE] Template: choose → explore → un-choose; pruning.
- [CORE] **Subsets family:** subsets I, subsets II (with duplicates: sort + skip), subset sums.
- [CORE] **Combinations family:** combination sum I (reuse allowed), II (each once, duplicates), III (k numbers summing to n), combinations nCk.
- [CORE] **Permutations family:** permutations I (swap method & used-array method), permutations II (duplicates), next permutation link.
- [CORE] **Partitioning:** palindrome partitioning, word break II, restore IP addresses.
- [CORE] **Grid/board search:** word search, rat in a maze (all paths), N-Queens (with column/diagonal sets), Sudoku solver, M-coloring.
- [STD] Letter combinations of a phone number, expression add operators, matchsticks to square / partition to K equal subsets.

## D11. Stacks and queues (extend `stacks`) — split into 2 concepts
**D11a. Stack & queue fundamentals**
- [CORE] Implement stack/queue using arrays & linked list; stack using queues and queue using stacks; circular queue; deque.
- [CORE] Balanced parentheses; min stack (O(1) getMin, both approaches).
- [CORE] Expression conversion & evaluation: infix → postfix/prefix, evaluate postfix (RPN), basic calculator I/II.
- [STD] Simplify path, decode string, asteroid collision, remove k digits (→ monotonic), backspace string compare.

**D11b. Monotonic stack & monotonic deque**
- [CORE] Next greater element I/II (circular), next smaller, previous greater/smaller (the 4 variants as one template).
- [CORE] Stock span, daily temperatures, celebrity problem.
- [CORE] Largest rectangle in histogram, maximal rectangle in binary matrix (histogram per row).
- [CORE] Sum of subarray minimums / ranges (contribution technique with PSE/NSE).
- [CORE] Trapping rain water (stack version).
- [CORE] Sliding window maximum (monotonic deque).
- [STD] Remove K digits, 132 pattern, online stock span.

## D12. Linked lists (extend `linked-lists`)
- [CORE] Singly/doubly/circular: create, traverse, insert, delete at head/tail/position/value.
- [CORE] **Reversal family:** reverse list (iterative & recursive), reverse between positions, reverse in k-groups, palindrome linked list (reverse second half).
- [CORE] **Fast–slow family:** middle node, detect cycle, cycle start & length, remove nth node from end, delete middle.
- [CORE] **Merge family:** merge two sorted lists, sort list (merge sort on LL), merge k sorted lists (heap), add two numbers, intersection of two lists.
- [CORE] **Rearrange family:** odd–even list, sort 0s 1s 2s list, rotate list, reorder list, partition list.
- [CORE] Copy list with random pointer; flatten a multilevel / "child-down" linked list.
- [STD] DLL: delete all occurrences of a key, find pairs with given sum, remove duplicates from sorted DLL.
- [STD] LRU cache (hashmap + DLL) — taught in D24.

## D13. Heaps / priority queues (extend `heaps`)
- [CORE] Binary heap implementation: heapify up/down, build heap O(n), heap sort.
- [CORE] **Top-K family:** kth largest/smallest, top k frequent elements, k closest points, sort k-sorted array, kth largest in stream.
- [CORE] **Two heaps:** median of data stream, sliding window median.
- [CORE] **K-way merge:** merge k sorted lists/arrays, smallest range covering k lists, kth smallest in sorted matrix.
- [CORE] **Greedy with heap / scheduling:** task scheduler, meeting rooms II (min rooms), IPO / maximise capital, reorganise string, connect ropes minimum cost, hands of straights.
- [STD] Maximum sum combinations, design Twitter.

## D14. Greedy (extend `greedy`)
- [CORE] When greedy works: exchange argument & "stays ahead" proof sketch; counter-example testing.
- [CORE] **Interval scheduling:** N meetings in one room / activity selection (sort by end), non-overlapping intervals (min removals), min arrows to burst balloons.
- [CORE] **Sorting-based:** assign cookies, minimum platforms, job sequencing with deadlines, fractional knapsack.
- [CORE] **Reach/jump:** jump game I (can reach), jump game II (min jumps, BFS-levels idea), gas station.
- [CORE] **Local balance:** candy, valid parenthesis string (range of open counts), lemonade change.
- [STD] Shortest job first, page faults (LRU) simulation, Huffman coding (concept), minimum coins (when greedy works vs not — contrast with DP coin change).

## D15. Intervals (extend `intervals`)
- [CORE] Merge intervals, insert interval, interval intersection (two lists), meeting rooms I/II, non-overlapping intervals, employee free time.
- [STD] Line sweep with events (+1/−1) — car pooling, my calendar I/II.

## D16. Binary trees (extend `binary-trees`) — split into 3 concepts
**D16a. Traversals and representation**
- [CORE] Tree terminology; array vs node representation.
- [CORE] DFS: preorder, inorder, postorder — recursive and iterative (one stack, two stacks), all three in one pass; Morris traversal (O(1) space) [STD].
- [CORE] BFS: level order, level order line by line, zigzag, reverse level order.
- [CORE] Height/max depth, min depth, count nodes, size.

**D16b. Tree problem patterns**
- [CORE] **"Return info from children" (post-order DP on tree):** diameter, balanced check, max path sum, identical trees, symmetric tree, subtree of another tree.
- [CORE] **Views & coordinates:** left/right view, top/bottom view (vertical order with column index + BFS), vertical order traversal, boundary traversal.
- [CORE] **Paths:** root-to-leaf paths, path sum I/II/III (prefix sum on tree), root to node path.
- [CORE] **LCA:** lowest common ancestor in binary tree.
- [CORE] **Distance problems:** all nodes at distance K (parent map + BFS), minimum time to burn tree.
- [CORE] Maximum width of binary tree (index numbering), children sum property, count complete tree nodes in < O(n).
- [STD] Flatten tree to linked list, invert tree, cousins.

**D16c. Construction & serialisation**
- [CORE] Build tree from inorder + preorder, inorder + postorder; why preorder + postorder isn't unique.
- [CORE] Serialize/deserialize binary tree.
- [STD] Construct BST from preorder; tree from level order.

## D17. Binary search trees (extend `bst`)
- [CORE] Search, insert, delete (3 cases), min/max, ceil/floor in BST.
- [CORE] Validate BST (range method), kth smallest/largest (inorder), LCA in BST.
- [CORE] Inorder successor/predecessor, BST iterator (stack), two-sum in BST, recover BST (two swapped nodes).
- [CORE] Construct BST from preorder; sorted array → balanced BST; largest BST in binary tree (return min/max/size).
- [STD] Self-balancing trees (AVL/Red-Black) — concept only; why `TreeMap`/`std::set` are O(log n).

## D18. Graphs — fundamentals and traversal (extend `graph-traversal`) — split into 4 concepts
**D18a. Representation & traversal**
- [CORE] Directed/undirected, weighted, adjacency list vs matrix vs edge list; implicit graphs (grids, word ladders, state spaces).
- [CORE] BFS and DFS (recursive & iterative); connected components; number of provinces.
- [CORE] **Grid graphs:** number of islands, flood fill, max area of island, surrounded regions / boundary DFS, number of enclaves, distinct islands (shape hashing).
- [CORE] **Multi-source BFS:** rotting oranges, 0/1 matrix (distance to nearest 0), walls and gates.
- [CORE] Bipartite check (BFS & DFS colouring).
- [CORE] Cycle detection in undirected (BFS/DFS with parent) and directed (DFS with path-visited) graphs.
- [STD] Clone graph, word ladder I (BFS on implicit graph), word ladder II [ADV].

**D18b. Topological sort** (extend `topological-sort`)
- [CORE] DFS-based and Kahn's algorithm (BFS indegree); cycle detection via Kahn.
- [CORE] Course schedule I/II, find eventual safe states, alien dictionary.
- [STD] Longest path in DAG, parallel courses / minimum semesters.

**D18c. Shortest paths** (extend `shortest-paths`)
- [CORE] Unweighted: BFS. Unit-weight in DAG: topo order relaxation.
- [CORE] Dijkstra (priority queue, why it fails with negative edges), printing the path.
- [CORE] Variants: path with minimum effort, cheapest flights within K stops (BFS/Bellman-style on stops), network delay time, number of ways to arrive at destination (Dijkstra + count), minimum multiplications to reach end, shortest path in binary matrix.
- [CORE] Bellman–Ford (negative edges, negative cycle detection).
- [CORE] Floyd–Warshall (all pairs), city with smallest number of neighbours within threshold.
- [STD] 0-1 BFS.

**D18d. MST, DSU and connectivity** (extend `union-find`; add MST [NEW to DSA])
- [CORE] DSU with path compression + union by rank/size; connected components; redundant connection.
- [CORE] DSU applications: number of operations to make network connected, accounts merge, most stones removed, number of islands II (online), making a large island.
- [CORE] Minimum spanning tree: Prim's and Kruskal's; min cost to connect all points.
- [STD] Bridges (Tarjan low-link), articulation points, Kosaraju SCC — interview-level awareness.

## D19. Dynamic programming — the full family breakdown (currently `dp-1d` + `dp-2d`; target ~12 concepts)

**Teaching method for every DP concept:** recursion → memoization → tabulation → space optimisation. Show all four for the anchor problem. Every family states: *state meaning in words*, *transition*, *base cases*, *answer cell*, *loop order*.

**D19.0 DP introduction** [CORE]
- Overlapping subproblems + optimal substructure; Fibonacci 4 ways; how to identify DP (choices + optimise/count).
- Top-down vs bottom-up trade-offs; reconstructing the answer (printing the path/choice).

**D19.1 1D DP** [CORE]
- Climbing stairs (and with k steps), frog jump (min energy, k jumps), house robber I/II (circular), min cost climbing stairs, decode ways, word break (string-split DP), perfect squares / min squares.

**D19.2 DP on grids / 2D** [CORE]
- Unique paths I/II (obstacles), minimum path sum, triangle (variable end), minimum/maximum falling path sum (variable start & end).
- **3D DP on grids:** cherry pickup II / "Ninja and his friends" (two walkers at once), cherry pickup I.
- [STD] Dungeon game (reverse direction DP), ninja's training (day × last activity).

**D19.3 0/1 knapsack family ("DP on subsequences/subsets")** [CORE]
Each item: take or skip once.
- Anchor: 0/1 knapsack.
- Subset sum (exists?), equal-sum partition, count subsets with sum K, partition into two subsets with minimum absolute difference, count partitions with given difference, target sum (assign +/−), last stone weight II.
- Ones and zeroes (2-dimensional capacity).
- Teaching points: why capacity loop goes backwards in 1D optimisation; handling zeros in count problems.

**D19.4 Unbounded knapsack family** [CORE]
Items reusable.
- Anchor: unbounded knapsack.
- Rod cutting, coin change I (min coins), coin change II (number of combinations), combination sum IV (number of permutations — contrast: loop order swaps combinations ↔ permutations), maximum ribbon cut.

**D19.5 DP on strings — LCS family** [CORE]
- Anchor: longest common subsequence (+ print the LCS).
- Longest common substring (reset on mismatch), shortest common supersequence (length + print), min insertions/deletions to convert A → B.
- Longest palindromic subsequence (= LCS(s, reverse(s))), min insertions to make string palindrome, min deletions to make palindrome.
- Longest repeating subsequence, sequence pattern matching (is A a subsequence of B).

**D19.6 DP on strings — edit/matching family** [CORE]
- Edit distance (insert/delete/replace), distinct subsequences (count occurrences of T in S), wildcard matching (`?`, `*`), regular expression matching (`.`, `*`) [STD], interleaving string.
- Palindromic substrings count / longest palindromic substring (expand-around-centre vs DP).

**D19.7 DP on stocks** [CORE]
- Buy & sell stock I (one transaction), II (unlimited), III (at most 2), IV (at most k), with cooldown, with transaction fee — one state machine `dp[i][canBuy][transactionsLeft]` explaining all six.

**D19.8 Longest increasing subsequence family** [CORE]
- LIS O(n²), print LIS, LIS O(n log n) with patience sorting / binary search (and why the tails array isn't the LIS itself).
- Largest divisible subset, longest string chain, longest bitonic subsequence, number of LIS, Russian doll envelopes (sort trick), maximum sum increasing subsequence.

**D19.9 Partition DP / Matrix Chain Multiplication (MCM) family** [CORE]
Try every split point k between i and j.
- Anchor: matrix chain multiplication.
- Minimum cost to cut a stick, burst balloons (choose last balloon), evaluate boolean expression to true (count ways), palindrome partitioning II (min cuts — front-partition 1D optimisation), partition array for maximum sum, scramble string [STD], egg dropping (and its optimised binary-search/“moves” version) [STD].

**D19.10 DP on squares / rectangles** [CORE]
- Maximal square, count square submatrices with all ones, maximal rectangle (histogram reuse from D11b).

**D19.11 DP on trees** [CORE]
- Diameter / max path sum as DP, house robber III (rob/skip per node), binary tree cameras, maximum sum of non-adjacent nodes.
- [STD] Rerooting idea (sum of distances in tree) — bridge to CP.

**D19.12 Other interview DP patterns** [STD]
- **Bitmask DP:** TSP on small n, minimum cost to visit all nodes, partition to K equal subsets with memo on mask, shortest path visiting all nodes.
- **Game DP (minimax):** predict the winner, stone game, optimal strategy for a coin game.
- **DP on intervals vs DP with states:** paint house (k colours), number of dice rolls with target sum, count vowels permutation (state machines).
- **DP + binary search / DP + hashing:** longest arithmetic subsequence, longest Fibonacci-like subsequence.
- **Digit DP (intro):** count numbers ≤ N with a property — awareness level for interviews (deep in CP).

## D20. Tries (extend `tries`)
- [CORE] Implement trie (insert, search, startsWith); count words equal to / starting with (with counts per node), erase.
- [CORE] Longest word with all prefixes, number of distinct substrings (trie of suffixes), word search II (trie + backtracking), replace words, design add & search words (wildcard).
- [CORE] **Bitwise trie:** maximum XOR of two numbers, maximum XOR with an element from array (offline queries sorted).

## D21. Bit manipulation (extend `bit-manipulation`)
- [CORE] Check/set/clear/toggle bit; remove last set bit (`n & (n-1)`), isolate lowest set bit (`n & -n`), count set bits (Brian Kernighan), power of 2/4.
- [CORE] XOR tricks: single number I (others twice), single number II (others thrice — bit counting), single number III (two singles — split by a set bit), missing number, swap without temp, XOR of 1..n in O(1), XOR of range L..R.
- [CORE] Subsets with bitmask enumeration; divide two integers with bits; minimum bit flips to convert.
- [STD] Gray code, reverse bits, sum of two integers without `+`.

## D22. Math for interviews [NEW]
- [CORE] GCD/LCM, Sieve of Eratosthenes, prime factorisation (√n and with SPF), count primes.
- [CORE] Modular arithmetic basics (`% (1e9+7)`), modular exponentiation.
- [CORE] nCr (Pascal / multiplicative), Pascal's triangle, Catalan numbers (count BSTs / valid parentheses).
- [STD] Reservoir sampling, random pick with weight (prefix + binary search), excel sheet column title/number, integer to Roman / Roman to integer, pow(x, n), fraction to recurring decimal, rectangle overlap, valid square.

## D23. String algorithms [NEW]
- [CORE] String manipulation patterns: reverse words, longest common prefix, string compression, valid anagram, check rotations.
- [CORE] Pattern matching: naive → **Rabin–Karp** (rolling hash), **KMP / LPS array**, **Z-function**; repeated string match, shortest palindrome (KMP on s + '#' + rev(s)), find the index of first occurrence.
- [STD] Manacher's algorithm (longest palindromic substring O(n)) — awareness.
- [STD] Minimum characters to add at front to make palindrome, count & say, string to integer (atoi) edge cases.

## D24. Design data structures [NEW]
- [CORE] LRU cache (hashmap + DLL), LFU cache (freq → DLL map), min stack, implement queue with stacks, design hashmap/hashset (chaining), insert-delete-getRandom O(1), time-based key-value store (binary search), design browser history, design Twitter.
- [STD] Snapshot array, all O(1) data structure, iterator design (peeking iterator, flatten nested list iterator).

## D25. Advanced data structures (interview awareness) [NEW][STD]
- Segment tree (range sum/min with point update), Fenwick tree — for "range sum query mutable", "count of smaller numbers after self".
- Ordered set usage (`TreeMap`, `SortedList`, `std::set`): contains duplicate III, my calendar, sliding window median.
- Sparse table concept (RMQ).

## D26. Interview execution skills [NEW]
- [CORE] UMPIRE / think-aloud framework: clarify → examples → brute force → optimise → code → test → complexity.
- [CORE] Writing clean interview code; naming; handling edge cases out loud; dry-running your own code.
- [CORE] Pattern recognition drill: given only a problem statement, name the pattern family (uses the contrast pairs).
- [STD] Behavioural basics (STAR) and low-level design primers (SOLID, design a parking lot / elevator) — optional module.

### Track 2 exit test (unseen-problem bar)
Timed mock: 2 unseen LeetCode Mediums in 60 minutes with explanation; 1 Hard from DP or graphs in 45 minutes; pattern-identification quiz of 20 statements with ≥ 85% accuracy.

---

# TRACK 3 — Competitive Programming

**Goal.** A learner can compete on Codeforces/CodeChef/AtCoder/LeetCode contests and climb rating bands: Newbie → Pupil (1200) → Specialist (1400) → Expert (1600) → Candidate Master (1900), and handle ICPC regional / Samsung-style coding rounds.

**Structure.** Organised by rating level (mirrors USACO Guide Bronze → Platinum), because CP difficulty comes from *combining* techniques, not just knowing them. Each level assumes the previous one and DSA-track equivalents (`dsa:*` prerequisites).

**Current state:** 20 concepts. Big gaps: no ad-hoc/constructive/observation training, number theory and combinatorics are thin, DP is 2 lessons (`dp-classics`, `bitmask-dp`), no digit DP/SOS/DP optimisations, no sparse table/sqrt decomposition/Mo's, segment tree has no lazy/walk/merge variants, no SCC/2-SAT/bridges/flows, strings missing Z/suffix array/Aho-Corasick, no game theory, no geometry, no matrix exponentiation, no interactive problems, no contest-strategy/stress-testing lesson.

## Level 0 — Setup and contest basics (≤ 1000)

### C0.1 Contest environment (extend `fast-io`)
- [CORE] C++ for CP: template, `#define`s (sparingly), `using ll = long long`, fast I/O, `endl` vs `'\n'`.
- [CORE] Reading multi-test input; resetting globals between tests (classic WA cause).
- [CORE] Time/memory limits → operation budgets; sum of n over test cases constraints.
- [CORE] Overflow: where to use `long long`, `1LL *`, `__int128` [STD].
- [CORE] Verdicts: WA, TLE, MLE, RE — systematic debugging per verdict.
- [STD] Python/Java in CP: `sys.stdin.buffer`, PyPy, `BufferedReader`/`StreamTokenizer`; when to switch to C++.

### C0.2 Stress testing and debugging [NEW]
- [CORE] Brute force + random generator + checker script; finding the minimal failing case.
- [CORE] Debug macros, `assert`, compiler flags (`-fsanitize=address,undefined`, `-D_GLIBCXX_DEBUG`).
- [STD] Upsolving routine; reading editorials effectively.

### C0.3 Implementation and simulation (extend `simulation`)
- [CORE] Translating statements precisely; simulation with careful indexing; grid simulation; string processing.
- [CORE] Casework problems: enumerating all cases cleanly.

### C0.4 Ad hoc and observations [NEW] — the biggest gap for 800–1400
- [CORE] Looking at small cases by hand; finding invariants (parity, sum mod k, sortedness).
- [CORE] Answer-bounds reasoning: "the answer is always ≤ 2", "is it always possible?".
- [CORE] Parity arguments, pigeonhole principle, extremal principle.
- [CORE] Working backwards; reformulating the problem.

### C0.5 Constructive algorithms [NEW]
- [CORE] Building arrays/permutations/strings meeting conditions; "output any valid answer".
- [CORE] Standard tricks: alternating patterns, placing extremes first, using 1..n permutations, power-of-two constructions, building from a small base case and extending.
- [CORE] Proving construction works; checking with a validator.

### C0.6 Basic math for CP (extend `number-theory`)
- [CORE] Divisibility, GCD/LCM properties (gcd(a, b) = gcd(a, b − a)), floor/ceil division with negatives.
- [CORE] Sum formulas, arithmetic progressions; counting with simple formulas.
- [CORE] Primes via √n, divisors via √n; even/odd reasoning.

### C0.7 Sorting & STL mastery (bridges `dsa:sorting`)
- [CORE] `sort` with comparators/lambdas, `pair`/`tuple` comparison, `set`/`multiset` (erase one occurrence!), `map`, `lower_bound` on set vs `std::lower_bound` on set (complexity trap), `priority_queue` with custom comparator, `deque`, `bitset`.
- [CORE] Coordinate compression.
- [STD] Policy-based data structures (`ordered_set`: order_of_key, find_by_order).

## Level 1 — Pupil to Specialist (1000–1500)

### C1.1 Complete search (extend `complete-search`)
- [CORE] Iterating all subsets via bitmask, all permutations (`next_permutation`), nested-loop brute force within limits.
- [CORE] Recursive search with pruning; generating candidates smartly (iterate over the answer, iterate over the smaller dimension).
- [STD] **Meet in the middle** [NEW]: subset sums with n = 40, 4-sum.

### C1.2 Prefix sums, difference arrays (extend `prefix-difference`)
- [CORE] 1D/2D prefix sums, difference arrays (1D and 2D), prefix XOR, prefix counts per character.
- [CORE] Prefix sums of prefix sums (adding arithmetic progressions on ranges) [STD].
- [CORE] Count subarrays with property using prefix + map; "number of pairs" problems via prefix frequencies.

### C1.3 Two pointers & sliding window for CP (bridges `dsa:two-pointers`, `dsa:sliding-window`)
- [CORE] Two pointers over monotone conditions; counting segments with good property; segment with small set (Codeforces EDU two-pointers module).
- [CORE] Two pointers over two sorted arrays; number of pairs with sum ≤ K.

### C1.4 Binary search (extend `binary-search-answer`)
- [CORE] Binary search on integer answer; on real answer (fixed iterations); on "k-th smallest" via counting.
- [CORE] Binary search + greedy check; binary search + prefix sums check; binary search on average/median (transform a[i] − x).
- [STD] Ternary search on unimodal functions; parallel binary search [ADV].

### C1.5 Greedy for CP (extend `greedy-cp`)
- [CORE] Exchange argument formally; sorting by a custom key (e.g. a+b, a−b, a/b via cross multiplication).
- [CORE] Greedy with priority queue (regret greedy: take now, undo later).
- [CORE] Interval greedy, deadlines scheduling, "minimum operations" greedy.
- [STD] Greedy on bits (build answer from the highest bit).

### C1.6 Number theory I (extend `number-theory`, `modular-arithmetic`)
- [CORE] Sieve of Eratosthenes, linear sieve, smallest prime factor (SPF) → factorisation in O(log n).
- [CORE] Number of divisors & sum of divisors from factorisation; divisors precomputation for all numbers ≤ N (harmonic loops).
- [CORE] Modular arithmetic: add/sub/mul under mod, binary exponentiation, modular inverse via Fermat (prime mod).
- [CORE] Extended Euclid, solving ax + by = c, modular inverse for non-prime mod.
- [STD] Segmented sieve; Euler's totient (single and sieve); gcd sums.

### C1.7 Combinatorics I (extend `combinatorics`)
- [CORE] nCr with precomputed factorials & inverse factorials mod p.
- [CORE] Permutations with repetition, stars and bars, counting pairs/triples.
- [CORE] Inclusion–exclusion (2–3 sets, then over subsets of primes).
- [CORE] Contribution technique: "sum over all subarrays/subsets" → each element's contribution.
- [STD] Catalan numbers, derangements, Pascal identities, Lucas theorem [ADV].

### C1.8 Bit manipulation for CP (extend `bitmasks`)
- [CORE] XOR properties (prefix XOR, pairing, XOR basis intuition), AND/OR monotonicity over subarrays.
- [CORE] Per-bit contribution: sum of XOR/AND/OR over all pairs; counting by bits.
- [CORE] `__builtin_popcount`, `__builtin_ctz/clz`, `__lg`; bitset speedups.
- [STD] XOR basis / linear basis (max subset XOR) [ADV].

### C1.9 Graph basics for CP (extend `graph-techniques`)
- [CORE] BFS/DFS on graphs & grids, connected components, bipartiteness, cycle detection, BFS shortest path with path reconstruction.
- [CORE] Trees as graphs: subtree sizes, depths, parent arrays, diameter (two BFS).
- [CORE] Functional graphs (each node one outgoing edge): cycle finding, tail lengths.
- [STD] Graph modelling: state-space BFS (node = (position, extra state)).

### C1.10 Classic DP for CP (extend `dp-classics`) — split into several concepts; see C2.x for advanced DP
Anchor set = **AtCoder Educational DP Contest A–Z**, plus CSES DP section:
- [CORE] Frog 1/2, Vacation (state = last activity), Knapsack 1 (weight small) vs Knapsack 2 (value small → swap dimension), LCS with reconstruction, Longest path in DAG, Grid 1, Coins (probability DP), Sushi (expected value DP), Stones (game DP), Deque (interval game DP), Candies (prefix-sum optimised transitions), Slimes (interval DP).
- [CORE] CSES: dice combinations, minimising coins, coin combinations I (ordered) vs II (unordered), removing digits, grid paths, book shop, array description, counting towers, edit distance, rectangle cutting, money sums, removal game, two sets II, increasing subsequence, projects (DP + binary search over sorted intervals), elevator rides (bitmask).
- [CORE] Recognising state from constraints; reducing dimensions; choosing which quantity is the DP value vs index.

## Level 2 — Specialist to Expert (1500–1900)

### C2.1 Range query structures
- [CORE] **Sparse table** [NEW]: O(1) RMQ, idempotent operations (min/max/gcd), O(n log n) build.
- [CORE] **Fenwick tree** (extend `fenwick-tree`): point update/range query, range update/point query, range update/range query (two BITs), counting inversions, order statistics via BIT walk.
- [CORE] **Segment tree** (extend `segment-tree`): build/query/update; custom merge nodes (max subarray sum node, count of max, gcd).
  - [CORE] **Lazy propagation**: range add, range assign, range add + range sum/min.
  - [CORE] **Segment tree walk / descent**: first index with value ≥ x, k-th one.
  - [STD] Merge sort tree, segment tree on compressed coordinates, segment tree with sets.
  - [ADV] Persistent segment tree (k-th smallest in range), segment tree beats, Li Chao tree.
- [CORE] Offline queries: sort queries + BIT (distinct elements in range).
- [STD] **Sqrt decomposition** [NEW] and **Mo's algorithm** [NEW] (distinct values in range offline, add/remove functions).

### C2.2 DSU advanced (bridges `dsa:union-find`)
- [CORE] DSU with extra data per component (size, sum, min/max), DSU on offline queries (reverse deletions → additions).
- [STD] Weighted DSU / DSU with parity (bipartite check online), DSU with rollback (for offline dynamic connectivity) [ADV].

### C2.3 Shortest paths and graph algorithms (extend `graph-techniques`, `mst`)
- [CORE] Dijkstra variants: multi-source, with state (node, used coupon), k-th shortest paths, count shortest paths, reconstruct path.
- [CORE] 0-1 BFS; Bellman–Ford & negative cycles; Floyd–Warshall (incl. transitive closure); SPFA caveat.
- [CORE] MST: Kruskal, Prim, MST properties (cycle/cut property), second-best MST [STD], minimum spanning forest with constraints.
- [CORE] **Topological sort + DP on DAG**: longest path, counting paths, game on DAG.
- [CORE] **SCC** [NEW]: Kosaraju & Tarjan, condensation graph, DP on condensation (CSES Coin Collector).
- [CORE] **Bridges & articulation points** [NEW] (low-link), 2-edge-connected components.
- [STD] **2-SAT** [NEW] (implication graph + SCC).
- [STD] **Euler path/circuit** [NEW] (Hierholzer), De Bruijn sequence.
- [ADV] **Flows & matching** [NEW]: Ford–Fulkerson/Edmonds–Karp/Dinic, min cut, bipartite matching (Kuhn/Hopcroft–Karp), min-cost flow.

### C2.4 Trees for CP (extend `tree-techniques`, `lca`)
- [CORE] Tree DP: subtree DP, max independent set, matching on tree, counting paths, tree diameter via DP.
- [CORE] **Rerooting DP** [NEW] (sum of distances to all nodes, max distance from each node).
- [CORE] LCA: binary lifting, Euler tour + RMQ; distance between nodes; k-th ancestor; path queries via LCA + prefix values.
- [CORE] **Euler tour / flattening** [NEW]: subtree queries become range queries (BIT/segment tree on tin/tout).
- [STD] Small-to-large merging (DSU on tree / sack).
- [ADV] Heavy–light decomposition (path queries), centroid decomposition (count paths of length k), virtual trees.

### C2.5 Strings for CP (extend `kmp`, `string-hashing`)
- [CORE] Prefix function (KMP): matching, periods, counting occurrences of each prefix, automaton.
- [CORE] **Z-function** [NEW]: matching, periods, string compression.
- [CORE] Polynomial hashing: double hashing / big mod, comparing substrings in O(1), longest palindromic substring via hash + binary search, anti-hash awareness.
- [STD] **Manacher** [NEW], **Trie of bits** for max XOR queries.
- [ADV] **Suffix array** [NEW] (O(n log n) doubling) + LCP (Kasai), distinct substrings, longest repeated substring; **Aho–Corasick** [NEW]; suffix automaton.

### C2.6 Number theory II
- [CORE] Chinese remainder theorem; Euler's theorem & totient (reducing huge exponents a^(b^c) mod m).
- [CORE] Counting multiples / coprime counting via inclusion–exclusion over prime factors.
- [STD] **Möbius function & Möbius inversion** [NEW]: count pairs with gcd = 1, sum of gcds.
- [STD] Divisor sum tricks: iterate over gcd values, "for d from 1 to N for multiples of d" pattern.
- [ADV] Pollard rho / Miller–Rabin for 64-bit, discrete log (baby-step giant-step), primitive roots.

### C2.7 Combinatorics & probability II
- [CORE] **Expected value** [NEW]: linearity of expectation, indicator variables, expected value DP, probabilities as modular fractions (p · q⁻¹ mod).
- [CORE] Counting with DP vs formula; bijections; counting paths in a grid with obstacles (inclusion–exclusion over sorted obstacles).
- [STD] Burnside's lemma (necklaces), generating functions intuition.

### C2.8 Game theory [NEW]
- [CORE] Winning/losing positions via DP on states; symmetry/mirroring strategies.
- [CORE] Nim, Sprague–Grundy theorem, Grundy numbers of composite games.
- [STD] Misère Nim, staircase Nim, Green Hackenbush intro.

### C2.9 Matrix exponentiation [NEW]
- [CORE] Linear recurrences (Fibonacci in O(log n)), counting paths of length k in a graph, transitions as matrices.
- [STD] Matrix exponentiation with min-plus (shortest path with exactly k edges).

### C2.10 Advanced DP families for CP [NEW] — split `dp-classics` into these concepts
- [CORE] **Digit DP**: count numbers in [L, R] with digit property (sum of digits, no adjacent equal, divisible by k); state (pos, tight, started, extra).
- [CORE] **Bitmask DP** (extend `bitmask-dp`): TSP/Hamiltonian path counts, assignment problems, "dp over subsets" with submask enumeration in 3ⁿ, broken profile / DP on grid with mask (counting tilings) [STD].
- [CORE] **SOS DP** (sum over subsets) — counting pairs with a & b = 0, superset sums.
- [CORE] **Interval DP**: Slimes, removal games, palindrome-removal, optimal merging, "zuma"-style.
- [CORE] **DP on trees** (see C2.4) incl. knapsack on tree (O(n²) merging argument).
- [CORE] **Probability/expectation DP** (Sushi, dice expected values, random walks).
- [CORE] **DP with data structures**: LIS with BIT/segment tree, DP transitions over ranges with segment tree, DP + monotonic deque (sliding window min transition).
- [CORE] **Counting DP with prefix sums** to drop a factor of n (Candies, array description).
- [STD] **DP optimisations**: convex hull trick, Li Chao tree, divide & conquer optimisation, Knuth optimisation, Aliens trick (Lagrangian relaxation/WQS binary search) [ADV], slope trick [ADV].
- [STD] **Profile/connectivity DP**, DP on broken profiles, DP on permutations (insertion DP, "connected components" DP) [ADV].
- [STD] **Exchange-argument DP**: sort items by a key then knapsack (e.g., projects with deadlines).

### C2.11 Geometry [NEW]
- [CORE] Points/vectors with integers; cross product & orientation; segment intersection; polygon area (shoelace); point in polygon.
- [STD] Convex hull (Andrew's monotone chain), Pick's theorem, closest pair of points, rotating calipers [ADV].
- [CORE] Precision handling: avoid floats, compare with epsilon when unavoidable.

## Level 3 — Expert to Candidate Master and beyond (1900+) [ADV]
- Advanced range techniques: persistent structures, wavelet tree, segment tree beats, offline divide & conquer (CDQ), parallel binary search, Mo's on trees, Mo's with updates.
- Advanced graphs: centroid decomposition, HLD, dominator trees, link-cut tree awareness, min-cost max-flow, Hungarian algorithm, general matching awareness.
- Polynomials: FFT/NTT for convolution (counting pair sums, string matching with wildcards).
- Strings: suffix automaton, palindromic tree (eertree), Lyndon factorisation.
- Math: Berlekamp–Massey, Lagrange interpolation, linear algebra mod p (Gaussian elimination, XOR basis), Dirichlet convolution / min_25 awareness.
- Randomisation: random shuffling, hashing sets (XOR hashing), probabilistic checks.

## C-cross. Contest craft [NEW] — applies at every level
- [CORE] Reading the whole problem set first; ordering by solve count; time management.
- [CORE] Interactive problems: flushing output, query limits, binary-search-style interaction.
- [CORE] Problem-classification drill: guess the technique from constraints alone (n ≤ 20 → bitmask; n ≤ 2·10⁵ with queries → segment tree/BIT; values ≤ 10⁶ → sieve/frequency; "minimum of maximum" → binary search).
- [CORE] Writing a personal template library (DSU, segment tree, modint, combinatorics, graph utilities) — and understanding every line.
- [STD] Virtual contests & upsolving plans per rating band; rating-based ladders (Socrat already has `library/ladder.py` — map ladders to these concepts).

### Track 3 exit tests (unseen-problem bar per band)
- **Pupil band:** solve A–C of a Div 2 / Div 3 virtual contest within 2 hours.
- **Specialist band:** solve A–D of Div 2 within 2 hours; solve 4 unseen 1500-rated problems from different families.
- **Expert band:** solve A–D consistently, E sometimes; solve unseen 1700–1800 problems spanning range queries, tree techniques and DP families.

---

# Appendix A — Gap map: current catalog → target concepts

| Track | Current concept file | Becomes / splits into |
| --- | --- | --- |
| zero | `programs-and-output` | Z1 How code runs + Z2 Output |
| zero | `input-and-arithmetic` | Z3 Operators + Z4 Input |
| zero | `nested-loops` | Z6 incl. pattern printing |
| zero | (none) | Z7 Math on numbers, Z14 Searching/sorting basics, Z15 Number systems, Z18 Exceptions, Z19 Files/modules, Z20 Std library, Z21 Complexity intuition, Z23 Mini projects |
| zero | `scope-and-mutation` | Z8 Functions (scope) + Z16 Memory model |
| dsa | `arrays-hashing` | D2 Arrays + D3 Hashing |
| dsa | `binary-search` | D7a Sorted arrays + D7b On answer + D7c 2D |
| dsa | `stacks` | D11a Stack/queue fundamentals + D11b Monotonic stack/deque |
| dsa | `backtracking` | D9 Recursion patterns + D10 Backtracking |
| dsa | `binary-trees` | D16a Traversals + D16b Patterns + D16c Construction |
| dsa | `graph-traversal` | D18a Traversal (grids, multi-source BFS, bipartite, cycles) |
| dsa | `union-find` | D18d DSU + MST |
| dsa | `dp-1d`, `dp-2d` | D19.0–D19.12 (13 DP concepts) |
| dsa | (none) | D22 Math, D23 String algorithms, D24 Design DS, D25 Advanced DS, D26 Interview skills |
| cp | `fast-io` | C0.1 Contest environment |
| cp | (none) | C0.2 Stress testing, C0.4 Ad hoc, C0.5 Constructive, C2.8 Game theory, C2.9 Matrix expo, C2.11 Geometry, C-cross Contest craft |
| cp | `segment-tree` | C2.1 incl. lazy, walk, merge-node, + sparse table, sqrt, Mo's |
| cp | `kmp`, `string-hashing` | C2.5 incl. Z-function, Manacher, suffix array, Aho–Corasick |
| cp | `graph-techniques`, `mst` | C1.9 + C2.3 incl. SCC, bridges, 2-SAT, Euler, flows |
| cp | `tree-techniques`, `lca` | C2.4 incl. rerooting, Euler tour, small-to-large, HLD, centroid |
| cp | `dp-classics`, `bitmask-dp` | C1.10 + C2.10 (digit, SOS, interval, probability, DP+DS, optimisations) |
| cp | `number-theory`, `modular-arithmetic`, `combinatorics` | C0.6 + C1.6 + C1.7 + C2.6 + C2.7 |

**Concept count target:** Zero ≈ 23 (from 18), DSA ≈ 45 (from 23), CP ≈ 45 (from 20), ≈ 113 total. Pattern families inside them: ~350.

# Appendix B — Build order (what to author first)

1. **DSA DP (D19.x)** — the largest gap and the most-searched topic; highest showcase value.
2. **DSA trees (D16) and graphs (D18)** — interview frequency.
3. **Zero Z6 pattern printing + Z7 math on numbers + Z14 sorting basics** — what free beginner playlists all have and Socrat lacks.
4. **DSA binary search (D7), monotonic stack (D11b), linked list families (D12)**.
5. **CP C0.4 ad hoc + C0.5 constructive + C1.10 AtCoder DP set** — what blocks 800 → 1400.
6. **CP range queries (C2.1) and tree techniques (C2.4)** — what blocks 1500 → 1900.
7. Everything tagged [ADV] last, unlocked by placement or rating.

# Appendix C — Authoring checklist per pattern family

- [ ] Recognition cues listed (keywords + constraints).
- [ ] Anchor problem: brute force → optimal, with dry-run table.
- [ ] Template in Python, C++, Java.
- [ ] 3–8 variants, each changing one thing; mapped to external practice IDs from `content/practice/problems.jsonl`.
- [ ] Contrast pair added to `content/patterns/contrasts.yaml`.
- [ ] 3+ quiz items (trace, predict-output, choose-the-state, spot-the-bug) added to `content/quiz/<track>/<concept>/`.
- [ ] 2 unseen check problems held out from the lesson.
- [ ] Common mistakes / misconception IDs linked to the existing repair taxonomy.
