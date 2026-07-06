"""ARPAbet → IPA conversion helpers.

Pure conversion logic with no g2p dependency — safe to import and unit-test
in isolation. The g2p singleton lives in ipa.py which imports from here.
"""

import re

# ---------------------------------------------------------------------------
# ARPAbet → IPA phoneme map — Oxford American (rhotic), OALD-US style.
#
# Design choices that make output track the Oxford Advanced Learner's
# Dictionary (American pronunciation):
#   - length marks on tense vowels: iː, uː, ɑː, ɔː  (e.g. see → siː)
#   - EH → e (OALD uses plain e for DRESS, not ɛ)
#   - rhotic: R keeps its /r/; ER carries r-colouring inline (bird → bɜːrd)
#   - AH and ER are STRESS-CONDITIONED — see REDUCED_VOWELS below
#
# This is the DEFAULT / stressed form for each phoneme. Stress-conditioned
# reductions are applied in _phone_to_ipa() before falling back to this table.
# ---------------------------------------------------------------------------

ARPA_IPA: dict[str, str] = {
    'AA': 'ɑː', 'AE': 'æ',  'AH': 'ʌ',  'AO': 'ɔː', 'AW': 'aʊ',
    'AY': 'aɪ', 'B':  'b',  'CH': 'tʃ', 'D':  'd',  'DH': 'ð',
    'EH': 'e',  'ER': 'ɜːr', 'EY': 'eɪ', 'F':  'f',  'G':  'ɡ',
    'HH': 'h',  'IH': 'ɪ',  'IY': 'iː', 'JH': 'dʒ', 'K':  'k',
    'L':  'l',  'M':  'm',  'N':  'n',  'NG': 'ŋ',  'OW': 'oʊ',
    'OY': 'ɔɪ', 'P':  'p',  'R':  'r',  'S':  's',  'SH': 'ʃ',
    'T':  't',  'TH': 'θ',  'UH': 'ʊ',  'UW': 'uː', 'V':  'v',
    'W':  'w',  'Y':  'j',  'Z':  'z',  'ZH': 'ʒ',
    # DX = alveolar flap (not emitted by g2p directly; produced by our
    # flapping pass — see _apply_flapping). OALD-US writes it as t̬.
    'DX': 't̬',
}

# ---------------------------------------------------------------------------
# Stress-conditioned reductions — the "special rules" that get us close to
# Oxford. ARPAbet marks vowel stress with a trailing digit: 0 = unstressed,
# 1 = primary, 2 = secondary. Some vowels change quality when unstressed:
#   - AH0 → ə  (schwa, e.g. 'about' → əˈbaʊt); AH1/AH2 → ʌ (STRUT vowel)
#   - ER0 → ər (weak r-coloured schwa, e.g. 'letter' → ˈlet̬ər);
#     ER1/ER2 → ɜːr (NURSE vowel, e.g. 'bird' → bɜːrd)
#   - IY0 → i  (short "happY" vowel, e.g. 'city' → ˈsɪt̬i, no length mark);
#     IY1/IY2 → iː (FLEECE vowel, e.g. 'see' → siː)
# ---------------------------------------------------------------------------

REDUCED_VOWELS: dict[str, str] = {
    'AH': 'ə',
    'ER': 'ər',
    'IY': 'i',
}

# Vowel nuclei — these carry the stress digit in ARPAbet
VOWELS: frozenset[str] = frozenset({
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY',
    'EH', 'ER', 'EY', 'IH', 'IY', 'OW',
    'OY', 'UH', 'UW',
})

# ---------------------------------------------------------------------------
# Syllabic-n triggers — consonants after which an unstressed AH0 + N collapses
# to a syllabic /n/ (the schwa is dropped). This is the OALD-US treatment of
# the '-tion/-sion/-en/-on' family:
#     station  → ˈsteɪʃn   (not ˈsteɪʃən)
#     question → ˈkwestʃn
#     button   → ˈbʌtn
#     listen   → ˈlɪsn
#     seven    → ˈsevn
# The drop only happens after CORONAL OBSTRUENTS (t, d, s, z, ʃ, ʒ, tʃ, dʒ,
# θ, ð) and the labiodentals f/v — the places of articulation where English
# actually forms a syllabic nasal. After other consonants the schwa is kept:
#     happen → ˈhæpən   bacon → ˈbeɪkən   common → ˈkɒmən   heron → ˈherən
# ---------------------------------------------------------------------------

SYLLABIC_N_TRIGGERS: frozenset[str] = frozenset({
    'T', 'D', 'S', 'Z', 'SH', 'ZH', 'CH', 'JH', 'TH', 'DH', 'F', 'V',
})

# ---------------------------------------------------------------------------
# Legal two-consonant onset clusters (English phonotactics, ARPAbet labels).
# Used by the syllabifier's maximal-onset step: when two consonants sit
# between vowels, the split point depends on whether they form a valid
# syllable onset. If they do (e.g. 'computer' → K + P + Y…: PY is legal),
# the whole cluster becomes the next syllable's onset; otherwise only the
# last consonant does. This is what moves the 't' in 'computer' so the
# stress lands as kəmˈpjuːtər rather than kəmpˈjuːtər.
#
# List covers the common obstruent+approximant and s+consonant clusters;
# it is intentionally not exhaustive (rare onsets fall back to single-onset).
# ---------------------------------------------------------------------------

LEGAL_ONSETS: frozenset[tuple[str, str]] = frozenset({
    # stop / fricative + approximant (l, r, w, y)
    ('P', 'L'), ('P', 'R'), ('P', 'Y'),
    ('B', 'L'), ('B', 'R'),
    ('T', 'R'), ('T', 'W'), ('T', 'Y'),
    ('D', 'R'), ('D', 'W'),
    ('K', 'L'), ('K', 'R'), ('K', 'W'), ('K', 'Y'),
    ('G', 'L'), ('G', 'R'), ('G', 'W'),
    ('F', 'L'), ('F', 'R'), ('F', 'Y'),
    ('TH', 'R'), ('TH', 'W'),
    ('SH', 'R'),
    ('HH', 'Y'), ('V', 'Y'), ('M', 'Y'), ('N', 'Y'),
    # s + consonant
    ('S', 'P'), ('S', 'T'), ('S', 'K'),
    ('S', 'L'), ('S', 'M'), ('S', 'N'), ('S', 'W'),
})

# Legal three-consonant onsets — all begin with 's' (English allows only
# s + voiceless-stop + approximant, e.g. 'string' → STR, 'splash' → SPL).
LEGAL_ONSETS_3: frozenset[tuple[str, str, str]] = frozenset({
    ('S', 'T', 'R'), ('S', 'P', 'R'), ('S', 'K', 'R'),
    ('S', 'P', 'L'), ('S', 'K', 'L'),
    ('S', 'K', 'W'), ('S', 'T', 'Y'), ('S', 'K', 'Y'),
})

# ---------------------------------------------------------------------------
# Broad / citation weak forms for common English function words (v1).
# This is intentionally small and comment-documented so it is easy to extend.
# These are broad phonetic approximations — not narrow allophonic detail.
# ---------------------------------------------------------------------------

WEAK_FORMS: dict[str, str] = {
    # Articles
    'a':    'ə',
    'an':   'ən',
    'the':  'ðə',
    # Prepositions
    'to':   'tə',
    'of':   'əv',
    'for':  'fər',
    'from': 'frəm',
    'at':   'ət',
    # Conjunctions / complementizers
    'and':  'ən',
    'but':  'bət',
    'that': 'ðət',   # conjunction sense; demonstrative stays strong
    'as':   'əz',
    'than': 'ðən',
    # Auxiliaries / modals
    'can':  'kən',
    'was':  'wəz',
    'were': 'wər',
    'are':  'ər',
    'do':   'də',
    # Pronouns
    'you':  'jə',
    'your': 'jər',
    'he':   'hi',
    'him':  'ɪm',
    'her':  'ər',
    'them': 'ðəm',
    'us':   'əs',
}

# Regex: full ARPAbet token (letters only, optional stress digit 0-2)
_ARPA_TOKEN_RE = re.compile(r'^[A-Z]+[0-2]?$')

# Characters stripped when matching weak-form keys
_PUNCT_STRIP = str.maketrans('', '', '.,!?;:\'"()[]{}')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base(phoneme: str) -> str:
    """Return the consonant/vowel label without trailing stress digit."""
    return phoneme.rstrip('012')


def _stress(phoneme: str) -> str:
    """Return stress digit ('0'/'1'/'2') or '' if the phoneme carries none."""
    return phoneme[-1] if phoneme and phoneme[-1].isdigit() else ''


def _phone_to_ipa(phoneme: str) -> str:
    """Map one ARPAbet phone (with optional stress digit) to its IPA string.

    Applies stress-conditioned reductions before the default table so that
    unstressed AH/ER collapse to their weak Oxford forms (ə / ər).
    """
    base = _base(phoneme)
    if base in REDUCED_VOWELS and _stress(phoneme) == '0':
        return REDUCED_VOWELS[base]
    return ARPA_IPA.get(base, '')


def _max_onset(cluster: list[str]) -> int:
    """Return how many trailing consonants of `cluster` form the next onset.

    Maximal-onset principle: assign the longest legal onset (max 3, English
    caps at s+stop+approximant) to the following syllable; the rest stay as
    coda on the current syllable. `cluster` holds bare consonant labels
    (stress digits already stripped) sitting between two vowels.

    A single trailing consonant is always a legal onset. Every English word
    starts with at most a 3-consonant onset, so we never need to test longer.
    """
    n = len(cluster)
    if n <= 1:
        return n
    if n >= 3 and tuple(cluster[-3:]) in LEGAL_ONSETS_3:
        return 3
    if tuple(cluster[-2:]) in LEGAL_ONSETS:
        return 2
    return 1


# ---------------------------------------------------------------------------
# Syllabification — maximal onset heuristic
# ---------------------------------------------------------------------------

def syllabify(phones: list[str]) -> list[list[str]]:
    """Split a single word's phone list into syllables.

    Uses maximal-onset heuristic:
    - locate all vowel nuclei by index
    - for each non-final vowel, take the consonant cluster between it and the
      next vowel, and hand the longest legal onset (via _max_onset) to the
      next syllable; the remaining consonants stay as coda on this syllable.
      Examples:
        computer  M P Y → PY is a legal onset → kəm.pjuː.tər
        winter    N T   → NT is not a legal onset → win.tər
        instrument N S T R → STR is a legal 3-onset → in.strə.mənt
    - no vowels → single syllable (e.g. function words like 'hmm')
    """
    vowel_indices = [i for i, p in enumerate(phones) if _base(p) in VOWELS]
    if not vowel_indices:
        return [phones]

    syllables: list[list[str]] = []
    start = 0

    for vi_pos, vow_i in enumerate(vowel_indices[:-1]):
        next_vow_i = vowel_indices[vi_pos + 1]
        # bare consonant labels strictly between this vowel and the next
        cluster = [_base(phones[j]) for j in range(vow_i + 1, next_vow_i)]
        # onset_len consonants belong to the NEXT syllable; the rest are coda
        onset_len = _max_onset(cluster)
        cut = next_vow_i - onset_len

        syllables.append(phones[start:cut])
        start = cut

    syllables.append(phones[start:])  # final syllable gets everything remaining
    return syllables


# ---------------------------------------------------------------------------
# Flapping — OALD-US allophonic rule for intervocalic /t/
# ---------------------------------------------------------------------------

def _apply_flapping(phones: list[str]) -> list[str]:
    """Turn intervocalic /t/ into the alveolar flap DX (rendered t̬).

    OALD-US flaps /t/ when it sits between a vowel (or an r-coloured vowel /
    ER / R) and a FOLLOWING UNSTRESSED vowel:
        water   → ˈwɔːt̬ər     (T between ɔː and unstressed ər)
        city    → ˈsɪt̬i       (T between ɪ and unstressed i)
        computer→ kəmˈpjuːt̬ər
    It does NOT flap before a stressed vowel:
        attack  → əˈtæk        (T precedes stressed æ → stays t)
        return  → rɪˈtɜːrn

    Operates on the flat phone list before syllabification so the vowel
    context is visible across syllable boundaries. Returns a new list.
    """
    out = list(phones)
    for i, p in enumerate(out):
        if _base(p) != 'T':
            continue
        if i == 0 or i + 1 >= len(out):
            continue
        prev_base = _base(out[i - 1])
        next_phone = out[i + 1]
        # left context: a vowel nucleus, R, or ER (r-coloured)
        left_ok = prev_base in VOWELS or prev_base == 'R'
        # right context: an UNSTRESSED vowel (stress digit 0)
        right_ok = _base(next_phone) in VOWELS and _stress(next_phone) == '0'
        if left_ok and right_ok:
            out[i] = 'DX'
    return out


# ---------------------------------------------------------------------------
# Syllabic-n — OALD-US collapse of unstressed schwa before /n/
# ---------------------------------------------------------------------------

def _apply_syllabic_n(phones: list[str]) -> list[str]:
    """Drop an unstressed AH0 sitting between a coronal/labiodental and N.

    Turns the CMUdict sequence  <trigger> AH0 N  into  <trigger> N, giving a
    syllabic /n/ instead of a schwa+n. This matches OALD-US for the common
    '-tion/-sion/-en' family:
        station  S T EY1 SH AH0 N  → ...SH N  → ˈsteɪʃn
        question K W EH1 S CH AH0 N → ...CH N → ˈkwestʃn
        button   B AH1 T AH0 N      → ...T N  → ˈbʌtn
    The AH0 is only removed after a trigger consonant (SYLLABIC_N_TRIGGERS);
    after other places (p/k/m/r) the schwa is kept (happen → ˈhæpən).

    Runs BEFORE flapping so the /t/ in 'button' ends up adjacent to /n/ (no
    intervocalic context) and therefore does not flap. Returns a new list.
    """
    out: list[str] = []
    i = 0
    while i < len(phones):
        # match  <trigger>  AH0  N
        if (
            i + 2 < len(phones)
            and _base(phones[i]) in SYLLABIC_N_TRIGGERS
            and phones[i + 1] == 'AH0'
            and _base(phones[i + 2]) == 'N'
        ):
            out.append(phones[i])      # keep the trigger consonant
            out.append(phones[i + 2])  # keep N, drop the AH0 between them
            i += 3
            continue
        out.append(phones[i])
        i += 1
    return out


# ---------------------------------------------------------------------------
# Word-level conversion
# ---------------------------------------------------------------------------

def word_to_ipa(phones: list[str]) -> str:
    """Convert a single word's ARPAbet phone list to an IPA string with stress marks."""
    phones = _apply_syllabic_n(phones)
    phones = _apply_flapping(phones)
    syllables = syllabify(phones)
    parts: list[str] = []

    for syl in syllables:
        # Determine stress from the vowel nucleus of this syllable
        stress_digit = ''
        for p in syl:
            if _base(p) in VOWELS:
                stress_digit = _stress(p)
                break

        prefix = 'ˈ' if stress_digit == '1' else ('ˌ' if stress_digit == '2' else '')
        body = ''.join(_phone_to_ipa(p) for p in syl)
        parts.append(prefix + body)

    return ''.join(parts)


# ---------------------------------------------------------------------------
# Sentence-level conversion (called from ipa.py)
# ---------------------------------------------------------------------------

def sentence_ipa(text: str, g2p_fn) -> str:
    """Convert a full sentence to IPA using a g2p callable.

    Args:
        text:    Raw English sentence string.
        g2p_fn:  A callable g2p_en.G2p instance (or compatible).

    Returns:
        Space-separated IPA string, one token per word. Empty string for
        sentences that are blank or produce no phoneme output.

    Edge cases handled:
    - Empty / punctuation-only input → returns ''
    - Numbers (e.g. '2026') expand to multiple words in g2p — word count
      diverges from group count → weak-form pass is skipped for that sentence
      (basic IPA is still returned correctly from the phone groups).
    - Per-word errors produce '' for that word (defensive, best-effort).
    """
    stripped = text.strip()
    if not stripped:
        return ''

    # g2p returns a flat list: ARPAbet tokens interleaved with ' ' (word boundary)
    # and punctuation/digit tokens.
    try:
        raw_phones: list[str] = g2p_fn(stripped)
    except Exception:
        return ''

    # Group ARPAbet tokens by word boundary (' ' separates words in g2p output)
    groups: list[list[str]] = []
    current: list[str] = []
    for token in raw_phones:
        if token == ' ':
            if current:
                groups.append(current)
                current = []
        elif _ARPA_TOKEN_RE.match(token):
            current.append(token)
        # punctuation/digit tokens not in ARPAbet set — skip
    if current:
        groups.append(current)

    if not groups:
        return ''

    # Convert each phone group to IPA
    ipa_words: list[str] = []
    for grp in groups:
        try:
            ipa_words.append(word_to_ipa(grp))
        except Exception:
            ipa_words.append('')

    # Apply weak forms only when word count aligns with phone-group count.
    # Misalignment occurs when numbers expand to multiple words inside g2p.
    surface_words = stripped.split()
    if len(surface_words) == len(ipa_words):
        for i, w in enumerate(surface_words):
            key = w.lower().translate(_PUNCT_STRIP)
            if key in WEAK_FORMS:
                ipa_words[i] = WEAK_FORMS[key]

    return ' '.join(ipa_words)
