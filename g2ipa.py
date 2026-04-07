#!/usr/bin/env python3
"""
sharada_ipa.py — Sharada Script -> IPA (Phase 1)
=================================================
Converts Unicode Sharada text to a broad IPA transcription.

Usage:
    python sharada_ipa.py corpus.txt              # annotate whole file
    python sharada_ipa.py --word <word>           # single word
    python sharada_ipa.py --words corpus.txt      # word-by-word table
    python sharada_ipa.py --inventory corpus.txt  # character inventory
"""

import sys
import unicodedata
from collections import Counter

# ══════════════════════════════════════════════════════════════════════════
# CHARACTER TABLES
# Sharada = supplementary plane U+11180-U+111DF.
# Python requires \U000XXXXX (8-digit capital U) for codepoints > 0xFFFF.
# ══════════════════════════════════════════════════════════════════════════

# Build tables from codepoint integers to avoid escape-sequence errors
def _c(*codepoints):
    """Return a dict mapping chr(cp) -> ipa for parallel lists."""
    return codepoints

# Independent vowels
INDEPENDENT_VOWELS = {
    chr(0x11183): "a",
    chr(0x11184): "a\u02D0",
    chr(0x11185): "i",
    chr(0x11186): "i\u02D0",
    chr(0x11187): "u",
    chr(0x11188): "u\u02D0",
    chr(0x11189): "r\u0329",
    chr(0x1118A): "r\u0329\u02D0",
    chr(0x1118B): "l\u0329",
    chr(0x1118C): "l\u0329\u02D0",
    chr(0x1118D): "e\u02D0",
    chr(0x1118E): "\u025B\u02D0",
    chr(0x1118F): "o\u02D0",
    chr(0x11190): "\u0254\u02D0",
}

# Dependent vowel signs (matras)
VOWEL_SIGNS = {
    chr(0x111B3): "a\u02D0",
    chr(0x111B4): "i",
    chr(0x111B5): "i\u02D0",
    chr(0x111B6): "u",
    chr(0x111B7): "u\u02D0",
    chr(0x111B8): "r\u0329",
    chr(0x111B9): "r\u0329\u02D0",
    chr(0x111BA): "l\u0329",
    chr(0x111BB): "l\u0329\u02D0",
    chr(0x111BC): "e\u02D0",
    chr(0x111BD): "\u025B\u02D0",
    chr(0x111BE): "o\u02D0",
    chr(0x111BF): "\u0254\u02D0",
}

# Consonants
CONSONANTS = {
    # Velars
    chr(0x11191): "k",
    chr(0x11192): "k\u02B0",
    chr(0x11193): "\u0261",
    chr(0x11194): "\u0261\u02B1",
    chr(0x11195): "\u014B",
    # Palatals
    chr(0x11196): "t\u0255",
    chr(0x11197): "t\u0255\u02B0",
    chr(0x11198): "d\u0291",
    chr(0x11199): "d\u0291\u02B1",
    chr(0x1119A): "\u0272",
    # Retroflexes
    chr(0x1119B): "\u0288",
    chr(0x1119C): "\u0288\u02B0",
    chr(0x1119D): "\u0256",
    chr(0x1119E): "\u0256\u02B1",
    chr(0x1119F): "\u0273",
    # Dentals
    chr(0x111A0): "t\u032A",
    chr(0x111A1): "t\u032A\u02B0",
    chr(0x111A2): "d\u032A",
    chr(0x111A3): "d\u032A\u02B1",
    chr(0x111A4): "n",
    # Labials
    chr(0x111A5): "p",
    chr(0x111A6): "p\u02B0",
    chr(0x111A7): "b",
    chr(0x111A8): "b\u02B1",
    chr(0x111A9): "m",
    # Sonorants
    chr(0x111AA): "j",
    chr(0x111AB): "r",
    chr(0x111AC): "l",
    chr(0x111AD): "\u026D",
    chr(0x111AE): "\u028B",
    # Sibilants
    chr(0x111AF): "\u0255",
    chr(0x111B0): "\u0282",
    chr(0x111B1): "s",
    # Glottal
    chr(0x111B2): "\u0266",
}

# Nasal place assimilation: (set of following consonant codepoints) -> nasal IPA
_NASAL_ASSIMILATION = [
    ({chr(c) for c in range(0x11191, 0x11196)}, "\u014B"),  # velars  -> ng
    ({chr(c) for c in range(0x11196, 0x1119B)}, "\u0272"),  # palatals -> ny
    ({chr(c) for c in range(0x1119B, 0x111A0)}, "\u0273"),  # retro   -> nn
    ({chr(c) for c in range(0x111A0, 0x111A5)}, "n"),       # dentals -> n
    ({chr(c) for c in range(0x111A5, 0x111AA)}, "m"),       # labials -> m
]

VIRAMA   = chr(0x111C0)
ANUSVARA = chr(0x11181)
VISARGA  = chr(0x11182)
AVAGRAHA = chr(0x111C1)
INHERENT_V = "a"

SHARADA_DIGITS = {chr(0x111D0 + i): str(i) for i in range(10)}

PUNCTUATION = {
    chr(0x111C5): " | ",
    chr(0x111C6): " || ",
    chr(0x111C7): "/",
    chr(0x111C8): ".",
}

# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _resolve_anusvara(chars, pos):
    j = pos + 1
    while j < len(chars) and chars[j] in " \t":
        j += 1
    if j < len(chars):
        nxt = chars[j]
        for cset, nasal in _NASAL_ASSIMILATION:
            if nxt in cset:
                return nasal
    return "m"

def _is_sharada(ch):
    return 0x11180 <= ord(ch) <= 0x111DF

# ══════════════════════════════════════════════════════════════════════════
# CORE CONVERTER
# ══════════════════════════════════════════════════════════════════════════

def sharada_to_ipa(text):
    chars = list(text)
    n = len(chars)
    out = []
    i = 0

    while i < n:
        c = chars[i]

        if c in CONSONANTS:
            out.append(CONSONANTS[c])
            i += 1
            if i >= n:
                out.append(INHERENT_V)
            elif chars[i] == VIRAMA:
                i += 1                          # suppress inherent vowel
            elif chars[i] in VOWEL_SIGNS:
                out.append(VOWEL_SIGNS[chars[i]])
                i += 1
            elif chars[i] == ANUSVARA:
                out.append(INHERENT_V)
                out.append(_resolve_anusvara(chars, i))
                i += 1
            elif chars[i] == VISARGA:
                out.append(INHERENT_V)
                out.append("h")
                i += 1
            else:
                out.append(INHERENT_V)

        elif c in INDEPENDENT_VOWELS:
            out.append(INDEPENDENT_VOWELS[c])
            i += 1

        elif c == ANUSVARA:
            out.append(_resolve_anusvara(chars, i))
            i += 1

        elif c == VISARGA:
            out.append("h")
            i += 1

        elif c == AVAGRAHA:
            out.append("\u0294")        # glottal stop = elision site
            i += 1

        elif c in SHARADA_DIGITS:
            out.append(SHARADA_DIGITS[c])
            i += 1

        elif c in PUNCTUATION:
            out.append(PUNCTUATION[c])
            i += 1

        elif c.isascii():
            out.append(c)
            i += 1

        elif ord(c) == 0x11180:         # cantillation mark, skip
            i += 1

        elif c in " \t\n\r":
            out.append(c)
            i += 1

        else:
            out.append(f"[U+{ord(c):05X}]")
            i += 1

    return "".join(out)

# ══════════════════════════════════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════════════════════════════════

def character_inventory(text):
    counts = Counter(ch for ch in text if _is_sharada(ch))
    print(f"{'CP':<10} {'Ch':<4} {'Count':>6}  {'Tag':<4}  Name")
    print("-" * 68)
    for ch, cnt in sorted(counts.items(), key=lambda x: ord(x[0])):
        cp = ord(ch)
        name = unicodedata.name(ch, f"<U+{cp:05X}>")
        if ch in CONSONANTS:               tag = "C"
        elif ch in VOWEL_SIGNS:            tag = "Vm"
        elif ch in INDEPENDENT_VOWELS:     tag = "Vi"
        elif ch == VIRAMA:                 tag = "VIR"
        elif ch == ANUSVARA:               tag = "ANS"
        elif ch == VISARGA:                tag = "VIS"
        elif ch in PUNCTUATION:            tag = "PUN"
        elif ch in SHARADA_DIGITS:         tag = "DIG"
        else:                              tag = "?"
        print(f"U+{cp:05X}    {ch}   {cnt:6d}  {tag:<4}  {name}")


def annotate_lines(text):
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        print(f"[{lineno:03d}] {s}")
        print(f"      {sharada_to_ipa(s)}")
        print()


def word_table(text):
    seen = set()
    print(f"{'Word':<35}  IPA")
    print("-" * 68)
    for token in text.split():
        core = token.strip(
            chr(0x111C5) + chr(0x111C6) + chr(0x111C7) + chr(0x111C8)
        )
        if not core or core in seen:
            continue
        seen.add(core)
        print(f"{core:<35}  {sharada_to_ipa(core)}")


# ══════════════════════════════════════════════════════════════════════════
# SAMPLE (your excerpt)
# ══════════════════════════════════════════════════════════════════════════

SAMPLE = (
    "\U000111A2\U000111BE\U000111B0\U000111BD\U000111AB\U000111BC"
    "\U000111A0\U000111BD\U00011182 "
    "\U00011191\U000111B6\U000111AC\U00011194\U000111C0\U000111A4"
    "\U000111B3\U000111A4\U000111B3\U00011181 "
    "\U000111AE\U000111AB\U000111C0\U0001119F\U000111B1\U00011195"
    "\U000111C0\U00011191\U000111AB\U00011191\U000111B3\U000111AB"
    "\U00011191\U000111BD\U00011182 \U000111C5\n"
    "\U00011187\U000111A0\U000111C0\U000111B1\U000111B3\U000111A2"
    "\U000111C0\U000111AA\U000111A4\U000111C0\U000111A0\U000111BC "
    "\U00011198\U000111B3\U000111A0\U000111B4\U000111A3\U000111AB"
    "\U000111C0\U000111A9\U000111B3\U00011182 "
    "\U00011191\U000111B6\U000111AC\U000111A3\U000111AB\U000111C0"
    "\U000111A9\U000111B3\U000111AF\U000111C0\U00011196 "
    "\U000111AF\U000111B3\U000111AF\U000111C0\U000111AE\U000111A0"
    "\U000111B3\U00011182 \U000111C6 1-43\U000111C6"
)

# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("No file given. Running on built-in sample.\n")
        annotate_lines(SAMPLE)
        print("\n-- Word table --\n")
        word_table(SAMPLE)

    elif args[0] == "--inventory" and len(args) > 1:
        text = open(args[1], encoding="utf-8").read()
        character_inventory(text)

    elif args[0] == "--word" and len(args) > 1:
        w = args[1]
        print(f"{w}  ->  {sharada_to_ipa(w)}")

    elif args[0] == "--words" and len(args) > 1:
        text = open(args[1], encoding="utf-8").read()
        word_table(text)

    else:
        text = open(args[0], encoding="utf-8").read()
        if "--inventory" in args:
            character_inventory(text)
            print()
        annotate_lines(text)
