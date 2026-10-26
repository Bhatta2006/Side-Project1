"""Insecure host execution for explicitly gated development demos only."""

import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import psutil

from runner.docker_backend import SandboxUnavailable
from runner.toolchains import toolchains
from socrat.execution.protocol import CaseResult, JobEnvelope, RuntimeProfile, same_output

# Windows: create suspended (assigned to a Job Object, then resumed) and without a console.
# A sys.platform check, unlike os.name, lets mypy accept the Windows-only constant on Linux.
if sys.platform == "win32":
    CREATION_FLAGS = 0x4 | subprocess.CREATE_NO_WINDOW
else:
    CREATION_FLAGS = 0


@dataclass
class Captured:
    code: int
    stdout: str
    stderr: str
    wall_ms: int
    limit: str = ""


@contextmanager
def job_directory(root: Path | None):
    holder = tempfile.TemporaryDirectory(prefix="socrat-job-", dir=root)
    try:
        yield holder.name
    finally:
        # TerminateJobObject returns before the killed tree releases its cwd and file handles.
        deadline = time.monotonic() + 5
        while True:
            try:
                holder.cleanup()
                break
            except PermissionError:
                if os.name != "nt" or time.monotonic() > deadline:
                    raise
                time.sleep(0.05)


def strip_directory(text: str, directory: Path) -> str:
    """Remove the job's temp path (it embeds the server username) from learner-visible output."""
    for base in {str(directory), str(directory.resolve())}:
        for form in (base, base.replace("\\", "/")):
            text = text.replace(form + os.sep, "").replace(form + "/", "").replace(form, "")
    return text


def scrubbed_environment(directory: Path, commands: list[str]) -> dict[str, str]:
    values = {
        "PATH": os.pathsep.join(dict.fromkeys(str(Path(x).resolve().parent) for x in commands)),
        "TEMP": str(directory),
        "TMP": str(directory),
        "TMPDIR": str(directory),
        "HOME": str(directory),
        "USERPROFILE": str(directory),
        "LANG": "C.UTF-8",
    }
    if os.name == "nt":
        values["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        values["WINDIR"] = values["SystemRoot"]
    return values


def capture_process(
    command: list[str],
    stdin: str,
    directory: Path,
    env: dict[str, str],
    *,
    seconds: float,
    memory_mb: int,
    pids: int,
    output_bytes: int,
    cpu_seconds: int,
) -> Captured:
    started = time.monotonic()
    job = None
    process = None
    if sys.platform == "win32":
        from runner.windows_job import WindowsJob

        job = WindowsJob(memory_mb * 1024 * 1024, pids)
    streams = [bytearray(), bytearray()]
    flooded = threading.Event()
    lock = threading.Lock()
    total = 0
    threads = []
    limited = ""
    try:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATION_FLAGS,
            start_new_session=os.name != "nt",
        )
        if job:
            job.assign_and_resume(process)

        def read(stream, index):
            nonlocal total
            try:
                while chunk := stream.read(4096):
                    with lock:
                        room = max(0, output_bytes - total)
                        streams[index].extend(chunk[:room])
                        total += len(chunk)
                        if total > output_bytes:
                            flooded.set()
            except (OSError, ValueError):
                pass
            finally:
                stream.close()

        def write():
            assert process is not None and process.stdin is not None
            try:
                process.stdin.write(stdin.encode())
                process.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                pass
            finally:
                try:
                    process.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    pass

        for target, args in ((read, (process.stdout, 0)), (read, (process.stderr, 1)), (write, ())):
            thread = threading.Thread(target=target, args=args, daemon=True)
            threads.append(thread)
            thread.start()
        while process.poll() is None:
            if flooded.is_set():
                limited = "output_limit"
            elif time.monotonic() - started >= seconds:
                limited = "timeout"
            else:
                try:
                    observed = psutil.Process(process.pid)
                    tree = [observed, *observed.children(recursive=True)]
                    memory = sum(child.memory_info().rss for child in tree if child.is_running())
                    cpu = sum(sum(child.cpu_times()[:2]) for child in tree if child.is_running())
                    if memory > memory_mb * 1024 * 1024:
                        limited = "memory_limit"
                    elif len(tree) > pids or cpu > cpu_seconds:
                        limited = "timeout"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if limited:
                break
            time.sleep(0.01)
        # Always kill descendants, even if the parent exited successfully while
        # leaving a child with inherited pipes open.
        if job:
            job.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
            except ProcessLookupError:
                pass
        process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
        if any(thread.is_alive() for thread in threads):
            raise SandboxUnavailable("local_process_cleanup_failed")
        if flooded.is_set():
            limited = "output_limit"
        stdout, stderr = (bytes(x).decode("utf-8", errors="replace") for x in streams)
        memory_errors = (
            "MemoryError",
            "std::bad_alloc",
            "OutOfMemoryError",
            "insufficient memory",
            "Could not reserve enough space",
        )
        if not limited and (
            process.returncode in {0xC0000017, 0xC000012D}
            or any(x in stderr for x in memory_errors)
        ):
            limited = "memory_limit"
        return Captured(
            process.returncode,
            stdout,
            stderr,
            min(60000, int((time.monotonic() - started) * 1000)),
            limited,
        )
    finally:
        if job:
            job.close()
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()


class LocalProcessBackend:
    def __init__(self, profiles: list[RuntimeProfile], *, environment: str, demo_mode: bool):
        if environment not in {"development", "test"} or not demo_mode:
            raise ValueError("Local process execution requires development/test demo mode")
        self.profiles = {x.image: x for x in profiles}
        self.temp_root: Path | None = None

    def preflight(self):
        if not Path(sys.executable).is_file():
            raise SandboxUnavailable("python_toolchain_missing")

    def available_images(self):
        return [x.image for x in self.profiles.values() if x.language in toolchains()]

    def execute(self, job: JobEnvelope) -> list[CaseResult]:
        try:
            return self._execute(job)
        except (OSError, subprocess.SubprocessError, psutil.Error) as exc:
            raise SandboxUnavailable("local_process_control_failure") from exc

    def _execute(self, job: JobEnvelope) -> list[CaseResult]:
        profile = self.profiles.get(job.manifest.image)
        if (
            profile is None
            or profile.id != job.manifest.runtime_id
            or profile.language != job.manifest.language
            or profile.limits != job.manifest.limits
        ):
            raise SandboxUnavailable("unapproved_local_profile")
        commands = toolchains().get(profile.language)
        if not commands:
            raise SandboxUnavailable("toolchain_missing")
        limits = profile.limits
        with job_directory(self.temp_root) as temporary:
            directory = Path(temporary)
            source = (
                directory
                / {"python": "solution.py", "cpp": "solution.cpp", "java": "Solution.java"}[
                    profile.language
                ]
            )
            source.write_text(job.source, encoding="utf-8")
            env = scrubbed_environment(directory, commands)
            compile_command = [
                sys.executable,
                "-I",
                "-B",
                "-c",
                "import pathlib; p=pathlib.Path('solution.py'); compile(p.read_text(encoding='utf-8'), str(p), 'exec')",
            ]
            run_command = [sys.executable, "-I", "-B", str(source)]
            if profile.language == "cpp":
                binary = directory / ("solution.exe" if os.name == "nt" else "solution")
                compile_command = [commands[0], "-std=c++20", "-O2", str(source), "-o", str(binary)]
                run_command = [str(binary)]
            elif profile.language == "java":
                compile_command = [
                    commands[0],
                    "-J-Xmx128m",
                    "-J-XX:+UseSerialGC",
                    "-J-XX:-UsePerfData",
                    "-J-XX:ActiveProcessorCount=1",
                    "-encoding",
                    "UTF-8",
                    "-d",
                    str(directory),
                    str(source),
                ]
                run_command = [
                    commands[1],
                    "-Xmx128m",
                    "-XX:+UseSerialGC",
                    "-XX:-UsePerfData",
                    "-XX:ActiveProcessorCount=1",
                    "-cp",
                    str(directory),
                    "Solution",
                ]
            built = capture_process(
                compile_command,
                "",
                directory,
                env,
                seconds=limits.compile_seconds,
                memory_mb=limits.memory_mb,
                pids=limits.pids,
                output_bytes=min(limits.output_bytes, 16000),
                cpu_seconds=limits.compile_seconds,
            )
            results = []
            for index, test in enumerate(job.tests):
                result = (
                    built
                    if built.code or built.limit
                    else capture_process(
                        run_command,
                        test.input,
                        directory,
                        env,
                        seconds=job.manifest.run_seconds,
                        memory_mb=limits.memory_mb,
                        pids=limits.pids,
                        output_bytes=limits.output_bytes,
                        cpu_seconds=limits.cpu_seconds,
                    )
                )
                status = result.limit or (
                    "compile_error"
                    if built.code
                    else "runtime_error"
                    if result.code
                    else "executed"
                    if test.expected is None
                    else "passed"
                    if same_output(result.stdout, test.expected)
                    else "wrong_answer"
                )
                public = test.visibility == "public"
                results.append(
                    CaseResult.model_validate(
                        dict(
                            index=index,
                            status=status,
                            wall_ms=result.wall_ms,
                            stdout=strip_directory(result.stdout, directory)[:16000]
                            if public
                            else "",
                            stderr=strip_directory(result.stderr, directory)[:16000]
                            if public
                            else "",
                        )
                    )
                )
            return results
