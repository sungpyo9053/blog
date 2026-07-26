"""Read Markdown documents with YAML frontmatter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class FrontmatterError(ValueError):
    """Raised when frontmatter cannot be parsed safely."""


@dataclass(frozen=True)
class MarkdownDocument:
    metadata: dict[str, Any]
    markdown: str
    source_path: Path


def load_document(path: Path) -> MarkdownDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FrontmatterError(f"Unable to read Markdown file: {exc}") from exc

    if not text.startswith("---"):
        raise FrontmatterError("Markdown must begin with YAML frontmatter")

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("Frontmatter opening delimiter must be on the first line")

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise FrontmatterError("Frontmatter closing delimiter is missing")

    raw_frontmatter = "\n".join(lines[1:closing_index])
    try:
        metadata = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise FrontmatterError("Frontmatter must be a key-value mapping")

    markdown = "\n".join(lines[closing_index + 1 :]).strip()
    return MarkdownDocument(metadata=metadata, markdown=markdown, source_path=path)
