# invoicer

Small invoice calculator. Each invoice is a list of lines; `Invoice.total()` is what the customer pays.

## Money rules

- Amounts are `Decimal` and exact to the cent. Never convert money to `float`.
- Unit prices are whole cents, for example `2.50`.
- A line's gross is its unit price times its quantity.
- A line discount is a percentage of the gross, rounded to the cent with `ROUND_HALF_UP`. Line discounts apply before tax.
- Tax is computed per line on the discounted (net) amount, rounded to the cent with `ROUND_HALF_UP`. Tax rates are fractions, for example `0.24`.
- A line's total is its net amount plus its tax. An invoice total is the sum of its line totals, and it is never rounded again.
- Every rounding in the package is `ROUND_HALF_UP`: a half cent always rounds up.

## Usage

    python3 -m invoicer.cli lines.json

`lines.json` is a list of objects with `description`, `unit_price`, `quantity`, `discount_percent` and `tax_rate`. The command prints the invoice total.

## Tests

    python3 -m pytest
