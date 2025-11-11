import os
import signal


def kill_process(pid: int) -> bool:
    """Kill a process by PID"""
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return False


def is_process_running(pid: int) -> bool:
    """Check if a process is running"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return False