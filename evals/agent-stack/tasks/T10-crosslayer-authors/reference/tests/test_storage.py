"""Repository round trips, updates and reopen behaviour."""

from shelf.models import Book
from shelf.storage import Repository


def test_add_and_get_round_trip(tmp_path):
    """An added book reads back with its id, authors and tags."""
    repo = Repository(str(tmp_path / "shelf.db"))
    try:
        added = repo.add(Book(id=None, title="Dune", authors=["Frank Herbert"], year=1965, tags=["scifi"]))
        assert added.id is not None
        assert repo.get(added.id) == added
    finally:
        repo.close()


def test_update_missing_book_returns_none(tmp_path):
    """Updating an id that does not exist reports None instead of inserting."""
    repo = Repository(str(tmp_path / "shelf.db"))
    try:
        assert repo.update(Book(id=999, title="Ghost", authors=["Nobody"], year=2000)) is None
    finally:
        repo.close()


def test_find_by_author_ignores_case(tmp_path):
    """Author lookup matches any author regardless of letter case."""
    repo = Repository(str(tmp_path / "shelf.db"))
    try:
        repo.add(Book(id=None, title="Good Omens", authors=["Terry Pratchett", "Neil Gaiman"], year=1990))
        repo.add(Book(id=None, title="Emma", authors=["Jane Austen"], year=1815))
        assert [book.title for book in repo.find_by_author("neil gaiman")] == ["Good Omens"]
    finally:
        repo.close()


def test_reopen_keeps_rows(tmp_path):
    """Closing and reopening the file keeps stored books without duplicating them."""
    path = str(tmp_path / "shelf.db")
    repo = Repository(path)
    repo.add(Book(id=None, title="Dune", authors=["Frank Herbert"], year=1965))
    repo.close()
    reopened = Repository(path)
    try:
        assert len(reopened.list_books()) == 1
    finally:
        reopened.close()
