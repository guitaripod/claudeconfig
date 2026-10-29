from .money import round_cents, to_decimal


def line_tax(net, rate):
    """Return the tax on a net line amount at rate (a fraction such as 0.24), rounded to the cent."""
    return round_cents(to_decimal(net) * to_decimal(rate))
