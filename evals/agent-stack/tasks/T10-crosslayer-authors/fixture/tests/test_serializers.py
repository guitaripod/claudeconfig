"""Serializer shape for books."""

from shelf.models import Book
from shelf.serializers import book_from_dict, book_to_dict


def test_to_dict_emits_author_key():
    """The wire shape carries the single author string."""
    data = book_to_dict(Book(id=3, title="Dune", author="Frank Herbert", year=1965, tags=["scifi"]))
    assert data == {"id": 3, "title": "Dune", "author": "Frank Herbert", "year": 1965, "tags": ["scifi"]}


def test_from_dict_ignores_supplied_id():
    """The store assigns ids, so an id in the request body is dropped."""
    book = book_from_dict({"id": 99, "title": "Dune", "author": "Frank Herbert", "year": "1965"})
    assert book.id is None
    assert book.year == 1965


def test_from_dict_defaults_tags_to_empty():
    """Missing tags become an empty list."""
    assert book_from_dict({"title": "Emma", "author": "Jane Austen", "year": 1815}).tags == []
