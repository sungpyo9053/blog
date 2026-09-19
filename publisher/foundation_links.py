"""Require explicit foundation evidence as real reader-facing body hyperlinks."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from urllib.parse import urlsplit

import markdown

from publisher.frontmatter import MarkdownDocument


class FoundationLinkError(ValueError):
    pass


class _BodyLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.links = set()
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = attrs.get('style', '').replace(' ', '').lower()
        excluded = tag in {'pre', 'script', 'style', 'template', 'noscript'}
        # A link may legitimately use an inline-code label, while anchors
        # appearing inside an existing code span are not reader links.
        excluded |= tag == 'code' and self.anchor is None
        excluded |= 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
        excluded |= 'display:none' in style or 'visibility:hidden' in style
        blocked = excluded or any(row[1] for row in self.stack)
        if tag not in {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'}:
            self.stack.append((tag, blocked))
        if tag == 'a':
            self.anchor = [attrs.get('href'), False] if not blocked else None

    def handle_data(self, data):
        if self.anchor is not None and data.strip() and not any(row[1] for row in self.stack):
            self.anchor[1] = True

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            if self.anchor[0] and self.anchor[1]:
                self.links.add(self.anchor[0])
            self.anchor = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def enforce_foundation_links(document: MarkdownDocument) -> None:
    """An explicit planner/frontmatter contract is binding; legacy manual lessons
    without one remain unchanged. Independent review and public audit still apply.
    """
    if document.metadata.get('content_type') != 'foundation_concept':
        return
    contracts = []
    if 'foundation_contract' in document.metadata:
        contracts.append(document.metadata['foundation_contract'])
    context_path = document.source_path.parent / 'planner-context.json'
    if context_path.exists():
        try:
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError('duplicate key')
                    value[key] = item
                return value
            context = json.loads(context_path.read_text(encoding='utf-8'), object_pairs_hook=unique)
            if not isinstance(context, dict):
                raise ValueError('context object required')
            if 'foundation_contract' in context:
                contracts.append(context['foundation_contract'])
        except (OSError, ValueError) as exc:
            raise FoundationLinkError('foundation_context_unreadable') from exc
    required = set()
    for contract in contracts:
        if contract == {}:
            continue
        if not isinstance(contract, dict):
            raise FoundationLinkError('foundation_contract_invalid')
        for field in ('worked_example', 'verification'):
            reference = contract.get(field)
            url = reference.get('public_url') if isinstance(reference, dict) else None
            if not isinstance(url, str):
                raise FoundationLinkError('foundation_evidence_url_invalid')
            try:
                parsed = urlsplit(url)
            except ValueError as exc:
                raise FoundationLinkError('foundation_evidence_url_invalid') from exc
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):
                raise FoundationLinkError('foundation_evidence_url_invalid')
            required.add(url)
    if not required:
        return
    rendered = markdown.markdown(document.markdown, extensions=['extra', 'sane_lists'], output_format='html5')
    parser = _BodyLinks()
    parser.feed(rendered)
    if not required <= parser.links:
        raise FoundationLinkError('foundation_public_evidence_links_missing')
