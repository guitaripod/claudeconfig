from __future__ import annotations

import re
from dataclasses import dataclass, field

_REFERENCE = re.compile(r"\$\{([^${}]+)\}")


@dataclass
class _Entry:
    """One key with its value parts and the source line range it occupies."""

    key: str
    indent: str
    first: int
    last: int
    parts: list[str]

    @property
    def value(self) -> str:
        """Return the raw value: inline text and continuation texts joined by newlines."""
        return "\n".join(self.parts)


@dataclass
class _Section:
    """One section: its header line, the last line it occupies and its entries by lowercased key."""

    name: str
    header: int | None
    last: int
    entries: dict[str, _Entry] = field(default_factory=dict)


class Document:
    """A parsed INI document that keeps its source lines. See SPEC.md for the editing and interpolation rules."""

    def __init__(self, lines: list[str]) -> None:
        """Index the given source lines, raising ValueError when they are malformed."""
        self._lines = list(lines)
        self._index()

    def sections(self) -> list[str]:
        """Return section names in document order, with the default section "" first when it has entries."""
        return list(self._sections)

    def keys(self, section: str) -> list[str]:
        """Return the key spellings of a section in document order. Raises KeyError for an unknown section."""
        return [entry.key for entry in self._section(section).entries.values()]

    def get(self, section: str, key: str, *, raw: bool = False) -> str:
        """Return a value with `${...}` references expanded, or unchanged when raw is true. Raises KeyError when missing."""
        entry = self._entry(section, key)
        if raw:
            return entry.value
        return self._expand(entry.value, section, frozenset({(section, key.lower())}))

    def set(self, section: str, key: str, value: str) -> None:
        """Store a raw value, editing the source lines in place and leaving the rest of the text untouched."""
        _check_key(key)
        _check_value(value)
        existing = self._sections.get(section)
        entry = existing.entries.get(key.lower()) if existing is not None else None
        if entry is not None:
            if entry.value == value:
                return
            self._lines[entry.first : entry.last + 1] = _render_entry(entry.indent, entry.key, value)
        else:
            self._insert(section, key, value, existing)
        self._index()

    def text(self) -> str:
        """Return the source text of the document as it currently stands."""
        return "\n".join(self._lines)

    def _index(self) -> None:
        """Rebuild the section and entry tables from the source lines, validating every line."""
        self._sections: dict[str, _Section] = {}
        current: _Section | None = None
        previous: _Entry | None = None
        for index, line in enumerate(self._lines):
            stripped = line.strip()
            if not stripped:
                previous = None
                continue
            if line[0] in " \t" and previous is not None and stripped[0] not in "#;":
                previous.parts.append(stripped)
                previous.last = index
                current.last = index
                continue
            previous = None
            if stripped[0] in "#;":
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                current = self._header(stripped[1:-1].strip(), index)
                continue
            if current is None:
                current = self._add_section("", None)
            previous = self._entry_from_line(line, stripped, index, current)
            current.last = index

    def _header(self, name: str, index: int) -> _Section:
        """Register a section header, rejecting an empty or repeated name."""
        if not name:
            raise ValueError(f"empty section name on line {index + 1}")
        if name in self._sections:
            raise ValueError(f"duplicate section [{name}] on line {index + 1}")
        return self._add_section(name, index)

    def _add_section(self, name: str, header: int | None) -> _Section:
        """Create and register a section whose last line is its header, or -1 for the default section."""
        section = _Section(name, header, -1 if header is None else header)
        self._sections[name] = section
        return section

    def _entry_from_line(self, line: str, stripped: str, index: int, section: _Section) -> _Entry:
        """Parse a `key = value` or `key: value` line, registering it in section."""
        cuts = [position for position in (stripped.find("="), stripped.find(":")) if position >= 0]
        if not cuts:
            raise ValueError(f"line {index + 1} is neither a header nor an entry: {line!r}")
        cut = min(cuts)
        key = stripped[:cut].strip()
        if not key:
            raise ValueError(f"empty key on line {index + 1}")
        if key.lower() in section.entries:
            raise ValueError(f"duplicate key {key!r} in section [{section.name}] on line {index + 1}")
        value = stripped[cut + 1 :].strip()
        indent = line[: len(line) - len(line.lstrip())]
        entry = _Entry(key, indent, index, index, [value] if value else [])
        section.entries[key.lower()] = entry
        return entry

    def _section(self, name: str) -> _Section:
        """Return the named section, raising KeyError when it does not exist."""
        if name not in self._sections:
            raise KeyError(f"no section [{name}]")
        return self._sections[name]

    def _entry(self, section: str, key: str) -> _Entry:
        """Return the entry for key in section, raising KeyError when either is missing."""
        entries = self._section(section).entries
        if key.lower() not in entries:
            raise KeyError(f"no key {key!r} in section [{section}]")
        return entries[key.lower()]

    def _expand(self, text: str, section: str, active: frozenset[tuple[str, str]]) -> str:
        """Expand every `${...}` reference in text, which belongs to section and is resolving the keys in active."""

        def substitute(match: re.Match[str]) -> str:
            """Return the expanded value a single reference points at."""
            reference = match.group(1)
            if ":" in reference:
                target_section, name = reference.split(":", 1)
            else:
                target_section, name = section, reference
            target = self._entry(target_section, name)
            marker = (target_section, name.lower())
            if marker in active:
                raise ValueError(f"interpolation cycle through ${{{reference}}}")
            return self._expand(target.value, target_section, active | {marker})

        return _REFERENCE.sub(substitute, text)

    def _insert(self, section: str, key: str, value: str, existing: _Section | None) -> None:
        """Insert a new entry into an existing section, or create the section at the right place."""
        lines = _render_entry("", key, value)
        if existing is not None:
            position = existing.last + 1
            self._lines[position:position] = lines
        elif section == "":
            self._lines[0:0] = lines
        else:
            self._append_section(section, lines)

    def _append_section(self, name: str, entry_lines: list[str]) -> None:
        """Append a new section header and its entry lines, keeping the text's final newline if it had one."""
        trailing_newline = self._lines[-1] == ""
        body = self._lines[:-1] if trailing_newline else list(self._lines)
        if body and body[-1].strip():
            body.append("")
        body.append(f"[{name}]")
        body.extend(entry_lines)
        self._lines = body + [""] if trailing_newline else body


def _render_entry(indent: str, key: str, value: str) -> list[str]:
    """Return the source lines of one entry, with continuation lines indented by four spaces."""
    if value == "":
        return [f"{indent}{key} ="]
    first, *rest = value.split("\n")
    return [f"{indent}{key} = {first}"] + [f"    {line}" for line in rest]


def _check_key(key: str) -> None:
    """Raise ValueError unless key can be written as an entry name without changing its meaning."""
    if not key or key != key.strip() or any(character in key for character in "=:\n") or key[0] in "#;[":
        raise ValueError(f"invalid key: {key!r}")


def _check_value(value: str) -> None:
    """Raise ValueError unless every line of value survives writing and re-parsing unchanged."""
    if not isinstance(value, str):
        raise ValueError(f"value must be a string: {value!r}")
    if value == "":
        return
    for line in value.split("\n"):
        if not line or line != line.strip() or line[0] in "#;":
            raise ValueError(f"value line cannot be written unchanged: {line!r}")


def parse(text: str) -> Document:
    """Parse INI text into a Document. Raises ValueError for malformed lines, duplicates or empty names."""
    return Document(text.split("\n"))


def dumps(doc: Document) -> str:
    """Return the document text, byte for byte the parsed text when nothing was changed."""
    return doc.text()
