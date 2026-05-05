#!/usr/bin/env python3
"""
ipa_to_roman.py
===============
Converts IPA transcriptions (produced by sharada_ipa.py) into a
Roman transliteration following a modified ISO 15919 / IAST-style scheme
adapted for Kashmiri phonology.

Pipeline:
    Sharada  →  [sharada_ipa.py]  →  IPA  →  [ipa_to_roman.py]  →  Roman

This file can also run the FULL pipeline (Sharada → Roman) by importing
sharada_ipa.sharada_ipa() directly, so you only need the corpus once.

Usage:
    # Full pipeline from raw Sharada corpus:
    python ipa_to_roman.py corpus.txt

    # From a pre-generated IPA file:
    python ipa_to_roman.py --from-ipa corpus_ipa.txt

    # Single IPA string:
    python ipa_to_roman.py --ipa-string "/samaɡata/"

    # Single Sharada word (full pipeline):
    python ipa_to_roman.py --word <sharada_token>

    # Word-level Roman table from corpus:
    python ipa_to_roman.py --word-table corpus.txt

Author: extends sharada_ipa.py rules
"""

import sys
import re
import argparse
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# IPA → ROMAN MAPPING TABLE
# Longest-match substitution; longer keys take priority.
# Scheme: broadly ISO 15919 with Kashmiri-specific additions.
# ─────────────────────────────────────────────────────────────────────────────

# NOTE: order matters when multiple keys share a prefix.
# We sort by descending length so longer patterns are tried first.

IPA_TO_ROMAN_RAW = {
    # ── Long vowels ──────────────────────────────────────────────────────────
    "aː": "ā",
    "iː": "ī",
    "uː": "ū",
    "eː": "ē",
    "ɛː": "ai",     # Kashmiri /ɛː/ conventionally written 'ai'
    "oː": "ō",
    "ɔː": "au",     # Kashmiri /ɔː/ conventionally written 'au'
    "r̩ː": "ṝ",
    "l̩ː": "ḹ",

    # ── Short vowels ─────────────────────────────────────────────────────────
    "a": "a",
    "i": "i",
    "u": "u",
    "r̩": "ṛ",
    "l̩": "ḷ",

    # ── Aspirated stops (digraphs first) ─────────────────────────────────────
    "kʰ": "kh",
    "ɡʱ": "gh",
    "tɕʰ": "ch",
    "dʑʱ": "jh",
    "ʈʰ": "ṭh",
    "ɖʱ": "ḍh",
    "t̪ʰ": "th",
    "d̪ʱ": "dh",
    "pʰ": "ph",
    "bʱ": "bh",

    # ── Plain stops ───────────────────────────────────────────────────────────
    "k":  "k",
    "ɡ":  "g",
    "tɕ": "c",
    "dʑ": "j",
    "ʈ":  "ṭ",
    "ɖ":  "ḍ",
    "t̪":  "t",
    "d̪":  "d",
    "p":  "p",
    "b":  "b",

    # ── Nasals ────────────────────────────────────────────────────────────────
    "ŋ":  "ṅ",
    "ɲ":  "ñ",
    "ɳ":  "ṇ",
    "n":  "n",
    "m":  "m",

    # ── Sonorants / approximants ──────────────────────────────────────────────
    "j":  "y",
    "r":  "r",
    "l":  "l",
    "ɭ":  "ḷ",
    "ʋ":  "v",

    # ── Sibilants ─────────────────────────────────────────────────────────────
    "ɕ":  "ś",
    "ʂ":  "ṣ",
    "s":  "s",

    # ── Glottals & other ──────────────────────────────────────────────────────
    "ɦ":  "h",
    "h":  "h",
    "ʔ":  "ʼ",     # avagraha / glottal stop → modifier letter apostrophe

    # ── IPA diacritics that appear in our output ──────────────────────────────
    # (handled implicitly via multi-char keys above)
}

IPA_TO_ROMAN = sorted(IPA_TO_ROMAN_RAW.items(), key=lambda x: -len(x[0]))


def ipa_to_roman(ipa_string: str) -> str:

    s = ipa_string
    out = []

    # Strip leading/trailing slashes that some IPA notations use
    s = s.strip("/")

    i = 0
    while i < len(s):
        matched = False
        for ipa_seq, roman in IPA_TO_ROMAN:
            if s[i:].startswith(ipa_seq):
                out.append(roman)
                i += len(ipa_seq)
                matched = True
                break
        if not matched:
            out.append(s[i])    # pass through unknown characters unchanged
            i += 1

    return "".join(out)


def sharada_to_roman(sharada_text: str) -> str:
    """
    Full pipeline: Sharada script → IPA → Roman transliteration.
    Imports sharada_ipa from the sibling module.
    """
    try:
        from sharada_ipa import sharada_ipa as s2ipa
    except ImportError:
        print(
            "ERROR: sharada_ipa.py not found in the same directory.\n"
            "       Place both scripts in the same folder.",
            file=sys.stderr,
        )
        sys.exit(1)

    ipa = s2ipa(sharada_text)
    return ipa_to_roman(ipa)


def convert_corpus_full_pipeline(input_path: str, output_path: str) -> None:
    """
    Sharada corpus → IPA → Roman.
    Writes a three-line block per verse/line:
        [Sharada original]
        [IPA]
        [Roman]
        (blank)
    """
    try:
        from sharada_ipa import sharada_ipa as s2ipa
    except ImportError:
        print(
            "ERROR: sharada_ipa.py not found in the same directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    text  = Path(input_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    out_lines = []
    converted = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        ipa   = s2ipa(stripped)
        roman = ipa_to_roman(ipa)
        out_lines.append(roman)
        converted += 1

    Path(output_path).write_text("\n".join(out_lines), encoding="utf-8")
    print(f"✓  Full pipeline (Sharada → IPA → Roman) complete")
    print(f"   Input  : {input_path}  ({len(lines)} lines)")
    print(f"   Output : {output_path}")
    print(f"   Lines converted : {converted}")


def convert_from_ipa_file(input_path: str, output_path: str) -> None:
    """
    Read a pre-generated IPA file (output of sharada_ipa.py)
    and convert IPA lines to Roman.

    Handles the paired format:
        [Sharada line]
        [IPA line]
        (blank)
    → outputs:
        [Sharada line]
        [IPA line]
        [Roman line]
        (blank)
    """
    text  = Path(input_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    out_lines = []
    converted = 0

    # Detect if file has paired Sharada/IPA blocks (2 non-blank lines per group)
    # or plain IPA lines
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            out_lines.append("")
            i += 1
            continue

        # Check if next non-empty line follows (paired mode)
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1

        if j < len(lines) and lines[j].strip():
            # Two consecutive non-blank lines: assume Sharada + IPA pair
            sharada_line = stripped
            ipa_line     = lines[j].strip()
            roman_line   = ipa_to_roman(ipa_line)
            out_lines.append(sharada_line)
            out_lines.append(ipa_line)
            out_lines.append(roman_line)
            out_lines.append("")
            converted += 1
            # Skip to after the IPA line
            i = j + 1
        else:
            # Single line: treat as plain IPA
            roman_line = ipa_to_roman(stripped)
            out_lines.append(stripped)
            out_lines.append(roman_line)
            out_lines.append("")
            converted += 1
            i += 1

    Path(output_path).write_text("\n".join(out_lines), encoding="utf-8")
    print(f"✓  IPA → Roman conversion complete")
    print(f"   Input  : {input_path}")
    print(f"   Output : {output_path}  ({converted} lines converted)")


def convert_single_ipa(ipa_string: str) -> None:
    roman = ipa_to_roman(ipa_string)
    print(f"\nIPA   : {ipa_string}")
    print(f"Roman : {roman}")


def convert_single_word(sharada_word: str) -> None:
    roman = sharada_to_roman(sharada_word)
    try:
        from sharada_ipa import sharada_ipa as s2ipa
        ipa = s2ipa(sharada_word)
    except ImportError:
        ipa = "(sharada_ipa.py not found)"
    print(f"\nSharada : {sharada_word}")
    print(f"IPA     : /{ipa}/")
    print(f"Roman   : {roman}")


def convert_word_table(input_path: str, output_path: str) -> None:
    try:
        from sharada_ipa import sharada_ipa as s2ipa
    except ImportError:
        print("ERROR: sharada_ipa.py not found.", file=sys.stderr)
        sys.exit(1)

    text = Path(input_path).read_text(encoding="utf-8")
    seen = {}
    strip_chars = (
        chr(0x111C5) + chr(0x111C6) + chr(0x111C7) + chr(0x111C8) + " \t\n"
    )

    for token in text.split():
        core = token.strip(strip_chars)
        if core and core not in seen:
            ipa   = s2ipa(core)
            roman = ipa_to_roman(ipa)
            seen[core] = (ipa, roman)

    header = "sharada\tipa\troman"
    rows = [header] + [
        f"{w}\t{ipa}\t{roman}"
        for w, (ipa, roman) in sorted(seen.items())
    ]
    Path(output_path).write_text("\n".join(rows), encoding="utf-8")

    print(f"✓  Word-level Roman table written")
    print(f"   Input  : {input_path}")
    print(f"   Output : {output_path}  ({len(rows)-1} unique tokens)")


def print_roman_mapping() -> None:
    """Print the full IPA → Roman mapping table."""
    print(f"\n{'IPA':<12}  Roman")
    print("─" * 28)
    for ipa_sym, roman in sorted(IPA_TO_ROMAN_RAW.items(), key=lambda x: x[1]):
        print(f"  {ipa_sym:<10}  {roman}")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ipa_to_roman.py",
        description="IPA → Roman transliterator for Sharada/Kashmiri",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline: Sharada corpus → IPA → Roman (3-line output blocks)
  python ipa_to_roman.py corpus.txt

  # From pre-generated IPA file
  python ipa_to_roman.py --from-ipa corpus_ipa.txt

  # Single IPA string
  python ipa_to_roman.py --ipa-string "d̪ʱarmaɕeːt̪re"

  # Single Sharada word (full pipeline)
  python ipa_to_roman.py --word <sharada_token>

  # Word-level TSV table (sharada / IPA / Roman)
  python ipa_to_roman.py --word-table corpus.txt

  # Print the IPA → Roman mapping table
  python ipa_to_roman.py --show-mapping
        """,
    )
    p.add_argument("corpus", nargs="?",
                   help="Sharada corpus file (triggers full pipeline)")
    p.add_argument("-o", "--output", default=None,
                   help="Output file (default: auto-named)")
    p.add_argument("--from-ipa", metavar="IPA_FILE",
                   help="Convert from a pre-generated IPA file")
    p.add_argument("--ipa-string", metavar="IPA",
                   help="Convert a single IPA string to Roman")
    p.add_argument("--word", metavar="SHARADA_TOKEN",
                   help="Convert a single Sharada word (full pipeline)")
    p.add_argument("--word-table", action="store_true",
                   help="Build word-level TSV (sharada / IPA / roman)")
    p.add_argument("--show-mapping", action="store_true",
                   help="Print the IPA → Roman mapping table and exit")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.show_mapping:
        print_roman_mapping()
        return

    if args.ipa_string:
        convert_single_ipa(args.ipa_string)
        return

    if args.word:
        convert_single_word(args.word)
        return

    if args.from_ipa:
        if not Path(args.from_ipa).exists():
            print(f"ERROR: file not found: {args.from_ipa}")
            sys.exit(1)
        stem = Path(args.from_ipa).stem
        outf = args.output or f"{stem}_roman.txt"
        convert_from_ipa_file(args.from_ipa, outf)
        return

    if args.word_table:
        if not args.corpus:
            print("ERROR: --word-table requires a corpus file.")
            sys.exit(1)
        stem = Path(args.corpus).stem
        outf = args.output or f"{stem}_roman_words.tsv"
        convert_word_table(args.corpus, outf)
        return

    if args.corpus:
        if not Path(args.corpus).exists():
            print(f"ERROR: file not found: {args.corpus}")
            sys.exit(1)
        stem = Path(args.corpus).stem
        outf = args.output or f"{stem}_roman.txt"
        convert_corpus_full_pipeline(args.corpus, outf)
        return

    parser.print_help()


if __name__ == "__main__":
    main()