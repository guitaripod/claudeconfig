"""SQLite repository for books, with ordered schema migrations."""

import json
import sqlite3

from shelf.models import Book


def _create_books(conn):
    """Migration 1: the books table with a single author column."""
    conn.execute(
        "CREATE TABLE books ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL,"
        " author TEXT NOT NULL,"
        " year INTEGER NOT NULL,"
        " tags TEXT NOT NULL DEFAULT '[]')"
    )


def _authors_list(conn):
    """Migration 2: replace the author column with a JSON authors list, keeping row ids and order."""
    conn.execute(
        "CREATE TABLE books_v2 ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL,"
        " authors TEXT NOT NULL,"
        " year INTEGER NOT NULL,"
        " tags TEXT NOT NULL DEFAULT '[]')"
    )
    rows = conn.execute("SELECT id, title, author, year, tags FROM books ORDER BY id").fetchall()
    conn.executemany(
        "INSERT INTO books_v2 (id, title, authors, year, tags) VALUES (?, ?, ?, ?, ?)",
        [(book_id, title, json.dumps([author]), year, tags) for book_id, title, author, year, tags in rows],
    )
    conn.execute("DROP TABLE books")
    conn.execute("ALTER TABLE books_v2 RENAME TO books")


MIGRATIONS = [_create_books, _authors_list]

COLUMNS = "id, title, authors, year, tags"


def _row_to_book(row):
    """Convert a books row into a Book."""
    return Book(id=row[0], title=row[1], authors=json.loads(row[2]), year=row[3], tags=json.loads(row[4]))


class Repository:
    """Books stored in one SQLite file; opening the file migrates it to the latest schema."""

    def __init__(self, path):
        self._conn = sqlite3.connect(path, isolation_level=None)
        self._migrate()

    def _migrate(self):
        """Apply every migration newer than the stored schema_version, each in its own transaction."""
        self._conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = self._conn.execute("SELECT version FROM schema_version").fetchone()
        current = row[0] if row else 0
        for number, migration in enumerate(MIGRATIONS, start=1):
            if number <= current:
                continue
            self._conn.execute("BEGIN")
            try:
                migration(self._conn)
                self._conn.execute("DELETE FROM schema_version")
                self._conn.execute("INSERT INTO schema_version (version) VALUES (?)", (number,))
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def close(self):
        """Close the underlying connection."""
        self._conn.close()

    def add(self, book):
        """Insert a book and return it with its assigned id."""
        cur = self._conn.execute(
            "INSERT INTO books (title, authors, year, tags) VALUES (?, ?, ?, ?)",
            (book.title, json.dumps(book.authors), book.year, json.dumps(book.tags)),
        )
        return self.get(cur.lastrowid)

    def get(self, book_id):
        """Return the book with book_id, or None."""
        row = self._conn.execute(f"SELECT {COLUMNS} FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_book(row) if row else None

    def list_books(self):
        """Return every book in id order."""
        rows = self._conn.execute(f"SELECT {COLUMNS} FROM books ORDER BY id").fetchall()
        return [_row_to_book(row) for row in rows]

    def find_by_author(self, name):
        """Return books with any author equal to name, case-insensitively, in id order."""
        needle = name.casefold()
        return [
            book for book in self.list_books() if any(author.casefold() == needle for author in book.authors)
        ]

    def update(self, book):
        """Overwrite the book with book.id; return the stored book, or None when it does not exist."""
        cur = self._conn.execute(
            "UPDATE books SET title = ?, authors = ?, year = ?, tags = ? WHERE id = ?",
            (book.title, json.dumps(book.authors), book.year, json.dumps(book.tags), book.id),
        )
        return self.get(book.id) if cur.rowcount else None
