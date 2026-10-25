"""Windows development loop: disconnected clients must not close the API listener.

CPython's Proactor closes a server socket when AcceptEx reports WinError 64.
Retry only that transient failure, retaining Proactor subprocess support for the
local browser checker. Production uses Uvicorn's normal event loop.
"""

import asyncio
import socket
import struct
import sys

if sys.platform == "win32":
    import _overlapped
    from asyncio.windows_events import IocpProactor

    class DevelopmentProactor(IocpProactor):
        def accept(self, listener):
            return self._loop.create_task(self._accept_retry(listener))  # type: ignore[attr-defined]

        async def _accept_retry(self, listener):
            while True:
                try:
                    return await self._accept_once(listener)
                except OSError as exc:
                    if exc.winerror != 64 or listener.fileno() == -1:
                        raise
                    await asyncio.sleep(0.01)

        async def _accept_once(self, listener):
            # Own the provisional socket until AcceptEx succeeds, including
            # cancellation; the stdlib helper closes it only on cancellation.
            self._register_with_iocp(listener)  # type: ignore[attr-defined]
            connection = self._get_accept_socket(listener.family)  # type: ignore[attr-defined]
            try:
                overlapped = _overlapped.Overlapped(0)
                overlapped.AcceptEx(listener.fileno(), connection.fileno())

                def finish_accept(transferred, key, completed):
                    completed.getresult()
                    connection.setsockopt(
                        socket.SOL_SOCKET,
                        _overlapped.SO_UPDATE_ACCEPT_CONTEXT,
                        struct.pack("@P", listener.fileno()),
                    )
                    connection.settimeout(listener.gettimeout())
                    return connection, connection.getpeername()

                return await self._register(overlapped, listener, finish_accept)  # type: ignore[attr-defined]
            except BaseException:
                connection.close()
                raise


def loop_factory(use_subprocess: bool = False) -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop(proactor=DevelopmentProactor())
    return asyncio.new_event_loop()
