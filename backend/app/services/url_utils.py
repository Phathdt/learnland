"""URL parsing utilities for YouTube video identifiers."""

import re
from urllib.parse import parse_qs, urlparse

# Matches standard 11-character YouTube video IDs
_VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# Trusted YouTube hostnames for the parse_qs fallback
_YOUTUBE_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com")

# Supported URL patterns (path-based, no host ambiguity)
_PATTERNS = [
    # https://www.youtube.com/watch?v=VIDEO_ID
    re.compile(r"(?:youtube\.com)/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # https://youtu.be/VIDEO_ID
    re.compile(r"youtu\.be/([a-zA-Z0-9_-]{11})"),
    # https://www.youtube.com/shorts/VIDEO_ID
    re.compile(r"(?:youtube\.com)/shorts/([a-zA-Z0-9_-]{11})"),
    # https://www.youtube.com/embed/VIDEO_ID
    re.compile(r"(?:youtube\.com)/embed/([a-zA-Z0-9_-]{11})"),
]


class InvalidYouTubeURLError(ValueError):
    """Raised when a URL cannot be resolved to a YouTube video ID."""


def canonical_url(video_id: str) -> str:
    """Return the canonical YouTube watch URL for a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def extract_video_id(url: str) -> str:
    """Parse a YouTube URL and return the 11-character video ID.

    Supports watch, youtu.be, shorts, and embed formats.
    Raises InvalidYouTubeURLError for unrecognised or invalid URLs.
    """
    url = url.strip()

    # Allow bare video IDs to pass through directly
    if _VIDEO_ID_RE.match(url):
        return url

    for pattern in _PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    # Fallback: parse query string — only for known YouTube hosts to prevent SSRF
    parsed = urlparse(url)
    if parsed.netloc in _YOUTUBE_HOSTS:
        qs = parse_qs(parsed.query)
        if "v" in qs and _VIDEO_ID_RE.match(qs["v"][0]):
            return qs["v"][0]

    raise InvalidYouTubeURLError(
        f"Cannot extract a YouTube video ID from URL: {url!r}"
    )
