"""In-memory search index over book titles and authors."""

import re

from shelf.models import Book

WORD = re.compile(r"\w+")


def tokenize(text):
    """Return the lowercase word tokens of text as a set."""
    return {match.group(0).lower() for match in WORD.finditer(text)}


class SearchIndex:
    """Inverted index from word tokens to books; search returns books containing every query token."""

    def __init__(self):
        self._books = {}
        self._postings = {}

    def add(self, book):
        """Index a book by the words of its title and author."""
        self._books[book.id] = book
        for token in tokenize(book.title) | tokenize(book.author):
            self._postings.setdefault(token, set()).add(book.id)

    def search(self, query):
        """Return books containing all query tokens, in id order."""
        tokens = tokenize(query)
        if not tokens:
            return []
        ids = set.intersection(*(self._postings.get(token, set()) for token in tokens))
        return [self._books[book_id] for book_id in sorted(ids)]
