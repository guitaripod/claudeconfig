from __future__ import annotations

from datetime import datetime


def next_fire_times(expr: str, start: datetime, n: int) -> list[datetime]:
    """Return the first n fire times of the cron expression strictly after start.

    See SPEC.md. Raises ValueError for invalid expressions, negative n, or an expression that never fires.
    """
    raise NotImplementedError
