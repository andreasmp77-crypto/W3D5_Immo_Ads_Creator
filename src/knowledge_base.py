"""Utilities for scanning, loading, and formatting KB markdown files.

The loader keeps primary and secondary knowledge bases separate, but also
supports building one combined context block for prompt injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

KB_ROOT = Path("knowledge_base")
PRIMARY_KB_DIR = KB_ROOT / "primary"
SECONDARY_KB_DIR = KB_ROOT / "secondary"


@dataclass(frozen=True)
class KnowledgeBaseDocument:
    """A single markdown document loaded from the knowledge base."""

    source: str
    path: Path
    title: str
    content: str
    last_updated: Optional[str] = None
    frontmatter: Optional[Dict[str, str]] = None


def scan_markdown_files(base_dir: Path) -> List[Path]:
    """Return all Markdown files under ``base_dir`` in stable sorted order."""
    if not base_dir.exists():
        return []
    return sorted(path for path in base_dir.rglob("*.md") if path.is_file())


def _parse_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    """Parse a small YAML-like frontmatter block if present."""
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    frontmatter_lines = lines[1:end_index]
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    frontmatter: Dict[str, str] = {}

    for raw_line in frontmatter_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip().lower()] = value.strip().strip('"').strip("'")

    return frontmatter, body


def _extract_title(path: Path, frontmatter: Dict[str, str], content: str) -> str:
    if frontmatter.get("title"):
        return frontmatter["title"]

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    return path.stem.replace("_", " ").strip() or path.name


def load_markdown_document(path: Path, source: str) -> KnowledgeBaseDocument:
    """Load one Markdown file and normalize its metadata."""
    text = path.read_text(encoding="utf-8")
    frontmatter, content = _parse_frontmatter(text)
    title = _extract_title(path, frontmatter, content)
    last_updated = frontmatter.get("last updated") or frontmatter.get("last_updated")

    return KnowledgeBaseDocument(
        source=source,
        path=path,
        title=title,
        content=content.strip(),
        last_updated=last_updated,
        frontmatter=frontmatter or None,
    )


def load_knowledge_base(base_dir: Path, source: str) -> List[KnowledgeBaseDocument]:
    """Load all Markdown files from a KB folder."""
    return [load_markdown_document(path, source=source) for path in scan_markdown_files(base_dir)]


def load_primary_knowledge_base() -> List[KnowledgeBaseDocument]:
    return load_knowledge_base(PRIMARY_KB_DIR, source="primary")


def load_secondary_knowledge_base() -> List[KnowledgeBaseDocument]:
    return load_knowledge_base(SECONDARY_KB_DIR, source="secondary")


def load_all_knowledge_base() -> List[KnowledgeBaseDocument]:
    """Load both KBs in a single list, primary first then secondary."""
    return load_primary_knowledge_base() + load_secondary_knowledge_base()


def format_knowledge_base_document(document: KnowledgeBaseDocument) -> str:
    """Format one KB document into a prompt-friendly block."""
    header_parts = [f"[{document.source.upper()}] {document.title}"]
    if document.last_updated:
        header_parts.append(f"Last updated: {document.last_updated}")
    header = " | ".join(header_parts)

    content = document.content.strip()
    title_line = f"# {document.title}".strip()
    if content.startswith(title_line):
        content = content[len(title_line) :].lstrip("\n")

    return f"{header}\n{content}".strip()


def format_knowledge_base_context(documents: Iterable[KnowledgeBaseDocument]) -> str:
    """Join multiple KB documents into one context string."""
    blocks = [format_knowledge_base_document(document) for document in documents]
    return "\n\n---\n\n".join(blocks)


def get_primary_kb_context() -> str:
    """Convenience wrapper for prompt templates and pipeline code."""
    return format_knowledge_base_context(load_primary_knowledge_base())


def get_secondary_kb_context() -> str:
    """Convenience wrapper for prompt templates and pipeline code."""
    return format_knowledge_base_context(load_secondary_knowledge_base())


def get_full_kb_context() -> str:
    """Convenience wrapper that combines both knowledge bases."""
    return format_knowledge_base_context(load_all_knowledge_base())


def get_kb_summary() -> Dict[str, int]:
    """Return a small count summary for diagnostics/tests."""
    primary_count = len(scan_markdown_files(PRIMARY_KB_DIR))
    secondary_count = len(scan_markdown_files(SECONDARY_KB_DIR))
    return {
        "primary": primary_count,
        "secondary": secondary_count,
        "total": primary_count + secondary_count,
    }

