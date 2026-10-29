# toolbox.csvdiff

Compares two CSV documents by key column and reports what changed.

## Public API

- `diff(old_csv: str, new_csv: str, key: str | list[str]) -> Diff`
- `format_diff(diff: Diff) -> str`
- `Diff` dataclass with fields, in this order:
  - `key_columns: tuple[str, ...]`: the key column names, in the order given
  - `added: list[dict[str, str]]`: rows present only in the new document, each as a dict of all its columns
  - `removed: list[dict[str, str]]`: rows present only in the old document, each as a dict of all its columns
  - `changed: list[Change]`
  - `added_columns: list[str]`
  - `removed_columns: list[str]`
- `Change` dataclass with fields `key: tuple[str, ...]` (key values in `key_columns` order) and `columns: dict[str, tuple[str, str]]` (column name to `(old, new)`), with columns in new-document header order.

## Reading CSV

- Records follow RFC 4180 as Python's `csv` module reads them with the default (excel) dialect: comma separator, double-quote quoting, `""` for a quote inside a quoted field, commas and line breaks allowed inside quoted fields. Both `\n` and `\r\n` end a record.
- A leading UTF-8 byte order mark (U+FEFF) is removed. It is never part of a header name.
- Records that are completely empty (a blank line) are ignored.
- The first remaining record is the header. Header names and field values are used exactly as read: no trimming, no case folding. `" id"` is a different column from `"id"`.
- Duplicate header names are a ValueError.
- Every other record must have exactly as many fields as the header, else ValueError.
- An input with no records has no columns and no rows.

## Keys

- `key` is a column name or a non-empty list of column names. An empty list, or a repeated name within the list, is a ValueError.
- Every key column must exist in both headers, else ValueError.
- The key of a row is the tuple of its key-column values. Two rows match when their key tuples are equal, compared exactly.
- A key that appears more than once within one document is a ValueError.

## What counts as a change

- Column order does not matter. Columns are matched by name.
- `added_columns` are columns only in the new header, in new-header order. `removed_columns` are columns only in the old header, in old-header order. Neither makes any row changed.
- Among the columns in both headers, excluding the key columns, a row is changed when any value differs exactly. `Change.columns` lists only the differing columns, as `(old, new)` pairs.
- `added` lists new-document rows with no matching key, in new-document order. `removed` lists old-document rows with no matching key, in old-document order. `changed` lists matched rows with at least one differing column, in new-document order.
- Matched rows with identical shared values are not reported.

## format_diff

Returns text made of these lines, in this order, each ending with `\n`:

1. one `+ column NAME` line per added column
2. one `- column NAME` line per removed column
3. one `+ row KEY` line per added row, where KEY is the row's key values joined with `|` in key-column order
4. one `- row KEY` line per removed row
5. for each changed row: a `~ row KEY` line, then one `    COLUMN: OLD -> NEW` line per changed column, in `Change.columns` order
6. always last: `summary: A added, R removed, C changed, AC columns added, RC columns removed`

Values are written as they are, so a value with a newline spans several lines. An empty diff is only the summary line, with all counts zero.
