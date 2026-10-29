import json
from decimal import Decimal

import pytest

from invoicer.cli import main
from invoicer.discounts import percent_discount
from invoicer.invoice import Invoice
from invoicer.lines import Line
from invoicer.tax import line_tax


def test_gross_is_unit_price_times_quantity():
    line = Line("Pen", Decimal("1.20"), 3, Decimal("0"), Decimal("0.10"))
    assert line.gross() == Decimal("3.60")


def test_zero_discount_leaves_net_equal_to_gross():
    line = Line("Pad", Decimal("4.00"), 2, Decimal("0"), Decimal("0.24"))
    assert line.net() == Decimal("8.00")
    assert line.tax() == Decimal("1.92")
    assert line.total() == Decimal("9.92")


def test_line_tax_rounds_to_cents():
    assert line_tax("3.33", "0.24") == Decimal("0.80")


def test_percent_discount_on_round_amount():
    assert percent_discount("19.99", "10") == Decimal("2.00")


def test_percent_discount_rejects_percent_above_100():
    with pytest.raises(ValueError):
        percent_discount("10.00", "101")


def test_invoice_totals_without_discounts():
    invoice = Invoice(
        [
            Line("Desk", Decimal("120.00"), 1, Decimal("0"), Decimal("0.24")),
            Line("Chair", Decimal("80.50"), 2, Decimal("0"), Decimal("0.24")),
        ]
    )
    assert invoice.subtotal() == Decimal("281.00")
    assert invoice.tax_total() == Decimal("67.44")
    assert invoice.total() == Decimal("348.44")


def test_customer_invoice_is_one_cent_off():
    line = Line("Coffee beans 1 kg", Decimal("2.50"), 1, Decimal("5"), Decimal("0.10"))
    assert line.total() == Decimal("2.61")


def test_cli_prints_invoice_total(tmp_path, capsys):
    path = tmp_path / "lines.json"
    rows = [{"description": "Tea", "unit_price": "3.00", "quantity": 4, "discount_percent": "0", "tax_rate": "0.10"}]
    path.write_text(json.dumps(rows), encoding="utf-8")
    assert main([str(path)]) == 0
    assert capsys.readouterr().out.strip() == "13.20"
