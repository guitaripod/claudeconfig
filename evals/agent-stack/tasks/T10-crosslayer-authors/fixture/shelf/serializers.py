"""JSON shape of books on the wire."""

from dataclasses import replace

from shelf.models import Book

PATCHABLE = ("title", "author", "year", "tags")


def book_to_dict(book):
    """Return the API representation of a book."""
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "tags": list(book.tags),
    }


def book_from_dict(data):
    """Build a Book from request data; a supplied id is ignored, the store assigns one."""
    return Book(
        id=None,
        title=str(data["title"]),
        author=str(data["author"]),
        year=int(data["year"]),
        tags=[str(tag) for tag in data.get("tags", [])],
    )


def book_patch(book, data):
    """Return book with the fields present in data replaced; the id is kept."""
    values = book_to_dict(book)
    values.update({key: data[key] for key in PATCHABLE if key in data})
    return replace(book_from_dict(values), id=book.id)
