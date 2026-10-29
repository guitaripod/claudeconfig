"""CLI add and list commands."""

from shelf import cli


def test_add_then_list(tmp_path, capsys):
    """A book added on the command line shows up in list output with all its authors."""
    db = str(tmp_path / "shelf.db")
    cli.main(["--db", db, "add", "--title", "Good Omens", "--author", "Terry Pratchett", "--author", "Neil Gaiman", "--year", "1990"])
    capsys.readouterr()
    cli.main(["--db", db, "list"])
    out = capsys.readouterr().out
    assert "Good Omens" in out
    assert "Terry Pratchett, Neil Gaiman" in out
