#!/usr/bin/env python3
"""Render one reviewed pilot Markdown file to stable UTF-8/LF HTML bytes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.frontmatter import load_document


def render(source: Path) -> tuple[dict, bytes]:
    document = load_document(source)
    html = markdown.markdown(
        document.markdown,
        extensions=["fenced_code", "tables"],
        output_format="html5",
    )
    stable = html.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    return document.metadata, stable.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    metadata, body = render(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(body)
    print(f"post_id={metadata.get('post_id')} bytes={len(body)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
