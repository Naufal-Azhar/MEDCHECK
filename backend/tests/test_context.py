from app.rag.context import build_context
from app.retrieval.service import SearchHit


def hit(chunk_id=1, document_id=1, title="Diabetes", content="Diabetes is a condition."):
    return SearchHit(chunk_id, document_id, 0, content, title, 1, "MedlinePlus",
                      f"https://medlineplus.gov/{title.lower().replace(' ', '')}.html", 0.8)


def test_context_labels_sources_and_deduplicates_documents():
    result = build_context("What is diabetes?", [hit(), hit(2, 1, content="More diabetes."), hit(3, 2, "Diabetes Type 2")])
    assert [item.citation_id for item in result.evidence] == ["S1", "S2"]
    assert [item.document_id for item in result.evidence] == [1, 2]
    assert "[S1] SOURCE: Diabetes" in result.prompt_context
    assert result.insufficient_evidence is False


def test_context_is_bounded_and_marks_empty_results():
    result = build_context("What is this?", [hit(content="x" * 1000)], max_chars=300)
    assert len(result.prompt_context) <= 300
    empty = build_context("What is this?", [])
    assert empty.insufficient_evidence is True


def test_context_rejects_invalid_limits():
    for kwargs in ({"max_items": 0}, {"max_chars": 0}, {"minimum_items": 0}):
        try:
            build_context("question", [hit()], **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
