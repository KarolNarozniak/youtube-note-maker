from backend.app.services.text_context import chunk_text, extract_web_page_text


def test_extract_web_page_text_removes_script_and_finds_title() -> None:
    page = extract_web_page_text(
        """
        <html>
          <head><title>Example Page</title><script>bad()</script></head>
          <body><nav>Skip</nav><h1>Hello</h1><p>Useful paragraph.</p></body>
        </html>
        """
    )

    assert page.title == "Example Page"
    assert "Useful paragraph." in page.text
    assert "bad()" not in page.text
    assert "Skip" not in page.text


def test_chunk_text_splits_large_context() -> None:
    text = "\n\n".join(["alpha beta gamma delta"] * 30)
    chunks = chunk_text(text, target_tokens=12, overlap_tokens=4)

    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert all(chunk.text for chunk in chunks)
