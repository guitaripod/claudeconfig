"""Write the Localizable and InfoPlist String Catalogs for T03-xcstrings-bulk.

The fixture keeps the new keys English-only; the reference translates every locale. Run from anywhere: python3 build/emit.py
"""

import json
import os

import catalog_data as data

TASK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join("PhotoJournal", "Resources")
EXPECTED = set(data.LOCALES) | {"en"}


def parse_simple(name, table):
    """Return {locale: value} for a simple key table and check every expected locale is present."""
    parsed = {}
    for line in table.strip().splitlines():
        locale, value = line.split(" ", 1)
        parsed[locale] = value
    check_coverage(name, parsed)
    return parsed


def parse_plural(name, table):
    """Return {locale: {category: value}} for a plural key table and check every expected locale is present."""
    parsed = {}
    for line in table.strip().splitlines():
        locale, rest = line.split(" ", 1)
        parsed[locale] = dict(part.split("=", 1) for part in rest.split("|"))
    check_coverage(name, parsed)
    return parsed


def check_coverage(name, parsed):
    """Raise when a table is missing a locale or has one the catalog does not use."""
    missing = EXPECTED - set(parsed)
    extra = set(parsed) - EXPECTED
    if missing or extra:
        raise SystemExit("%s: missing %s, unexpected %s" % (name, sorted(missing), sorted(extra)))


def unit(value):
    """Return a translated stringUnit for one value."""
    return {"stringUnit": {"state": "translated", "value": value}}


def strings_for(existing, new, plural, english_only):
    """Return the strings map for one catalog, keeping only English for new keys when english_only is set."""
    keep = (lambda locale: locale == "en") if english_only else (lambda locale: True)
    strings = {}
    for key, table in existing.items():
        strings[key] = {"localizations": {loc: unit(v) for loc, v in parse_simple(key, table).items()}}
    for key, table in new.items():
        strings[key] = {"localizations": {loc: unit(v) for loc, v in parse_simple(key, table).items() if keep(loc)}}
    for key, table in plural.items():
        forms_by_locale = parse_plural(key, table)
        strings[key] = {
            "localizations": {
                loc: {"variations": {"plural": {cat: unit(v) for cat, v in forms.items()}}}
                for loc, forms in forms_by_locale.items()
                if keep(loc)
            }
        }
    return dict(sorted(strings.items()))


def document(strings):
    """Return a String Catalog document with the sourceLanguage and version fields."""
    return {"sourceLanguage": "en", "strings": strings, "version": "1.0"}


def write(path, doc):
    """Write doc to path as sorted, indented UTF-8 JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main():
    """Emit both catalogs into fixture/ (English-only new keys) and reference/ (every cell translated)."""
    catalogs = {
        "Localizable": (data.LOCALIZABLE_EXISTING, data.LOCALIZABLE_NEW, data.LOCALIZABLE_PLURAL),
        "InfoPlist": (data.INFOPLIST_EXISTING, data.INFOPLIST_NEW, {}),
    }
    for variant, english_only in (("fixture", True), ("reference", False)):
        for name, (existing, new, plural) in catalogs.items():
            doc = document(strings_for(existing, new, plural, english_only))
            write(os.path.join(TASK_DIR, variant, RESOURCES, name + ".xcstrings"), doc)


if __name__ == "__main__":
    main()
