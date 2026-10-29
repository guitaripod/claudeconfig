"""Grade a bulk String Catalog translation: 12 new keys x 39 locales across Localizable and InfoPlist.

Gated on existing keys, sourceLanguage and version staying untouched in both catalogs.
Usage: grade.py WORKDIR ANSWER_FILE. The answer file is ignored; the result is read from WORKDIR's catalogs.
"""

import json
import os
import re
import sys

RESOURCES = os.path.join("PhotoJournal", "Resources")
CATALOGS = {
    "Localizable": os.path.join(RESOURCES, "Localizable.xcstrings"),
    "InfoPlist": os.path.join(RESOURCES, "InfoPlist.xcstrings"),
}
TASK_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_KEYS = {
    "Localizable": [
        "export.success",
        "journal.entries.count",
        "album.delete.confirm",
        "welcome.back",
        "sync.paused.lowpower",
        "storage.used",
        "album.move.summary",
        "import.failed.reason",
        "sync.last.updated",
        "share.link.copied",
    ],
    "InfoPlist": ["NSPhotoLibraryUsageDescription", "NSCameraUsageDescription"],
}
PLURAL_KEYS = {"export.success", "journal.entries.count"}
LOCALES = [
    "ar", "bg", "ca", "cs", "da", "de", "el", "en-AU", "en-CA", "en-GB", "es", "es-MX", "fi", "fr", "fr-CA",
    "he", "hi", "hr", "hu", "id", "it", "ja", "ko", "ms", "nb", "nl", "pl", "pt-BR", "pt-PT", "ro", "ru", "sk",
    "sv", "th", "tr", "uk", "vi", "zh-Hans", "zh-Hant",
]
EN_VARIANTS = {"en-AU", "en-CA", "en-GB"}
PLURAL_CATEGORIES = {
    "ar": ["zero", "one", "two", "few", "many", "other"],
    "bg": ["one", "other"],
    "ca": ["one", "other"],
    "cs": ["one", "few", "other"],
    "da": ["one", "other"],
    "de": ["one", "other"],
    "el": ["one", "other"],
    "en-AU": ["one", "other"],
    "en-CA": ["one", "other"],
    "en-GB": ["one", "other"],
    "es": ["one", "other"],
    "es-MX": ["one", "other"],
    "fi": ["one", "other"],
    "fr": ["one", "other"],
    "fr-CA": ["one", "other"],
    "he": ["one", "other"],
    "hi": ["one", "other"],
    "hr": ["one", "few", "other"],
    "hu": ["one", "other"],
    "id": ["other"],
    "it": ["one", "other"],
    "ja": ["other"],
    "ko": ["other"],
    "ms": ["other"],
    "nb": ["one", "other"],
    "nl": ["one", "other"],
    "pl": ["one", "few", "many", "other"],
    "pt-BR": ["one", "other"],
    "pt-PT": ["one", "other"],
    "ro": ["one", "few", "other"],
    "ru": ["one", "few", "many", "other"],
    "sk": ["one", "few", "other"],
    "sv": ["one", "other"],
    "th": ["other"],
    "tr": ["one", "other"],
    "uk": ["one", "few", "many", "other"],
    "vi": ["other"],
    "zh-Hans": ["other"],
    "zh-Hant": ["other"],
}
SCRIPTS = {
    "cjk": "぀-ヿ㐀-䶿一-鿿豈-﫿",
    "hangul": "ᄀ-ᇿ㄰-㆏가-힯",
    "arabic": "؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿",
    "hebrew": "֐-׿",
    "cyrillic": "Ѐ-ӿ",
    "greek": "Ͱ-Ͽ",
    "thai": "฀-๿",
    "devanagari": "ऀ-ॿ",
}
REQUIRED_SCRIPT = {
    "ja": "cjk",
    "zh-Hans": "cjk",
    "zh-Hant": "cjk",
    "ko": "hangul",
    "ar": "arabic",
    "he": "hebrew",
    "ru": "cyrillic",
    "uk": "cyrillic",
    "bg": "cyrillic",
    "el": "greek",
    "th": "thai",
    "hi": "devanagari",
}
SCRIPT_PATTERNS = {name: re.compile("[%s]" % ranges) for name, ranges in SCRIPTS.items()}
NON_LATIN = re.compile("[%s]" % "".join(SCRIPTS.values()))
SPECIFIER = re.compile(r"%(\d+\$)?(lld|ld|d|@|f)")
TOTAL = sum(len(keys) for keys in NEW_KEYS.values()) * len(LOCALES)


def load(path):
    """Return the parsed JSON document at path."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dict_of(value):
    """Return value when it is a dict, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def specifiers(text):
    """Return the sorted multiset of format specifiers in text."""
    return sorted(match.group(0) for match in SPECIFIER.finditer(text))


def script_ok(value, locale):
    """Return True when value uses the locale's script, or, for Latin-script locales, uses no other script."""
    if locale in REQUIRED_SCRIPT:
        return SCRIPT_PATTERNS[REQUIRED_SCRIPT[locale]].search(value) is not None
    return NON_LATIN.search(value) is None


def value_ok(value, source, reference, locale):
    """Return True when value is a non-empty translation with source's specifiers, differing from reference unless an English variant."""
    if not isinstance(value, str) or not value.strip():
        return False
    if locale not in EN_VARIANTS and value == reference:
        return False
    if specifiers(value) != specifiers(source):
        return False
    return script_ok(value, locale)


def unit_ok(entry, source, reference, locale):
    """Return True when a localization entry holds one translated stringUnit that passes value_ok."""
    if not isinstance(entry, dict):
        return False
    unit = entry.get("stringUnit")
    if not isinstance(unit, dict) or unit.get("state") != "translated":
        return False
    return value_ok(unit.get("value"), source, reference, locale)


def plural_ok(entry, forms, locale):
    """Return True when a localization entry has a passing translated variant for every CLDR category the locale needs."""
    variations = dict_of(entry).get("variations")
    plural = dict_of(variations).get("plural")
    if not isinstance(plural, dict):
        return False
    for category in PLURAL_CATEGORIES[locale]:
        reference = forms["one"] if category == "one" else forms["other"]
        if not unit_ok(plural.get(category), forms["other"], reference, locale):
            return False
    return True


def cell_correct(entry, forms, locale, plural):
    """Return True when one (key, locale) cell is a correct translation of the English forms."""
    if plural:
        return plural_ok(entry, forms, locale)
    return unit_ok(entry, forms["other"], forms["other"], locale)


def english_forms(base_entry):
    """Return the English source text: 'other' for every key, plus 'one' for plural keys."""
    english = base_entry["localizations"]["en"]
    plural = dict_of(english.get("variations")).get("plural")
    if isinstance(plural, dict):
        return {"one": plural["one"]["stringUnit"]["value"], "other": plural["other"]["stringUnit"]["value"]}
    return {"other": english["stringUnit"]["value"]}


def existing_unchanged(name, baseline, candidate):
    """Return True when every key outside NEW_KEYS[name] keeps its baseline localizations."""
    strings = dict_of(candidate.get("strings"))
    for key, base in baseline["strings"].items():
        if key in NEW_KEYS[name]:
            continue
        current = strings.get(key)
        if not isinstance(current, dict) or current.get("localizations") != base.get("localizations"):
            return False
    return True


def score_catalogs(workdir):
    """Return (score, checks) for the two catalogs under workdir."""
    checks = {
        "cells_correct": 0,
        "cells_total": TOTAL,
        "existing_unchanged": False,
        "json_valid": False,
        "plural_cells_correct": 0,
    }
    candidates = {}
    try:
        for name, rel in CATALOGS.items():
            candidates[name] = load(os.path.join(workdir, rel))
    except (OSError, ValueError) as exc:
        return 0.0, dict(checks, error="catalog is not valid JSON: %s" % exc.__class__.__name__)
    checks["json_valid"] = True
    correct = plural_correct = 0
    unchanged = True
    metadata_ok = True
    for name, rel in CATALOGS.items():
        baseline = load(os.path.join(TASK_DIR, "fixture", rel))
        candidate = dict_of(candidates[name])
        unchanged = unchanged and existing_unchanged(name, baseline, candidate)
        metadata_ok = (
            metadata_ok
            and candidate.get("sourceLanguage") == baseline.get("sourceLanguage")
            and candidate.get("version") == baseline.get("version")
        )
        strings = dict_of(candidate.get("strings"))
        for key in NEW_KEYS[name]:
            forms = english_forms(baseline["strings"][key])
            localizations = dict_of(dict_of(strings.get(key)).get("localizations"))
            for locale in LOCALES:
                if cell_correct(localizations.get(locale), forms, locale, key in PLURAL_KEYS):
                    correct += 1
                    plural_correct += key in PLURAL_KEYS
    checks.update(cells_correct=correct, existing_unchanged=unchanged, plural_cells_correct=plural_correct)
    if not (unchanged and metadata_ok):
        return 0.0, checks
    return correct / TOTAL, checks


def main():
    """Print the single JSON result line; any failure prints score 0 with an error key."""
    try:
        score, checks = score_catalogs(sys.argv[1])
        result = {"score": score, "checks": checks}
    except Exception as exc:
        result = {
            "score": 0.0,
            "checks": {
                "cells_correct": 0,
                "cells_total": TOTAL,
                "existing_unchanged": False,
                "json_valid": False,
                "plural_cells_correct": 0,
            },
            "error": "%s: %s" % (exc.__class__.__name__, exc),
        }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
