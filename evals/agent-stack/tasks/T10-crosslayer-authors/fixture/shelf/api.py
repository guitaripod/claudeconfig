"""Request router for the books resource; each call returns a (status, body) pair."""

from shelf.serializers import book_from_dict, book_patch, book_to_dict


class Api:
    """Routes GET and POST /books and GET and PATCH /books/<id> against a Repository."""

    def __init__(self, repo):
        self.repo = repo

    def handle(self, method, path, query=None, body=None):
        """Dispatch one request and return (status, dict)."""
        query = query or {}
        parts = [part for part in path.split("/") if part]
        try:
            if parts == ["books"] and method == "GET":
                return self._list(query)
            if parts == ["books"] and method == "POST":
                return self._create(body)
            if len(parts) == 2 and parts[0] == "books" and parts[1].isdigit():
                if method == "GET":
                    return self._get(int(parts[1]))
                if method == "PATCH":
                    return self._patch(int(parts[1]), body)
            return 404, {"error": "not found"}
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"error": str(exc)}

    def _list(self, query):
        """List every book, or only those matching the author query parameter."""
        if "author" in query:
            books = self.repo.find_by_author(query["author"])
        else:
            books = self.repo.list_books()
        return 200, {"books": [book_to_dict(book) for book in books]}

    def _get(self, book_id):
        """Return one book or 404."""
        book = self.repo.get(book_id)
        if book is None:
            return 404, {"error": "not found"}
        return 200, book_to_dict(book)

    def _create(self, body):
        """Store a new book from the request body."""
        book = self.repo.add(book_from_dict(body))
        return 201, book_to_dict(book)

    def _patch(self, book_id, body):
        """Apply the fields present in body to an existing book."""
        current = self.repo.get(book_id)
        if current is None:
            return 404, {"error": "not found"}
        updated = self.repo.update(book_patch(current, body))
        return 200, book_to_dict(updated)
