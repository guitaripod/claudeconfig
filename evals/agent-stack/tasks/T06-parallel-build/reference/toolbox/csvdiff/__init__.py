from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

_BOM = "﻿"


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


@dataclass
class _Table:
    """A parsed CSV document: its header and its rows, each row as a dict keyed by header name."""

    header: list[str]
    rows: list[dict[str, str]]


def diff(old_csv: str, new_csv: str, key: str | list[str]) -> Diff:
    """Compare two CSV documents by key column(s). Raises ValueError for bad keys, duplicate keys or malformed CSV."""
    key_columns = _key_columns(key)
    old = _read(old_csv, "old")
    new = _read(new_csv, "new")
    _require_key(old, key_columns, "old")
    _require_key(new, key_columns, "new")
    old_rows = _index(old, key_columns, "old")
    new_rows = _index(new, key_columns, "new")
    shared = [column for column in new.header if column in old.header and column not in key_columns]
    return Diff(
        key_columns=key_columns,
        added=_only_in(new_rows, old_rows),
        removed=_only_in(old_rows, new_rows),
        changed=_changed(old_rows, new_rows, shared),
        added_columns=_difference(new.header, old.header),
        removed_columns=_difference(old.header, new.header),
    )


def _require_key(table: _Table, key_columns: tuple[str, ...], label: str) -> None:
    """Raise ValueError unless every key column is in the header of table."""
    for column in key_columns:
        if column not in table.header:
            raise ValueError(f"key column {column!r} is missing from the {label} header")


def _difference(names: list[str], others: list[str]) -> list[str]:
    """Return the names that do not appear in others, in their original order."""
    return [name for name in names if name not in others]


def _only_in(
    rows: dict[tuple[str, ...], dict[str, str]], others: dict[tuple[str, ...], dict[str, str]]
) -> list[dict[str, str]]:
    """Return the rows whose key is absent from others, in order."""
    return [row for key_values, row in rows.items() if key_values not in others]


def _changed(
    old_rows: dict[tuple[str, ...], dict[str, str]], new_rows: dict[tuple[str, ...], dict[str, str]], shared: list[str]
) -> list[Change]:
    """Return a Change for every key present in both documents whose shared columns differ."""
    changes = []
    for key_values, new_row in new_rows.items():
        if key_values in old_rows:
            change = _compare_row(key_values, old_rows[key_values], new_row, shared)
            if change is not None:
                changes.append(change)
    return changes


def format_diff(diff: Diff) -> str:
    """Return the stable text rendering of a Diff described in SPEC.md."""
    lines = _column_lines(diff.added_columns, "+")
    lines += _column_lines(diff.removed_columns, "-")
    lines += _row_lines("+", diff.added, diff.key_columns)
    lines += _row_lines("-", diff.removed, diff.key_columns)
    for change in diff.changed:
        lines += _change_lines(change)
    lines.append(_summary_line(diff))
    return "\n".join(lines) + "\n"


def _column_lines(columns: list[str], sign: str) -> list[str]:
    """Return one `sign column NAME` line per column."""
    return [f"{sign} column {column}" for column in columns]


def _row_lines(sign: str, rows: list[dict[str, str]], key_columns: tuple[str, ...]) -> list[str]:
    """Return one `sign row KEY` line per added or removed row."""
    return [f"{sign} row {_key_text(key_columns, row)}" for row in rows]


def _change_lines(change: Change) -> list[str]:
    """Return the `~ row` header line of a change followed by one indented line per changed column."""
    lines = [f"~ row {'|'.join(change.key)}"]
    lines += [f"    {column}: {old} -> {new}" for column, (old, new) in change.columns.items()]
    return lines


def _summary_line(diff: Diff) -> str:
    """Return the closing summary line with every count."""
    return (
        f"summary: {len(diff.added)} added, {len(diff.removed)} removed, {len(diff.changed)} changed, "
        f"{len(diff.added_columns)} columns added, {len(diff.removed_columns)} columns removed"
    )


def _key_columns(key: str | list[str]) -> tuple[str, ...]:
    """Return the key column names as a tuple, rejecting an empty or repeated list."""
    columns = (key,) if isinstance(key, str) else tuple(key)
    if not columns:
        raise ValueError("at least one key column is required")
    if len(set(columns)) != len(columns):
        raise ValueError(f"repeated key column in {list(columns)!r}")
    return columns


def _read(text: str, label: str) -> _Table:
    """Parse one CSV document, skipping blank records and enforcing a unique header and rectangular rows."""
    records = _records(text, label)
    if not records:
        return _Table([], [])
    header = records[0]
    _check_header(header, label)
    rows = []
    for number, record in enumerate(records[1:], start=2):
        if len(record) != len(header):
            raise ValueError(f"record {number} of the {label} document has {len(record)} fields, expected {len(header)}")
        rows.append(dict(zip(header, record)))
    return _Table(header, rows)


def _records(text: str, label: str) -> list[list[str]]:
    """Return the non-blank CSV records of text, without its byte order mark."""
    if text.startswith(_BOM):
        text = text[len(_BOM):]
    try:
        return [record for record in csv.reader(io.StringIO(text, newline="")) if record]
    except csv.Error as exc:
        raise ValueError(f"malformed CSV in {label} document: {exc}") from exc


def _check_header(header: list[str], label: str) -> None:
    """Raise ValueError when a header names the same column twice."""
    if len(set(header)) != len(header):
        raise ValueError(f"duplicate column name in {label} header: {header!r}")


def _index(table: _Table, key_columns: tuple[str, ...], label: str) -> dict[tuple[str, ...], dict[str, str]]:
    """Map each key tuple of table to its row, rejecting a key that occurs twice."""
    index: dict[tuple[str, ...], dict[str, str]] = {}
    for row in table.rows:
        key_values = _key_of(row, key_columns)
        if key_values in index:
            raise ValueError(f"duplicate key {key_values!r} in the {label} document")
        index[key_values] = row
    return index


def _unchanged(old_row: dict[str, str], new_row: dict[str, str], shared: list[str]) -> bool:
    """Return whether every shared column holds the same value in both rows."""
    return all(old_row[column] == new_row[column] for column in shared)


def _compare_row(
    key_values: tuple[str, ...], old_row: dict[str, str], new_row: dict[str, str], shared: list[str]
) -> Change | None:
    """Return the Change for a matched row, or None when no shared column differs."""
    if _unchanged(old_row, new_row, shared):
        return None
    columns = {column: (old_row[column], new_row[column]) for column in shared if old_row[column] != new_row[column]}
    return Change(key_values, columns)


def _key_of(row: dict[str, str], key_columns: tuple[str, ...]) -> tuple[str, ...]:
    """Return the tuple of key values of row, in key-column order."""
    return tuple(row[column] for column in key_columns)


def _key_text(key_columns: tuple[str, ...], row: dict[str, str]) -> str:
    """Return the key values of row joined with `|` in key-column order."""
    return "|".join(_key_of(row, key_columns))
