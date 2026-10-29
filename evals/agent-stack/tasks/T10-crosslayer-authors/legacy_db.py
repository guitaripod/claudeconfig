"""Deterministic schema-version-1 shelf database with 20 synthetic rows, shared by setup.sh and grade.py."""

import json
import os
import sqlite3
import sys

LEGACY_SCHEMA = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version (version) VALUES (1);
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]'
);
"""

TITLES = [
    "The Glass Orchard",
    "Winter Ledger",
    "Salt Maps",
    "Quiet Engines",
    "Harbor Notes",
    "The Long Meridian",
    "Paper Lanterns",
    "Field Almanac",
    "Night Tram",
    "Copper Garden",
    "Cinder Atlas",
    "Still Water Ballads",
    "Moss and Signal",
    "Borrowed Light",
    "The Tidewright",
    "Slow Orbit",
    "Lantern Street",
    "Iron Thread",
    "Marrow Hill",
    "Kite Season",
]

AUTHORS = [
    "Ada Quill",
    "Bo Tern",
    "Mara Lind",
    "Teo Harrow",
    "Ines Vale",
    "Oru Pell",
    "Zoe Ibarra",
    "Kade Marrow",
    "Lio Stane",
    "Vera Kell",
]

TAGS = [["fiction"], ["history", "maps"], [], ["poetry"], ["fiction", "sea"]]


def rows():
    """Return the 20 legacy rows as (title, author, year, tags-json) tuples."""
    out = []
    for index, title in enumerate(TITLES):
        author = AUTHORS[(index * 3) % len(AUTHORS)]
        year = 1948 + (index * 29) % 71
        out.append((title, author, year, json.dumps(TAGS[index % len(TAGS)])))
    return out


def build(path):
    """Write a fresh legacy database at path, replacing any file already there."""
    for suffix in ("", "-journal"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(LEGACY_SCHEMA)
        conn.executemany("INSERT INTO books (title, author, year, tags) VALUES (?, ?, ?, ?)", rows())
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    build(sys.argv[1])
