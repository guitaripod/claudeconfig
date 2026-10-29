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
    book = create(api, title="Dune", author="Frank Herbert", year=1965)
    status, body = api.handle("GET", f"/books/{book['id']}", {}, None)
    assert status == 200
    assert body["title"] == "Dune"


def test_list_filters_by_author(api):
    """The author query parameter narrows the list."""
    create(api, title="Dune", author="Frank Herbert", year=1965)
    create(api, title="Emma", author="Jane Austen", year=1815)
    status, body = api.handle("GET", "/books", {"author": "jane austen"}, None)
    assert status == 200
    assert [book["title"] for book in body["books"]] == ["Emma"]


def test_patch_updates_title(api):
    """PATCH replaces only the fields it names."""
    book = create(api, title="Dune", author="Frank Herbert", year=1965)
    status, body = api.handle("PATCH", f"/books/{book['id']}", {}, {"title": "Dune Messiah"})
    assert status == 200
    assert body["title"] == "Dune Messiah"
    assert body["author"] == "Frank Herbert"


def test_missing_book_is_404(api):
    """An unknown id answers 404."""
    status, _ = api.handle("GET", "/books/404", {}, None)
    assert status == 404


def test_missing_field_is_400(api):
    """A body without a required field answers 400 and names the field."""
    status, body = api.handle("POST", "/books", {}, {"title": "No Author"})
    assert status == 400
    assert "author" in body["error"]
