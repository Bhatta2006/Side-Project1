"""Trusted entrypoint inside gVisor. Contains no tests, expected answers, or secrets."""

import json
import os
import resource
import subprocess
import sys

COMMANDS = {
    "python": ([], ["/usr/local/bin/python3", "-I", "-B", "/work/solution.py"]),
    "cpp": (
        ["g++", "-std=c++20", "-O2", "/work/solution.cpp", "-o", "/work/solution"],
        ["/work/solution"],
    ),
    "java": (
        ["/opt/java/openjdk/bin/javac", "-encoding", "UTF-8", "/work/Solution.java"],
        [
            "/opt/java/openjdk/bin/java",
            "-Xms16m",
            "-Xmx128m",
            "-XX:ActiveProcessorCount=1",
            "-XX:+UseSerialGC",
            "-cp",
            "/work",
            "Solution",
        ],
    ),
}

os.environ.clear()
os.environ.update(PATH="/usr/local/bin:/usr/bin:/bin", HOME="/work", TMPDIR="/work", LANG="C.UTF-8")
language, compile_seconds, wall_seconds, cpu_seconds = sys.argv[1:]
payload = json.loads(sys.stdin.buffer.read(512000))
filename = {"python": "solution.py", "cpp": "solution.cpp", "java": "Solution.java"}[language]
with open("/work/" + filename, "w", encoding="utf-8") as source:
    source.write(payload["source"])
compile_command, run_command = COMMANDS[language]
if compile_command:
    try:
        result = subprocess.run(
            compile_command, stdin=subprocess.DEVNULL, timeout=int(compile_seconds)
        )
    except subprocess.TimeoutExpired:
        sys.exit(124)
    if result.returncode:
        sys.exit(65)
try:

    def restrict_cpu():
        resource.setrlimit(resource.RLIMIT_CPU, (int(cpu_seconds), int(cpu_seconds)))

    result = subprocess.run(
        run_command,
        input=payload["stdin"].encode(),
        timeout=float(wall_seconds),
        preexec_fn=restrict_cpu,
    )
except subprocess.TimeoutExpired:
    sys.exit(124)
sys.exit(result.returncode if result.returncode >= 0 else 128 - result.returncode)
