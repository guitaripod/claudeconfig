# toolbox.semrange

npm-style semantic versions: parsing, precedence, and range matching.

## Public API

- `parse(version: str) -> Version`
- `compare(a: str, b: str) -> int`: -1, 0 or 1
- `satisfies(version: str, range: str) -> bool`
- `Version`: frozen dataclass with `major: int`, `minor: int`, `patch: int`, `prerelease: tuple[str, ...]` (empty for a release, identifiers as written), `build: str` (metadata as written, empty if none)

## Versions

`[v|=]MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`

- An optional leading `v` or `=` is ignored.
- Numbers are decimal without leading zeros (`0` is fine, `01` is not).
- PRERELEASE is dot-separated identifiers made of `[0-9A-Za-z-]`. Each identifier is non-empty. An all-digit identifier has no leading zero.
- BUILD is dot-separated identifiers of the same character set. Leading zeros are allowed in build metadata.
- Anything else, including a partial version such as `1.2`, raises ValueError from `parse` and `compare`.

Precedence, used by `compare`:

1. Compare MAJOR, then MINOR, then PATCH as integers.
2. A version with no prerelease is greater than the same version with one: `1.0.0 > 1.0.0-rc.1`.
3. Prerelease identifiers are compared left to right. Two all-digit identifiers compare as integers. An all-digit identifier is lower than a non-numeric one. Non-numeric identifiers compare as ASCII strings. If all shared identifiers are equal, the longer list is greater.
4. BUILD is ignored for precedence. `1.0.0+a` and `1.0.0+b` compare equal.

The chain `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0` is strictly increasing.

## Ranges

A range is one or more alternatives separated by `||`. An alternative is a set of comparators separated by whitespace, all of which must hold (AND). An alternative is either a comparator set or a single hyphen range.

Whole-range rules:

- An empty or whitespace-only range matches any release. A bare `*`, `x` or `X` (no operator) also matches any release. It is a comparator with no bound.
- An empty alternative (for example `|| 1.0.0` or `1.0.0 ||`) raises ValueError.
- Any unparseable piece, such as `>=`, `>=abc`, `1.2.3.4`, `~>1.2.3` or `!1.0.0`, raises ValueError.

Operators: `<`, `<=`, `>`, `>=`, `=`, `~`, `^`, or none. An operator may be followed by whitespace before its version: `>= 1.2.3` is one comparator. An operator with no version, or a bare wildcard after an operator (`>=*`), raises ValueError.

### Partial versions

A version in a comparator may be partial. `1`, `1.2`, `1.x`, `1.2.x`, `1.*.*` and `1.X` are partial. Once a component is a wildcard (`x`, `X` or `*`), every later component must also be a wildcard, so `1.x.3` is invalid. A partial version may not carry a prerelease or build (`1.2-beta` is invalid). Wildcards are the same as omitted components.

For a partial version with s specified components, the bound "lower" is the version with missing components set to 0. The bound "next at index i" bumps component i by one and sets later components to 0, with a `-0` prerelease when stated.

### Comparator meaning

| Comparator | Meaning |
| --- | --- |
| `1.2.3`, `=1.2.3` | exactly 1.2.3 (BUILD ignored) |
| `1`, `1.x`, `1.2`, `1.2.x`, `=1.2` | `>=lower` and `<next at last specified index` with a `-0` prerelease: `1` is `>=1.0.0 <2.0.0-0`, `1.2` is `>=1.2.0 <1.3.0-0` |
| `<1.2.3`, `<=1.2.3`, `>1.2.3`, `>=1.2.3` | ordinary comparisons with that version |
| `<1.2` | `<1.2.0-0` |
| `<=1.2` | `<1.3.0-0`; `<=1` is `<2.0.0-0` |
| `>1.2` | `>=1.3.0`; `>1` is `>=2.0.0` |
| `>=1.2` | `>=1.2.0`; `>=1` is `>=1.0.0` |
| `~1.2.3` | `>=1.2.3 <1.3.0-0` |
| `~1.2`, `~1.2.x` | `>=1.2.0 <1.3.0-0` |
| `~1`, `~1.x` | `>=1.0.0 <2.0.0-0` |
| `^1.2.3` | `>=1.2.3 <2.0.0-0` |
| `^0.2.3` | `>=0.2.3 <0.3.0-0` |
| `^0.0.3` | `>=0.0.3 <0.0.4-0` |
| `^0.0.0` | `>=0.0.0 <0.0.1-0` |
| `^0.0`, `^0.0.x` | `>=0.0.0 <0.1.0-0` |
| `^0`, `^0.x`, `^0.x.x` | `>=0.0.0 <1.0.0-0` |
| `^1.x`, `^1.2` | `>=1.0.0 <2.0.0-0`, `>=1.2.0 <2.0.0-0` |

For caret, the bumped component is the first specified component that is non-zero, or the last specified component when all specified components are zero. `^1.2.3-beta.2` is `>=1.2.3-beta.2 <2.0.0-0`.

For tilde, the bumped component is the major when only the major is specified, and the minor otherwise.

### Hyphen ranges

`A - B` with whitespace around the hyphen is an alternative on its own. It may not be combined with other comparators in the same alternative, so `1.0.0 - 2.0.0 3.0.0` is ValueError. `A` and `B` are versions that may be partial.

- The lower bound is `>=` the lower form of A.
- If B is a full version, the upper bound is `<=B`.
- If B is partial, the upper bound is `<` the next version at its last specified index, with a `-0` prerelease. `1.2 - 2.3` is `>=1.2.0 <2.4.0-0`. `1.2.3 - 2` is `>=1.2.3 <3.0.0-0`.

## Matching

`satisfies(version, range)` is true when some alternative matches. An alternative matches when:

- every comparator in it holds for `version`, using `compare`, and
- prerelease rule: if `version` has a prerelease, the alternative must contain at least one comparator whose version has a prerelease and the same major, minor and patch as `version`. Otherwise the alternative does not match.

Consequences: `satisfies("1.3.0-beta.2", ">=1.2.3 <2.0.0")` is false. `satisfies("1.2.3-beta", ">=1.2.3-alpha <2.0.0")` is true. `satisfies("1.0.0-beta", "*")` is false, while `satisfies("1.0.0", "*")` is true. `satisfies("1.2.0-alpha", "<1.2")` is false.

`version` must be a full version, otherwise ValueError.
