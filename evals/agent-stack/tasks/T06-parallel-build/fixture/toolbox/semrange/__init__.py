from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Version:
    """A parsed full semantic version. See SPEC.md for the field meanings."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: str = ""


def parse(version: str) -> Version:
    """Parse a full semantic version such as `1.2.3-rc.1+build.5`. Raises ValueError when invalid."""
    raise NotImplementedError


def compare(a: str, b: str) -> int:
    """Return -1, 0 or 1 comparing two full versions by semver precedence."""
    raise NotImplementedError


def satisfies(version: str, range: str) -> bool:
    """Return whether the full version satisfies the npm-style range, following SPEC.md."""
    raise NotImplementedError
