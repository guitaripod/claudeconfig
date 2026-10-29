"""CLI add and list commands."""

from shelf import cli


def test_add_then_list(tmp_path, capsys):
    """A book added on the command line shows up in list output."""
    db = str(tmp_path / "shelf.db")
    cli.main(["--db", db, "add", "--title", "Dune", "--author", "Frank Herbert", "--year", "1965"])
    capsys.readouterr()
    cli.main(["--db", db, "list"])
    out = capsys.readouterr().out
    assert "Dune" in out
    assert "Frank Herbert" in out
