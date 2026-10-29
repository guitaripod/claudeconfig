# toolbox.cronexpr

Parses five-field cron expressions and computes upcoming fire times.

## Public API

- `next_fire_times(expr: str, start: datetime, n: int) -> list[datetime]`

## Expression

Five fields, in order: minute (0-59), hour (0-23), day of month (1-31), month (1-12), day of week (0-7). Fields are separated by one or more spaces or tabs. Leading and trailing whitespace is ignored.

Each field is a comma-separated list of one or more items. An item is one of:

- `*`: the field's full range
- `N`: a single value
- `N-M`: every value from N through M inclusive (N must be less than or equal to M)
- `*/S`: the full range in steps of S
- `N/S`: from N through the field's maximum, in steps of S
- `N-M/S`: from N through M, in steps of S

S is a positive decimal integer no larger than the field's span (maximum minus minimum plus one). Any other step is a ValueError.

Values are decimal integers inside the field's range, with leading zeros allowed. In the month and day-of-week fields, the case-insensitive names `jan` to `dec` and `sun` to `sat` are also accepted wherever a value is accepted, including range endpoints.

Day of week: 0 and 7 both mean Sunday, 1 is Monday, 6 is Saturday. `5-7` means Friday through Sunday. Ranges never wrap: `sat-sun` is a ValueError.

Anything else raises ValueError: a field count other than five, empty items (`1,,2`, a trailing comma), a value outside its field's range, negative numbers, non-digit text, and the extensions `L`, `W`, `#`, `?`, and macros such as `@daily`.

## Day matching

A day-of-month field is restricted when its text does not start with `*`. The day-of-week field is restricted by the same rule. So `*/2` in the day-of-month field is unrestricted.

- If both fields are restricted, a day matches when its day of month is in the day-of-month set OR its day of week is in the day-of-week set.
- Otherwise the day must match both fields.

The month field must always match.

## Fire times

`next_fire_times` returns the first `n` matching times strictly after `start`, in ascending order.

- Each result has seconds and microseconds equal to zero.
- Times are computed on the wall-clock fields of `start`, with no DST adjustment. Each result carries `start.tzinfo`, so a naive `start` gives naive results and an aware `start` gives results with the same tzinfo.
- `n == 0` returns `[]`. A negative `n` is a ValueError. The expression is validated even when `n == 0`.
- If more than 3294 consecutive days pass without a match, the expression is treated as never firing and a ValueError is raised. A result is still returned for an expression such as `0 0 29 2 *` whose next match is eight years away.
