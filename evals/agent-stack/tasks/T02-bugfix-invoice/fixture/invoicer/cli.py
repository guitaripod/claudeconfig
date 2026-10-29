import argparse
import json
import sys
from decimal import Decimal

from .invoice import Invoice
from .lines import Line


def load_invoice(path):
    """Read a JSON list of line objects from path and return the Invoice they make up."""
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    return Invoice(
        Line(
            description=row["description"],
            unit_price=Decimal(row["unit_price"]),
            quantity=int(row["quantity"]),
            discount_percent=Decimal(row.get("discount_percent", "0")),
            tax_rate=Decimal(row.get("tax_rate", "0")),
        )
        for row in rows
    )


def main(argv=None):
    """Print the total of the invoice in the JSON file named in argv."""
    parser = argparse.ArgumentParser(prog="invoicer")
    parser.add_argument("lines", help="JSON file with a list of invoice lines")
    args = parser.parse_args(argv)
    print(load_invoice(args.lines).total())
    return 0


if __name__ == "__main__":
    sys.exit(main())
