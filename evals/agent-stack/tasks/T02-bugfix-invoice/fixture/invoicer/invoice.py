from decimal import Decimal

ZERO = Decimal("0.00")


class Invoice:
    def __init__(self, lines=()):
        self.lines = list(lines)

    def add(self, line):
        """Append a line to the invoice."""
        self.lines.append(line)

    def subtotal(self):
        """Return the sum of the line gross amounts."""
        return sum((line.gross() for line in self.lines), ZERO)

    def discount_total(self):
        """Return the sum of the line discounts."""
        return sum((line.discount() for line in self.lines), ZERO)

    def tax_total(self):
        """Return the sum of the line taxes."""
        return sum((line.tax() for line in self.lines), ZERO)

    def total(self):
        """Return the sum of the line totals."""
        return sum((line.total() for line in self.lines), ZERO)
