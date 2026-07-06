"""IPA phonetic transcription service — offline, deterministic pipeline.

Uses g2p-en (CMU dict + neural G2P fallback) to convert English text to
ARPAbet, then maps to IPA via the helpers in arpabet_ipa.py.

This module owns the G2p singleton and the public generate_ipa API.
The conversion math (syllabification, stress marks, weak forms) lives in
arpabet_ipa.py to keep concerns separated and the unit-test surface clean.

Public contract (unchanged from LLM version):
    class  IpaError(Exception)
    @dataclass IpaResult(ipa: list[str])
    def generate_ipa(texts: list[str]) -> IpaResult
"""

import logging
import threading
from dataclasses import dataclass, field

import nltk

from app.services.arpabet_ipa import sentence_ipa

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class IpaError(Exception):
    """Raised when IPA transcription fails unrecoverably."""


@dataclass
class IpaResult:
    ipa: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# NLTK data — lazy one-time download
# ---------------------------------------------------------------------------

def _ensure_nltk_data() -> None:
    """Download averaged_perceptron_tagger_eng if not already present.

    g2p-en uses NLTK POS tagging for context-aware heteronym resolution
    (e.g., 'read' past tense vs present tense). Without this tagger the
    G2p() constructor will raise a LookupError.
    """
    resource = 'taggers/averaged_perceptron_tagger_eng'
    try:
        nltk.data.find(resource)
    except LookupError:
        logger.info("Downloading NLTK resource '%s' (one-time)…", resource)
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)


# ---------------------------------------------------------------------------
# G2p singleton — double-checked locking (mirrors transcriber.get_model())
# ---------------------------------------------------------------------------

_g2p = None  # type: ignore[var-annotated]  # G2p type from g2p_en; avoid runtime import at module level
_g2p_lock = threading.Lock()


def _get_g2p():  # -> G2p
    """Return the cached G2p instance, initialising on first call (thread-safe)."""
    global _g2p
    if _g2p is None:
        with _g2p_lock:
            if _g2p is None:  # second check inside lock
                _ensure_nltk_data()
                from g2p_en import G2p  # deferred import — heavy model load

                logger.info("Loading G2p model (one-time)…")
                _g2p = G2p()
                logger.info("G2p model ready.")
    return _g2p


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_ipa(texts: list[str]) -> IpaResult:
    """Return IPA transcriptions for every text in `texts`, preserving order.

    This function is synchronous and CPU-bound. Callers in async contexts
    should wrap it with asyncio.get_event_loop().run_in_executor(None, …).
    With the offline pipeline each call is fast (no network round-trip).

    Args:
        texts: English strings to transcribe phonetically.

    Returns:
        IpaResult with .ipa list aligned 1-to-1 with the input list.
        Per-sentence errors produce '' for that slot (best-effort).
        Empty input list returns IpaResult(ipa=[]) immediately.

    Raises:
        IpaError: Only for unrecoverable initialisation failures (e.g.
                  G2p model or NLTK data cannot be loaded).
    """
    if not texts:
        return IpaResult(ipa=[])

    try:
        g2p = _get_g2p()
    except Exception as exc:
        raise IpaError(f"Failed to initialise G2p model: {exc}") from exc

    results: list[str] = []
    for text in texts:
        try:
            results.append(sentence_ipa(text, g2p))
        except Exception as exc:  # noqa: BLE001 — best-effort per sentence
            logger.warning("IPA conversion failed for sentence (%s): %s", type(exc).__name__, exc)
            results.append('')

    return IpaResult(ipa=results)
