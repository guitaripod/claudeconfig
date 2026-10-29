"""Search index lookups by title and author."""

from shelf.models import Book
from shelf.search import SearchIndex


def build():
    """Return an index over three books, one of them co-written."""
    index = SearchIndex()
    index.add(Book(id=1, title="Dune", authors=["Frank Herbert"], year=1965))
    index.add(Book(id=2, title="Emma", authors=["Jane Austen"], year=1815))
    index.add(Book(id=3, title="Persuasion", authors=["Jane Austen"], year=1817))
    index.add(Book(id=4, title="Good Omens", authors=["Terry Pratchett", "Neil Gaiman"], year=1990))
    return index


def test_search_by_title_word():
    """A title word finds its book."""
    assert [book.id for book in build().search("dune")] == [1]


def test_search_by_author_returns_all_matches():
    """An author word finds every book by that author, in id order."""
    assert [book.id for book in build().search("austen")] == [2, 3]


def test_search_by_second_author():
    """A later author of a co-written book is also indexed."""
    assert [book.id for book in build().search("gaiman")] == [4]


def test_empty_query_returns_nothing():
    """A query with no word characters matches nothing."""
    assert build().search("   ") == []
