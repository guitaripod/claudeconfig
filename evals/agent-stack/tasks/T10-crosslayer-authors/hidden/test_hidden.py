"""Hidden acceptance tests for the multi-author change, run against a fresh schema-v1 database."""

import json
import os
import shutil
import sqlite3

import pytest

from shelf import cli
from shelf.api import Api
from shelf.models import Book
from shelf.search import SearchIndex
from shelf.serializers import book_from_dict, book_to_dict
from shelf.storage import Repository


@pytest.fixture
def legacy_path(tmp_path):
    """Return a private copy of the pristine schema-v1 database."""
    dest = tmp_path / "legacy.db"
    shutil.copy(os.environ["SHELF_LEGACY_DB"], dest)
    return str(dest)


@pytest.fixture
def repo(tmp_path):
    """Return an open repository on a fresh database."""
    store = Repository(str(tmp_path / "fresh.db"))
    yield store
    store.close()


@pytest.fixture
def api(repo):
    """Return the request router over the fresh repository."""
    return Api(repo)


def legacy_rows(path):
    """Read (id, title, author, year, tags-json) straight from the schema-v1 table."""
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT id, title, author, year, tags FROM books ORDER BY id").fetchall()
    finally:
        conn.close()


def has_key(value, key):
    """Return True when key is a dict key anywhere inside value."""
    if isinstance(value, dict):
        return key in value or any(has_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(has_key(item, key) for item in value)
    return False


def titles(body):
    """Return the titles of a list response body."""
    return [book["title"] for book in body["books"]]


def create_book(api, **fields):
    """POST a book, assert it was created and return the response body."""
    status, body = api.handle("POST", "/books", {}, fields)
    assert status == 201, body
    return body


def test_migration_keeps_every_legacy_row(legacy_path):
    """Opening a schema-v1 database keeps all 20 rows with their id, title, year and tags."""
    rows = legacy_rows(legacy_path)
    store = Repository(legacy_path)
    try:
        books = store.list_books()
    finally:
        store.close()
    assert len(rows) == 20
    assert [(b.id, b.title, b.year, b.tags) for b in books] == [
        (row[0], row[1], row[3], json.loads(row[4])) for row in rows
    ]


def test_migration_maps_author_to_single_element_list(legacy_path):
    """Each legacy author becomes a one-element authors list."""
    expected = [[row[2]] for row in legacy_rows(legacy_path)]
    store = Repository(legacy_path)
    try:
        actual = [book.authors for book in store.list_books()]
    finally:
        store.close()
    assert actual == expected


def test_migration_preserves_row_order(legacy_path):
    """Migrated books come back in the original row order."""
    ids = [row[0] for row in legacy_rows(legacy_path)]
    store = Repository(legacy_path)
    try:
        assert [book.id for book in store.list_books()] == ids
    finally:
        store.close()


def test_second_open_is_idempotent(legacy_path):
    """Reopening an already migrated database changes nothing and does not fail."""
    first = Repository(legacy_path)
    before = [(book.id, book.authors) for book in first.list_books()]
    first.close()
    second = Repository(legacy_path)
    try:
        after = [(book.id, book.authors) for book in second.list_books()]
    finally:
        second.close()
    assert len(after) == 20
    assert after == before


def test_fresh_database_stores_several_authors(repo):
    """A new book keeps every author it was given."""
    added = repo.add(Book(id=None, title="Anthology", authors=["Ada Quill", "Bo Tern"], year=2001, tags=[]))
    assert repo.get(added.id).authors == ["Ada Quill", "Bo Tern"]


def test_author_order_survives_reopen(tmp_path):
    """The author order of a book is kept across close and reopen."""
    path = str(tmp_path / "shelf.db")
    store = Repository(path)
    added = store.add(Book(id=None, title="Trio", authors=["Zed Ar", "Ann Be", "Cy Fen"], year=1999, tags=[]))
    store.close()
    reopened = Repository(path)
    try:
        assert reopened.get(added.id).authors == ["Zed Ar", "Ann Be", "Cy Fen"]
    finally:
        reopened.close()


def test_serializer_accepts_legacy_author_key():
    """A legacy author key on input becomes a one-element authors list."""
    book = book_from_dict({"title": "Old Form", "author": "Ann Be", "year": 1980})
    assert book.authors == ["Ann Be"]


def test_serializer_reads_authors_list():
    """An authors list on input is taken as given, in order."""
    book = book_from_dict({"title": "New Form", "authors": ["Ann Be", "Cy Fen"], "year": 1981})
    assert book.authors == ["Ann Be", "Cy Fen"]


def test_serializer_emits_authors_and_no_author_key():
    """Output always carries authors as a list and never an author key."""
    data = book_to_dict(Book(id=7, title="T", authors=["Ann Be", "Cy Fen"], year=1982, tags=["x"]))
    assert data["authors"] == ["Ann Be", "Cy Fen"]
    assert "author" not in data


def test_api_create_returns_authors_without_author_key(api):
    """POST with an authors list answers with authors and no author key."""
    body = create_book(api, title="Pair", authors=["Ada Quill", "Bo Tern"], year=2001)
    assert body["authors"] == ["Ada Quill", "Bo Tern"]
    assert "author" not in body


def test_api_create_accepts_legacy_author_key(api):
    """POST with the legacy author key stores a one-element authors list."""
    body = create_book(api, title="Old Client", author="Mara Lind", year=1999)
    assert body["authors"] == ["Mara Lind"]


def test_author_filter_matches_any_author(api):
    """GET with author=X finds a book through its second author."""
    create_book(api, title="Duet", authors=["Ada Quill", "Bo Tern"], year=2001)
    status, body = api.handle("GET", "/books", {"author": "Bo Tern"}, None)
    assert status == 200
    assert "Duet" in titles(body)


def test_author_filter_is_case_insensitive(api):
    """The author filter ignores letter case in both directions."""
    create_book(api, title="Duet", authors=["Ada Quill", "Bo Tern"], year=2001)
    for name in ("ada quill", "BO TERN"):
        _, body = api.handle("GET", "/books", {"author": name}, None)
        assert "Duet" in titles(body), name


def test_author_filter_needs_whole_name(api):
    """A partial author name does not match, while the full name does."""
    create_book(api, title="Duet", authors=["Ada Quill", "Bo Tern"], year=2001)
    _, exact = api.handle("GET", "/books", {"author": "Ada Quill"}, None)
    _, partial = api.handle("GET", "/books", {"author": "Ada"}, None)
    assert "Duet" in titles(exact)
    assert "Duet" not in titles(partial)


def test_patch_sets_authors(api):
    """PATCH with an authors list replaces the list and the change is persisted."""
    created = create_book(api, title="Solo", authors=["Ada Quill"], year=2001)
    status, body = api.handle("PATCH", f"/books/{created['id']}", {}, {"authors": ["Cy Fen", "Di Holt"]})
    assert status == 200
    assert body["authors"] == ["Cy Fen", "Di Holt"]
    _, fetched = api.handle("GET", f"/books/{created['id']}", {}, None)
    assert fetched["authors"] == ["Cy Fen", "Di Holt"]


def test_no_response_carries_author_key(api):
    """No list, detail, create or patch response contains an author key anywhere."""
    created = create_book(api, title="Solo", authors=["Ada Quill"], year=2001)
    responses = [
        created,
        api.handle("GET", "/books", {}, None)[1],
        api.handle("GET", f"/books/{created['id']}", {}, None)[1],
        api.handle("PATCH", f"/books/{created['id']}", {}, {"title": "Solo II"})[1],
    ]
    for body in responses:
        assert not has_key(body, "author"), body


def test_search_finds_book_by_second_author():
    """The search index finds a book by any of its authors."""
    index = SearchIndex()
    index.add(Book(id=1, title="Duet", authors=["Ada Quill", "Bo Tern"], year=2001, tags=[]))
    assert [book.title for book in index.search("tern")] == ["Duet"]


def test_cli_add_takes_repeatable_author(tmp_path):
    """The add command stores every --author it is given, in order."""
    path = str(tmp_path / "shelf.db")
    cli.main(["--db", path, "add", "--title", "Duet", "--author", "Ada Quill", "--author", "Bo Tern", "--year", "2001"])
    store = Repository(path)
    try:
        assert store.list_books()[-1].authors == ["Ada Quill", "Bo Tern"]
    finally:
        store.close()
