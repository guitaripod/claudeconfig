from dataclasses import dataclass
from decimal import Decimal

from .discounts import percent_discount
from .tax import line_tax


@dataclass(frozen=True)
class Line:
    description: str
    unit_price: Decimal
    quantity: int
    discount_percent: Decimal
    tax_rate: Decimal

    def gross(self):
        """Return unit price times quantity."""
        return self.unit_price * self.quantity

    def discount(self):
        """Return the line discount, applied to the gross before tax."""
        return percent_discount(self.gross(), self.discount_percent)

    def net(self):
        """Return the gross minus the discount."""
        return self.gross() - self.discount()

    def tax(self):
        """Return the tax on the net amount."""
        return line_tax(self.net(), self.tax_rate)

    def total(self):
        """Return the net amount plus its tax."""
        return self.net() + self.tax()
