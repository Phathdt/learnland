"""WebVTT segment parser for YouTube caption extraction.

Parses WebVTT cue blocks into time-coded segment dicts:
  {"start": float_seconds, "end": float_seconds, "text": str}

Handles:
- HH:MM:SS.mmm and MM:SS.mmm timestamp formats
- Inline tags stripped (<c>, <c.colorXXXX>, <00:00:00.000>, etc.)
- Consecutive duplicate cues deduplicated (fast-path)
- Rolling/cumulative auto-caption duplication collapsed:
    "this program is"          →  dropped (prefix of next)
    "this program is brought"  →  dropped (prefix of next)
    "this program is brought to you by Stanford"  →  KEPT (settled)
  Start time of the first cue in the growth chain is preserved.
- Empty cues discarded
"""

import re
from typing import Optional


def _vtt_ts_to_sec(ts: str) -> float:
    """Convert HH:MM:SS.mmm or MM:SS.mmm WebVTT timestamp to seconds."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def _collapse_rolling_cues(raw: list[dict]) -> list[dict]:
    """Collapse rolling/cumulative auto-caption duplication.

    YouTube auto-captions emit growing cues where the same text appears
    incrementally across multiple cues until it "settles". Example raw input:

        "this program is brought to you by"
        "this program is brought to you by Stanford University"
        "this program is brought to you by Stanford University please visit us"

    Only the final settled cue is emitted; its start time is taken from the
    first cue in the growth chain so shadowing highlight aligns correctly.

    A cue is considered a partial/growing version of the next when:
      - next_text.startswith(cur_text), OR
      - cur_text is fully contained within next_text
    A minimum length guard (> 3 chars) prevents single-word false positives.
    """
    if len(raw) < 2:
        return list(raw)

    result: list[dict] = []
    chain_start: float = raw[0]["start"]

    for i, seg in enumerate(raw):
        is_last = (i == len(raw) - 1)
        if not is_last:
            cur = seg["text"]
            nxt = raw[i + 1]["text"]
            # Current is a partial/prefix of the next → skip, keep chain start
            if len(cur) > 3 and (nxt.startswith(cur) or cur in nxt):
                continue  # chain_start stays unchanged

        # This segment is "settled" — emit with the preserved chain start
        result.append({
            "start": chain_start,
            "end": seg["end"],
            "text": seg["text"],
        })
        # Reset chain start for the next run
        if i + 1 < len(raw):
            chain_start = raw[i + 1]["start"]

    return result


def parse_vtt_segments(vtt_text: str) -> list[dict]:
    """Parse WebVTT text into time-coded segment dicts.

    Each segment: {"start": float, "end": float, "text": str}.

    Two dedup passes are applied:
    1. Consecutive-identical fast-path (exact string match).
    2. Rolling-growth collapse: drop intermediate cues that are prefixes or
       substrings of the following cue, preserving the earliest start time.

    Args:
        vtt_text: Raw WebVTT file content as a string.

    Returns:
        List of segment dicts ordered by start time. Empty list if no cues found.
    """
    raw: list[dict] = []
    last_text: Optional[str] = None

    # Split into cue blocks separated by blank lines
    blocks = re.split(r"\n\s*\n", vtt_text.strip())

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        # Locate the cue timing line (must contain "-->")
        ts_idx: Optional[int] = next(
            (i for i, line in enumerate(lines) if "-->" in line), None
        )
        if ts_idx is None:
            continue

        ts_parts = lines[ts_idx].split("-->")
        if len(ts_parts) < 2:
            continue

        try:
            start = _vtt_ts_to_sec(ts_parts[0].strip())
            # End timestamp may have trailing cue settings: "00:01:02.000 align:start"
            end = _vtt_ts_to_sec(ts_parts[1].strip().split()[0])
        except (ValueError, IndexError):
            continue

        # Collect text lines after the timestamp.
        # Strip ALL inline VTT markup: <c>, <c.colorXXXX>, <00:00:00.000>, etc.
        # The regex <[^>]+> covers all tag forms including timestamp tokens.
        text_lines = lines[ts_idx + 1:]
        cleaned = [re.sub(r"<[^>]+>", "", line).strip() for line in text_lines]
        text = " ".join(seg for seg in cleaned if seg)

        if not text:
            continue

        # Fast-path: skip exact consecutive duplicates
        if text == last_text:
            continue

        last_text = text
        raw.append({"start": start, "end": end, "text": text})

    # Second pass: collapse rolling auto-caption growth chains
    return _collapse_rolling_cues(raw)
