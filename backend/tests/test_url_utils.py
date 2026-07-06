"""Tests for URL parsing utilities."""

import pytest
from app.services.url_utils import extract_video_id, InvalidYouTubeURLError


@pytest.mark.parametrize(
    "url,expected",
    [
        # Standard watch URL
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # No www
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Extra query params
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
        # youtu.be short URL
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
        # Shorts
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Embed
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Bare video ID passed directly
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_valid(url: str, expected: str) -> None:
    assert extract_video_id(url) == expected


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://vimeo.com/123456789",
        "not-a-url",
        "",
        "https://youtube.com/",
        "https://www.youtube.com/watch",  # no v= param
    ],
)
def test_extract_video_id_invalid(bad_url: str) -> None:
    with pytest.raises(InvalidYouTubeURLError):
        extract_video_id(bad_url)
