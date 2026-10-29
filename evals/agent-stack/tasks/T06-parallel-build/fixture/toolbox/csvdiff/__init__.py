from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Change:
    """A matched row whose shared columns differ: key values and column name to (old, new)."""

    key: tuple[str, ...]
    columns: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass
class Diff:
    """The differences between two CSV documents. See SPEC.md for the field meanings."""

    key_columns: tuple[str, ...]
    added: list[dict[str, str]] = field(default_factory=list)
    removed: list[dict[str, str]] = field(default_factory=list)
    changed: list[Change] = field(default_factory=list)
    added_columns: list[str] = field(default_factory=list)
    removed_columns: list[str] = field(default_factory=list)


def diff(old_csv: str, new_csv: str, key: str | list[str]) -> Diff:
    """Compare two CSV documents by key column(s). Raises ValueError for bad keys, duplicate keys or malformed CSV."""
    raise NotImplementedError


def format_diff(diff: Diff) -> str:
    """Return the stable text rendering of a Diff described in SPEC.md."""
    raise NotImplementedError
