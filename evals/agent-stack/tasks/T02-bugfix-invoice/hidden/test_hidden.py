import json
from decimal import Decimal

from invoicer.cli import main
from invoicer.discounts import percent_discount
from invoicer.invoice import Invoice
from invoicer.lines import Line
from invoicer.tax import line_tax


def test_discount_half_cent_rounds_up():
    assert percent_discount("2.50", "5") == Decimal("0.13")


def test_discount_result_is_exact_decimal():
    result = percent_discount("19.99", "10")
    assert isinstance(result, Decimal)
    assert result == Decimal("2.00")


def test_zero_discount_is_zero():
    assert percent_discount("10.00", "0") == Decimal("0.00")
    line = Line("Mug", Decimal("7.35"), 2, Decimal("0"), Decimal("0.24"))
    assert line.total() == Decimal("18.23")


def test_full_discount_zeroes_the_line():
    assert percent_discount("7.35", "100") == Decimal("7.35")
    line = Line("Gift card", Decimal("7.35"), 1, Decimal("100"), Decimal("0.24"))
    assert line.net() == Decimal("0.00")
    assert line.tax() == Decimal("0.00")
    assert line.total() == Decimal("0.00")


def test_tax_tie_rounds_up():
    assert line_tax("2.45", "0.10") == Decimal("0.25")


def test_tax_small_tie_rounds_up():
    assert line_tax("0.05", "0.50") == Decimal("0.03")


def test_line_discount_half_cent_applies_before_tax():
    line = Line("Tea", Decimal("1.25"), 1, Decimal("10"), Decimal("0.10"))
    assert line.discount() == Decimal("0.13")
    assert line.total() == Decimal("1.23")


def test_discount_and_tax_ties_together():
    line = Line("Beans", Decimal("2.50"), 1, Decimal("5"), Decimal("0.50"))
    assert line.net() == Decimal("2.37")
    assert line.tax() == Decimal("1.19")
    assert line.total() == Decimal("3.56")


def test_many_lines_each_round_tax_half_up():
    invoice = Invoice(
        Line(f"Item {i}", Decimal("0.05"), 1, Decimal("0"), Decimal("0.50")) for i in range(40)
    )
    assert invoice.tax_total() == Decimal("1.20")
    assert invoice.total() == Decimal("3.20")


def test_tax_is_rounded_per_line_not_per_invoice():
    invoice = Invoice(
        Line(f"Pin {i}", Decimal("1.25"), 1, Decimal("0"), Decimal("0.10")) for i in range(3)
    )
    assert invoice.tax_total() == Decimal("0.39")
    assert invoice.total() == Decimal("4.14")


def test_cli_total_with_discount_and_tax_ties(tmp_path, capsys):
    path = tmp_path / "lines.json"
    rows = [
        {
            "description": "Beans",
            "unit_price": "2.50",
            "quantity": 1,
            "discount_percent": "5",
            "tax_rate": "0.50",
        }
    ]
    path.write_text(json.dumps(rows), encoding="utf-8")
    assert main([str(path)]) == 0
    assert capsys.readouterr().out.strip() == "3.56"
