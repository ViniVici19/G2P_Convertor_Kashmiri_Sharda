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

The virama (U+111C0) suppresses the inherent vowel, allowing consonant clusters. The anusvara (U+11181) is a nasal marker resolved contextually as described above. The visarga (U+11182) is a post-vocalic aspiration marker that undergoes sandhi assimilation depending on the following consonant (see Section 3.6, Rules R6–R8). The candrabindu (U+11180) is a vowel nasalisation marker that adds a nasal quality to the preceding vowel without introducing a separate nasal consonant. The avagraha (U+111C1) marks sandhi elision and is rendered as a glottal stop ʔ. The jihvamuliya (U+111C2) is a rare allophone of visarga that represents a voiceless velar fricative [x], used specifically before velar stops. The upadhmaniya (U+111C3) is the corresponding voiceless bilabial fricative [ɸ], used before labial stops. The OM sign (U+111C4) represents the sacred syllable and is transcribed as oːm. Sharada digits (U+111D0 through U+111D9) are converted to their Arabic numeral equivalents.

3.3 The Core Conversion Function

The function sharada_to_ipa(text) is the main entry point. It converts the input string to a list of characters and iterates through them with an index pointer. For each character, it checks a series of conditions in order:

First, if the character is a consonant, it emits the consonant IPA and then looks ahead. If the next character is a virama, it advances past it, suppressing the inherent vowel. If the next character is a vowel sign, it emits the matra IPA. If the next character is an anusvara, it emits the inherent "a" and then applies the anusvara resolution rules (place assimilation or vowel nasalisation depending on context). If the next character is a visarga, it emits the inherent "a" followed by the sandhi-resolved visarga output. If nothing special follows, it emits the inherent "a".

Second, if the character is an independent vowel, it emits the vowel IPA directly.

Third, standalone anusvara is resolved using the same contextual rules: place assimilation before stops, vowel nasalisation before sibilants or ha, and default "m" otherwise.

Fourth, standalone visarga is resolved using sandhi rules: assimilation before sibilants, voiceless velar fricative before velars, voiceless bilabial fricative before labials, and plain "h" otherwise.

Fifth, avagraha emits a glottal stop.

Sixth, jihvamuliya emits voiceless velar fricative [x], upadhmaniya emits voiceless bilabial fricative [ɸ], and the OM sign emits oːm.

Seventh, Sharada digits and punctuation are converted to their ASCII equivalents.

Eighth, ASCII characters pass through unchanged.

Ninth, candrabindu nasalises the preceding vowel by appending a combining tilde diacritic.

Finally, any truly unrecognized character produces a bracketed placeholder like [U+XXXXX], though we found that no such fallbacks occur when processing our corpus.

The function _resolve_anusvara scans forward from the anusvara position, skipping whitespace, to find the next consonant and determine the appropriate nasal. When the following character is a sibilant or ha, it returns a nasalisation diacritic instead. The function _resolve_visarga performs analogous lookahead to determine the correct sandhi output for visarga. The function _is_sharada simply checks whether a character falls within the Sharada Unicode range.

3.5 Reporting and CLI

The script provides three reporting modes. The annotate_lines function prints each line of input with its IPA transcription below. The word_table function extracts unique words and prints them alongside their IPA. The character_inventory function counts all Sharada characters in the input and prints a frequency table with their Unicode names and category tags.

The command-line interface supports the following usage:

python sharada_to_ipa.py corpus.txt                  -- convert the corpus to IPA (generates a new text file)
python sharada_to_ipa.py --word <word>               -- convert a single Sharada word to IPA
python sharada_to_ipa.py --annotate corpus.txt       -- output original lines with IPA transcription below each
python sharada_to_ipa.py --word-table corpus.txt     -- generate a deduplicated word ↔ IPA TSV table
python sharada_to_ipa.py --inventory corpus.txt      -- print a frequency table of Sharada characters


python ipa_to_roman.py corpus.txt                -- full pipeline: Sharada → IPA → Roman (one line per input line)
python ipa_to_roman.py --from-ipa file.txt       -- convert a pre-generated IPA file to Roman
python ipa_to_roman.py --ipa-string "<ipa>"      -- convert a single IPA string to Roman
python ipa_to_roman.py --word <word>             -- convert a single Sharada word (full pipeline)
python ipa_to_roman.py --word-table corpus.txt   -- generate a TSV with sharada / IPA / Roman columns
python ipa_to_roman.py --show-mapping            -- display the IPA → Roman mapping table


The code features Rishi.html file that upon being run is a GUI that soupports Sharada to IPA conversion.
To run it just, use a live server (supported on VS Code) and run it just like an ordinary HTML File.

Running with no arguments processes a built-in sample excerpt.


## 4. Training and Testing Methodology

Since this is a rule-based system rather than a learned model, the "training" phase consists of manual inspection. We use the first 100 non-empty lines of the corpus to verify the IPA output against known correct pronunciations, identify edge cases in sandhi and conjunct handling, and refine the mapping rules.

The remaining approximately 1,500 lines are reserved for testing. Evaluation metrics include phoneme error rate (PER), character coverage (the percentage of input characters that are successfully converted without falling back to placeholder output), and the correctness of contextual rules like anusvara assimilation and inherent vowel insertion.

In our analysis, the converter achieves full coverage on the corpus, with zero unknown-character fallbacks across all 1,653 non-empty lines.


## 5. Phonological Conversion Rules

This section documents every contextual rule implemented in the converter. For each rule, we describe what it does, the linguistic motivation behind it, the specific exception case in the corpus that necessitated it, and a before/after example showing how the output changes.

5.1 Rule R1: Candrabindu — Vowel Nasalisation

| Aspect | Detail |
|---|---|
| Character | Candrabindu (U+11180) |
| Output | Combining tilde ◌̃ appended to preceding vowel |
| Exception case | The candrabindu was previously misidentified as a "cantillation mark" and silently discarded. When the corpus line ॐ 𑆯𑇀𑆫𑆵 (OṂ ŚRĪḤ) begins with the nasalised vowel 𑆏𑆀, the candrabindu after the independent vowel O marks nasalisation. Skipping it produced "oː" when the correct output is "oː̃". |
| Example | 𑆏𑆀 → oː̃ (nasalised long o, not plain oː) |

5.2 Rule R2: Inherent Vowel Insertion and Suppression

| Aspect | Detail |
|---|---|
| Mechanism | Every consonant carries inherent "a" unless followed by virama, matra, anusvara, or visarga |
| Exception case | In Brahmic scripts, the inherent vowel is the most common source of G2P errors. The word 𑆣𑆫𑇀𑆩 (dharma) contains a virama between RA and MA, suppressing the inherent vowel to produce "d̪ʱarma" rather than "d̪ʱarama". Without this rule, every consonant cluster would incorrectly insert a spurious "a". The corpus contains 8,489 consonant-adjacent sequences where virama-based suppression is required. |
| Example | 𑆣𑆫𑇀𑆩 → d̪ʱarma (not d̪ʱarama) |

5.3 Rule R3: Avagraha as Glottal Stop

| Aspect | Detail |
|---|---|
| Character | Avagraha (U+111C1) |
| Output | Glottal stop ʔ |
| Exception case | In sandhi-fused Sanskrit text, the avagraha marks the elision of an initial vowel. The corpus contains 243 avagraha characters. For instance, 𑆥𑇀𑆫𑆡𑆩𑆾𑇁𑆣𑇀𑆪𑆳𑆪 (prathamo'dhyāya) has an avagraha between the final O of "prathamo" and the initial A (elided) of "adhyāya". Without a dedicated mapping, this character would either fall through to the unknown-character placeholder or be silently dropped, losing the phonological boundary between the two morphemes. |
| Example | 𑆥𑇀𑆫𑆡𑆩𑆾𑇁𑆣𑇀𑆪𑆳𑆪 → prat̪ʰamoːʔd̪ʱjaːja |

5.4 Rule R4: Anusvara Place Assimilation

| Aspect | Detail |
|---|---|
| Character | Anusvara (U+11181) before a stop/nasal consonant |
| Output | Nasal consonant at same place of articulation as following stop |
| Assimilation table | Before velars → ŋ, before palatals → ɲ, before retroflexes → ɳ, before dentals → n, before labials → m |
| Exception case | The corpus contains 1,374 anusvara-before-consonant sequences. The word 𑆱𑆁𑆘𑆪 (saṃjaya) has anusvara before palatal JA. Without assimilation, the output would be "samdʑaja"; with assimilation, it correctly becomes "saɲdʑaja" because the nasal adopts the palatal place of the following consonant. Similarly, 𑆱𑆕𑇀𑆓 (saṅga) has anusvara before velar GA, producing "saŋɡa" rather than "samɡa". |
| Example | 𑆱𑆁𑆘𑆪 → saɲdʑaja (not samdʑaja) |

5.5 Rule R5: Anusvara Nasalisation before Sibilants and Ha

| Aspect | Detail |
|---|---|
| Character | Anusvara (U+11181) before SHA (U+111AF), SSA (U+111B0), SA (U+111B1), or HA (U+111B2) |
| Output | Nasalisation diacritic ◌̃ on preceding vowel |
| Exception case | The anusvara place assimilation rule (R4) only covers stops and nasals grouped by place. Sibilants (ɕ, ʂ, s) and the glottal fricative ɦ do not belong to any of those five articulatory groups. In Sanskrit phonology, anusvara before a sibilant or ha does not become a separate nasal consonant; instead, it nasalises the preceding vowel. The word 𑆱𑆁𑆯𑆪 (saṃśaya, meaning "doubt") has anusvara before palatal sibilant SHA. Under the old default-to-m rule, this produced "samɕaja", which implies a bilabial nasal [m] that is phonetically inappropriate before a palatal fricative. The corrected output is "sã̃ɕaja" with a nasalised vowel. The same pattern occurs in 𑆱𑆁𑆲𑆳𑆫 (saṃhāra) where anusvara precedes HA. |
| Example | 𑆱𑆁𑆲𑆳𑆫 → sã̃ɦaːra (not samɦaːra) |

5.6 Rule R6: Visarga Sandhi — Assimilation before Sibilants

| Aspect | Detail |
|---|---|
| Character | Visarga (U+11182) followed (possibly across whitespace) by SHA, SSA, or SA |
| Output | Matching sibilant IPA (ɕ, ʂ, or s respectively) |
| Exception case | The corpus contains 215 visarga-before-sibilant sequences. In Sanskrit external sandhi, visarga completely assimilates to a following sibilant: /aḥ ś/ → /aɕ ɕ/. The phrase 𑆑𑆫𑇀𑆟𑆯𑇀𑆖 𑆑𑆸𑆥𑆯𑇀𑆖 contains a visarga on the HA of "karṇaḥ" followed by SA in "ca". Without this rule, the output would be "karɳah tɕa", but in recitation the visarga assimilates to produce "karɳaɕ tɕa". Similarly, 𑆢𑆶𑆂𑆰𑇀𑆑𑆸𑆠 (duḥṣkṛta) has visarga before retroflex SSA, assimilating to produce "d̪uʂʂkr̩t̪a" rather than "d̪uhʂkr̩t̪a". |
| Example | 𑆤𑆩𑆂 𑆯𑇀𑆫𑆵 → namaɕ ɕriː (not namah ɕriː) |

5.7 Rule R7: Visarga Sandhi — Jihvamuliya before Voiceless Velars

| Aspect | Detail |
|---|---|
| Character | Visarga (U+11182) followed by KA (U+11191) or KHA (U+11192); also the explicit Jihvamuliya character (U+111C2) |
| Output | Voiceless velar fricative [x] |
| Exception case | The corpus contains 78 visarga-before-KA sequences. In Vedic and classical Sanskrit phonology, visarga before a voiceless velar becomes the jihvamuliya, a voiceless velar fricative articulated at the back of the tongue. The compound 𑆢𑆶𑆂𑆑𑆸𑆠 (duḥkṛta, "wrongdoing") has visarga before KA. The naïve output "d̪uhkr̩t̪a" misrepresents the pronunciation; the correct output is "d̪uxkr̩t̪a", where [x] reflects the velar place of articulation shared with the following stop. The explicit Jihvamuliya character (U+111C2), if encountered, maps directly to [x]. |
| Example | 𑆤𑆂 𑆑 → nax ka (not nah ka) |

5.8 Rule R8: Visarga Sandhi — Upadhmaniya before Voiceless Labials

| Aspect | Detail |
|---|---|
| Character | Visarga (U+11182) followed by PA (U+111A5) or PHA (U+111A6); also the explicit Upadhmaniya character (U+111C3) |
| Output | Voiceless bilabial fricative [ɸ] |
| Exception case | The corpus contains 137 visarga-before-PA sequences, the single largest visarga sandhi context. In Sanskrit, visarga before a voiceless labial becomes the upadhmaniya, a voiceless bilabial fricative. The phrase 𑆩𑆳𑆩𑆑𑆳𑆂 𑆥𑆳𑆟𑇀𑆝𑆮𑆳𑆂 (māmakāḥ pāṇḍavāḥ, "my sons and the sons of Pāṇḍu") has visarga on māmakāḥ followed by PA. Without this rule, the output would be "maːmakaːh paːɳɖaʋaːh", but the phonologically accurate output is "maːmakaːɸ paːɳɖaʋaːh", reflecting the labial place assimilation. The explicit Upadhmaniya character (U+111C3), if encountered, maps directly to [ɸ]. |
| Example | 𑆩𑆳𑆩𑆑𑆳𑆂 𑆥𑆳𑆟𑇀𑆝𑆮𑆳𑆂 → maːmakaːɸ paːɳɖaʋaːh (not maːmakaːh paːɳɖaʋaːh) |

5.9 Rule R9: Jihvamuliya Character

| Aspect | Detail |
|---|---|
| Character | Jihvamuliya (U+111C2) |
| Output | Voiceless velar fricative [x] |
| Exception case | The Sharada Unicode block includes a dedicated codepoint for the jihvamuliya, separate from the contextual visarga sandhi rule. While our corpus uses the composed visarga+KA sequence rather than the standalone jihvamuliya character, other Sharada manuscripts and digital texts may use this codepoint directly. Without handling it, the character would fall through to the unknown-character placeholder, producing "[U+111C2]" in the output. |
| Example | 𑇂 → x |

5.10 Rule R10: Upadhmaniya Character

| Aspect | Detail |
|---|---|
| Character | Upadhmaniya (U+111C3) |
| Output | Voiceless bilabial fricative [ɸ] |
| Exception case | Analogous to Rule R9. The Sharada Unicode block includes a dedicated codepoint for the upadhmaniya. Some Vedic manuscripts and Unicode-encoded texts use this character explicitly rather than relying on visarga sandhi. Without this rule, the character would produce a placeholder output. |
| Example | 𑇃 → ɸ |

5.11 Rule R11: OM Sign

| Aspect | Detail |
|---|---|
| Character | OM (U+111C4) |
| Output | oːm |
| Exception case | The Sharada OM sign is a single ligature character that represents the sacred syllable. Some texts write OM as the sequence O+Candrabindu+MA, while others use this single codepoint. If the dedicated OM character appeared in a text without this rule, it would be emitted as a placeholder. We map it to "oːm" to match the conventional IPA transcription of the syllable. |
| Example | 𑇄 → oːm |


## 6. Character Mapping Reference

The following tables give the complete mapping from Sharada codepoints to IPA used by the converter.

6.1 Consonants

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

6.2 Vowels

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

6.3 Special Characters and Punctuation

| Character | Codepoint | Function | IPA Output |
|---|---|---|---|
| Candrabindu 𑆀 | U+11180 | Vowel nasalisation | ◌̃ (tilde on preceding vowel) |
| Anusvara 𑆁 | U+11181 | Nasal marker | Context-dependent (R4/R5) |
| Visarga 𑆂 | U+11182 | Post-vocalic aspiration | Context-dependent (R6/R7/R8 or h) |
| Virama 𑇀 | U+111C0 | Suppresses inherent vowel | (none, blocks "a") |
| Avagraha 𑇁 | U+111C1 | Sandhi elision | ʔ |
| Jihvamuliya 𑇂 | U+111C2 | Voiceless velar fricative | x |
| Upadhmaniya 𑇃 | U+111C3 | Voiceless bilabial fricative | ɸ |
| OM 𑇄 | U+111C4 | Sacred syllable | oːm |
| Single Danda 𑇅 | U+111C5 | Half-verse break | \| |
| Double Danda 𑇆 | U+111C6 | Verse end | \|\| |
| Digits 𑇐–𑇙 | U+111D0–D9 | Numerals 0–9 | 0–9 |


## 7. Challenges and Theoretical Issues

Building a G2P system for Sharada script presents several challenges that are inherent to the nature of the script, the languages it encodes, and the limitations of a rule-based approach.

7.1 Sandhi and Word Boundary Ambiguity

Sanskrit text, which forms our corpus, is written with extensive sandhi, the phonological fusion of sounds across word boundaries. When two words are joined by sandhi, the resulting grapheme sequence may not correspond to a simple concatenation of the individual words' phonemes. For example, a final "a" and an initial "a" may merge into a long "aa", or a final vowel may cause the elision of an initial vowel marked by avagraha. A character-by-character converter handles each grapheme in isolation and cannot reconstruct the underlying morpheme boundaries, making it difficult to distinguish sandhi-fused forms from genuinely long vowels or consonant clusters.

7.2 The Inherent Vowel Problem

The most fundamental challenge in any Brahmic script G2P system is determining when a consonant carries its inherent vowel "a" and when it does not. In Sharada, the virama explicitly suppresses the inherent vowel, but in practice, scribes and modern renderings do not always use it consistently. This is less of a problem in our corpus, which uses virama systematically, but in handwritten manuscripts or OCR-derived text, missing or misplaced viramas would cause the converter to insert spurious "a" vowels or fail to suppress them.

7.3 Anusvara Ambiguity

The anusvara character has context-dependent pronunciation: it assimilates to the place of articulation of the following consonant. Our converter handles this by scanning ahead in the text. However, when the anusvara appears at a word boundary or before a vowel, the correct nasal is ambiguous. The converter defaults to "m" in such cases, which is the conventional choice but not always phonetically accurate, since the intended nasal may be velar or palatal depending on the morphological context that a rule-based system cannot access.

7.4 Diphthong Representation

The traditional Sanskrit vowels AI and AU are historically diphthongs, pronounced as /ai/ and /au/. Over time, in many modern Indic traditions, these have been monophthongized to ɛː and ɔː respectively. The choice between these two representations is a genuine phonological question. We adopted the monophthongized forms (ɛː and ɔː) as they align with the predominant modern pronunciation used in recitation traditions, but this means our IPA output does not reflect the archaic diphthongal values.

7.5 Supplementary Plane Unicode Handling

The Sharada block occupies the Supplementary Multilingual Plane at codepoints U+11180 through U+111DF. Unlike the Basic Multilingual Plane characters that most scripts use, these require surrogate pairs in UTF-16 and four-byte sequences in UTF-8. In Python, each Sharada character is a single code point, but in other environments such as JavaScript or certain text editors, string indexing may treat a single Sharada character as two units. This creates practical difficulties in text processing, rendering, and testing that are not encountered with more commonly used scripts.

7.6 Consonant Cluster Ambiguity

Sharada represents consonant clusters using sequences of consonant-virama-consonant. A sequence like ka-virama-sha is unambiguously the cluster "kʂ". However, the system must correctly handle arbitrarily deep stacking. When three or more consonants are clustered (for instance, in words like "striya" or "jnana"), the converter must correctly consume all virama-consonant pairs before emitting the final inherent vowel or matra. While our implementation handles this through its sequential processing, edge cases in deeply nested clusters or unusual conjunct forms in manuscripts can be problematic.

7.7 Lack of Ground Truth

Perhaps the most significant challenge is the absence of a verified gold-standard IPA transcription for Sharada text. Without an established reference dataset of Sharada words paired with their correct IPA, evaluation relies on manual comparison by people with knowledge of both the script and the phonology. This makes large-scale quantitative evaluation difficult and introduces the possibility of systematic errors going undetected in the mapping tables.


## 8. Example Output

Running the converter on the Sharada text for "shriimadbhagavadgiitaa" produces:

    Input:  𑆯𑇀𑆫𑆵𑆩𑆢𑇀𑆨𑆓𑆮𑆢𑇀𑆓𑆵𑆠𑆳
    Output: ɕriːmad̪bʱaɡaʋad̪ɡiːt̪aː

And for the opening of the first verse:

    Input:  𑆣𑆫𑇀𑆩𑆑𑇀𑆰𑆼𑆠𑇀𑆫𑆼 𑆑𑆶𑆫𑆶𑆑𑇀𑆰𑆼𑆠𑇀𑆫𑆼
    Output: d̪ʱarmakʂeːt̪reː kurukʂeːt̪reː


## 9. Requirements

Python 3.6 or later is required for proper handling of supplementary plane Unicode escapes. No external packages are needed.
