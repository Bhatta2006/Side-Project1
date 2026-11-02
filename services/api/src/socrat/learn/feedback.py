"""Short feedback grounded in judge evidence, with no rewards for clicks or time."""

from socrat.models import Submission


def submission_copy(job: Submission) -> str | None:
    if job.status != "done":
        return None
    if job.verdict == "accepted":
        if job.mode == "run":
            return "Visible tests passed. Submit to check the hidden cases."
        if job.assistance == 0:
            return "Solved without hints. That counts as independent evidence."
        return "Accepted. Check the complexity below, then ask Soc whether there is a faster way."
    if job.verdict == "compile_error":
        return "Check the first compiler diagnostic and make one small syntax repair. This does not measure your understanding of the algorithm."
    if job.verdict == "wrong_answer":
        from socrat.judge.analysis import diagnosis

        return diagnosis(job) or (
            "A tested case did not match. Trace one small example and check the boundary where the result changes."
        )
    if job.verdict in {"timeout", "time_limit"}:
        return "The program exceeded its time limit. Check termination first, then count the work as the input grows."
    if job.verdict == "system_error":
        return "The runner could not check this attempt. It has not been counted as a learning failure."
    return "Inspect the reported result, make one precise change, and try again."
