"""gVisor-only dedicated Docker host driver. No host/socket mounts or fallback runtime."""

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Literal, cast

from socrat.execution.protocol import CaseResult, JobEnvelope, RuntimeProfile, same_output


class SandboxUnavailable(Exception):
    pass


def container_args(job: JobEnvelope, name: str):
    manifest = job.manifest
    limits = manifest.limits
    return [
        "docker",
        "create",
        "--name",
        name,
        "--runtime=runsc",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user=10001:10001",
        f"--memory={limits.memory_mb}m",
        f"--memory-swap={limits.memory_mb}m",
        "--cpus=1",
        f"--pids-limit={limits.pids}",
        "--ipc=none",
        "--ulimit",
        f"cpu={limits.compile_seconds}:{limits.compile_seconds}",
        "--ulimit",
        f"fsize={limits.disk_mb * 1024 * 1024}:{limits.disk_mb * 1024 * 1024}",
        "--ulimit",
        "nofile=64:64",
        "--log-driver=none",
        "--tmpfs",
        f"/work:rw,nosuid,nodev,size={limits.disk_mb}m,uid=10001,gid=10001,mode=700",
        "--workdir=/work",
        "--env=HOME=/work",
        "--env=TMPDIR=/work",
        "--interactive",
        manifest.image,
        "/usr/local/bin/python3",
        "-I",
        "-B",
        "/opt/socrat/launch.py",
        manifest.language,
        str(limits.compile_seconds),
        str(manifest.run_seconds),
        str(limits.cpu_seconds),
    ]


def cpu_usage(pid: int, proc_root=Path("/proc"), cgroup_root=Path("/sys/fs/cgroup")):
    """Read the complete sandbox cgroup, including descendants; require unified cgroups."""
    mapping = (proc_root / str(pid) / "cgroup").read_text().splitlines()
    unified = next((line[3:] for line in mapping if line.startswith("0::")), None)
    if unified is None:
        raise SandboxUnavailable("unified_cgroup_required")
    root = cgroup_root.resolve()
    directory = (root / unified.lstrip("/")).resolve()
    if not directory.is_relative_to(root):
        raise SandboxUnavailable("invalid_cgroup_path")
    stats = dict(line.split() for line in (directory / "cpu.stat").read_text().splitlines())
    return int(stats["usage_usec"]) / 1_000_000


def capture(args: list[str], stdin: bytes, timeout: int, limit: int, abort, cpu_exceeded):
    """Drain both pipes concurrently; retain bounded bytes and kill the whole sandbox."""
    process = subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    chunks = [bytearray(), bytearray()]
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    exceeded = threading.Event()
    lock = threading.Lock()
    total = 0

    def drain(stream, index):
        nonlocal total
        while True:
            data = stream.read(4096)
            if not data:
                break
            with lock:
                total += len(data)
                remaining = max(0, limit - sum(len(x) for x in chunks))
                chunks[index].extend(data[:remaining])
                if total > limit:
                    exceeded.set()

    readers = [
        threading.Thread(target=drain, args=(process.stdout, 0), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, 1), daemon=True),
    ]
    for thread in readers:
        thread.start()

    def feed():
        assert process.stdin is not None
        try:
            process.stdin.write(stdin)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    started = time.monotonic()
    timed_out = False
    try:
        while process.poll() is None:
            if exceeded.is_set() or time.monotonic() - started >= timeout or cpu_exceeded():
                timed_out = not exceeded.is_set()
                abort()
                process.kill()
                break
            time.sleep(0.01)
        process.wait(timeout=3)
    except BaseException:
        try:
            abort()
        finally:
            process.kill()
            process.wait(timeout=3)
        raise
    finally:
        for thread in readers:
            thread.join(timeout=3)
        feeder.join(timeout=1)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
    return process.returncode, bytes(chunks[0]), bytes(chunks[1]), timed_out, exceeded.is_set()


class DockerBackend:
    def __init__(self, profiles: list[RuntimeProfile], cosign_key: str):
        self.profiles = {x.image: x for x in profiles}
        self.cosign_key = cosign_key

    def command(self, args, **kwargs):
        if args[0] == "docker":
            args = [args[0], "--host=unix:///var/run/docker.sock", *args[1:]]
        return subprocess.run(args, capture_output=True, timeout=30, check=True, **kwargs)

    def preflight(self):
        try:
            information = json.loads(
                self.command(["docker", "info", "--format", "{{json .}}"]).stdout
            )
            if "runsc" not in information["Runtimes"] or not all(
                information.get(x) for x in ("MemoryLimit", "PidsLimit", "CPUQuota")
            ):
                raise SandboxUnavailable("gVisor and resource controllers required")
            if str(information.get("CgroupVersion")) != "2":
                raise SandboxUnavailable("Unified cgroups required for aggregate CPU enforcement")
            if not self.cosign_key:
                raise SandboxUnavailable("Runtime signature verification required")
            for image in self.profiles:
                self.command(["cosign", "verify", "--key", self.cosign_key, image])
                self.command(["docker", "image", "inspect", image])
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            raise SandboxUnavailable("execution_host_unavailable") from exc

    def execute(self, job: JobEnvelope) -> list[CaseResult]:
        profile = self.profiles.get(job.manifest.image)
        if (
            profile is None
            or job.manifest.limits != profile.limits
            or job.manifest.language != profile.language
        ):
            raise SandboxUnavailable("Unapproved execution profile")
        results = []
        # Each case gets a new security context. Hidden bundles never enter a sandbox filesystem.
        for index, test in enumerate(job.tests):
            if time.time() > job.manifest.expires_at:
                raise SandboxUnavailable("Job deadline exceeded")
            name = f"socrat-{job.manifest.job_id}-{index}"
            try:
                self.command(container_args(job, name))
                started = time.monotonic()
                pid = 0

                def cpu_exceeded(container_name=name):
                    nonlocal pid
                    if not pid:
                        pid = int(
                            self.command(
                                ["docker", "inspect", "--format", "{{.State.Pid}}", container_name]
                            ).stdout
                        )
                        if not pid:
                            return False
                    try:
                        return cpu_usage(pid) >= job.manifest.limits.cpu_seconds
                    except FileNotFoundError as exc:
                        state = json.loads(
                            self.command(
                                ["docker", "inspect", "--format", "{{json .State}}", container_name]
                            ).stdout
                        )
                        if not state.get("Running"):
                            return False
                        raise SandboxUnavailable("cpu_accounting_unavailable") from exc
                    except (OSError, KeyError, ValueError) as exc:
                        raise SandboxUnavailable("cpu_accounting_unavailable") from exc

                code, stdout, stderr, timed_out, flooded = capture(
                    [
                        "docker",
                        "--host=unix:///var/run/docker.sock",
                        "start",
                        "--attach",
                        "--interactive",
                        name,
                    ],
                    json.dumps({"source": job.source, "stdin": test.input}).encode(),
                    job.manifest.limits.compile_seconds + job.manifest.limits.wall_seconds,
                    job.manifest.limits.output_bytes,
                    lambda container_name=name: self.command(["docker", "kill", container_name]),
                    cpu_exceeded,
                )
                inspection = json.loads(
                    self.command(["docker", "inspect", "--format", "{{json .State}}", name]).stdout
                )
                if inspection.get("Status") != "exited" or inspection.get("Error"):
                    raise SandboxUnavailable("sandbox_start_or_control_failure")
                if inspection.get("OOMKilled"):
                    status = "memory_limit"
                elif flooded:
                    status = "output_limit"
                elif timed_out or code in {124, 137, 152}:
                    status = "timeout"
                elif code == 65:
                    status = "compile_error"
                elif code != 0:
                    status = "runtime_error"
                elif test.expected is None:
                    status = "executed"
                else:
                    status = (
                        "passed"
                        if same_output(stdout.decode("utf-8", errors="replace"), test.expected)
                        else "wrong_answer"
                    )
                public = test.visibility == "public"
                results.append(
                    CaseResult(
                        index=index,
                        status=cast(
                            Literal[
                                "passed",
                                "wrong_answer",
                                "executed",
                                "compile_error",
                                "runtime_error",
                                "timeout",
                                "memory_limit",
                                "output_limit",
                            ],
                            status,
                        ),
                        wall_ms=min(60000, int((time.monotonic() - started) * 1000)),
                        stdout=stdout.decode("utf-8", errors="replace")[:16000] if public else "",
                        stderr=stderr.decode("utf-8", errors="replace")[:16000] if public else "",
                    )
                )
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                raise SandboxUnavailable("worker_failure") from exc
            finally:
                # Docker removal kills the sandbox's entire cgroup, including escaped child processes.
                try:
                    self.command(["docker", "rm", "--force", name])
                except (OSError, subprocess.SubprocessError) as exc:
                    raise SandboxUnavailable("sandbox_cleanup_failed") from exc
        return results
