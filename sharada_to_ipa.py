#!/usr/bin/env python3
"""
sharada_to_ipa.py
=================
Converts Sharada script corpus to IPA (International Phonetic Alphabet).

Usage:
    python sharada_to_ipa.py corpus.txt                   # outputs corpus_ipa.txt
    python sharada_to_ipa.py corpus.txt -o output.txt     # custom output file
    python sharada_to_ipa.py --word <sharada_word>        # single word
    python sharada_to_ipa.py --inventory corpus.txt       # character inventory report

Pipeline:
    Sharada graphemes  -->  [Rule-based G2P]  -->  IPA transcription

Author: based on g2ipa.py rules
"""

import sys
import unicodedata
import argparse
from collections import Counter
from pathlib import Path


# Independent vowels  (standalone vowel letters)
INDEPENDENT_VOWELS = {
    chr(0x11183): "a",
    chr(0x11184): "aː",
    chr(0x11185): "i",
    chr(0x11186): "iː",
    chr(0x11187): "u",
    chr(0x11188): "uː",
    chr(0x11189): "r̩",
    chr(0x1118A): "r̩ː",
    chr(0x1118B): "l̩",
    chr(0x1118C): "l̩ː",
    chr(0x1118D): "eː",
    chr(0x1118E): "ɛː",
    chr(0x1118F): "oː",
    chr(0x11190): "ɔː",
}

# Dependent vowel signs (mātrās) that follow consonants
VOWEL_SIGNS = {
    chr(0x111B3): "aː",
    chr(0x111B4): "i",
    chr(0x111B5): "iː",
    chr(0x111B6): "u",
    chr(0x111B7): "uː",
    chr(0x111B8): "r̩",
    chr(0x111B9): "r̩ː",
    chr(0x111BA): "l̩",
    chr(0x111BB): "l̩ː",
    chr(0x111BC): "eː",
    chr(0x111BD): "ɛː",
    chr(0x111BE): "oː",
    chr(0x111BF): "ɔː",
}

# Consonants  (inherent vowel /a/ is added unless followed by virama or matra)
CONSONANTS = {
    # Velars 
    chr(0x11191): "k",
    chr(0x11192): "kʰ",
    chr(0x11193): "ɡ",
    chr(0x11194): "ɡʱ",
    chr(0x11195): "ŋ",
    # Palatals
    chr(0x11196): "tɕ",
    chr(0x11197): "tɕʰ",
    chr(0x11198): "dʑ",
    chr(0x11199): "dʑʱ",
    chr(0x1119A): "ɲ",
    # Retroflexes
    chr(0x1119B): "ʈ",
    chr(0x1119C): "ʈʰ",
    chr(0x1119D): "ɖ",
    chr(0x1119E): "ɖʱ",
    chr(0x1119F): "ɳ",
    # Dentals
    chr(0x111A0): "t̪",
    chr(0x111A1): "t̪ʰ",
    chr(0x111A2): "d̪",
    chr(0x111A3): "d̪ʱ",
    chr(0x111A4): "n",
    # Labials
    chr(0x111A5): "p",
    chr(0x111A6): "pʰ",
    chr(0x111A7): "b",
    chr(0x111A8): "bʱ",
    chr(0x111A9): "m",
    # Sonorants / approximants
    chr(0x111AA): "j",
    chr(0x111AB): "r",
    chr(0x111AC): "l",
    chr(0x111AD): "ɭ",
    chr(0x111AE): "ʋ",
    # Sibilants
    chr(0x111AF): "ɕ",
    chr(0x111B0): "ʂ",
    chr(0x111B1): "s",
    # Glottal 
    chr(0x111B2): "ɦ",
}


# ANUSVARA ASSIMILATION  (nasal place assimilation before consonants)

_NASAL_GROUPS = [
    ({chr(c) for c in range(0x11191, 0x11196)}, "ŋ"),   # before velars
    ({chr(c) for c in range(0x11196, 0x1119B)}, "ɲ"),   # before palatals
    ({chr(c) for c in range(0x1119B, 0x111A0)}, "ɳ"),   # before retroflexes
    ({chr(c) for c in range(0x111A0, 0x111A5)}, "n"),   # before dentals
    ({chr(c) for c in range(0x111A5, 0x111AA)}, "m"),   # before labials
]


# SPECIAL CHARACTERS

VIRAMA   = chr(0x111C0)   # halant — suppresses inherent vowel
ANUSVARA = chr(0x11181)   # chandrabindu-style nasal
VISARGA  = chr(0x11182)   # final aspiration  /h/
AVAGRAHA = chr(0x111C1)   # elision mark → IPA glottal stop ʔ

SHARADA_DIGITS = {chr(0x111D0 + i): str(i) for i in range(10)}

PUNCTUATION_MAP = {
    chr(0x111C5): " | ",    # danda
    chr(0x111C6): " || ",   # double danda
    chr(0x111C7): "/",
    chr(0x111C8): ".",
}

INHERENT_VOWEL = "a"      # every bare consonant carries /a/ by default



# CORE CONVERSION FUNCTION


def _resolve_anusvara(chars: list, pos: int) -> str:
    """Return the correct nasal allophone for the anusvara at *pos*."""
    j = pos + 1
    # skip whitespace between anusvara and following consonant
    while j < len(chars) and chars[j] in " \t":
        j += 1
    if j < len(chars):
        nxt = chars[j]
        for consonant_set, nasal_ipa in _NASAL_GROUPS:
            if nxt in consonant_set:
                return nasal_ipa
    return "m"   # default if word-final or before non-consonant


def sharada_to_ipa(text: str) -> str:
    """
    Convert a Sharada-script string to a broad IPA transcription.

    Rules applied:
      1. Consonant + virama        → consonant only (no inherent vowel)
      2. Consonant + vowel sign    → consonant + that vowel
      3. Consonant + anusvara      → consonant + /a/ + assimilated nasal
      4. Consonant + visarga       → consonant + /a/ + /h/
      5. Bare consonant            → consonant + inherent /a/
      6. Independent vowel         → vowel IPA
      7. Anusvara (standalone)     → assimilated nasal
      8. Visarga (standalone)      → /h/
      9. Avagraha                  → ʔ  (marks elision)
    """
    chars = list(text)
    n = len(chars)
    out = []
    i = 0

    while i < n:
        c = chars[i]

        # Consonant 
        if c in CONSONANTS:
            out.append(CONSONANTS[c])
            i += 1

            if i >= n:
                out.append(INHERENT_VOWEL)

            elif chars[i] == VIRAMA:
                i += 1                        # virama: no inherent vowel

            elif chars[i] in VOWEL_SIGNS:
                out.append(VOWEL_SIGNS[chars[i]])
                i += 1

            elif chars[i] == ANUSVARA:
                out.append(INHERENT_VOWEL)
                out.append(_resolve_anusvara(chars, i))
                i += 1

            elif chars[i] == VISARGA:
                out.append(INHERENT_VOWEL)
                out.append("h")
                i += 1

            else:
                out.append(INHERENT_VOWEL)    # bare consonant

        # Independent vowel
        elif c in INDEPENDENT_VOWELS:
            out.append(INDEPENDENT_VOWELS[c])
            i += 1

        # Standalone anusvara
        elif c == ANUSVARA:
            out.append(_resolve_anusvara(chars, i))
            i += 1

        # Visarga 
        elif c == VISARGA:
            out.append("h")
            i += 1

        # Avagraha (elision) 
        elif c == AVAGRAHA:
            out.append("ʔ")
            i += 1

        # ── Digits
        elif c in SHARADA_DIGITS:
            out.append(SHARADA_DIGITS[c])
            i += 1

        # ── Sharada punctuation 
        elif c in PUNCTUATION_MAP:
            out.append(PUNCTUATION_MAP[c])
            i += 1

        # ── ASCII pass-through (spaces, digits, Latin letters, etc.) ────────
        elif c.isascii():
            out.append(c)
            i += 1

        # ── Cantillation mark (U+11180) — skip silently ─────────────────────
        elif ord(c) == 0x11180:
            i += 1

        # ── Whitespace ──────────────────────────────────────────────────────
        elif c in " \t\n\r":
            out.append(c)
            i += 1

        # ── Unknown Sharada character ────────────────────────────────────────
        else:
            out.append(f"[U+{ord(c):05X}]")
            i += 1

    return "".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: Character inventory
# ─────────────────────────────────────────────────────────────────────────────

def _is_sharada(ch: str) -> bool:
    return 0x11180 <= ord(ch) <= 0x111DF


def character_inventory(text: str) -> None:
    """Print a table of all Sharada characters found in *text*."""
    counts = Counter(ch for ch in text if _is_sharada(ch))
    print(f"\n{'CP':<10} {'Ch':<4} {'Count':>7}  {'Tag':<5}  Name")
    print("─" * 72)
    for ch, cnt in sorted(counts.items(), key=lambda x: ord(x[0])):
        cp = ord(ch)
        name = unicodedata.name(ch, f"<U+{cp:05X}>")
        if ch in CONSONANTS:           tag = "C"
        elif ch in VOWEL_SIGNS:        tag = "Vm"
        elif ch in INDEPENDENT_VOWELS: tag = "Vi"
        elif ch == VIRAMA:             tag = "VIR"
        elif ch == ANUSVARA:           tag = "ANS"
        elif ch == VISARGA:            tag = "VIS"
        elif ch in PUNCTUATION_MAP:    tag = "PUN"
        elif ch in SHARADA_DIGITS:     tag = "DIG"
        else:                          tag = "?"
        print(f"U+{cp:05X}    {ch}   {cnt:7d}  {tag:<5}  {name}")
    print(f"\nTotal unique Sharada chars: {len(counts)}")
    print(f"Total Sharada char tokens : {sum(counts.values())}")


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT MODES
# ─────────────────────────────────────────────────────────────────────────────

def convert_corpus(input_path: str, output_path: str) -> None:
    """
    Read the corpus line by line, convert each line to IPA,
    and write paired output:

        [original Sharada]
        [IPA transcription]
        (blank line)
    """
    text = Path(input_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    out_lines = []
    converted = 0
    skipped   = 0

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            skipped += 1
            continue
        ipa = sharada_to_ipa(stripped)
        out_lines.append(f"{ipa}")
        converted += 1

    Path(output_path).write_text("\n".join(out_lines), encoding="utf-8")

    print(f"✓  IPA conversion complete")
    print(f"   Input  : {input_path}  ({len(lines)} lines)")
    print(f"   Output : {output_path}")
    print(f"   Lines converted : {converted}")
    print(f"   Lines skipped   : {skipped}")


def convert_single_word(word: str) -> None:
    ipa = sharada_to_ipa(word)
    print(f"\nInput  : {word}")
    print(f"IPA    : /{ipa}/")


def convert_word_table(input_path: str, output_path: str) -> None:
    """
    Build a deduplicated word-level IPA table from the corpus.
    Output is a TSV: word <TAB> IPA
    """
    text = Path(input_path).read_text(encoding="utf-8")
    seen = {}
    strip_chars = (
        chr(0x111C5) + chr(0x111C6) + chr(0x111C7) + chr(0x111C8) + " \t\n"
    )

    for token in text.split():
        core = token.strip(strip_chars)
        if core and core not in seen:
            seen[core] = sharada_to_ipa(core)

    rows = [f"{w}\t{ipa}" for w, ipa in sorted(seen.items(), key=lambda x: x[0])]
    Path(output_path).write_text("\n".join(rows), encoding="utf-8")

    print(f"✓  Word-level IPA table written")
    print(f"   Input  : {input_path}")
    print(f"   Output : {output_path}  ({len(rows)} unique tokens)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sharada_to_ipa.py",
        description="Rule-based Sharada → IPA G2P converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sharada_to_ipa.py corpus.txt
  python sharada_to_ipa.py corpus.txt -o gita_ipa.txt
  python sharada_to_ipa.py --word <sharada_token>
  python sharada_to_ipa.py --word-table corpus.txt -o words_ipa.tsv
  python sharada_to_ipa.py --inventory corpus.txt
        """,
    )
    p.add_argument("corpus", nargs="?", help="Path to Sharada corpus (.txt)")
    p.add_argument("-o", "--output",   default=None,
                   help="Output file path (default: <corpus>_ipa.txt)")
    p.add_argument("--word",       metavar="TOKEN",
                   help="Convert a single Sharada word to IPA")
    p.add_argument("--word-table", action="store_true",
                   help="Build deduplicated word↔IPA TSV from corpus")
    p.add_argument("--inventory",  action="store_true",
                   help="Print character inventory of corpus")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    # ── Single word ──────────────────────────────────────────────────────────
    if args.word:
        convert_single_word(args.word)
        return

    # ── Corpus required for everything else ──────────────────────────────────
    if not args.corpus:
        parser.print_help()
        sys.exit(1)

    if not Path(args.corpus).exists():
        print(f"ERROR: file not found: {args.corpus}")
        sys.exit(1)

    if args.inventory:
        text = Path(args.corpus).read_text(encoding="utf-8")
        character_inventory(text)
        return

    if args.word_table:
        stem   = Path(args.corpus).stem
        outf   = args.output or f"{stem}_ipa_words.tsv"
        convert_word_table(args.corpus, outf)
        return

    stem   = Path(args.corpus).stem
    outf   = args.output or f"{stem}_ipa.txt"
    convert_corpus(args.corpus, outf)


if __name__ == "__main__":
    main()