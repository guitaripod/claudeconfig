from __future__ import annotations

import re
from dataclasses import dataclass

_IDENTIFIER = re.compile(r"[0-9A-Za-z-]+")
_NUMBER = re.compile(r"0|[1-9][0-9]*")
_OPERATORS = ("<=", ">=", "<", ">", "=", "~", "^")
_WILDCARDS = ("x", "X", "*")


@dataclass(frozen=True)
class Version:
    """A parsed full semantic version. See SPEC.md for the field meanings."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: str = ""


_Bound = tuple[str, Version]


def parse(version: str) -> Version:
    """Parse a full semantic version such as `1.2.3-rc.1+build.5`. Raises ValueError when invalid."""
    parts, prerelease, build = _split(version, allow_partial=False)
    return Version(parts[0], parts[1], parts[2], prerelease, build)


def compare(a: str, b: str) -> int:
    """Return -1, 0 or 1 comparing two full versions by semver precedence."""
    return _compare(parse(a), parse(b))


def satisfies(version: str, range: str) -> bool:
    """Return whether the full version satisfies the npm-style range, following SPEC.md."""
    candidate = parse(version)
    for alternative in _alternatives(range):
        if _alternative_matches(candidate, alternative):
            return True
    return False


def _split(text: str, allow_partial: bool) -> tuple[list[int | None], tuple[str, ...], str]:
    """Split a version or partial version into three components, a prerelease tuple and build text."""
    body = text[1:] if text[:1] in ("v", "=") else text
    core, plus, build = body.partition("+")
    core, dash, prerelease_text = core.partition("-")
    if plus and not _identifiers_ok(build, is_build=True):
        raise ValueError(f"invalid build metadata: {text!r}")
    if dash and not _identifiers_ok(prerelease_text, is_build=False):
        raise ValueError(f"invalid prerelease: {text!r}")
    parts = _components(core, text)
    partial = None in parts
    if partial and (dash or plus):
        raise ValueError(f"partial version cannot carry a prerelease or build: {text!r}")
    if partial and not allow_partial:
        raise ValueError(f"expected a full version: {text!r}")
    prerelease = tuple(prerelease_text.split(".")) if dash else ()
    return parts, prerelease, build


def _components(core: str, text: str) -> list[int | None]:
    """Return the three components of core, with None for omitted or wildcard components."""
    pieces = core.split(".")
    if len(pieces) > 3:
        raise ValueError(f"too many version components: {text!r}")
    parts: list[int | None] = []
    wildcard_seen = False
    for piece in pieces:
        if piece in _WILDCARDS:
            wildcard_seen = True
            parts.append(None)
        elif wildcard_seen or _NUMBER.fullmatch(piece) is None:
            raise ValueError(f"invalid version component {piece!r} in {text!r}")
        else:
            parts.append(int(piece))
    return parts + [None] * (3 - len(parts))


def _identifiers_ok(text: str, is_build: bool) -> bool:
    """Return whether text is dot-separated identifiers; numeric prerelease identifiers may not have leading zeros."""
    if not text or any(not _IDENTIFIER.fullmatch(part) for part in text.split(".")):
        return False
    if is_build:
        return True
    return all(_NUMBER.fullmatch(part) or not part.isdigit() for part in text.split("."))


def _compare(left: Version, right: Version) -> int:
    """Return -1, 0 or 1 for the precedence order of two parsed versions."""
    for a, b in ((left.major, right.major), (left.minor, right.minor), (left.patch, right.patch)):
        if a != b:
            return -1 if a < b else 1
    return _compare_prerelease(left.prerelease, right.prerelease)


def _compare_prerelease(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    """Return -1, 0 or 1 for two prerelease tuples, where a release is greater than any prerelease."""
    if left == right:
        return 0
    if not left:
        return 1
    if not right:
        return -1
    for a, b in zip(left, right):
        if a == b:
            continue
        a_numeric, b_numeric = a.isdigit(), b.isdigit()
        if a_numeric and b_numeric:
            return -1 if int(a) < int(b) else 1
        if a_numeric != b_numeric:
            return -1 if a_numeric else 1
        return -1 if a < b else 1
    return -1 if len(left) < len(right) else 1


def _alternatives(range_text: str) -> list[list[_Bound]]:
    """Return the `||` alternatives of a range as lists of bounds; an empty list means any release."""
    text = range_text.strip()
    if not text:
        return [[]]
    alternatives = []
    for alternative in text.split("||"):
        tokens = alternative.split()
        if not tokens:
            raise ValueError(f"empty alternative in range: {range_text!r}")
        alternatives.append(_alternative_bounds(tokens))
    return alternatives


def _alternative_bounds(tokens: list[str]) -> list[_Bound]:
    """Return the bounds of one alternative: a hyphen range, or AND-ed comparators."""
    if "-" in tokens:
        if len(tokens) != 3 or tokens[1] != "-":
            raise ValueError(f"hyphen range must stand alone: {' '.join(tokens)!r}")
        return _hyphen_bounds(tokens[0], tokens[2])
    bounds: list[_Bound] = []
    for comparator in _join_operators(tokens):
        if comparator in _WILDCARDS:
            continue
        bounds.extend(_comparator_bounds(comparator))
    return bounds


def _join_operators(tokens: list[str]) -> list[str]:
    """Join each operator token with the version token that follows it."""
    joined: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _OPERATORS:
            if index + 1 >= len(tokens) or tokens[index + 1] in _OPERATORS:
                raise ValueError(f"operator {token!r} has no version")
            joined.append(token + tokens[index + 1])
            index += 2
        else:
            joined.append(token)
            index += 1
    return joined


def _comparator_bounds(text: str) -> list[_Bound]:
    """Return the bounds for one comparator such as `^1.2.3`, `~1.2`, `>=1.x` or `1.2.3`."""
    operator = next((candidate for candidate in _OPERATORS if text.startswith(candidate)), "")
    parts, prerelease, build = _split(text[len(operator):], allow_partial=True)
    specified = _specified(parts)
    if specified == 0:
        raise ValueError(f"wildcard comparator needs a version: {text!r}")
    full = specified == 3
    version = Version(parts[0] or 0, parts[1] or 0, parts[2] or 0, prerelease, build)
    lower = _lower(parts, version)
    if operator in ("", "="):
        if full:
            return [("=", version)]
        return [(">=", lower), ("<", _bumped(parts, specified - 1, zero_prerelease=True))]
    if operator == "<":
        return [("<", version if full else _with_zero_prerelease(lower))]
    if operator == "<=":
        return [("<=", version)] if full else [("<", _bumped(parts, specified - 1, zero_prerelease=True))]
    if operator == ">":
        return [(">", version)] if full else [(">=", _bumped(parts, specified - 1, zero_prerelease=False))]
    if operator == ">=":
        return [(">=", version if full else lower)]
    if operator == "~":
        index = 0 if specified == 1 else 1
        return [(">=", lower), ("<", _bumped(parts, index, zero_prerelease=True))]
    index = _caret_index(parts, specified)
    return [(">=", lower), ("<", _bumped(parts, index, zero_prerelease=True))]


def _specified(parts: list[int | None]) -> int:
    """Return how many components of parts are given (wildcards and omitted components are not)."""
    return sum(1 for part in parts if part is not None)


def _with_zero_prerelease(version: Version) -> Version:
    """Return version with the `-0` prerelease that excludes its own prereleases from partial ranges."""
    return Version(version.major, version.minor, version.patch, ("0",), version.build)


def _lower(parts: list[int | None], version: Version) -> Version:
    """Return the lowest version a partial or full comparator starts from."""
    return Version(parts[0] or 0, parts[1] or 0, parts[2] or 0, version.prerelease, version.build)


def _caret_index(parts: list[int | None], specified: int) -> int:
    """Return the component a caret range bumps: the first non-zero one, else the last one given."""
    for index in range(specified):
        if parts[index] != 0:
            return index
    return specified - 1


def _bumped(parts: list[int | None], index: int, zero_prerelease: bool) -> Version:
    """Return the version with component index incremented and later components zeroed."""
    values = []
    for position in range(3):
        if position < index:
            values.append(parts[position] or 0)
        elif position == index:
            values.append((parts[position] or 0) + 1)
        else:
            values.append(0)
    prerelease = ("0",) if zero_prerelease else ()
    return Version(values[0], values[1], values[2], prerelease)


def _hyphen_bounds(low_text: str, high_text: str) -> list[_Bound]:
    """Return the bounds of `A - B`, where a partial B becomes an exclusive bound at its next component."""
    low_parts, low_pre, low_build = _split(low_text, allow_partial=True)
    low_specified = _specified(low_parts)
    if low_specified == 0:
        raise ValueError(f"hyphen range needs a lower version: {low_text!r}")
    lower = Version(low_parts[0] or 0, low_parts[1] or 0, low_parts[2] or 0, low_pre, low_build)
    high_parts, high_pre, high_build = _split(high_text, allow_partial=True)
    high_specified = _specified(high_parts)
    if high_specified == 0:
        raise ValueError(f"hyphen range needs an upper version: {high_text!r}")
    if high_specified == 3:
        upper = Version(high_parts[0], high_parts[1], high_parts[2], high_pre, high_build)
        return [(">=", lower), ("<=", upper)]
    return [(">=", lower), ("<", _bumped(high_parts, high_specified - 1, zero_prerelease=True))]


def _alternative_matches(candidate: Version, bounds: list[_Bound]) -> bool:
    """Return whether every bound holds and the prerelease rule passes for candidate."""
    if candidate.prerelease and not any(
        bound.prerelease and (bound.major, bound.minor, bound.patch) == (candidate.major, candidate.minor, candidate.patch)
        for _, bound in bounds
    ):
        return False
    return all(_holds(candidate, operator, bound) for operator, bound in bounds)


def _holds(candidate: Version, operator: str, bound: Version) -> bool:
    """Return whether candidate stands in relation operator to bound."""
    order = _compare(candidate, bound)
    if operator == "=":
        return order == 0
    if operator == "<":
        return order < 0
    if operator == "<=":
        return order <= 0
    if operator == ">":
        return order > 0
    return order >= 0
