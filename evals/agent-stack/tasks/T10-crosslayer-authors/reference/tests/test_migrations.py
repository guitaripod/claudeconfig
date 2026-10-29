"""Opening schema-v1 databases migrates them in place."""

import json
import sqlite3

from shelf.storage import Repository


def legacy_db(path):
    """Write a schema-v1 database with two books."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version (version) VALUES (1);
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]'
        );
        INSERT INTO books (title, author, year, tags) VALUES ('Dune', 'Frank Herbert', 1965, '["scifi"]');
        INSERT INTO books (title, author, year, tags) VALUES ('Emma', 'Jane Austen', 1815, '[]');
        """
    )
    conn.commit()
    conn.close()


def test_legacy_rows_migrate_to_single_author_lists(tmp_path):
    """Each row keeps its id and order and gains a one-element authors list."""
    path = str(tmp_path / "legacy.db")
    legacy_db(path)
    repo = Repository(path)
    try:
        books = repo.list_books()
    finally:
        repo.close()
    assert [(b.id, b.title, b.authors, b.year, b.tags) for b in books] == [
        (1, "Dune", ["Frank Herbert"], 1965, ["scifi"]),
        (2, "Emma", ["Jane Austen"], 1815, []),
    ]


def test_reopen_after_migration_is_idempotent(tmp_path):
    """A second open of a migrated database leaves the data unchanged."""
    path = str(tmp_path / "legacy.db")
    legacy_db(path)
    Repository(path).close()
    repo = Repository(path)
    try:
        assert [b.authors for b in repo.list_books()] == [["Frank Herbert"], ["Jane Austen"]]
    finally:
        repo.close()
    conn = sqlite3.connect(path)
    try:
        assert json.loads(conn.execute("SELECT authors FROM books WHERE id = 1").fetchone()[0]) == ["Frank Herbert"]
    finally:
        conn.close()
