from __future__ import annotations


class Document:
    """A parsed INI document that keeps its source lines. See SPEC.md for the editing and interpolation rules."""

    def sections(self) -> list[str]:
        """Return section names in document order, with the default section "" first when it has entries."""
        raise NotImplementedError

    def keys(self, section: str) -> list[str]:
        """Return the key spellings of a section in document order. Raises KeyError for an unknown section."""
        raise NotImplementedError

    def get(self, section: str, key: str, *, raw: bool = False) -> str:
        """Return a value with `${...}` references expanded, or unchanged when raw is true. Raises KeyError when missing."""
        raise NotImplementedError

    def set(self, section: str, key: str, value: str) -> None:
        """Store a raw value, editing the source lines in place and leaving the rest of the text untouched."""
        raise NotImplementedError


def parse(text: str) -> Document:
    """Parse INI text into a Document. Raises ValueError for malformed lines, duplicates or empty names."""
    raise NotImplementedError


def dumps(doc: Document) -> str:
    """Return the document text, byte for byte the parsed text when nothing was changed."""
    raise NotImplementedError
