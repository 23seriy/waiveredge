"""Unit tests for name resolution — _normalize_name and resolve_names.

Covers: accent folding, punctuation stripping, hyphenated names, suffixes,
empty/whitespace input, deduplication, and case insensitivity.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendations import _normalize_name, resolve_names  # noqa: E402


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------

def test_basic_lowercase():
    assert _normalize_name("LeBron James") == "lebron james"


def test_strips_apostrophes():
    assert _normalize_name("D'Angelo Russell") == "dangelo russell"


def test_strips_periods_and_hyphens():
    assert _normalize_name("Karl-Anthony Towns Jr.") == "karlanthony towns jr"


def test_collapses_whitespace():
    assert _normalize_name("  Stephen   Curry  ") == "stephen curry"


def test_accent_folding_caron():
    assert _normalize_name("Nikola Jokić") == "nikola jokic"
    assert _normalize_name("Luka Dončić") == "luka doncic"


def test_accent_folding_acute():
    assert _normalize_name("José Altuve") == "jose altuve"


def test_accent_folding_tilde():
    assert _normalize_name("Señor García") == "senor garcia"


def test_empty_string():
    assert _normalize_name("") == ""


def test_whitespace_only():
    assert _normalize_name("   ") == ""


def test_all_punctuation():
    assert _normalize_name("...---'''") == ""


# ---------------------------------------------------------------------------
# resolve_names
# ---------------------------------------------------------------------------

PLAYERS = [
    {"id": 1, "name": "LeBron James"},
    {"id": 2, "name": "Stephen Curry"},
    {"id": 3, "name": "Nikola Jokić"},
    {"id": 4, "name": "D'Angelo Russell"},
    {"id": 5, "name": "Karl-Anthony Towns Jr."},
]


def test_exact_match():
    ids, unresolved = resolve_names(["LeBron James"], PLAYERS)
    assert ids == [1]
    assert unresolved == []


def test_case_insensitive():
    ids, _ = resolve_names(["lebron james", "STEPHEN CURRY"], PLAYERS)
    assert ids == [1, 2]


def test_accent_folding_match():
    ids, _ = resolve_names(["nikola jokic"], PLAYERS)
    assert ids == [3]


def test_punctuation_match():
    ids, _ = resolve_names(["dangelo russell"], PLAYERS)
    assert ids == [4]


def test_hyphen_match():
    # Hyphens are stripped (Karl-Anthony -> karlanthony), so input with hyphen matches
    ids, _ = resolve_names(["Karl-Anthony Towns Jr."], PLAYERS)
    assert ids == [5]
    # Also match without the hyphen if user removes it
    ids2, _ = resolve_names(["karlanthony towns jr"], PLAYERS)
    assert ids2 == [5]


def test_unresolved_reported():
    ids, unresolved = resolve_names(["LeBron James", "Fake Player"], PLAYERS)
    assert ids == [1]
    assert unresolved == ["Fake Player"]


def test_deduplication():
    ids, _ = resolve_names(["LeBron James", "lebron james", "LEBRON JAMES"], PLAYERS)
    assert ids == [1]  # single entry, no duplicates


def test_empty_input():
    ids, unresolved = resolve_names([], PLAYERS)
    assert ids == []
    assert unresolved == []


def test_whitespace_entries_skipped():
    ids, unresolved = resolve_names(["  ", "", "LeBron James"], PLAYERS)
    assert ids == [1]
    assert unresolved == []


def test_all_unresolved():
    ids, unresolved = resolve_names(["Fake1", "Fake2"], PLAYERS)
    assert ids == []
    assert len(unresolved) == 2


# ---- manual runner ----------------------------------------------------------
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
