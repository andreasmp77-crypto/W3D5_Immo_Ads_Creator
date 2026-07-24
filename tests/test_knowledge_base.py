from __future__ import annotations

from src.knowledge_base import (
    KnowledgeBaseDocument,
    format_knowledge_base_context,
    format_knowledge_base_document,
    get_primary_kb_context,
    get_secondary_kb_context,
    load_all_knowledge_base,
    load_primary_knowledge_base,
    load_secondary_knowledge_base,
    scan_markdown_files,
)


def test_scan_markdown_files_finds_expected_docs():
    primary_files = scan_markdown_files(__import__("pathlib").Path("knowledge_base/primary"))
    secondary_files = scan_markdown_files(__import__("pathlib").Path("knowledge_base/secondary"))

    assert any(path.name == "Ad1_Westend_3-Room_OldBuilding_Private_EN.md" for path in primary_files)
    assert any(path.name == "berlin_districts.md" for path in secondary_files)
    assert any(path.name == "market_context.md" for path in secondary_files)


def test_load_knowledge_bases_return_documents():
    primary_docs = load_primary_knowledge_base()
    secondary_docs = load_secondary_knowledge_base()

    assert primary_docs
    assert secondary_docs
    assert all(doc.title for doc in primary_docs + secondary_docs)
    assert all(doc.content for doc in primary_docs + secondary_docs)


def test_formatting_knowledge_base_document_and_context():
    document = KnowledgeBaseDocument(
        source="primary",
        path=__import__("pathlib").Path("knowledge_base/primary/example.md"),
        title="Example Title",
        content="# Example Title\nBody text",
        last_updated="2026-07-24",
    )

    formatted = format_knowledge_base_document(document)
    assert formatted.startswith("[PRIMARY] Example Title | Last updated: 2026-07-24")
    assert "# Example Title" not in formatted
    assert "Body text" in formatted

    context = format_knowledge_base_context([document])
    assert "Example Title" in context


def test_context_helpers_load_both_kbs():
    primary_context = get_primary_kb_context()
    secondary_context = get_secondary_kb_context()
    all_docs = load_all_knowledge_base()

    assert "Westend 3-Room Old-Building Apartment" in primary_context
    assert "Berlin District & Lifestyle Summaries" in secondary_context
    assert len(all_docs) == len(load_primary_knowledge_base()) + len(load_secondary_knowledge_base())
