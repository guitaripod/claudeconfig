"""JSON shape of books on the wire."""

from dataclasses import replace

from shelf.models import Book

PATCHABLE = ("title", "authors", "author", "year", "tags")


def book_to_dict(book):
    """Return the API representation of a book; authors is always a list."""
    return {
        "id": book.id,
        "title": book.title,
        "authors": list(book.authors),
        "year": book.year,
        "tags": list(book.tags),
    }


def _authors_from(data):
    """Return the authors list from request data, accepting the legacy single author key."""
    if "authors" in data:
        authors = data["authors"]
        if not isinstance(authors, list):
            raise TypeError("authors must be a list")
        return [str(author) for author in authors]
    return [str(data["author"])]


def book_from_dict(data):
    """Build a Book from request data; a supplied id is ignored, the store assigns one."""
    return Book(
        id=None,
        title=str(data["title"]),
        authors=_authors_from(data),
        year=int(data["year"]),
        tags=[str(tag) for tag in data.get("tags", [])],
    )


def book_patch(book, data):
    """Return book with the fields present in data replaced; the id is kept.

    A legacy author key in data replaces the whole authors list with that one author.
    """
    values = book_to_dict(book)
    if "author" in data and "authors" not in data:
        del values["authors"]
    values.update({key: data[key] for key in PATCHABLE if key in data})
    return replace(book_from_dict(values), id=book.id)
