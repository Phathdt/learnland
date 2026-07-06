"""Unit tests for app.services.ipa — offline g2p-en pipeline, no LLM/network.

All tests run against the real G2p model (deterministic, CPU-only).
The G2p singleton is reset between tests that need isolation.
"""

import pytest

import app.services.ipa as ipa_module
from app.services.ipa import IpaError, IpaResult, generate_ipa


# ---------------------------------------------------------------------------
# Fixture: reset the lazy G2p singleton so each test starts clean.
# We do NOT reset between every test by default (model load is slow);
# only tests that explicitly need isolation use the fixture.
# ---------------------------------------------------------------------------

@pytest.fixture()
def reset_g2p_singleton():
    """Reset G2p singleton before and after the test."""
    ipa_module._g2p = None
    yield
    ipa_module._g2p = None


# ---------------------------------------------------------------------------
# (a) Basic smoke — non-empty output with stress marks
# ---------------------------------------------------------------------------

def test_generate_ipa_non_empty_with_stress():
    """generate_ipa returns a non-empty IPA string containing at least one stress mark."""
    result = generate_ipa(["Hello world."])

    assert isinstance(result, IpaResult)
    assert len(result.ipa) == 1
    ipa = result.ipa[0]
    assert ipa, "Expected non-empty IPA string for 'Hello world.'"
    assert "ˈ" in ipa, f"Expected primary stress mark ˈ in IPA output, got: {ipa!r}"


# ---------------------------------------------------------------------------
# (b) Empty input → immediate empty result, no model load
# ---------------------------------------------------------------------------

def test_generate_ipa_empty_input(reset_g2p_singleton):
    """Empty input list returns IpaResult(ipa=[]) without touching the G2p model."""
    result = generate_ipa([])
    assert isinstance(result, IpaResult)
    assert result.ipa == []
    # Model should NOT have been initialised (fast path)
    assert ipa_module._g2p is None


# ---------------------------------------------------------------------------
# (c) 1-to-1 alignment
# ---------------------------------------------------------------------------

def test_generate_ipa_alignment():
    """Output list length matches input list length exactly."""
    inputs = ["first sentence", "second sentence", "third one"]
    result = generate_ipa(inputs)

    assert isinstance(result, IpaResult)
    assert len(result.ipa) == len(inputs), (
        f"Expected {len(inputs)} IPA entries, got {len(result.ipa)}"
    )
    for i, ipa in enumerate(result.ipa):
        assert isinstance(ipa, str), f"Entry {i} is not a string: {ipa!r}"


# ---------------------------------------------------------------------------
# (d) Context-aware heteronym: "read" (past vs present)
# g2p-en uses POS tagging so these should differ.
# We assert at minimum both are non-empty; when the model handles it
# correctly they will differ (verified in prototype).
# ---------------------------------------------------------------------------

def test_generate_ipa_heteronym_read():
    """'read' in past-tense context produces IPA different from present-tense context."""
    result = generate_ipa([
        "I read a book yesterday",   # past tense → rɛd
        "I read books every day",    # present tense → riːd / rid
    ])

    past_ipa   = result.ipa[0]
    present_ipa = result.ipa[1]

    assert past_ipa,    "Expected non-empty IPA for past-tense 'read' sentence"
    assert present_ipa, "Expected non-empty IPA for present-tense 'read' sentence"

    # Both sentences share identical words except tense context — IPA should differ.
    # If g2p POS tagging works, the 'read' token will differ.
    assert past_ipa != present_ipa, (
        f"Expected context-aware heteronym difference but got identical IPA:\n"
        f"  past:    {past_ipa!r}\n"
        f"  present: {present_ipa!r}"
    )


# ---------------------------------------------------------------------------
# (e) Weak forms — 'to' and 'the' should reduce to schwa forms
# ---------------------------------------------------------------------------

def test_generate_ipa_weak_forms():
    """Common function words ('to', 'the') appear as their weak/schwa forms."""
    result = generate_ipa(["go to the store"])
    assert result.ipa, "Expected non-empty IPA"
    ipa = result.ipa[0]
    assert ipa, f"Expected non-empty IPA string, got: {ipa!r}"

    # The IPA should contain the schwa symbol indicating weak form reduction.
    # Weak-form 'to' → 'tə', 'the' → 'ðə' — both carry ə (Oxford-US style).
    assert "ə" in ipa, (
        f"Expected schwa (ə) from weak-form function words in {ipa!r}"
    )


# ---------------------------------------------------------------------------
# (f) OOV word — g2p neural fallback produces non-empty output
# ---------------------------------------------------------------------------

def test_generate_ipa_oov_word():
    """An invented/OOV word still yields non-empty IPA via g2p neural fallback."""
    result = generate_ipa(["skibidi"])
    assert result.ipa
    ipa = result.ipa[0]
    assert ipa, f"Expected non-empty IPA for OOV word 'skibidi', got: {ipa!r}"


# ---------------------------------------------------------------------------
# (g) Sentence containing a number — must not crash
# ---------------------------------------------------------------------------

def test_generate_ipa_sentence_with_number():
    """Sentence containing a digit string does not raise; returns a string."""
    result = generate_ipa(["The year 2026 was eventful"])
    assert isinstance(result, IpaResult)
    assert len(result.ipa) == 1
    # Result is a string (possibly empty if alignment skipped, but never an exception)
    assert isinstance(result.ipa[0], str)


# ---------------------------------------------------------------------------
# (h) Punctuation-only / blank sentence — returns '' without crashing
# ---------------------------------------------------------------------------

def test_generate_ipa_blank_sentence():
    """Blank or punctuation-only sentence returns empty string, does not crash."""
    result = generate_ipa([""])
    assert isinstance(result, IpaResult)
    assert result.ipa == [""]


# ---------------------------------------------------------------------------
# (i) Known IPA outputs (regression anchors from prototype verification)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected_ipa", [
    ("Hello world",    "həˈloʊ ˈwɜːrld"),
    ("today",          "təˈdeɪ"),
    ("information",    "ˌɪnfərˈmeɪʃən"),
    ("computer",       "kəmˈpjuːt̬ər"),   # maximal-onset stress + flapped t̬
    # Oxford-American rule anchors (length marks + rhoticity)
    ("transport",      "ˈtrænspɔːrt"),   # AO → ɔː, rhotic r kept
    ("see",            "ˈsiː"),          # IY1 → iː (length mark)
    ("food",           "ˈfuːd"),         # UW → uː (length mark)
    # Stress-conditioned reductions (the "special rules")
    ("about",          "əˈbaʊt"),        # AH0 → ə (schwa)
    ("bird",           "ˈbɜːrd"),        # ER1 → ɜːr (NURSE, stressed)
    ("letter",         "ˈlet̬ər"),        # EH → e, ER0 → ər, intervocalic t̬
    ("happy",          "ˈhæpi"),         # IY0 → i (happY, no length mark)
    # Maximal-onset syllabification → correct stress placement
    ("instrument",     "ˈɪnstrəmənt"),   # STR legal 3-onset
    ("winter",         "ˈwɪntər"),       # NT not an onset → t stays (no flap after n)
    # Flapping allophony
    ("water",          "ˈwɔːt̬ər"),       # intervocalic /t/ → t̬
    ("attack",         "əˈtæk"),         # /t/ before STRESSED vowel → stays t
])
def test_generate_ipa_known_outputs(text: str, expected_ipa: str):
    """Spot-check known IPA outputs to catch regressions in conversion logic."""
    result = generate_ipa([text])
    assert result.ipa[0] == expected_ipa, (
        f"IPA for {text!r}: expected {expected_ipa!r}, got {result.ipa[0]!r}"
    )
