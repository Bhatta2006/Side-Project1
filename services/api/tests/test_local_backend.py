"""Real native Windows/POSIX execution, never simulated result callbacks."""

import os
import time

import psutil
import pytest
from runner.local_backend import LocalProcessBackend, job_directory
from runner.worker import execute

from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
)
from socrat.models import identifier

SECRET = "native-test-signing-secret-" * 3


def envelope(source, language="python", **limits):
    profile = RuntimeProfile.model_validate(
        dict(
            id="local_" + language,
            language=language,
            image="socrat/local-" + language + "@sha256:" + "a" * 64,
            attestation_reference="Insecure local development toolchain",
            limits=dict(
                wall_seconds=2,
                compile_seconds=20,
                memory_mb=256,
                pids=8,
                output_bytes=4096,
                **limits,
            ),
        )
    )
    tests = [
        TestInput(input="2\n", expected="4", visibility="public"),
        TestInput(input="3\n", expected="6", visibility="hidden"),
    ]
    stamp = int(time.time())
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce="b" * 64,
        issued_at=stamp,
        expires_at=stamp + 600,
        language=language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical([x.model_dump() for x in tests])),
        pack_digest="sha256:" + "c" * 64,
        mode="submit",
        limits=profile.limits,
        compile_config=COMMANDS[language],
    )
    job = JobEnvelope(
        manifest=manifest, signature=sign(manifest.model_dump(), SECRET), source=source, tests=tests
    )
    return LocalProcessBackend([profile], environment="test", demo_mode=True), job


@pytest.mark.parametrize(
    "source,status",
    [
        ("print(int(input())*2)", "passed"),
        ("print(0)", "wrong_answer"),
        ("a=1\ndef broken(:\n  pass", "compile_error"),
        ("a=1\nraise ValueError('real traceback')", "runtime_error"),
        ("while True: pass", "timeout"),
        ("while True: print('X'*4096)", "output_limit"),
        ("x=bytearray(2_000_000_000)", "memory_limit"),
    ],
)
def test_native_python_results_and_cleanup(source, status, tmp_path):
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy"
    assert [x["status"] for x in result["cases"]] == [status, status]
    assert result["cases"][1]["stdout"] == result["cases"][1]["stderr"] == ""
    assert not list(tmp_path.iterdir())
    if status == "compile_error":
        assert "line 2" in result["cases"][0]["stderr"]
    if status == "runtime_error":
        assert "line 2" in result["cases"][0]["stderr"]
    assert len(result["cases"][0]["stdout"]) <= 4096


def test_no_secrets_and_no_oracle_files(monkeypatch):
    monkeypatch.setenv("SOCRAT_EXECUTION_SIGNING_SECRET", "private-never-leak")
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "private-never-leak")
    source = "import os,pathlib\nassert not any('SOCRAT' in k or 'PRIVATE' in k for k in os.environ)\nassert sorted(x.name for x in pathlib.Path('.').iterdir()) == ['solution.py']\nprint(int(input())*2)"
    backend, job = envelope(source)
    assert all(x.status == "passed" for x in backend.execute(job))


def test_timeout_kills_descendants_and_spawn_is_contained(tmp_path):
    marker = "socrat-orphan-" + identifier()
    source = f"import subprocess,sys\nfor n in range(1000):\n subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)',{marker!r}])\nwhile True: pass"
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    assert all(
        x.status in {"timeout", "runtime_error", "memory_limit"} for x in backend.execute(job)
    )
    time.sleep(0.1)
    for process in psutil.process_iter(["cmdline"]):
        assert marker not in " ".join(process.info["cmdline"] or [])
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "environment,demo",
    [("production", True), ("staging", True), ("development", False), ("test", False)],
)
def test_local_process_guard(environment, demo):
    with pytest.raises(ValueError, match="demo mode"):
        LocalProcessBackend([], environment=environment, demo_mode=demo)


LANGUAGE_PROGRAMS = {
    "cpp": {
        "passed": "#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<n*2;}",
        "wrong_answer": "#include <iostream>\nint main(){std::cout<<0;}",
        "compile_error": "#include <iostream>\nint main(){invalid_symbol;}",
        "runtime_error": "#include <cstdlib>\nint main(){std::abort();}",
        "timeout": "int main(){while(true){}}",
        "output_limit": '#include <iostream>\nint main(){while(true)std::cout<<"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX";}',
        "memory_limit": "#include <vector>\nint main(){std::vector<char> x(2000000000); volatile char* p=x.data(); for(long i=0;i<2000000000;i++)p[i]=1;}",
    },
    "java": {
        "passed": "public class Solution {public static void main(String[] a){System.out.println(new java.util.Scanner(System.in).nextInt()*2);}}",
        "wrong_answer": "public class Solution {public static void main(String[] a){System.out.println(0);}}",
        "compile_error": "public class Solution {\npublic static void main(String[] a){invalid_symbol;}\n}",
        "runtime_error": 'public class Solution {\npublic static void main(String[] a){throw new RuntimeException("real traceback");}\n}',
        "timeout": "public class Solution {public static void main(String[] a){while(true){}}}",
        "output_limit": 'public class Solution {public static void main(String[] a){while(true)System.out.print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX");}}',
        "memory_limit": "public class Solution {public static void main(String[] a){byte[] x=new byte[2000000000];System.out.print(x.length);}}",
    },
}


@pytest.mark.parametrize("language", ["cpp", "java"])
@pytest.mark.parametrize("status", list(LANGUAGE_PROGRAMS["cpp"]))
def test_native_compiled_languages(language, status, tmp_path):
    backend, job = envelope(LANGUAGE_PROGRAMS[language][status], language)
    backend.temp_root = tmp_path
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy", "Required CI toolchain is missing"
    assert [case["status"] for case in result["cases"]] == [status, status]
    assert result["cases"][1]["stdout"] == result["cases"][1]["stderr"] == ""
    if status == "compile_error":
        assert ":2:" in result["cases"][0]["stderr"]
    assert not list(tmp_path.iterdir())
    for process in psutil.process_iter(["cmdline"]):
        assert str(tmp_path) not in " ".join(process.info["cmdline"] or [])


@pytest.mark.parametrize("language", ["cpp", "java"])
def test_compiled_environment_and_oracle_files(language, monkeypatch, tmp_path):
    monkeypatch.setenv("SOCRAT_EXECUTION_SIGNING_SECRET", "private-never-leak")
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "private-never-leak")
    source = (
        '#include <cstdlib>\n#include <filesystem>\n#include <iostream>\nint main(){if(std::getenv("SOCRAT_EXECUTION_SIGNING_SECRET")||std::getenv("PRIVATE_PROVIDER_KEY"))return 1;for(auto const& entry:std::filesystem::directory_iterator(".")){auto n=entry.path().filename().string();if(n!="solution.cpp"&&n!="solution.exe"&&n!="solution")return 2;}int n;std::cin>>n;std::cout<<n*2;}'
        if language == "cpp"
        else 'public class Solution {public static void main(String[] a)throws Exception{if(System.getenv().keySet().stream().anyMatch(k->k.startsWith("SOCRAT_")||k.startsWith("PRIVATE_")))throw new Exception("secret");try(var files=java.nio.file.Files.list(java.nio.file.Path.of("."))){if(files.anyMatch(p->!java.util.Set.of("Solution.java","Solution.class").contains(p.getFileName().toString())))throw new Exception("oracle file");}System.out.println(new java.util.Scanner(System.in).nextInt()*2);}}'
    )
    backend, job = envelope(source, language)
    backend.temp_root = tmp_path
    cases = backend.execute(job)
    assert all(case.status == "passed" for case in cases), cases
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("language", ["cpp", "java"])
def test_compiled_spawn_bomb_leaves_no_orphan(language, tmp_path):
    import json
    import os
    import subprocess
    import sys

    marker = "socrat-compiled-orphan-" + identifier()
    arguments = [sys.executable, "-I", "-B", "-c", "import time;time.sleep(60)", marker]
    if language == "java":
        args = ",".join(json.dumps(value) for value in arguments)
        source = (
            "public class Solution{public static void main(String[] a)throws Exception{for(int i=0;i<1000;i++)new ProcessBuilder("
            + args
            + ").start();Thread.sleep(60000);}}"
        )
    elif os.name == "nt":
        command = json.dumps(subprocess.list2cmdline(arguments))
        source = (
            "#include <windows.h>\n#include <cstring>\nint main(){for(int i=0;i<1000;i++){char command[4096];strcpy(command,"
            + command
            + ");STARTUPINFOA s{};s.cb=sizeof(s);PROCESS_INFORMATION p{};if(CreateProcessA(nullptr,command,nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&s,&p)){CloseHandle(p.hProcess);CloseHandle(p.hThread);}}Sleep(60000);}"
        )
    else:
        source = "#include <unistd.h>\nint main(){for(int i=0;i<1000;i++)if(fork()==0){sleep(60);return 0;}sleep(60);}"
    backend, job = envelope(source, language)
    backend.temp_root = tmp_path
    assert all(
        case.status in {"timeout", "runtime_error", "memory_limit"} for case in backend.execute(job)
    )
    for process in psutil.process_iter(["cmdline"]):
        command = " ".join(process.info["cmdline"] or [])
        assert marker not in command and str(tmp_path) not in command
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(os.name != "nt", reason="Windows file locks only")
def test_job_directory_waits_for_a_released_lock(tmp_path):
    import threading

    with job_directory(tmp_path) as directory:
        held = open(os.path.join(directory, "held"), "w")
        threading.Timer(0.3, held.close).start()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("backend", ["local_process", "demo_docker"])
@pytest.mark.parametrize("environment", ["staging", "production"])
def test_development_backend_settings_rejected(backend, environment):
    from socrat.config import Settings

    with pytest.raises(ValueError, match="development/test"):
        Settings(_env_file=None, environment=environment, demo_mode=True, execution_backend=backend)


def test_missing_compiler_is_operational_zero_case_result(monkeypatch):
    monkeypatch.setattr("runner.local_backend.toolchains", lambda: {"python": []})
    backend, job = envelope("int main(){}", "cpp")
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "failed"
    assert result["cases"] == []


@pytest.mark.parametrize("environment", ["development", "test", "staging", "production"])
def test_production_worker_always_requires_https(environment, monkeypatch):
    import json

    from runner.worker import main
    from runner_support import profiles

    for key, value in {
        "SOCRAT_ENVIRONMENT": environment,
        "SOCRAT_EXECUTION_BACKEND": "gvisor_docker",
        "SOCRAT_EXECUTION_API_URL": "http://127.0.0.1:8000",
        "SOCRAT_EXECUTION_SIGNING_SECRET": SECRET,
        "SOCRAT_EXECUTION_WORKER_SECRET": "different-worker-secret-" * 3,
        "SOCRAT_EXECUTION_WORKER_ID": "test",
        "SOCRAT_EXECUTION_PROFILES": json.dumps(profiles()),
    }.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="HTTPS"):
        main()


@pytest.mark.parametrize("environment", ["development", "test"])
def test_local_worker_http_only_with_demo_guards(environment, monkeypatch):
    import json

    from runner.worker import main
    from runner_support import profiles

    for key, value in {
        "SOCRAT_ENVIRONMENT": environment,
        "SOCRAT_DEMO_MODE": "true",
        "SOCRAT_EXECUTION_BACKEND": "local_process",
        "SOCRAT_EXECUTION_API_URL": "http://127.0.0.1:8000",
        "SOCRAT_EXECUTION_SIGNING_SECRET": SECRET,
        "SOCRAT_EXECUTION_WORKER_SECRET": "different-worker-secret-" * 3,
        "SOCRAT_EXECUTION_WORKER_ID": "test",
        "SOCRAT_EXECUTION_PROFILES": json.dumps(profiles()),
    }.items():
        monkeypatch.setenv(key, value)

    class Authorized(Exception):
        pass

    def accepted(settings):
        raise Authorized()

    monkeypatch.setattr("runner.worker.make_backend", accepted)
    with pytest.raises(Authorized):
        main()
    monkeypatch.setenv("SOCRAT_EXECUTION_API_URL", "http://remote.example.test:8000")
    with pytest.raises(ValueError, match="local API"):
        main()
