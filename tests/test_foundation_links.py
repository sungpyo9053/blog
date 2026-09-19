import json
import tempfile
import unittest
from pathlib import Path

from publisher.foundation_links import FoundationLinkError, enforce_foundation_links
from publisher.frontmatter import MarkdownDocument


class FoundationLinksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.example = 'https://github.com/example/repo/blob/' + 'a'*40 + '/example.py'
        self.proof = 'https://github.com/example/repo/blob/' + 'a'*40 + '/verification.json'
        self.contract = {'worked_example': {'public_url': self.example}, 'verification': {'public_url': self.proof}}
        self.context = self.root/'planner-context.json'
        self.context.write_text(json.dumps({'foundation_contract': self.contract}))

    def check(self, body, **metadata):
        enforce_foundation_links(MarkdownDocument({'content_type': 'foundation_concept', **metadata}, body, self.root/'publish.md'))

    def test_requires_both_exact_urls(self):
        for body in ('no links', f'[example]({self.example})', f'[proof]({self.proof})',
                     f'[example]({self.example}?fake=1) [proof]({self.proof})'):
            with self.subTest(body=body), self.assertRaisesRegex(FoundationLinkError, 'links_missing'):
                self.check(body)

    def test_markdown_reference_links_and_html_anchors_pass(self):
        for body in (f'[example]({self.example}) [proof]({self.proof})',
                     f'[`example.py`]({self.example}) [`verification.json`]({self.proof})',
                     f'[example][a] [proof][b]\n\n[a]: {self.example}\n[b]: {self.proof}',
                     f'<a href="{self.example}">example</a><a href="{self.proof}">proof</a>'):
            self.check(body)

    def test_non_body_non_clickable_and_hidden_urls_do_not_count(self):
        links = f'[example]({self.example}) [proof]({self.proof})'
        html = f'<a href="{self.example}">example</a><a href="{self.proof}">proof</a>'
        for body in (f'{self.example} {self.proof}', f'```md\n{links}\n```',
                     f'~~~html\n{html}\n~~~', f'`{links}`', f'    {links}',
                     f'<!-- {html} -->', f'<pre>{html}</pre>', f'<code>{html}</code>',
                     f'<div hidden>{html}</div>', f'<div style="display: none">{html}</div>',
                     f'![image]({self.example}) ![proof]({self.proof})',
                     f'<a href="{self.example}"></a><a href="{self.proof}"></a>'):
            with self.subTest(body=body), self.assertRaisesRegex(FoundationLinkError, 'links_missing'):
                self.check(body, extra_urls=[self.example, self.proof])

    def test_absent_or_empty_manual_contract_preserved(self):
        self.context.unlink()
        self.check('manual foundation lesson')
        self.context.write_text('{"foundation_contract":{}}')
        self.check('manual foundation lesson')

    def test_explicit_frontmatter_contract_also_requires_body_links(self):
        self.context.unlink()
        with self.assertRaises(FoundationLinkError):
            self.check('no body links', foundation_contract=self.contract)

    def test_broken_or_partial_supplied_contract_fails_closed(self):
        for text in ('[]', '{broken', '{"foundation_contract":null}',
                     '{"foundation_contract":{},"foundation_contract":{}}',
                     json.dumps({'foundation_contract': {'worked_example': {'public_url': self.example}}})):
            self.context.write_text(text)
            with self.subTest(text=text), self.assertRaises(FoundationLinkError):
                self.check('no links')


if __name__ == '__main__':
    unittest.main()
