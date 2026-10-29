from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_decimal(value):
    """Return value as a Decimal, going through the string form of numbers so no binary float leaks in."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_cents(value):
    """Round an amount to whole cents, half up."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
