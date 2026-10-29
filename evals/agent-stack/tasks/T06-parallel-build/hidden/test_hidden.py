from datetime import datetime, timezone

import pytest

from toolbox.cronexpr import next_fire_times
from toolbox.csvdiff import Change, diff, format_diff
from toolbox.inifile import dumps, parse
from toolbox.semrange import Version, compare, satisfies
from toolbox.semrange import parse as parse_version


def _fires(expr, start, n):
    return [moment.replace(tzinfo=None) for moment in next_fire_times(expr, start, n)]


def test_cronexpr_step_and_star_with_loose_whitespace():
    assert _fires("*/15 * * * *", datetime(2026, 10, 26, 10, 0), 4) == [
        datetime(2026, 10, 26, 10, 15),
        datetime(2026, 10, 26, 10, 30),
        datetime(2026, 10, 26, 10, 45),
        datetime(2026, 10, 26, 11, 0),
    ]
    assert _fires("  */30\t* *  *  * ", datetime(2026, 10, 26, 10, 0), 2) == [
        datetime(2026, 10, 26, 10, 30),
        datetime(2026, 10, 26, 11, 0),
    ]


def test_cronexpr_start_is_exclusive_and_drops_seconds():
    assert _fires("*/15 * * * *", datetime(2026, 10, 26, 10, 15), 1) == [datetime(2026, 10, 26, 10, 30)]
    assert _fires("*/15 * * * *", datetime(2026, 10, 26, 10, 14, 59), 1) == [datetime(2026, 10, 26, 10, 15)]
    assert _fires("*/15 * * * *", datetime(2026, 10, 26, 10, 0, 0, 500), 1) == [datetime(2026, 10, 26, 10, 15)]


def test_cronexpr_lists_ranges_and_step_forms():
    assert _fires("0 9-17/4 * * *", datetime(2026, 10, 26, 8, 0), 4) == [
        datetime(2026, 10, 26, 9, 0),
        datetime(2026, 10, 26, 13, 0),
        datetime(2026, 10, 26, 17, 0),
        datetime(2026, 10, 27, 9, 0),
    ]
    assert _fires("5/20 * * * *", datetime(2026, 10, 26, 8, 0), 4) == [
        datetime(2026, 10, 26, 8, 5),
        datetime(2026, 10, 26, 8, 25),
        datetime(2026, 10, 26, 8, 45),
        datetime(2026, 10, 26, 9, 5),
    ]
    assert _fires("0 6,18 * * *", datetime(2026, 10, 26, 7, 0), 2) == [
        datetime(2026, 10, 26, 18, 0),
        datetime(2026, 10, 27, 6, 0),
    ]


def test_cronexpr_month_and_weekday_names_are_case_insensitive():
    assert _fires("0 12 * jan-mar MON", datetime(2026, 10, 26, 8, 0), 3) == [
        datetime(2027, 1, 4, 12, 0),
        datetime(2027, 1, 11, 12, 0),
        datetime(2027, 1, 18, 12, 0),
    ]
    assert _fires("0 12 1 Mar,DEC *", datetime(2026, 10, 26, 8, 0), 2) == [
        datetime(2026, 12, 1, 12, 0),
        datetime(2027, 3, 1, 12, 0),
    ]


def test_cronexpr_or_semantics_when_both_day_fields_are_restricted():
    assert _fires("0 0 13 * FRI", datetime(2026, 10, 26, 8, 0), 4) == [
        datetime(2026, 10, 30, 0, 0),
        datetime(2026, 11, 6, 0, 0),
        datetime(2026, 11, 13, 0, 0),
        datetime(2026, 11, 20, 0, 0),
    ]


def test_cronexpr_and_semantics_when_one_day_field_is_unrestricted():
    assert _fires("0 0 */2 * FRI", datetime(2026, 10, 26, 8, 0), 4) == [
        datetime(2026, 11, 13, 0, 0),
        datetime(2026, 11, 27, 0, 0),
        datetime(2026, 12, 11, 0, 0),
        datetime(2026, 12, 25, 0, 0),
    ]
    assert _fires("0 0 13 * *", datetime(2026, 10, 26, 8, 0), 2) == [
        datetime(2026, 11, 13, 0, 0),
        datetime(2026, 12, 13, 0, 0),
    ]


def test_cronexpr_sunday_is_zero_or_seven():
    assert _fires("0 0 * * 7", datetime(2026, 10, 26, 8, 0), 2) == [
        datetime(2026, 11, 1, 0, 0),
        datetime(2026, 11, 8, 0, 0),
    ]
    assert _fires("0 0 * * 0", datetime(2026, 10, 26, 8, 0), 2) == _fires("0 0 * * 7", datetime(2026, 10, 26, 8, 0), 2)


def test_cronexpr_weekday_range_and_name_list():
    assert _fires("0 0 * * 5-7", datetime(2026, 10, 26, 8, 0), 4) == [
        datetime(2026, 10, 30, 0, 0),
        datetime(2026, 10, 31, 0, 0),
        datetime(2026, 11, 1, 0, 0),
        datetime(2026, 11, 6, 0, 0),
    ]
    assert _fires("0 0 * * sat,sun", datetime(2026, 10, 26, 8, 0), 3) == [
        datetime(2026, 10, 31, 0, 0),
        datetime(2026, 11, 1, 0, 0),
        datetime(2026, 11, 7, 0, 0),
    ]


def test_cronexpr_leap_day_is_found_eight_years_out():
    assert _fires("0 0 29 2 *", datetime(2096, 3, 1), 1) == [datetime(2104, 2, 29, 0, 0)]
    assert _fires("0 0 29 2 *", datetime(2026, 3, 1), 1) == [datetime(2028, 2, 29, 0, 0)]


def test_cronexpr_year_boundary_is_crossed():
    assert _fires("0 0 1 1 *", datetime(2026, 6, 1), 1) == [datetime(2027, 1, 1, 0, 0)]


def test_cronexpr_never_firing_expression_raises():
    with pytest.raises(ValueError):
        next_fire_times("0 0 31 2 *", datetime(2026, 1, 1), 1)


def test_cronexpr_zero_count_and_negative_count():
    assert next_fire_times("0 0 31 2 *", datetime(2026, 1, 1), 0) == []
    assert next_fire_times("*/5 * * * *", datetime(2026, 1, 1), 0) == []
    with pytest.raises(ValueError):
        next_fire_times("*/5 * * * *", datetime(2026, 1, 1), -1)
    with pytest.raises(ValueError):
        next_fire_times("bogus", datetime(2026, 1, 1), 0)


def test_cronexpr_keeps_start_timezone():
    results = next_fire_times("30 6 * * *", datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 2)
    assert results == [
        datetime(2026, 1, 1, 6, 30, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 6, 30, tzinfo=timezone.utc),
    ]
    assert all(moment.tzinfo is timezone.utc for moment in results)


def test_cronexpr_rejects_malformed_and_unsupported_expressions():
    bad = [
        "* * * *",
        "* * * * * *",
        "",
        "1,,2 * * * *",
        "1, * * * *",
        "a * * * *",
        "-5 * * * *",
        "5- * * * *",
        "@daily",
        "L * * * *",
        "0 0 L * *",
        "0 0 1W * *",
        "0 0 ? * *",
        "0 0 * * 1#2",
        "1-7/0 * * * *",
        "*/x * * * *",
        "* * * jan/13 *",
    ]
    for expr in bad:
        with pytest.raises(ValueError):
            next_fire_times(expr, datetime(2026, 1, 1), 1)


def test_cronexpr_rejects_out_of_range_and_reversed_values():
    bad = ["60 * * * *", "* 24 * * *", "* * 0 * *", "* * 32 * *", "* * * 0 *", "* * * 13 *", "* * * * 8", "5-1 * * * *", "*/0 * * * *", "*/61 * * * *", "0 0 * * sat-sun", "0 25-30 * * *"]
    for expr in bad:
        with pytest.raises(ValueError):
            next_fire_times(expr, datetime(2026, 1, 1), 1)


def test_cronexpr_leading_zeros_and_mixed_lists():
    assert _fires("05,10 08 * * *", datetime(2026, 10, 26, 7, 0), 3) == [
        datetime(2026, 10, 26, 8, 5),
        datetime(2026, 10, 26, 8, 10),
        datetime(2026, 10, 27, 8, 5),
    ]


def test_semrange_parse_splits_prerelease_and_build():
    assert parse_version("1.2.3-rc.1+build.5") == Version(1, 2, 3, ("rc", "1"), "build.5")
    assert parse_version("v2.0.0") == Version(2, 0, 0, (), "")
    assert parse_version("=0.10.11-0") == Version(0, 10, 11, ("0",), "")


def test_semrange_rejects_malformed_versions():
    for text in ["1.2", "1", "01.2.3", "1.2.3-", "1.2.3-01", "a.b.c", "1.2.3-alpha..1", "1.2.3+", "1.2.3.4", "", "1.2.3-b$"]:
        with pytest.raises(ValueError):
            parse_version(text)
    with pytest.raises(ValueError):
        compare("1.2", "1.2.3")
    with pytest.raises(ValueError):
        satisfies("1.2", "*")


def test_semrange_prerelease_precedence_chain():
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
        "1.0.1",
        "1.1.0",
        "2.0.0",
    ]
    for lower, higher in zip(chain, chain[1:]):
        assert compare(lower, higher) == -1
        assert compare(higher, lower) == 1
        assert compare(lower, lower) == 0


def test_semrange_build_metadata_does_not_affect_precedence():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+build.9", "1.0.0") == 0
    assert satisfies("1.0.0+x", "1.0.0") is True
    assert satisfies("1.0.0+x", "=1.0.0+y") is True


def test_semrange_numeric_and_alphanumeric_identifiers():
    assert compare("1.0.0-2", "1.0.0-10") == -1
    assert compare("1.0.0-10", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-alpha.0") == -1
    assert compare("1.0.0-x.7.z.92", "1.0.0-x.7.z.92") == 0
    assert compare("1.0.0-x.7.z.92", "1.0.0-x.7.z.93") == -1


def test_semrange_caret_on_full_versions():
    assert satisfies("1.9.9", "^1.2.3") is True
    assert satisfies("2.0.0", "^1.2.3") is False
    assert satisfies("1.2.2", "^1.2.3") is False
    assert satisfies("0.2.9", "^0.2.3") is True
    assert satisfies("0.3.0", "^0.2.3") is False
    assert satisfies("0.0.3", "^0.0.3") is True
    assert satisfies("0.0.4", "^0.0.3") is False


def test_semrange_caret_on_partial_and_zero_versions():
    assert satisfies("1.9.0", "^1.2") is True
    assert satisfies("2.0.0", "^1.2") is False
    assert satisfies("0.0.9", "^0.0") is True
    assert satisfies("0.1.0", "^0.0") is False
    assert satisfies("0.9.0", "^0.x") is True
    assert satisfies("1.0.0", "^0.x") is False
    assert satisfies("0.5.0", "^0") is True
    assert satisfies("1.0.0", "^0") is False


def test_semrange_tilde_ranges():
    assert satisfies("1.2.9", "~1.2.3") is True
    assert satisfies("1.3.0", "~1.2.3") is False
    assert satisfies("1.2.2", "~1.2.3") is False
    assert satisfies("1.2.0", "~1.2") is True
    assert satisfies("1.3.0", "~1.2") is False
    assert satisfies("1.9.9", "~1") is True
    assert satisfies("2.0.0", "~1") is False


def test_semrange_x_ranges_and_wildcards():
    assert satisfies("1.99.0", "1.x") is True
    assert satisfies("2.0.0", "1.x") is False
    assert satisfies("1.2.5", "1.2.*") is True
    assert satisfies("1.3.0", "1.2.*") is False
    assert satisfies("0.0.1", "*") is True
    assert satisfies("0.0.1", "") is True
    assert satisfies("7.0.0", "X") is True
    assert satisfies("1.0.0", ">=1.x") is True
    assert satisfies("0.9.9", ">=1.x") is False
    assert satisfies("0.9.9", "<1.x") is True
    assert satisfies("1.0.0", "<1.x") is False


def test_semrange_hyphen_ranges_with_partial_upper_bounds():
    assert satisfies("2.3.4", "1.2.3 - 2.3.4") is True
    assert satisfies("2.3.5", "1.2.3 - 2.3.4") is False
    assert satisfies("1.2.2", "1.2.3 - 2.3.4") is False
    assert satisfies("2.3.9", "1.2 - 2.3") is True
    assert satisfies("2.4.0", "1.2 - 2.3") is False
    assert satisfies("1.2.0", "1.2 - 2.3") is True
    assert satisfies("2.9.9", "1 - 2") is True
    assert satisfies("3.0.0", "1 - 2") is False


def test_semrange_comparator_sets_and_alternatives():
    rng = ">=1.2.3 <2.0.0 || >=3.0.0"
    assert satisfies("1.2.3", rng) is True
    assert satisfies("2.5.0", rng) is False
    assert satisfies("3.1.0", rng) is True
    assert satisfies("2.9.9", rng) is False
    assert satisfies("1.9.0", ">= 1.2.3 <2.0.0") is True
    assert satisfies("1.2.5", ">=1.2.3 <1.3") is True
    assert satisfies("1.3.0", ">=1.2.3 <1.3") is False


def test_semrange_prerelease_needs_a_comparator_with_the_same_tuple():
    assert satisfies("1.3.0-beta.2", ">=1.2.3 <2.0.0") is False
    assert satisfies("1.2.3-beta", ">=1.2.3-alpha <2.0.0") is True
    assert satisfies("1.2.4-beta", ">=1.2.3-alpha <2.0.0") is False
    assert satisfies("1.0.0-beta", "*") is False
    assert satisfies("1.0.0", "*") is True


def test_semrange_prerelease_with_caret_tilde_and_exact():
    assert satisfies("1.2.3-beta.2", "^1.2.3-beta.1") is True
    assert satisfies("1.2.4-beta", "^1.2.3") is False
    assert satisfies("1.2.4", "~1.2.3-beta") is True
    assert satisfies("1.2.3-beta.2", "~1.2.3-beta") is True
    assert satisfies("1.2.3-rc", "1.2.3") is False
    assert satisfies("1.2.3+meta", "=1.2.3") is True
    assert satisfies("1.2.4", "=1.2.3") is False


def test_semrange_partial_bounds_exclude_their_own_prereleases():
    assert satisfies("1.2.0-alpha", "<1.2") is False
    assert satisfies("1.1.9", "<1.2") is True
    assert satisfies("1.5.0-rc.1", "1.x") is False
    assert satisfies("1.2.9", "<=1.2") is True
    assert satisfies("1.3.0", "<=1.2") is False
    assert satisfies("1.3.0", ">1.2") is True
    assert satisfies("1.2.9", ">1.2") is False


def test_semrange_rejects_malformed_ranges():
    bad = [
        ">=",
        ">=abc",
        "1.2.3.4",
        "~>1.2.3",
        "!1.0.0",
        "|| 1.0.0",
        "1.0.0 ||",
        "1.0.0 - 2.0.0 3.0.0",
        "1.0.0 - ",
        ">=*",
        "1.x.3",
        "1.2-beta",
        "1.2.3-01",
        "x.x",
    ]
    for text in bad:
        with pytest.raises(ValueError):
            satisfies("1.0.0", text)


def test_inifile_separators_values_and_case_insensitive_keys():
    doc = parse("[server]\nHost: example.org\nport =  8080  \nurl = http://x/?a=b\n")
    assert doc.sections() == ["server"]
    assert doc.get("server", "host") == "example.org"
    assert doc.get("server", "PORT") == "8080"
    assert doc.get("server", "url") == "http://x/?a=b"
    assert doc.keys("server") == ["Host", "port", "url"]


def test_inifile_section_names_are_case_sensitive_and_lookups_raise_keyerror():
    doc = parse("[Server]\nname = upper\n[server]\nname = lower\n")
    assert doc.sections() == ["Server", "server"]
    assert doc.get("Server", "name") == "upper"
    assert doc.get("server", "name") == "lower"
    with pytest.raises(KeyError):
        doc.get("SERVER", "name")
    with pytest.raises(KeyError):
        doc.get("server", "missing")
    with pytest.raises(KeyError):
        doc.keys("nope")


def test_inifile_comments_and_blank_lines_never_become_values():
    doc = parse("# c\n; d\n[s]\na = 1\n  # not part\n  ; nor this\n\nb = 2\n")
    assert doc.get("s", "a") == "1"
    assert doc.get("s", "b") == "2"
    assert doc.keys("s") == ["a", "b"]


def test_inifile_continuation_lines_join_with_newlines():
    doc = parse("[s]\nkey = first\n    second\n\tthird\nempty =\n    only\n    lines\nafter = x\n")
    assert doc.get("s", "key") == "first\nsecond\nthird"
    assert doc.get("s", "empty") == "only\nlines"
    assert doc.get("s", "after") == "x"


def test_inifile_blank_line_ends_a_value():
    doc = parse("[s]\na = 1\n\n  b = 2\n")
    assert doc.get("s", "a") == "1"
    assert doc.get("s", "b") == "2"


def test_inifile_keys_before_any_header_form_the_default_section():
    doc = parse("x = 1\ny: two\n[s]\nz = 3\n")
    assert doc.sections() == ["", "s"]
    assert doc.keys("") == ["x", "y"]
    assert doc.get("", "y") == "two"
    with pytest.raises(KeyError):
        doc.get("s", "x")


def test_inifile_interpolation_uses_the_defining_section():
    doc = parse("[a]\nbase = /srv\npath = ${base}/x\nrun = ${path}\n[b]\nbase = /other\nlocal = ${base}\nremote = ${a:run}\n")
    assert doc.get("a", "path") == "/srv/x"
    assert doc.get("a", "run") == "/srv/x"
    assert doc.get("b", "local") == "/other"
    assert doc.get("b", "remote") == "/srv/x"
    assert doc.get("a", "path", raw=True) == "${base}/x"
    assert doc.get("b", "remote", raw=True) == "${a:run}"


def test_inifile_interpolation_cycles_raise_valueerror():
    with pytest.raises(ValueError):
        parse("a = ${b}\nb = ${a}\n").get("", "a")
    with pytest.raises(ValueError):
        parse("s = ${s}\n").get("", "s")
    with pytest.raises(ValueError):
        parse("[x]\nk = ${y:k}\n[y]\nk = ${x:k}\n").get("x", "k")


def test_inifile_missing_references_and_literal_dollars():
    doc = parse("[a]\nbad = ${missing}\ncost = $5 and ${oops\nempty = ${}\n")
    with pytest.raises(KeyError):
        doc.get("a", "bad")
    assert doc.get("a", "cost") == "$5 and ${oops"
    assert doc.get("a", "empty") == "${}"


def test_inifile_malformed_input_raises_valueerror():
    bad = [
        "novalue\n",
        "[s]\n= v\n",
        "[]\nk = v\n",
        "[s]\nk = 1\nK = 2\n",
        "[s]\n[s]\nk = v\n",
        "[s]\n  = nokey\n",
    ]
    for text in bad:
        with pytest.raises(ValueError):
            parse(text)


def test_inifile_unchanged_document_round_trips_byte_for_byte():
    text = (
        "# title\n\n[a]\nKey: value with spaces  \nkey2 =\n    cont one\n\tcont two\n"
        "url = http://x/?a=b\n; comment\n  indented = yes\n[b]\n\n\nx=${a:key}\n\n   \n# end"
    )
    assert dumps(parse(text)) == text
    assert dumps(parse(dumps(parse(text)))) == text


def test_inifile_set_updates_existing_value_in_place():
    doc = parse("# head\n[server]\nHost: example.org\nport=8080\n; keep\n\n[client]\nname = c\n")
    doc.set("server", "port", "9090")
    doc.set("server", "HOST", "h")
    assert dumps(doc) == "# head\n[server]\nHost = h\nport = 9090\n; keep\n\n[client]\nname = c\n"
    assert doc.get("server", "host") == "h"
    assert doc.keys("server") == ["Host", "port"]


def test_inifile_set_to_the_stored_value_changes_nothing():
    text = "[s]\nport=8080\nmotd =\n    a\n    b\n"
    doc = parse(text)
    doc.set("s", "port", "8080")
    doc.set("s", "motd", "a\nb")
    assert dumps(doc) == text


def test_inifile_set_inserts_new_keys_and_sections_in_place():
    doc = parse("[a]\nx = 1\n; trailing comment\n\n[b]\ny = 2")
    doc.set("a", "z", "3")
    doc.set("c", "k", "v")
    doc.set("", "top", "0")
    assert dumps(doc) == "top = 0\n[a]\nx = 1\nz = 3\n; trailing comment\n\n[b]\ny = 2\n\n[c]\nk = v"
    assert doc.sections() == ["", "a", "b", "c"]


def test_inifile_set_multiline_and_empty_values_round_trip():
    doc = parse("[s]\nmotd = old\n    stale\n\n[t]\nk = ${s:motd}\n")
    doc.set("s", "motd", "line one\nline two")
    assert dumps(doc) == "[s]\nmotd = line one\n    line two\n\n[t]\nk = ${s:motd}\n"
    assert doc.get("t", "k") == "line one\nline two"
    doc.set("s", "motd", "")
    assert dumps(doc) == "[s]\nmotd =\n\n[t]\nk = ${s:motd}\n"
    assert doc.get("s", "motd") == ""


def test_inifile_set_rejects_values_that_would_not_survive_writing():
    doc = parse("[s]\nk = v\n")
    for key in ["", "a=b", "a:b", " x", "#c", "[s", "x\ny"]:
        with pytest.raises(ValueError):
            doc.set("s", key, "v")
    for value in [" lead", "trail ", "a\n\nb", "a\n  b", "a\n# x"]:
        with pytest.raises(ValueError):
            doc.set("s", "k", value)
    assert dumps(doc) == "[s]\nk = v\n"


def test_inifile_colon_and_equals_split_at_the_first_separator():
    doc = parse("url: http://x/?a=b\nq = b:c\n")
    assert doc.get("", "url") == "http://x/?a=b"
    assert doc.get("", "q") == "b:c"


def test_csvdiff_added_removed_and_changed_rows():
    old = "id,name,qty\n1,a,1\n2,b,2\n3,c,3\n"
    new = "id,name,qty\n2,b,5\n3,c,3\n4,d,4\n"
    result = diff(old, new, "id")
    assert result.key_columns == ("id",)
    assert result.added == [{"id": "4", "name": "d", "qty": "4"}]
    assert result.removed == [{"id": "1", "name": "a", "qty": "1"}]
    assert len(result.changed) == 1
    assert result.changed[0].key == ("2",)
    assert result.changed[0].columns == {"qty": ("2", "5")}
    assert result.added_columns == [] and result.removed_columns == []


def test_csvdiff_changed_columns_follow_new_header_order():
    result = diff("id,a,b,c\n1,x,y,z\n", "id,c,a,b\n1,Q,X,y\n", "id")
    assert list(result.changed[0].columns) == ["c", "a"]
    assert result.changed[0].columns == {"c": ("z", "Q"), "a": ("x", "X")}


def test_csvdiff_column_reordering_is_not_a_change():
    result = diff("id,a,b\n1,x,y\n", "b,id,a\ny,1,x\n", "id")
    assert result.changed == []
    assert result.added == [] and result.removed == []
    assert result.added_columns == [] and result.removed_columns == []


def test_csvdiff_added_and_removed_columns_are_reported_apart():
    old = "id,a,gone\n1,x,g\n2,y,h\n"
    new = "id,a,new1,new2\n1,x,p,q\n2,z,r,s\n"
    result = diff(old, new, "id")
    assert result.added_columns == ["new1", "new2"]
    assert result.removed_columns == ["gone"]
    assert result.added == [] and result.removed == []
    assert [(change.key, change.columns) for change in result.changed] == [(("2",), {"a": ("y", "z")})]


def test_csvdiff_quoted_fields_with_commas_quotes_and_newlines():
    old = 'id,text\n1,"a, ""b"""\n2,"line1\nline2"\n'
    new = 'id,text\n1,"a, ""b"""\n2,"line1\nline2!"\n'
    result = diff(old, new, "id")
    assert result.added == [] and result.removed == []
    assert [(change.key, change.columns) for change in result.changed] == [
        (("2",), {"text": ("line1\nline2", "line1\nline2!")})
    ]


def test_csvdiff_bom_is_stripped_and_crlf_is_a_line_break():
    result = diff("﻿id,name\r\n1,a\r\n2,b\r\n", "id,name\n1,a\n2,c\n", "id")
    assert result.changed[0].columns == {"name": ("b", "c")}
    assert len(result.changed) == 1
    assert diff("﻿id,name\r\n1,a\r\n", "id,name\r\n1,a\r\n", "id").changed == []


def test_csvdiff_composite_keys_match_on_every_key_column():
    old = "region,id,v\neu,1,a\nus,1,b\n"
    new = "region,id,v\nus,1,B\neu,2,c\n"
    result = diff(old, new, ["region", "id"])
    assert result.key_columns == ("region", "id")
    assert result.added == [{"region": "eu", "id": "2", "v": "c"}]
    assert result.removed == [{"region": "eu", "id": "1", "v": "a"}]
    assert [(change.key, change.columns) for change in result.changed] == [(("us", "1"), {"v": ("b", "B")})]


def test_csvdiff_comparison_is_exact_for_keys_and_values():
    result = diff("id,v\n1,x y\n", "id,v\n1,x  y\n", "id")
    assert result.changed[0].columns == {"v": ("x y", "x  y")}
    result = diff("id,v\n1,a\n", "id,v\n 1,a\n", "id")
    assert result.added == [{"id": " 1", "v": "a"}]
    assert result.removed == [{"id": "1", "v": "a"}]


def test_csvdiff_duplicate_keys_raise():
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n1,b\n", "id,v\n1,a\n", "id")
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n", "id,v\n2,a\n2,b\n", "id")
    with pytest.raises(ValueError):
        diff("r,id,v\neu,1,a\neu,1,b\n", "r,id,v\n", ["r", "id"])


def test_csvdiff_bad_key_arguments_raise():
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n", "id,v\n1,a\n", "nope")
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n", "v,x\na,1\n", "id")
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n", "id,v\n1,a\n", [])
    with pytest.raises(ValueError):
        diff("id,v\n1,a\n", "id,v\n1,a\n", ["id", "id"])


def test_csvdiff_duplicate_header_names_raise():
    with pytest.raises(ValueError):
        diff("id,id\n1,2\n", "id,id\n1,2\n", "id")
    with pytest.raises(ValueError):
        diff("id,v\n1,2\n", "id,v,v\n1,2,3\n", "id")


def test_csvdiff_ragged_records_raise():
    with pytest.raises(ValueError):
        diff("id,v\n1\n", "id,v\n1,2\n", "id")
    with pytest.raises(ValueError):
        diff("id,v\n1,2\n", "id,v\n1,2,3\n", "id")


def test_csvdiff_blank_lines_and_empty_inputs():
    result = diff("id,v\n\n1,a\n\n", "id,v\r\n1,a\r\n\r\n", "id")
    assert result.changed == [] and result.added == [] and result.removed == []
    with pytest.raises(ValueError):
        diff("", "", "id")
    with pytest.raises(ValueError):
        diff("id,v\n", "", "id")


def test_csvdiff_rows_keep_document_order():
    old = "id,v\n5,a\n3,b\n1,c\n"
    new = "id,v\n1,C\n9,z\n3,B\n7,y\n"
    result = diff(old, new, "id")
    assert [row["id"] for row in result.added] == ["9", "7"]
    assert [row["id"] for row in result.removed] == ["5"]
    assert [change.key for change in result.changed] == [("1",), ("3",)]


def test_csvdiff_format_diff_exact_text():
    old = "id,a,b,gone\n1,x,y,g\n2,p,q,h\n3,m,n,k\n"
    new = "id,a,b,extra\n1,x,Y,e\n2,P,Q,f\n4,r,s,t\n"
    expected = (
        "+ column extra\n"
        "- column gone\n"
        "+ row 4\n"
        "- row 3\n"
        "~ row 1\n"
        "    b: y -> Y\n"
        "~ row 2\n"
        "    a: p -> P\n"
        "    b: q -> Q\n"
        "summary: 1 added, 1 removed, 2 changed, 1 columns added, 1 columns removed\n"
    )
    assert format_diff(diff(old, new, "id")) == expected


def test_csvdiff_format_diff_empty_and_composite_keys():
    empty = "summary: 0 added, 0 removed, 0 changed, 0 columns added, 0 columns removed\n"
    assert format_diff(diff("id,v\n1,a\n", "id,v\n1,a\n", "id")) == empty
    composite = diff("region,id,v\n", "region,id,v\nus,1,x\n", ["region", "id"])
    assert format_diff(composite) == (
        "+ row us|1\nsummary: 1 added, 0 removed, 0 changed, 0 columns added, 0 columns removed\n"
    )
