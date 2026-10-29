from decimal import Decimal

from .money import round_cents, to_decimal

HUNDRED = Decimal("100")


def percent_discount(amount, percent):
    """Return the discount for amount at percent (0 to 100), rounded to the cent."""
    percent = to_decimal(percent)
    if not Decimal("0") <= percent <= HUNDRED:
        raise ValueError("discount percent must be between 0 and 100")
    return round_cents(to_decimal(amount) * percent / HUNDRED)
