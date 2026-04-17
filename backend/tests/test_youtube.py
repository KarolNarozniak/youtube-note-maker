from backend.app.services.youtube import (
    classify_youtube_url,
    extract_playlist_id,
    extract_youtube_video_id,
    stable_point_id,
)


def test_classifies_video_urls() -> None:
    assert classify_youtube_url("https://www.youtube.com/watch?v=abc123") == "video"
    assert classify_youtube_url("https://youtu.be/abc123") == "video"
    assert classify_youtube_url("https://www.youtube.com/shorts/abc123") == "video"


def test_classifies_playlist_urls() -> None:
    url = "https://www.youtube.com/watch?v=abc123&list=PLxyz"
    assert classify_youtube_url(url) == "playlist"
    assert extract_playlist_id(url) == "PLxyz"


def test_extracts_video_ids() -> None:
    assert extract_youtube_video_id("https://youtu.be/abc123?t=4") == "abc123"
    assert extract_youtube_video_id("https://www.youtube.com/embed/abc123") == "abc123"
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"


def test_stable_point_id_is_uuid_shaped_and_deterministic() -> None:
    first = stable_point_id("video", 1, "embeddinggemma")
    second = stable_point_id("video", 1, "embeddinggemma")
    assert first == second
    assert len(first.split("-")) == 5
