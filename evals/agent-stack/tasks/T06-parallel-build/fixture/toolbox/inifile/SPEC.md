# toolbox.inifile

An INI parser that keeps the source text, so an unchanged document is written back byte for byte.

## Public API

- `parse(text: str) -> Document`
- `dumps(doc: Document) -> str`
- `Document`:
  - `sections() -> list[str]`: section names in document order. The default section `""` comes first when the document has keys before its first header, and is omitted otherwise.
  - `keys(section: str) -> list[str]`: key spellings in document order. KeyError for an unknown section.
  - `get(section: str, key: str, *, raw: bool = False) -> str`: the value. KeyError when the section or key is missing. Interpolation is applied unless `raw` is true.
  - `set(section: str, key: str, value: str) -> None`: see Editing.

Text is split on `\n` only. There is no special handling of `\r`.

## Lines

Each line is classified in this order:

1. **Blank**: only spaces and tabs. Kept as is. It ends any continuation.
2. **Continuation**: starts with a space or tab, is not blank, is not a comment once stripped, and the previous line was an entry or a continuation. Its stripped text is appended to the current value. A continuation is never a comment, even when it is indented.
3. **Comment**: the first non-blank character is `#` or `;`. Kept as is. It ends any continuation.
4. **Section header**: the stripped line starts with `[` and ends with `]`. The name is the text between the brackets, stripped. An empty name is a ValueError. A repeated header (same name, case-sensitive) is a ValueError. Headers end any continuation.
5. **Entry**: anything else. The separator is the first `=` or `:`, whichever comes first. The key is the stripped text before it and must be non-empty. The value is the stripped text after it. A line with no separator is a ValueError. Leading indentation on an entry is ignored when it does not follow an entry, so an indented `key = value` after a header is an ordinary entry.

Entries before any header belong to the default section `""`.

Keys are case-insensitive: `get`, `set` and duplicate detection compare keys case-insensitively, while `keys()` returns the spelling from the file. Section names are case-sensitive. An empty key or a duplicate key within one section (case-insensitive) is a ValueError.

### Values

A value is its inline text followed by its continuation texts, joined with `\n`. Empty inline text is left out of the join, so `key =` followed by the indented lines `a` and `b` gives `a\nb`. A value with no inline text and no continuation is `""`.

A blank line ends the value. An indented line after a blank line is an ordinary entry or an error by the rules above.

## Interpolation

`get` (with `raw=False`) expands references in the returned value:

- `${key}`: the key in the same section as the value that contains the reference. Not the section passed to `get`.
- `${section:key}`: the key in the named section. The section name is the text before the first `:` inside the braces. Text inside the braces is not stripped.
- Expansion is recursive: the referenced value is itself expanded in its own section.
- A reference to a missing section or key raises KeyError.
- A cycle, including a self-reference such as `a = ${a}`, raises ValueError.
- Text that is not a complete reference is left as is. This includes a lone `$`, an unclosed `${`, and an empty `${}`. There is no escape syntax.

`raw=True` returns the stored value unchanged.

## Editing

`set` changes the document and keeps everything else byte for byte.

- The value must be a string. It may be empty. Otherwise each line of the value (split on `\n`) must be non-empty, must equal its own stripped form, and must not start with `#` or `;`. Violations are a ValueError. The key must be non-empty, must not contain `=`, `:` or a newline, must equal its stripped form, and must not start with `#`, `;` or `[`. Violations are a ValueError.
- If the key exists in the section and the stored raw value already equals the new value, nothing changes.
- If the key exists and the value differs, the entry's lines (the key line and its continuation lines) are replaced by `<indent><key spelling in the file> = <first line>`, followed by one line per further value line, each written as four spaces followed by that line. An empty value is written as `<indent><key> =` with no trailing space. `<indent>` is the leading whitespace of the original key line.
- If the key does not exist, it is inserted after the last entry or continuation line of the section, so trailing comments and blank lines of that section stay after it. The new entry is written as `key = value`, with continuation lines as above. If the section has no entries, the key goes directly after its header. The default section with no entries gets the key at the top of the document.
- If the section does not exist, it is appended at the end of the document: one blank line first when the document already has non-blank content at its end, then `[name]`, then the entry lines. A document that ended with a newline still ends with one.

After `set`, `get` returns the new value, interpolated as usual.

`dumps(doc)` returns the document text. For a document that was only parsed, or where every `set` was a no-op, `dumps(parse(text)) == text` for every text that parses.
