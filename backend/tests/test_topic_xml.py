from app.ingestion.topic_xml import parse_snapshot, balanced_order


def test_snapshot_rejects_non_authoritative_and_preserves_inline_text(tmp_path):
    summary = "A &lt;b&gt;health&lt;/b&gt; topic. " + "public information " * 30
    path = tmp_path / "topics.xml"
    path.write_text(f'''<health-topics date-generated="test">
      <health-topic language="English" id="1" title="Valid" url="https://medlineplus.gov/valid.html">
       <full-summary>{summary}</full-summary><group>General</group></health-topic>
      <health-topic language="English" id="2" title="External" url="https://example.invalid/other.html">
       <full-summary>{summary}</full-summary></health-topic>
      <health-topic language="Spanish" id="3" title="Other" url="https://medlineplus.gov/spanish/other.html"/>
      <health-topic language="English" id="4" title="Table" url="https://medlineplus.gov/table.html">
       <full-summary>&lt;table&gt;{summary}&lt;/table&gt;</full-summary></health-topic>
    </health-topics>''')
    records, stats = parse_snapshot(path)
    assert len(records) == 1
    assert records[0]["content"].startswith("A health topic.")
    assert stats["languages"] == {"English": 3, "Spanish": 1}
    assert len(stats["rejected"]) == 2


def test_selection_balanced_independent_of_query_labels():
    records = [{"title": "B", "groups": ["g1"]}, {"title": "A", "groups": ["g1"]},
               {"title": "C", "groups": ["g2"]}]
    assert [r["title"] for r in balanced_order(records)] == ["A", "C", "B"]
