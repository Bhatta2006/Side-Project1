"""Win32 Job Object ownership, with assignment before learner instructions run.

The child is created suspended; its sole primary thread is resumed only after
assignment. No breakaway flags are permitted. Closing the job kills descendants.
See https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects.
This module is imported only on Windows.
"""

import ctypes as ct
import sys
import time
from ctypes import wintypes as wt

# Lets mypy skip the Win32-only ctypes APIs below when type-checking on Linux (CI).
assert sys.platform == "win32"

SIZE = ct.c_size_t


class BasicLimit(ct.Structure):
    _fields_ = [
        ("process_time", ct.c_int64),
        ("job_time", ct.c_int64),
        ("flags", wt.DWORD),
        ("minimum", SIZE),
        ("maximum", SIZE),
        ("processes", wt.DWORD),
        ("affinity", SIZE),
        ("priority", wt.DWORD),
        ("scheduling", wt.DWORD),
    ]


class IO(ct.Structure):
    _fields_ = [
        (name, ct.c_uint64)
        for name in (
            "read_ops",
            "write_ops",
            "other_ops",
            "read_bytes",
            "write_bytes",
            "other_bytes",
        )
    ]


class ExtendedLimit(ct.Structure):
    _fields_ = [
        ("basic", BasicLimit),
        ("io", IO),
        ("process_memory", SIZE),
        ("job_memory", SIZE),
        ("peak_process", SIZE),
        ("peak_job", SIZE),
    ]


class Accounting(ct.Structure):
    """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION."""

    _fields_ = [
        ("user_time", ct.c_int64),
        ("kernel_time", ct.c_int64),
        ("period_user_time", ct.c_int64),
        ("period_kernel_time", ct.c_int64),
        ("page_faults", wt.DWORD),
        ("total_processes", wt.DWORD),
        ("active_processes", wt.DWORD),
        ("terminated_processes", wt.DWORD),
    ]


class ThreadEntry(ct.Structure):
    _fields_ = [
        ("size", wt.DWORD),
        ("usage", wt.DWORD),
        ("id", wt.DWORD),
        ("owner", wt.DWORD),
        ("priority", wt.LONG),
        ("delta", wt.LONG),
        ("flags", wt.DWORD),
    ]


kernel = ct.WinDLL("kernel32", use_last_error=True)
for name, args, result in (
    ("CreateJobObjectW", [ct.c_void_p, wt.LPCWSTR], wt.HANDLE),
    ("SetInformationJobObject", [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD], wt.BOOL),
    ("AssignProcessToJobObject", [wt.HANDLE, wt.HANDLE], wt.BOOL),
    ("TerminateJobObject", [wt.HANDLE, wt.UINT], wt.BOOL),
    (
        "QueryInformationJobObject",
        [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)],
        wt.BOOL,
    ),
    ("CloseHandle", [wt.HANDLE], wt.BOOL),
    ("CreateToolhelp32Snapshot", [wt.DWORD, wt.DWORD], wt.HANDLE),
    ("Thread32First", [wt.HANDLE, ct.POINTER(ThreadEntry)], wt.BOOL),
    ("Thread32Next", [wt.HANDLE, ct.POINTER(ThreadEntry)], wt.BOOL),
    ("OpenThread", [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
    ("ResumeThread", [wt.HANDLE], wt.DWORD),
    ("SetErrorMode", [wt.UINT], wt.UINT),
):
    function = getattr(kernel, name)
    function.argtypes, function.restype = args, result


def checked(ok):
    if not ok:
        raise ct.WinError(ct.get_last_error())
    return ok


class WindowsJob:
    def __init__(self, memory_bytes: int, pids: int):
        # Inherited by children: runtime faults must not open a Windows dialog
        # and hang a non-interactive worker instead of returning an exit code.
        kernel.SetErrorMode(0x1 | 0x2 | 0x8000)
        self.handle = checked(kernel.CreateJobObjectW(None, None))
        try:
            limits = ExtendedLimit()
            # ACTIVE_PROCESS + PROCESS_MEMORY + JOB_MEMORY + KILL_ON_JOB_CLOSE.
            limits.basic.flags = 0x8 | 0x100 | 0x200 | 0x2000
            limits.basic.processes = pids
            limits.process_memory = memory_bytes
            limits.job_memory = memory_bytes
            checked(
                kernel.SetInformationJobObject(self.handle, 9, ct.byref(limits), ct.sizeof(limits))
            )
        except BaseException:
            self.close()
            raise

    def assign_and_resume(self, process):
        # Popen closes its primary-thread handle. Toolhelp retrieves that one
        # thread while the process is suspended; use documented Win32 APIs.
        checked(kernel.AssignProcessToJobObject(self.handle, int(process._handle)))
        snapshot = kernel.CreateToolhelp32Snapshot(0x4, 0)
        if snapshot == ct.c_void_p(-1).value:
            raise ct.WinError(ct.get_last_error())
        try:
            entry = ThreadEntry(size=ct.sizeof(ThreadEntry))
            found = kernel.Thread32First(snapshot, ct.byref(entry))
            while found:
                if entry.owner == process.pid:
                    thread = checked(kernel.OpenThread(0x2, False, entry.id))
                    try:
                        if kernel.ResumeThread(thread) == 0xFFFFFFFF:
                            raise ct.WinError(ct.get_last_error())
                        return
                    finally:
                        kernel.CloseHandle(thread)
                found = kernel.Thread32Next(snapshot, ct.byref(entry))
            raise OSError("Suspended primary thread not found")
        finally:
            kernel.CloseHandle(snapshot)

    def kill(self, seconds: float = 5):
        """Terminate every process in the job and wait until all of them have exited.

        TerminateJobObject only starts termination. A process that is still exiting keeps its
        working directory open, so deleting the job's temporary directory straight away fails
        with "being used by another process" after a spawn burst.
        """
        checked(kernel.TerminateJobObject(self.handle, 1))
        info = Accounting()
        deadline = time.monotonic() + seconds
        while True:
            # Class 1: JobObjectBasicAccountingInformation.
            checked(
                kernel.QueryInformationJobObject(
                    self.handle, 1, ct.byref(info), ct.sizeof(info), None
                )
            )
            if info.active_processes == 0:
                return
            if time.monotonic() > deadline:
                raise OSError(f"{info.active_processes} job processes did not exit")
            time.sleep(0.01)

    def close(self):
        if self.handle:
            checked(kernel.CloseHandle(self.handle))
            self.handle = None
