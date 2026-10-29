from decimal import ROUND_HALF_EVEN

from .money import CENT, to_decimal


def line_tax(net, rate):
    """Return the tax on a net line amount at rate (a fraction such as 0.24), rounded to the cent."""
    return (to_decimal(net) * to_decimal(rate)).quantize(CENT, rounding=ROUND_HALF_EVEN)
