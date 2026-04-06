from __future__ import annotations

import signal
from contextlib import contextmanager
from typing import Iterator


class TimeoutExecutionError(TimeoutError):
    """Raised when a Phase 8.5 benchmark step exceeds its configured timeout."""


@contextmanager
def time_limit(seconds: int | float | None, message: str) -> Iterator[None]:
    if not isinstance(seconds, (int, float)) or float(seconds) <= 0:
        yield
        return

    if not hasattr(signal, "setitimer") or not hasattr(signal, "SIGALRM"):
        yield
        return

    try:
        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)
    except Exception:
        yield
        return

    def _handle_timeout(signum, frame):  # type: ignore[unused-argument]
        raise TimeoutExecutionError(message)

    try:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.setitimer(signal.ITIMER_REAL, float(seconds))
        yield
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            if isinstance(previous_timer, tuple) and previous_timer[0] > 0:
                signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])
        except Exception:
            pass