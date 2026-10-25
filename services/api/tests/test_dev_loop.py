"""Transient AcceptEx failures retain the listener and Proactor subprocess support."""

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from socrat import dev_loop

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows AcceptEx regression")


def error(code):
    exc = OSError("accept failed")
    exc.winerror = code
    return exc


@pytest.mark.parametrize(
    ("code", "open_socket", "retries"), [(64, True, True), (5, True, False), (64, False, False)]
)
def test_only_transient_errors_on_open_listeners_retry(monkeypatch, code, open_socket, retries):
    async def run():
        proactor = dev_loop.DevelopmentProactor()
        proactor._loop = asyncio.get_running_loop()
        accept = AsyncMock(side_effect=[error(code), ("connection", "address")])
        monkeypatch.setattr(proactor, "_accept_once", accept)
        listener = SimpleNamespace(fileno=lambda: 7 if open_socket else -1)
        try:
            if retries:
                assert await proactor.accept(listener) == ("connection", "address")
                assert accept.await_count == 2
            else:
                with pytest.raises(OSError):
                    await proactor.accept(listener)
                assert accept.await_count == 1
        finally:
            proactor.close()

    asyncio.run(run())


def test_cancelled_accept_is_not_retried(monkeypatch):
    async def run():
        proactor = dev_loop.DevelopmentProactor()
        proactor._loop = asyncio.get_running_loop()
        pending = asyncio.Future()

        async def wait(listener):
            return await pending

        accept = AsyncMock(side_effect=wait)
        monkeypatch.setattr(proactor, "_accept_once", accept)
        try:
            task = proactor.accept(SimpleNamespace(fileno=lambda: 7))
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert accept.await_count == 1
        finally:
            proactor.close()

    asyncio.run(run())


def test_failed_accept_closes_the_provisional_socket(monkeypatch):
    async def run():
        proactor = dev_loop.DevelopmentProactor()
        connection = Mock()
        listener = Mock()
        monkeypatch.setattr(proactor, "_register_with_iocp", Mock())
        monkeypatch.setattr(proactor, "_get_accept_socket", Mock(return_value=connection))
        monkeypatch.setattr(
            dev_loop, "_overlapped", SimpleNamespace(Overlapped=Mock(return_value=Mock()))
        )
        failed = asyncio.Future()
        failed.set_exception(error(64))
        monkeypatch.setattr(proactor, "_register", Mock(return_value=failed))
        try:
            with pytest.raises(OSError):
                await proactor._accept_once(listener)
            connection.close.assert_called_once()
        finally:
            proactor.close()

    asyncio.run(run())


def test_development_loop_keeps_async_subprocess_support():
    async def run():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", "print('checker ready')", stdout=asyncio.subprocess.PIPE
        )
        output, _ = await process.communicate()
        assert process.returncode == 0 and output.strip() == b"checker ready"

    with asyncio.Runner(loop_factory=dev_loop.loop_factory) as runner:
        runner.run(run())
