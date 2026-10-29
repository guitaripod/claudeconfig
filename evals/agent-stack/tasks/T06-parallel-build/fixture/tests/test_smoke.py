from datetime import datetime

import pytest

from toolbox.cronexpr import next_fire_times
from toolbox.csvdiff import diff, format_diff
from toolbox.inifile import dumps, parse
from toolbox.semrange import compare, satisfies


def test_cronexpr_every_fifteen_minutes():
    assert [str(moment) for moment in next_fire_times("*/15 * * * *", datetime(2026, 10, 26, 10, 0), 2)] == [
        "2026-10-26 10:15:00",
        "2026-10-26 10:30:00",
    ]


def test_cronexpr_rejects_bad_field_count():
    with pytest.raises(ValueError):
        next_fire_times("* * * *", datetime(2026, 1, 1), 1)


def test_semrange_orders_prereleases_before_release():
    assert compare("1.0.0-rc.1", "1.0.0") == -1


def test_semrange_caret_range():
    assert satisfies("1.4.0", "^1.2.3") is True
    assert satisfies("2.0.0", "^1.2.3") is False


def test_inifile_unchanged_document_round_trips():
    text = "[a]\nk = v\n"
    assert dumps(parse(text)) == text


def test_inifile_get_is_case_insensitive_for_keys():
    assert parse("[a]\nK: 1\n").get("a", "k") == "1"


def test_csvdiff_reports_changed_column_pair():
    result = diff("id,v\n1,a\n", "id,v\n1,b\n", "id")
    assert result.changed[0].columns == {"v": ("a", "b")}


def test_csvdiff_summary_line_ends_the_report():
    assert format_diff(diff("id\n", "id\n", "id")).endswith("0 columns removed\n")
