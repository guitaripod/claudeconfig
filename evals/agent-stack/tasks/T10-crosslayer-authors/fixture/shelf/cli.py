"""Command-line entry point: python3 -m shelf.cli --db PATH list|add."""

import argparse
import sys

from shelf.models import Book
from shelf.storage import Repository


def build_parser():
    """Return the argument parser for the list and add subcommands."""
    parser = argparse.ArgumentParser(prog="shelf")
    parser.add_argument("--db", required=True, help="path to the SQLite database")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list all books")
    add = commands.add_parser("add", help="add a book")
    add.add_argument("--title", required=True)
    add.add_argument("--author", required=True)
    add.add_argument("--year", type=int, required=True)
    add.add_argument("--tag", action="append", default=[])
    return parser


def main(argv=None):
    """Run one command against the database and return the exit status."""
    args = build_parser().parse_args(argv)
    repo = Repository(args.db)
    try:
        if args.command == "list":
            for book in repo.list_books():
                print(f"{book.id}\t{book.title}\t{book.author}\t{book.year}")
        else:
            book = repo.add(Book(id=None, title=args.title, author=args.author, year=args.year, tags=args.tag))
            print(f"added {book.id}")
    finally:
        repo.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
