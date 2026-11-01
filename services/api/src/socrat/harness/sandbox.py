"""Run capabilities in a separate worker process that is killed when it takes too long.

Capabilities handle untrusted input (a learner's algebra, a model's claim) and may be slow
(computer algebra can blow up). The worker keeps its libraries loaded between calls so a check
costs milliseconds; a call that exceeds its time limit kills the worker, which restarts fresh.
One worker serves one call at a time; put a pool here when load needs it.
"""

import multiprocessing
import threading
from typing import Any

CONTEXT = multiprocessing.get_context("spawn")
GRACE = 20.0  # the first call may need to start the process and import the libraries


class Failed(Exception):
    """The capability crashed, was invalid, or ran out of time."""


def _serve(connection) -> None:
    from socrat.harness import registry

    table = registry.capabilities()
    while True:
        try:
            name, arguments = connection.recv()
        except EOFError:
            return
        try:
            connection.send(("ok", table[name].run(arguments)))
        except Exception as exc:  # the worker must survive any capability bug
            connection.send(("error", f"{type(exc).__name__}: {exc}"))


class Worker:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: Any = None  # a spawned multiprocessing.Process
        self.connection: Any = None  # our end of its Pipe
        self.warm = False

    def _start(self) -> None:
        mine, theirs = CONTEXT.Pipe()
        process = CONTEXT.Process(target=_serve, args=(theirs,), daemon=True)
        process.start()
        theirs.close()
        self.process, self.connection, self.warm = process, mine, False

    def _stop(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.join(2)
        if self.connection is not None:
            self.connection.close()
        self.process = self.connection = None

    def run(self, name: str, arguments: dict, timeout: float) -> dict:
        with self.lock:
            if self.process is None or not self.process.is_alive():
                self._stop()
                self._start()
            limit = timeout if self.warm else timeout + GRACE
            try:
                self.connection.send((name, arguments))
                if not self.connection.poll(limit):
                    self._stop()
                    raise Failed(f"Took longer than {timeout:g} seconds.")
                status, payload = self.connection.recv()
            except (EOFError, OSError, BrokenPipeError):
                self._stop()
                raise Failed("The checker stopped unexpectedly.") from None
            self.warm = True
        if status != "ok":
            raise Failed(payload)
        return payload


_worker = Worker()


def run(name: str, arguments: dict, timeout: float) -> dict:
    return _worker.run(name, arguments, timeout)


def shutdown() -> None:
    with _worker.lock:
        _worker._stop()
