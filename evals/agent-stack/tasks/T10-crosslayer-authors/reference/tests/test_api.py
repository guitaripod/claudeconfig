"""Request router behaviour for /books."""

import pytest

from shelf.api import Api
from shelf.storage import Repository


@pytest.fixture
def api(tmp_path):
    """Return a router over a fresh database."""
    repo = Repository(str(tmp_path / "shelf.db"))
    yield Api(repo)
    repo.close()


def create(api, **fields):
    """POST a book and return its response body."""
    status, body = api.handle("POST", "/books", {}, fields)
    assert status == 201
    return body


def test_create_and_get(api):
    """A created book is returned by id."""
    book = create(api, title="Dune", authors=["Frank Herbert"], year=1965)
    status, body = api.handle("GET", f"/books/{book['id']}", {}, None)
    assert status == 200
    assert body["title"] == "Dune"


def test_list_filters_by_any_author(api):
    """The author query parameter matches any author, ignoring case."""
    create(api, title="Dune", authors=["Frank Herbert"], year=1965)
    create(api, title="Good Omens", authors=["Terry Pratchett", "Neil Gaiman"], year=1990)
    status, body = api.handle("GET", "/books", {"author": "neil GAIMAN"}, None)
    assert status == 200
    assert [book["title"] for book in body["books"]] == ["Good Omens"]


def test_create_accepts_legacy_author_key(api):
    """A legacy author key in a request is stored as a one-element list."""
    body = create(api, title="Emma", author="Jane Austen", year=1815)
    assert body["authors"] == ["Jane Austen"]
    assert "author" not in body


def test_patch_updates_title_and_keeps_authors(api):
    """PATCH replaces only the fields it names."""
    book = create(api, title="Dune", authors=["Frank Herbert"], year=1965)
    status, body = api.handle("PATCH", f"/books/{book['id']}", {}, {"title": "Dune Messiah"})
    assert status == 200
    assert body["title"] == "Dune Messiah"
    assert body["authors"] == ["Frank Herbert"]


def test_patch_sets_authors(api):
    """PATCH with an authors list replaces the list."""
    book = create(api, title="Dune", authors=["Frank Herbert"], year=1965)
    status, body = api.handle("PATCH", f"/books/{book['id']}", {}, {"authors": ["Brian Herbert", "Kevin Anderson"]})
    assert status == 200
    assert body["authors"] == ["Brian Herbert", "Kevin Anderson"]


def test_missing_book_is_404(api):
    """An unknown id answers 404."""
    status, _ = api.handle("GET", "/books/404", {}, None)
    assert status == 404


def test_missing_field_is_400(api):
    """A body without a required field answers 400 and names the field."""
    status, body = api.handle("POST", "/books", {}, {"title": "No Author"})
    assert status == 400
    assert "author" in body["error"]
