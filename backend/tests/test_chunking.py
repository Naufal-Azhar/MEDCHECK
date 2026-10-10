from app.ingestion.chunking import chunk_text


def test_chunking_preserves_content_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(10))
    chunks = chunk_text(text, max_words=6, overlap_words=2)

    assert len(chunks) == 2
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]
    assert "word0" in chunks[0].content
    assert "word9" in chunks[-1].content


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("   ") == []
