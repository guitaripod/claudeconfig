from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MAX_QUIET_DAYS = 3294

_FIELD_LABELS = ("minute", "hour", "day of month", "month", "day of week")
_FIELD_BOUNDS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
_MONTH_NAMES = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1
    )
}
_WEEKDAY_NAMES = {name: number for number, name in enumerate(("sun", "mon", "tue", "wed", "thu", "fri", "sat"))}
_FIELD_NAMES = ({}, {}, {}, _MONTH_NAMES, _WEEKDAY_NAMES)
_ITEM = re.compile(r"(\*|[^-/]+(?:-[^-/]+)?)(?:/([^-/]+))?")
_DIGITS = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class _Schedule:
    """The value sets of the five fields and the day-matching mode of one expression."""

    minutes: tuple[int, ...]
    hours: tuple[int, ...]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]
    dom_restricted: bool
    dow_restricted: bool

    def matches_day(self, day: date) -> bool:
        """Return whether day is selected by the month, day-of-month and day-of-week sets."""
        if day.month not in self.months:
            return False
        in_dom = day.day in self.days
        in_dow = (day.weekday() + 1) % 7 in self.weekdays
        if self.dom_restricted and self.dow_restricted:
            return in_dom or in_dow
        return in_dom and in_dow


def next_fire_times(expr: str, start: datetime, n: int) -> list[datetime]:
    """Return the first n fire times of the cron expression strictly after start.

    See SPEC.md. Raises ValueError for invalid expressions, negative n, or an expression that never fires.
    """
    schedule = _parse(expr)
    _check_count(n)
    if n == 0:
        return []
    floor = _first_candidate(start)
    return _scan(schedule, floor, n, start.tzinfo, expr)


def _check_count(n: int) -> None:
    """Raise ValueError when the requested number of fire times is negative."""
    if n < 0:
        raise ValueError(f"n must not be negative: {n}")


def _first_candidate(start: datetime) -> datetime:
    """Return the earliest whole minute strictly after start."""
    return start.replace(second=0, microsecond=0) + timedelta(minutes=1)


def _scan(schedule: _Schedule, floor: datetime, n: int, tzinfo, expr: str) -> list[datetime]:
    """Walk forward day by day from floor, collecting up to n fire times and giving up after a long quiet stretch."""
    results: list[datetime] = []
    day = floor.date()
    quiet_days = 0
    while len(results) < n:
        if quiet_days > MAX_QUIET_DAYS:
            raise ValueError(f"cron expression never fires: {expr!r}")
        matches = _fire_times_on(schedule, day, floor, tzinfo) if schedule.matches_day(day) else []
        if matches:
            quiet_days = 0
            results.extend(matches[: n - len(results)])
        else:
            quiet_days += 1
        day += timedelta(days=1)
    return results


def _parse(expr: str) -> _Schedule:
    """Parse an expression into its schedule, raising ValueError when it is malformed."""
    fields = _split_fields(expr)
    sets = [_parse_field(text, index) for index, text in enumerate(fields)]
    return _Schedule(
        minutes=tuple(sorted(sets[0])),
        hours=tuple(sorted(sets[1])),
        days=sets[2],
        months=sets[3],
        weekdays=sets[4],
        dom_restricted=_restricted(fields[2]),
        dow_restricted=_restricted(fields[4]),
    )


def _restricted(text: str) -> bool:
    """Return whether a day field takes part in OR matching, which holds when its text does not start with `*`."""
    return not text.startswith("*")


def _split_fields(expr: str) -> list[str]:
    """Split an expression into its five whitespace-separated fields, rejecting any other count."""
    if not isinstance(expr, str):
        raise ValueError(f"cron expression must be a string: {expr!r}")
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError(f"expected 5 fields, found {len(fields)}: {expr!r}")
    return fields


def _parse_field(text: str, index: int) -> frozenset[int]:
    """Return the values selected by a comma-separated field, with day-of-week 7 folded onto 0."""
    values: set[int] = set()
    for item in text.split(","):
        values |= _expand_item(item, index)
    if index == 4:
        values = {value % 7 for value in values}
    return frozenset(values)


def _expand_item(item: str, index: int) -> set[int]:
    """Return the values selected by one item such as `*`, `5`, `1-9`, `*/15` or `10/5`."""
    first, last, step = _item_bounds(item, index)
    return set(range(first, last + 1, step))


def _item_bounds(item: str, index: int) -> tuple[int, int, int]:
    """Return the inclusive first and last values and the step of one field item."""
    label = _FIELD_LABELS[index]
    match = _ITEM.fullmatch(item)
    if match is None:
        raise ValueError(f"invalid {label} item: {item!r}")
    head, step_text = match.groups()
    low, high = _FIELD_BOUNDS[index]
    step = 1 if step_text is None else _number(step_text, "step")
    _check_step(step, index, item)
    if head == "*":
        return low, high, step
    if "-" in head:
        return _range_bounds(head, index, item) + (step,)
    first = _bounded(head, index)
    last = high if step_text is not None else first
    return first, last, step


def _range_bounds(head: str, index: int, item: str) -> tuple[int, int]:
    """Return the first and last value of an explicit `N-M` range, rejecting a reversed range."""
    start_text, _, end_text = head.partition("-")
    first = _bounded(start_text, index)
    last = _bounded(end_text, index)
    if first > last:
        raise ValueError(f"reversed range in {_FIELD_LABELS[index]} item: {item!r}")
    return first, last


def _check_step(step: int, index: int, item: str) -> None:
    """Raise ValueError unless step lies between 1 and the span of the field."""
    low, high = _FIELD_BOUNDS[index]
    if not 1 <= step <= high - low + 1:
        raise ValueError(f"step out of range in {_FIELD_LABELS[index]} item: {item!r}")


def _bounded(text: str, index: int) -> int:
    """Return the value of a field token, raising ValueError when it lies outside the field's range."""
    value = _value(text, index)
    low, high = _FIELD_BOUNDS[index]
    if not low <= value <= high:
        raise ValueError(f"{_FIELD_LABELS[index]} out of range: {text!r}")
    return value


def _value(text: str, index: int) -> int:
    """Return the number a token stands for, accepting month and weekday names case-insensitively."""
    names = _FIELD_NAMES[index]
    if text.lower() in names:
        return names[text.lower()]
    return _number(text, _FIELD_LABELS[index])


def _number(text: str, label: str) -> int:
    """Return the value of a plain decimal integer token, raising ValueError for anything else."""
    if _DIGITS.fullmatch(text) is None:
        raise ValueError(f"invalid {label}: {text!r}")
    return int(text)


def _fire_times_on(schedule: _Schedule, day: date, floor: datetime, tzinfo) -> list[datetime]:
    """Return the times of day that the schedule selects and that are not before floor, in order."""
    times: list[datetime] = []
    for hour in schedule.hours:
        for minute in schedule.minutes:
            moment = datetime.combine(day, time(hour, minute), tzinfo=tzinfo)
            if moment >= floor:
                times.append(moment)
    return times
