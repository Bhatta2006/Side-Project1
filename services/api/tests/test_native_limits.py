"""A signed problem budget applies after compilation, including subsecond limits."""

import time

import pytest
from runner.docker_backend import container_args
from runner.worker import execute
from test_local_backend import SECRET, envelope

from socrat.execution.protocol import JobEnvelope, sign


@pytest.mark.parametrize(("milliseconds", "expected"), [(500, "timeout"), (4000, "passed")])
def test_java_uses_problem_budget(milliseconds, expected, tmp_path):
    source = """public class Solution {
        public static void main(String[] args) throws Exception {
            Thread.sleep(1500);
            System.out.println(new java.util.Scanner(System.in).nextInt() * 2);
        }
    }"""
    backend, job = envelope(source, "java")
    backend.temp_root = tmp_path
    job.manifest.time_limit_ms = milliseconds
    # The profile's two-second safety cap remains independent of the problem budget.
    job.signature = sign(job.manifest.model_dump(), SECRET)
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy"
    assert [case["status"] for case in result["cases"]] == [expected, expected]
    assert not list(tmp_path.iterdir())


def test_old_manifest_signatures_remain_valid_and_new_limits_are_authenticated():
    _, job = envelope("print(4)")
    original = job.model_dump()
    assert "time_limit_ms" not in original["manifest"]
    JobEnvelope.model_validate(original).authenticate(SECRET, int(time.time()))
    job.manifest.time_limit_ms = 500
    with pytest.raises(ValueError, match="execution_signature_invalid"):
        job.authenticate(SECRET, int(time.time()))
    job.signature = sign(job.manifest.model_dump(), SECRET)
    job.authenticate(SECRET, int(time.time()))
    args = container_args(job, "budget-check")
    assert args[-2] == "0.5"
