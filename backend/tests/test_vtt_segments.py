"""Unit tests for app.services.vtt_parser.parse_vtt_segments."""

import pytest
from app.services.vtt_parser import parse_vtt_segments, _vtt_ts_to_sec


# ---------------------------------------------------------------------------
# Timestamp conversion
# ---------------------------------------------------------------------------

def test_vtt_ts_to_sec_hms():
    assert _vtt_ts_to_sec("00:01:30.500") == pytest.approx(90.5)


def test_vtt_ts_to_sec_ms():
    assert _vtt_ts_to_sec("01:05.000") == pytest.approx(65.0)


def test_vtt_ts_to_sec_hours():
    assert _vtt_ts_to_sec("01:00:00.000") == pytest.approx(3600.0)


# ---------------------------------------------------------------------------
# Core parsing — 3-cue sample with one consecutive exact duplicate
# ---------------------------------------------------------------------------

SAMPLE_VTT = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:04.000 --> 00:00:07.500
Hello world

00:00:07.500 --> 00:00:11.000
This is the second unique cue

00:00:11.000 --> 00:00:14.200
And the third cue here
"""


def test_parse_vtt_segments_basic():
    segs = parse_vtt_segments(SAMPLE_VTT)
    # Dedup removes the consecutive "Hello world" repeat → 3 unique segments
    assert len(segs) == 3


def test_parse_vtt_segments_first_start_end():
    segs = parse_vtt_segments(SAMPLE_VTT)
    assert segs[0]["start"] == pytest.approx(1.0)
    assert segs[0]["end"] == pytest.approx(4.0)


def test_parse_vtt_segments_text_content():
    segs = parse_vtt_segments(SAMPLE_VTT)
    assert segs[0]["text"] == "Hello world"
    assert "second unique" in segs[1]["text"]
    assert "third cue" in segs[2]["text"]


def test_parse_vtt_segments_last_end():
    segs = parse_vtt_segments(SAMPLE_VTT)
    assert segs[2]["end"] == pytest.approx(14.2)


def test_parse_vtt_segments_dedup_consecutive():
    """Consecutive identical cues must be deduplicated."""
    segs = parse_vtt_segments(SAMPLE_VTT)
    texts = [s["text"] for s in segs]
    # "Hello world" appears only once in output despite two consecutive cues
    assert texts.count("Hello world") == 1


def test_parse_vtt_segments_non_consecutive_dup_kept():
    """Same text appearing non-consecutively should NOT be dropped."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
Repeat text

00:00:04.000 --> 00:00:07.000
Different text

00:00:07.000 --> 00:00:10.000
Repeat text
"""
    segs = parse_vtt_segments(vtt)
    texts = [s["text"] for s in segs]
    assert texts.count("Repeat text") == 2


# ---------------------------------------------------------------------------
# Rolling / cumulative auto-caption deduplication (H1 bug fix)
# ---------------------------------------------------------------------------

# Pattern from real YouTube auto-caption VTT: each cue is a growing accumulation
# of the same speech until the line "settles". Collapsed output must contain the
# final settled version once, with the start time of the first partial cue.
ROLLING_VTT = """\
WEBVTT

00:00:09.000 --> 00:00:12.000
this program is brought to you by

00:00:10.000 --> 00:00:13.000
this program is brought to you by Stanford University please visit us

00:00:11.000 --> 00:00:14.000
this program is brought to you by Stanford University please visit us at

00:00:12.000 --> 00:00:15.000
this program is brought to you by Stanford University please visit us at stanford.edu
"""


def test_rolling_dedup_collapses_to_single_segment():
    """4 growing cues for the same speech line → collapsed to 1 segment."""
    segs = parse_vtt_segments(ROLLING_VTT)
    assert len(segs) == 1


def test_rolling_dedup_keeps_settled_text():
    """The kept segment must be the fully settled (longest) version."""
    segs = parse_vtt_segments(ROLLING_VTT)
    assert "stanford.edu" in segs[0]["text"]


def test_rolling_dedup_preserves_first_start_time():
    """Start time must be the first partial cue's start (9.0s), not the last."""
    segs = parse_vtt_segments(ROLLING_VTT)
    assert segs[0]["start"] == pytest.approx(9.0)


def test_rolling_dedup_keeps_last_end_time():
    """End time must come from the settled (last) cue."""
    segs = parse_vtt_segments(ROLLING_VTT)
    assert segs[0]["end"] == pytest.approx(15.0)


def test_rolling_dedup_no_overlap_in_adjacent_segments():
    """For all adjacent pairs, the earlier text must not be a substring of the later."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
hello

00:00:02.000 --> 00:00:05.000
hello there friend

00:00:05.000 --> 00:00:08.000
welcome back

00:00:06.000 --> 00:00:09.000
welcome back to the show
"""
    segs = parse_vtt_segments(vtt)
    for i in range(len(segs) - 1):
        cur_text = segs[i]["text"]
        nxt_text = segs[i + 1]["text"]
        assert cur_text not in nxt_text, (
            f"Segment {i} ({cur_text!r}) is substring of segment {i+1} ({nxt_text!r})"
        )


def test_rolling_dedup_distinct_lines_not_collapsed():
    """Genuinely distinct consecutive lines sharing common words are NOT collapsed."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
the cat sat on the mat

00:00:04.000 --> 00:00:07.000
the dog ran in the park

00:00:07.000 --> 00:00:10.000
and everyone had a good time
"""
    segs = parse_vtt_segments(vtt)
    # None are prefix/subset of next → all 3 kept
    assert len(segs) == 3


def test_rolling_dedup_chain_with_preceding_distinct_segment():
    """A rolling chain preceded by a distinct line only collapses the chain."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
welcome to the show

00:00:05.000 --> 00:00:08.000
today we discuss

00:00:06.000 --> 00:00:09.000
today we discuss machine learning

00:00:07.000 --> 00:00:10.000
today we discuss machine learning and AI
"""
    segs = parse_vtt_segments(vtt)
    # "welcome to the show" is distinct; rolling chain collapses to 1
    assert len(segs) == 2
    assert segs[0]["text"] == "welcome to the show"
    assert "machine learning and AI" in segs[1]["text"]
    # Chain start preserved: "today we discuss" started at 5.0
    assert segs[1]["start"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_parse_vtt_segments_empty_returns_empty():
    assert parse_vtt_segments("") == []
    assert parse_vtt_segments("WEBVTT\n\n") == []


def test_parse_vtt_segments_strips_inline_tags():
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
<c.colorE5E5E5>Hello <00:00:02.000><c> world</c>
"""
    segs = parse_vtt_segments(vtt)
    assert len(segs) == 1
    assert segs[0]["text"] == "Hello  world"


def test_parse_vtt_segments_strips_inline_timestamp_tokens():
    """Inline <HH:MM:SS.mmm> timestamp tokens inside cue text are stripped."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:05.000
<00:00:01.000><c>Stanford</c><00:00:02.500><c> University</c>
"""
    segs = parse_vtt_segments(vtt)
    assert len(segs) == 1
    # Tags stripped; only the words remain
    assert "Stanford" in segs[0]["text"]
    assert "University" in segs[0]["text"]
    assert "<" not in segs[0]["text"]


def test_parse_vtt_segments_skips_empty_cues():
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000
<c>   </c>

00:00:04.000 --> 00:00:07.000
Real content
"""
    segs = parse_vtt_segments(vtt)
    assert len(segs) == 1
    assert segs[0]["text"] == "Real content"


def test_parse_vtt_segments_cue_with_settings():
    """Cue timing lines may have trailing position settings — should still parse."""
    vtt = """\
WEBVTT

00:00:01.000 --> 00:00:04.000 align:start position:0%
Text with settings
"""
    segs = parse_vtt_segments(vtt)
    assert len(segs) == 1
    assert segs[0]["start"] == pytest.approx(1.0)
    assert segs[0]["text"] == "Text with settings"


def test_parse_vtt_segments_segment_shape():
    """Every segment dict must have exactly start, end, text."""
    segs = parse_vtt_segments(SAMPLE_VTT)
    for seg in segs:
        assert set(seg.keys()) == {"start", "end", "text"}
        assert isinstance(seg["start"], float)
        assert isinstance(seg["end"], float)
        assert isinstance(seg["text"], str)

