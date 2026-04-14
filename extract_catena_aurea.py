#!/usr/bin/env python3
"""
Modular, on-demand parser for Catena Aurea exegesis from the TOML directories.

No large JSON or SQLite to commit to your repo.

Usage in your desktop app:
    from catena_toml_parser import CatenaParser

    parser = CatenaParser("/path/to/Commentaries-Database")
    exegeses = parser.get_catena_for_verse("Matthew", 5, 3)  # or "matthew"

    for e in exegeses:
        print(e["father_name"], e["quote"][:100])

This keeps your app repo tiny. The user of your software either:
- Points the app at their local clone of Commentaries-Database, or
- Your app downloads the needed book folder(s) on first use of that book.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
import rtoml


def _normalize_book(name: str) -> str:
    """Map common Vulgata/book names to folder names used in the database."""
    n = name.strip().lower().replace(" ", "").replace("_", "")
    mapping = {
        "genesis": "Genesis",
        "exodus": "Exodus",
        "leviticus": "Leviticus",
        "numbers": "Numbers",
        "deuteronomy": "Deuteronomy",
        "matthew": "Matthew",
        "mark": "Mark",
        "luke": "Luke",
        "john": "John",
        "acts": "Acts",
        "romans": "Romans",
        "1corinthians": "1 Corinthians",
        "2corinthians": "2 Corinthians",
        "galatians": "Galatians",
        "ephesians": "Ephesians",
        "philippians": "Philippians",
        "colossians": "Colossians",
        "1thessalonians": "1 Thessalonians",
        "2thessalonians": "2 Thessalonians",
        "1timothy": "1 Timothy",
        "2timothy": "2 Timothy",
        "titus": "Titus",
        "philemon": "Philemon",
        "hebrews": "Hebrews",
        "james": "James",
        "1peter": "1 Peter",
        "2peter": "2 Peter",
        "1john": "1 John",
        "2john": "2 John",
        "3john": "3 John",
        "jude": "Jude",
        "revelation": "Revelation",
        "apocalypse": "Revelation",
    }
    return mapping.get(n, name)  # fall back to original


def _string_to_verse_range(verse_string: str):
    """Parse '5_3', '5_3-7', '5_3-6_2' etc."""
    pieces = re.split(r"[_-]", verse_string)
    sc = int(pieces[0])
    sv = int(pieces[1])
    if len(pieces) == 2:
        return sc, sv, sc, sv
    elif len(pieces) == 3:
        return sc, sv, sc, int(pieces[2])
    else:
        return sc, sv, int(pieces[2]), int(pieces[3])


def _ranges_overlap(q_start: int, q_end: int, f_start: int, f_end: int) -> bool:
    """Check if query verse range overlaps file range (using encoded loc)."""
    return not (q_end < f_start or q_start > f_end)


def _encode(ch: int, v: int) -> int:
    return ch * 1000000 + v


class CatenaParser:
    def __init__(self, db_root: Path):
        self.db_root = Path(db_root)
        if not self.db_root.exists():
            raise FileNotFoundError(f"Database root not found: {db_root}")

    def get_catena_for_verse(
        self, book: str, chapter: int, verse: int
    ) -> List[Dict]:
        """
        Return all Catena Aurea exegesis covering the given verse.
        Searches the TOML directory tree on demand using filename patterns.
        Loads only the few candidate files that might match.
        """
        book_name = _normalize_book(book)
        q_loc = _encode(chapter, verse)

        # Build glob patterns that can catch the verse
        # e.g. "Matthew 5_3*.toml" catches 5_3, 5_3-7, 5_3-6_2 etc.
        patterns = [
            f"{book_name} {chapter}_{verse}.toml",
            f"{book_name} {chapter}_{verse}-*.toml",
        ]

        candidate_files: List[Path] = []
        for pat in patterns:
            candidate_files.extend(self.db_root.rglob(pat))

        # Also catch ranges that start before our verse but cover it (e.g. 5_1-10.toml for verse 3)
        # Do a broader search for the chapter and filter
        broad_pat = f"{book_name} {chapter}_*.toml"
        for f in self.db_root.rglob(broad_pat):
            if f not in candidate_files:
                candidate_files.append(f)

        results: List[Dict] = []
        for toml_file in candidate_files:
            if toml_file.name == "metadata.toml":
                continue
            stem = toml_file.stem
            try:
                range_part = stem.split()[-1]
                fs, fv, fe_c, fe_v = _string_to_verse_range(range_part)
                f_start = _encode(fs, fv)
                f_end = _encode(fe_c, fe_v)

                if not _ranges_overlap(q_loc, q_loc, f_start, f_end):
                    continue

                obj = rtoml.load(toml_file.read_text(encoding="utf-8"))
                for c in obj.get("commentary", []):
                    if "Catena Aurea" in c.get("source_title", ""):
                        results.append(
                            {
                                "father_name": toml_file.parent.name,
                                "append_to_author_name": c.get(
                                    "append_to_author_name", ""
                                ),
                                "quote": c.get("quote", "").strip(),
                                "source_url": c.get("source_url", ""),
                                "source_title": c.get("source_title", ""),
                                "time": c.get("time", 9999999),
                                "file": toml_file.name,
                            }
                        )
            except Exception:
                continue

        results.sort(key=lambda x: x["time"])
        # Dedup if any file matched multiple patterns
        seen = set()
        unique = []
        for r in results:
            key = (r["file"], r["father_name"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique


# Simple CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python catena_toml_parser.py <db_root> <Book> <chapter> <verse>")
        sys.exit(1)

    db = sys.argv[1]
    book = sys.argv[2]
    ch = int(sys.argv[3])
    v = int(sys.argv[4])

    p = CatenaParser(db)
    hits = p.get_catena_for_verse(book, ch, v)
    print(f"Found {len(hits)} Catena Aurea entries for {book} {ch}:{v}")
    for h in hits[:3]:
        print("-", h["father_name"], h.get("append_to_author_name", "")[:30])
        print(" ", h["quote"], "\n")
