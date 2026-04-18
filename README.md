# Grapheme-to-Phoneme Mapping for Kashmiri written in the Sharada Script

This document describes the design and implementation of a rule-based Grapheme-to-Phoneme (G2P) conversion system for text written in the Sharada script (Unicode block U+11180 to U+111DF). The system converts Sharada characters into broad IPA (International Phonetic Alphabet) transcriptions. This README walks through the converter script, the character mappings it uses, the corpus it operates on, and known issues we have identified.


## 1. Background

The Sharada script is a historical Brahmic writing system that was used to write both Kashmiri and Sanskrit. Like other Indic scripts, Sharada is an abugida where each consonant carries an inherent vowel "a" that is suppressed by a virama or replaced by an explicit vowel sign (matra). The script includes support for independent vowels, consonant conjuncts, nasalization (anusvara), aspiration markers (visarga), and sandhi notation (avagraha).

Our converter, sharada_ipa.py, is a purely rule-based system with no machine learning component. It processes text character by character, applying deterministic lookup tables and contextual rules to produce IPA output.


## 2. The Corpus

The corpus file (corpus.txt) contains 2,477 lines of text, of which 1,653 are non-empty. The text is a transcription of the Bhagavad Gita written entirely in the Sharada script, sourced from the manuscript rbsc_ms36_bhagavadgita_sarada-script.pdf. All 18 chapters are covered, with 1,443 verse-ending double dandas and 783 half-verse single dandas.

The corpus uses 71 unique Sharada codepoints. We verified that every character in the corpus is either an ASCII character or a valid Sharada Unicode character; there are no stray codepoints from other scripts. The only anomalous line is the very first one, "shrImadbhagavadgItA", which is an ASCII transliteration rather than Sharada text.

For evaluation purposes, we treat the first 100 non-empty lines as our development set, used for inspecting and refining the G2P rules. The remaining approximately 1,553 lines serve as the test set for measuring conversion accuracy and coverage.


## 3. How the Converter Works

The converter is implemented in a single file, sharada_ipa.py, which requires only the Python standard library (sys, unicodedata, collections). It has no external dependencies.

3.1 Character Mapping Tables

At the core of the system are four lookup dictionaries that map Sharada codepoints to IPA strings.

The first table, INDEPENDENT_VOWELS, covers the 14 standalone vowel characters. These appear at the beginning of words or syllables where no consonant precedes. For example, U+11183 maps to "a" (short a), U+11184 maps to "aː" (long aa), U+1118D maps to "eː", and so on.

The second table, VOWEL_SIGNS, covers the 13 dependent vowel diacritics (matras) that attach to consonants. These parallel the independent vowels but exclude the short "a", which is the inherent vowel that every consonant carries by default. When a consonant is followed by a vowel sign, the converter emits the consonant IPA plus the matra IPA instead of the inherent "a".

The third table, CONSONANTS, maps all 34 consonant characters organized by place of articulation. The velars (ka through nga) map to k, kʰ, ɡ, ɡʱ, ŋ. The palatals (ca through nya) map to tɕ, tɕʰ, dʑ, dʑʱ, ɲ. The retroflexes (tta through nna) map to ʈ, ʈʰ, ɖ, ɖʱ, ɳ. The dentals (ta through na) map to t̪, t̪ʰ, d̪, d̪ʱ, n. The labials (pa through ma) map to p, pʰ, b, bʱ, m. The sonorants (ya, ra, la, lla, va) map to j, r, l, ɭ, ʋ. The three sibilants (sha, ssa, sa) map to ɕ, ʂ, s respectively. Finally, ha maps to ɦ.

The fourth structure, _NASAL_ASSIMILATION, handles anusvara context. When the anusvara character appears before a consonant, its pronunciation assimilates to the place of articulation of that consonant. Before velars it becomes ŋ, before palatals it becomes ɲ, before retroflexes ɳ, before dentals n, and before labials m. If no consonant follows, it defaults to m.

3.2 Special Characters

The virama (U+111C0) suppresses the inherent vowel, allowing consonant clusters. The anusvara (U+11181) is a nasal marker resolved contextually as described above. The visarga (U+11182) produces an "h" sound. The avagraha (U+111C1) marks sandhi elision and is rendered as a glottal stop ʔ. Sharada digits (U+111D0 through U+111D9) are converted to their Arabic numeral equivalents.

3.3 The Core Conversion Function

The function sharada_to_ipa(text) is the main entry point. It converts the input string to a list of characters and iterates through them with an index pointer. For each character, it checks a series of conditions in order:

First, if the character is a consonant, it emits the consonant IPA and then looks ahead. If the next character is a virama, it advances past it, suppressing the inherent vowel. If the next character is a vowel sign, it emits the matra IPA. If the next character is an anusvara or visarga, it emits the inherent "a" followed by the appropriate nasal or "h". If nothing special follows, it emits the inherent "a".

Second, if the character is an independent vowel, it emits the vowel IPA directly.

Third, standalone anusvara and visarga are handled as nasal and "h" respectively.

Fourth, avagraha emits a glottal stop.

Fifth, Sharada digits and punctuation are converted to their ASCII equivalents.

Sixth, ASCII characters pass through unchanged.

Finally, the cantillation mark (U+11180) is silently skipped, and any truly unrecognized character would produce a bracketed placeholder like [U+XXXXX], though we found that no such fallbacks occur when processing our corpus.

3.4 Helper Functions

The function _resolve_anusvara scans forward from the anusvara position, skipping whitespace, to find the next consonant and determine the appropriate nasal. The function _is_sharada simply checks whether a character falls within the Sharada Unicode range.

3.5 Reporting and CLI

The script provides three reporting modes. The annotate_lines function prints each line of input with its IPA transcription below. The word_table function extracts unique words and prints them alongside their IPA. The character_inventory function counts all Sharada characters in the input and prints a frequency table with their Unicode names and category tags.

The command-line interface supports the following usage:

    python sharada_ipa.py corpus.txt              -- annotate the whole file
    python sharada_ipa.py --word <word>            -- convert a single word
    python sharada_ipa.py --words corpus.txt       -- print word-by-word table
    python sharada_ipa.py --inventory corpus.txt   -- character frequency report

Running with no arguments processes a built-in sample excerpt.


## 4. Training and Testing Methodology

Since this is a rule-based system rather than a learned model, the "training" phase consists of manual inspection. We use the first 100 non-empty lines of the corpus to verify the IPA output against known correct pronunciations, identify edge cases in sandhi and conjunct handling, and refine the mapping rules.

The remaining approximately 1,500 lines are reserved for testing. Evaluation metrics include phoneme error rate (PER), character coverage (the percentage of input characters that are successfully converted without falling back to placeholder output), and the correctness of contextual rules like anusvara assimilation and inherent vowel insertion.

In our analysis, the converter achieves full coverage on the corpus, with zero unknown-character fallbacks across all 1,653 non-empty lines.


## 5. Character Mapping Reference

The following tables give the complete mapping from Sharada codepoints to IPA used by the converter.

5.1 Consonants

| Codepoint | Sharada | Name | IPA | Place |
|---|---|---|---|---|
| U+11191 | 𑆑 | KA | k | Velar |
| U+11192 | 𑆒 | KHA | kʰ | Velar |
| U+11193 | 𑆓 | GA | ɡ | Velar |
| U+11194 | 𑆔 | GHA | ɡʱ | Velar |
| U+11195 | 𑆕 | NGA | ŋ | Velar |
| U+11196 | 𑆖 | CA | tɕ | Palatal |
| U+11197 | 𑆗 | CHA | tɕʰ | Palatal |
| U+11198 | 𑆘 | JA | dʑ | Palatal |
| U+11199 | 𑆙 | JHA | dʑʱ | Palatal |
| U+1119A | 𑆚 | NYA | ɲ | Palatal |
| U+1119B | 𑆛 | TTA | ʈ | Retroflex |
| U+1119C | 𑆜 | TTHA | ʈʰ | Retroflex |
| U+1119D | 𑆝 | DDA | ɖ | Retroflex |
| U+1119E | 𑆞 | DDHA | ɖʱ | Retroflex |
| U+1119F | 𑆟 | NNA | ɳ | Retroflex |
| U+111A0 | 𑆠 | TA | t̪ | Dental |
| U+111A1 | 𑆡 | THA | t̪ʰ | Dental |
| U+111A2 | 𑆢 | DA | d̪ | Dental |
| U+111A3 | 𑆣 | DHA | d̪ʱ | Dental |
| U+111A4 | 𑆤 | NA | n | Dental |
| U+111A5 | 𑆥 | PA | p | Labial |
| U+111A6 | 𑆦 | PHA | pʰ | Labial |
| U+111A7 | 𑆧 | BA | b | Labial |
| U+111A8 | 𑆨 | BHA | bʱ | Labial |
| U+111A9 | 𑆩 | MA | m | Labial |
| U+111AA | 𑆪 | YA | j | Sonorant |
| U+111AB | 𑆫 | RA | r | Sonorant |
| U+111AC | 𑆬 | LA | l | Sonorant |
| U+111AD | 𑆭 | LLA | ɭ | Retroflex Lateral |
| U+111AE | 𑆮 | VA | ʋ | Sonorant |
| U+111AF | 𑆯 | SHA | ɕ | Palatal Sibilant |
| U+111B0 | 𑆰 | SSA | ʂ | Retroflex Sibilant |
| U+111B1 | 𑆱 | SA | s | Dental Sibilant |
| U+111B2 | 𑆲 | HA | ɦ | Glottal |

5.2 Vowels

Each vowel exists in two forms: an independent letter used word-initially, and a dependent sign (matra) attached to a consonant.

| Independent | Codepoint | Matra | Codepoint | IPA |
|---|---|---|---|---|
| 𑆃 A | U+11183 | (inherent) | — | a |
| 𑆄 AA | U+11184 | 𑆳 | U+111B3 | aː |
| 𑆅 I | U+11185 | 𑆴 | U+111B4 | i |
| 𑆆 II | U+11186 | 𑆵 | U+111B5 | iː |
| 𑆇 U | U+11187 | 𑆶 | U+111B6 | u |
| 𑆈 UU | U+11188 | 𑆷 | U+111B7 | uː |
| 𑆉 Vocalic R | U+11189 | 𑆸 | U+111B8 | r̩ |
| 𑆊 Vocalic RR | U+1118A | 𑆹 | U+111B9 | r̩ː |
| 𑆋 Vocalic L | U+1118B | 𑆺 | U+111BA | l̩ |
| 𑆌 Vocalic LL | U+1118C | 𑆻 | U+111BB | l̩ː |
| 𑆍 E | U+1118D | 𑆼 | U+111BC | eː |
| 𑆎 AI | U+1118E | 𑆽 | U+111BD | ɛː |
| 𑆏 O | U+1118F | 𑆾 | U+111BE | oː |
| 𑆐 AU | U+11190 | 𑆿 | U+111BF | ɔː |

5.3 Special Characters and Punctuation

| Character | Codepoint | Function | IPA Output |
|---|---|---|---|
| Virama 𑇀 | U+111C0 | Suppresses inherent vowel | (none, blocks "a") |
| Anusvara 𑆁 | U+11181 | Nasal marker | Context-dependent nasal |
| Visarga 𑆂 | U+11182 | Voiceless aspiration | h |
| Avagraha 𑇁 | U+111C1 | Sandhi elision | ʔ |
| Single Danda 𑇅 | U+111C5 | Half-verse break | \| |
| Double Danda 𑇆 | U+111C6 | Verse end | \|\| |
| Digits 𑇐–𑇙 | U+111D0–D9 | Numerals 0–9 | 0–9 |


## 6. Challenges and Theoretical Issues

Building a G2P system for Sharada script presents several challenges that are inherent to the nature of the script, the languages it encodes, and the limitations of a rule-based approach.

6.1 Sandhi and Word Boundary Ambiguity

Sanskrit text, which forms our corpus, is written with extensive sandhi, the phonological fusion of sounds across word boundaries. When two words are joined by sandhi, the resulting grapheme sequence may not correspond to a simple concatenation of the individual words' phonemes. For example, a final "a" and an initial "a" may merge into a long "aa", or a final vowel may cause the elision of an initial vowel marked by avagraha. A character-by-character converter handles each grapheme in isolation and cannot reconstruct the underlying morpheme boundaries, making it difficult to distinguish sandhi-fused forms from genuinely long vowels or consonant clusters.

6.2 The Inherent Vowel Problem

The most fundamental challenge in any Brahmic script G2P system is determining when a consonant carries its inherent vowel "a" and when it does not. In Sharada, the virama explicitly suppresses the inherent vowel, but in practice, scribes and modern renderings do not always use it consistently. This is less of a problem in our corpus, which uses virama systematically, but in handwritten manuscripts or OCR-derived text, missing or misplaced viramas would cause the converter to insert spurious "a" vowels or fail to suppress them.

6.3 Anusvara Ambiguity

The anusvara character has context-dependent pronunciation: it assimilates to the place of articulation of the following consonant. Our converter handles this by scanning ahead in the text. However, when the anusvara appears at a word boundary or before a vowel, the correct nasal is ambiguous. The converter defaults to "m" in such cases, which is the conventional choice but not always phonetically accurate, since the intended nasal may be velar or palatal depending on the morphological context that a rule-based system cannot access.

6.4 Diphthong Representation

The traditional Sanskrit vowels AI and AU are historically diphthongs, pronounced as /ai/ and /au/. Over time, in many modern Indic traditions, these have been monophthongized to ɛː and ɔː respectively. The choice between these two representations is a genuine phonological question. We adopted the monophthongized forms (ɛː and ɔː) as they align with the predominant modern pronunciation used in recitation traditions, but this means our IPA output does not reflect the archaic diphthongal values.

6.5 Supplementary Plane Unicode Handling

The Sharada block occupies the Supplementary Multilingual Plane at codepoints U+11180 through U+111DF. Unlike the Basic Multilingual Plane characters that most scripts use, these require surrogate pairs in UTF-16 and four-byte sequences in UTF-8. In Python, each Sharada character is a single code point, but in other environments such as JavaScript or certain text editors, string indexing may treat a single Sharada character as two units. This creates practical difficulties in text processing, rendering, and testing that are not encountered with more commonly used scripts.

6.6 Consonant Cluster Ambiguity

Sharada represents consonant clusters using sequences of consonant-virama-consonant. A sequence like ka-virama-sha is unambiguously the cluster "kʂ". However, the system must correctly handle arbitrarily deep stacking. When three or more consonants are clustered (for instance, in words like "striya" or "jnana"), the converter must correctly consume all virama-consonant pairs before emitting the final inherent vowel or matra. While our implementation handles this through its sequential processing, edge cases in deeply nested clusters or unusual conjunct forms in manuscripts can be problematic.

6.7 Lack of Ground Truth

Perhaps the most significant challenge is the absence of a verified gold-standard IPA transcription for Sharada text. Without an established reference dataset of Sharada words paired with their correct IPA, evaluation relies on manual comparison by people with knowledge of both the script and the phonology. This makes large-scale quantitative evaluation difficult and introduces the possibility of systematic errors going undetected in the mapping tables.


## 7. Example Output

Running the converter on the Sharada text for "shriimadbhagavadgiitaa" produces:

    Input:  𑆯𑇀𑆫𑆵𑆩𑆢𑇀𑆨𑆓𑆮𑆢𑇀𑆓𑆵𑆠𑆳
    Output: ɕriːmad̪bʱaɡaʋad̪ɡiːt̪aː

And for the opening of the first verse:

    Input:  𑆣𑆫𑇀𑆩𑆑𑇀𑆰𑆼𑆠𑇀𑆫𑆼 𑆑𑆶𑆫𑆶𑆑𑇀𑆰𑆼𑆠𑇀𑆫𑆼
    Output: d̪ʱarmakʂeːt̪reː kurukʂeːt̪reː


## 8. Requirements

Python 3.6 or later is required for proper handling of supplementary plane Unicode escapes. No external packages are needed.
