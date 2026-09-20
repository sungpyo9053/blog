import unittest
import time
import html
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from scripts.editorial_gate import enforce_prepublication, inspect_article, style_preservation


class EditorialGateTests(unittest.TestCase):
    def inventory(self, text=""):
        return {"metadata":{"complete":True,"full_content":True,"statuses":{"publish":1,"draft":0},"collected_at":datetime.now(UTC).isoformat()},"posts":[{"post_id":1,"status":"publish","content":text}]}

    def test_current_private_runtime_path_is_blocked_and_not_echoed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            publish = directory / 'publish.md'
            inventory = directory / 'inventory.json'
            inventory.write_text(json.dumps(self.inventory()))
            publish.write_text(f'본문\n```text\n{directory}/.venv/bin/python audit.py\n```')
            with self.assertRaisesRegex(ValueError, 'private_runtime_path') as raised:
                enforce_prepublication(publish, inventory)
            report = (directory / 'editorial-gate.json').read_text()
            self.assertFalse(json.loads(report)['passed'])
            self.assertNotIn(str(directory), report)
            self.assertNotIn(str(directory), str(raised.exception))

    def test_html_escaped_current_private_runtime_path_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix='private&topic-') as temporary:
            directory = Path(temporary).resolve()
            publish = directory / 'publish.md'
            inventory = directory / 'inventory.json'
            inventory.write_text(json.dumps(self.inventory()))
            publish.write_text(f'본문<pre>{html.escape(str(directory))}/final.md</pre>')
            with self.assertRaisesRegex(ValueError, 'private_runtime_path'):
                enforce_prepublication(publish, inventory)

    def test_relative_public_and_unrelated_example_paths_are_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            publish = directory / 'publish.md'
            inventory = directory / 'inventory.json'
            inventory.write_text(json.dumps(self.inventory()))
            publish.write_text('본문 ./images/capture.png\nhttps://huntlab.app/example/\n`/home/example/project`')
            self.assertTrue(enforce_prepublication(publish, inventory)['passed'])

    def test_inventory_cannot_claim_completeness_without_bodies_or_status_counts(self):
        inv = self.inventory()
        del inv["posts"][0]["content"]
        self.assertFalse(inspect_article("본문", inv)["passed"])
        inv = self.inventory()
        inv["metadata"]["statuses"]["draft"] = 1
        self.assertIn("inventory_status_count_mismatch", inspect_article("본문", inv)["failures"])

    def test_inventory_duplicate_ids_fail_closed(self):
        inv = self.inventory()
        inv["posts"].append(dict(inv["posts"][0]))
        self.assertIn("duplicate_inventory_ids", inspect_article("본문", inv)["failures"])

    def test_future_full_body_participates_in_duplicate_comparison(self):
        passage = '예약 글의 고유한 설명입니다. ' * 30
        inv = self.inventory()
        inv['posts'].append({'post_id': 2, 'status': 'future', 'content': passage})
        inv['metadata']['statuses']['future'] = 1
        result = inspect_article(passage, inv)
        self.assertIn('substantial_existing_passage', result['failures'])
        self.assertEqual(result['duplicates'][0]['post_id'], 2)
        self.assertEqual(result['checked_posts'], 2)

    def test_future_inventory_counts_are_validated_and_legacy_is_supported(self):
        inv = self.inventory()
        self.assertTrue(inspect_article('새 설명', inv)['passed'])
        inv['metadata']['statuses']['future'] = 0
        self.assertTrue(inspect_article('새 설명', inv)['passed'])
        inv['posts'].append({'post_id': 2, 'status': 'future', 'content': '예약된 다른 글'})
        for count in (0, True, None):
            inv['metadata']['statuses']['future'] = count
            self.assertIn('inventory_status_count_mismatch', inspect_article('새 설명', inv)['failures'])
        del inv['metadata']['statuses']['future']
        self.assertIn('inventory_status_count_mismatch', inspect_article('새 설명', inv)['failures'])
        inv['metadata']['statuses']['future'] = 1
        self.assertTrue(inspect_article('새 설명', inv)['passed'])

    def test_malformed_inventory_and_empty_body_fail_closed(self):
        for inv in (None, {}, {"metadata": None, "posts": "oops"}):
            self.assertFalse(inspect_article("본문", inv)["passed"])
        self.assertIn("empty_body", inspect_article("", self.inventory())["failures"])

    def test_shared_code_is_not_a_prose_duplicate(self):
        code = "response = requests.get(url)\n" * 20
        inv = self.inventory("<pre>" + code + "</pre>원래 설명")
        self.assertTrue(inspect_article("```python\n" + code + "```\n다른 설명", inv)["passed"])

    def test_exact_threshold_at_unaligned_offsets_including_last_window(self):
        passage = "가" * 179 + "나"
        for prefix in ("", "앞", "앞부분" * 61):
            result = inspect_article("원문" + passage, self.inventory(prefix + passage))
            self.assertEqual(result["duplicates"][0]["characters"], 180)
            self.assertTrue(result["duplicates"][0]["characters_is_lower_bound"])
        self.assertFalse(inspect_article("가" * 179 + "나", self.inventory("가" * 179 + "다"))["duplicates"])

    def test_repetitive_full_corpus_comparison_finishes_in_bounded_time(self):
        # Shared low-entropy alphabet, but no shared 180-character window: the
        # old longest-match algorithm spends quadratic time on this fixture.
        inv = self.inventory()
        inv["posts"] = [{"post_id":i + 1,"status":"publish",
                         "content":("가나다라마바사" * 20 + "다름") * 57} for i in range(122)]
        inv["metadata"]["statuses"]["publish"] = 122
        start = time.monotonic()
        result = inspect_article(("가나다라마바사" * 20 + "원문") * 57, inv)
        self.assertTrue(result["passed"])
        self.assertLess(time.monotonic() - start, 5.0)

    def test_repeated_passage_is_blocked_even_with_new_title(self):
        passage = "WordPress 목록을 모두 모은 뒤 동일한 ID 집합인지 비교한다. " * 10
        result = inspect_article("새 제목\n" + passage, self.inventory(passage))
        self.assertIn("substantial_existing_passage", result["failures"])

    def test_missing_full_content_and_stale_snapshot_fail_closed(self):
        inv = self.inventory()
        inv["metadata"]["full_content"] = False
        inv["metadata"]["collected_at"] = (datetime.now(UTC)-timedelta(days=2)).isoformat()
        self.assertEqual(set(inspect_article("독자용 설명", inv)["failures"]), {"incomplete_full_content_inventory","stale_inventory"})

    def test_existing_post_update_excludes_itself(self):
        text = "같은 글의 내용을 수정할 때 자기 자신과의 중복은 제외한다. " * 10
        self.assertTrue(inspect_article(text,self.inventory(text),existing_post_id=1)["passed"])

    def test_copyedit_cannot_change_code_numbers_or_urls(self):
        text = "서버에서 12건을 확인했다. `status=201`\nhttps://example.com/source"
        for replacement in (text.replace('12건','13건'),text.replace('201','200'),text.replace('/source','/other')):
            self.assertFalse(style_preservation(text,replacement)["passed"])

    def test_small_prose_edit_keeps_original_evidence(self):
        before = "서버에서 12건을 확인하였습니다. `status=201`\nhttps://example.com/source"
        self.assertTrue(style_preservation(before,before.replace('확인하였습니다','확인했습니다'))["passed"])

    def test_copyedit_preserves_markdown_table_text_and_row_order(self):
        for table in (
            "| 단계 | 결과 |\n| --- | --- |\n| 이전 | 성공 |\n| 이후 | 실패 |\n",
            "단계 | 결과\n:--- | ---:\n이전 | 성공\n이후 | 실패\n",
        ):
            before = "작은 표를 확인하였습니다.\n" + table
            self.assertTrue(style_preservation(before, before.replace("확인하였습니다", "확인했습니다"))["passed"])
            for after in (before.replace("성공", "통과"), before.replace("이전", "이후", 1)):
                self.assertIn("markdown_tables", style_preservation(before, after)["failures"])

    def test_copyedit_preserves_html_table_and_math_without_number_changes(self):
        examples = [
            ("<table><tr><td>관측</td><td>성공</td></tr></table>", "성공", "실패", "html_tables"),
            (r"$x + y$", "+", "-", "math"),
            (r"$$x + y$$", "+", "-", "math"),
            (r"\(x + y\)", "+", "-", "math"),
            (r"\[x + y\]", "+", "-", "math"),
            ("<math><mi>x</mi><mo>+</mo><mi>y</mi></math>", "+", "-", "math"),
            ("x_next = x + a", "+", "-", "equation_lines"),
        ]
        for span, old, new, failure in examples:
            before = "계산 과정의 설명은 이와 같이 그대로 유지한다.\n" + span
            self.assertIn(failure, style_preservation(before, before.replace(old, new))["failures"])

    def test_copyedit_preserves_quotes_blockquotes_and_html_quotes(self):
        for quote in ('“명령과 결과는 다르다”', "‘명령과 결과는 다르다’", '"명령과 결과는 다르다"',
                      "'명령과 결과는 다르다'", '「명령과 결과는 다르다」',
                      '> 명령과 결과는 다르다\n> 다음 설명\n',
                      '<blockquote>명령과 결과는 다르다</blockquote>', '<q>명령과 결과는 다르다</q>'):
            before = "인용은 그대로 두고 주변 문장만 다듬는다.\n" + quote
            self.assertIn("quotes", style_preservation(before, before.replace("다르다", "같다"))["failures"])

    def test_copyedit_preserves_negation_and_unverified_scope(self):
        for claim, changed in (
            ("실물에서 검증하지 않았다.", "실물에서 검증했다."),
            ("피드백은 학습이 아니다.", "피드백은 학습이다."),
            ("해당 실행은 미확인이다.", "해당 실행은 확인됐다."),
            ("성공을 보장하지 않는다.", "성공을 보장한다."),
            ("We did not test the robot.", "We did test the robot."),
            ("This was never tested.", "This was tested."),
            ("This doesn't prove safety.", "This does prove safety."),
        ):
            before = "확인 범위를 정확히 기록하는 설명이다.\n" + claim
            after = before.replace(claim, changed)
            self.assertIn("qualified_claims", style_preservation(before, after)["failures"])

    def test_copyedit_preserves_named_terms_and_configured_literal_terms(self):
        before = "Gymnasium의 관측 자료와 정책 설명을 연결한다. 전용도구는 Falcon-X다."
        self.assertIn("technical_terms", style_preservation(before, before.replace("Gymnasium", "MuJoCo"))["failures"])
        self.assertIn("technical_terms", style_preservation(before, before.replace("관측", "입력"))["failures"])
        result = style_preservation(before, before.replace("Falcon-X", "다른도구"), protected_terms=("Falcon-X",))
        self.assertIn("technical_terms", result["failures"])
        for invalid in ("Falcon-X", [""], [None]):
            self.assertIn("invalid_protected_terms", style_preservation(before, before, protected_terms=invalid)["failures"])

    def test_copyedit_preserves_tilde_fences_and_long_backticks(self):
        for fence in ("~~~", "````"):
            before = "이 설명의 실행 코드만 그대로 보존한다.\n" + fence + "python\nprint('yes')\n" + fence
            self.assertIn("code", style_preservation(before, before.replace("yes", "no"))["failures"])
        before = "이 설명의 인라인 구현을 그대로 보존한다. <code>foo()</code>"
        self.assertIn("code", style_preservation(before, before.replace("foo", "bar"))["failures"])

    def test_copyedit_cannot_swap_quantities_without_changing_multiset(self):
        before = "처음에는 12건, 다음에는 13건을 확인했다. 수치의 대응은 중요하다."
        after = "처음에는 13건, 다음에는 12건을 확인했다. 수치의 대응은 중요하다."
        self.assertIn("numbers", style_preservation(before, after)["failures"])

    def test_copyedit_preserves_identifiers_but_allows_normal_english_prose(self):
        before = "We carefully checked the useful result. readValue and result_count use API."
        self.assertTrue(style_preservation(before, before.replace("carefully checked", "checked"))["passed"])
        self.assertIn("identifiers", style_preservation(before, before.replace("readValue", "readOther"))["failures"])

    def test_retention_does_not_claim_semantic_equivalence_or_echo_protected_text(self):
        before = "An ordinary explanation describes the result clearly."
        result = style_preservation(before, before.replace("clearly", "briefly"))
        self.assertTrue(result["passed"])
        self.assertFalse(result["semantic_equivalence_verified"])
        self.assertTrue(result["independent_review_required"])
        secret = "private-example-credential"
        result = style_preservation('"' + secret + '"', '"changed"')
        self.assertNotIn(secret, json.dumps(result))

    def test_shell_path_placeholders_block_markdown(self):
        for language in ('bash', 'sh', 'shell'):
            for path in ('<check-dir>/manifest.json', '<source_path>', '<directory>', '<path>'):
                for fence in ('```', '~~~'):
                    with self.subTest(language=language, path=path, fence=fence):
                        result = inspect_article(f'본문\n{fence}{language}\npython audit.py --manifest {path}\n{fence}', self.inventory())
                        self.assertIn('unresolved_shell_path_placeholder', result['failures'])

    def test_shell_path_placeholders_block_encoded_html(self):
        for opening in ('<pre><code class="language-bash">', '<pre class="language-shell"><code>', '<pre data-language="sh"><code>'):
            result = inspect_article('본문' + opening + 'cat &lt;check-dir&gt;/manifest.json</code></pre>', self.inventory())
            self.assertIn('unresolved_shell_path_placeholder', result['failures'])

    def test_transcripts_non_shell_blocks_and_inline_examples_not_blocked(self):
        for language in ('text', 'plain', 'console', 'python', 'bashful', ''):
            self.assertTrue(inspect_article(f'본문\n```{language}\ncat <check-dir>/manifest.json\n```', self.inventory())['passed'])
        self.assertTrue(inspect_article('본문 `<check-dir>` <pre><code class="language-text">&lt;check-dir&gt;</code></pre>', self.inventory())['passed'])

    def test_shell_literals_comments_xml_heredoc_and_real_paths_not_blocked(self):
        snippets = [
            'printf "%s\\n" "<check-dir>/manifest.json"',
            "printf '%s\\n' '<source-path>'",
            'example="<check-dir>"',
            '# cat <check-dir>/manifest.json\nprintf ok',
            'printf "%s" "<root><path>value</path></root>"',
            "cat <<'EOF'\n<root><path>value</path></root>\nEOF",
            'cat <<-EOF\n\t<check-dir>/manifest.json\n\tEOF',
            'check_dir=$(mktemp -d)\npython audit.py --manifest "$check_dir/manifest.json"',
            'test 1 -lt 2\ncat < input.txt > output.txt',
        ]
        for code in snippets:
            with self.subTest(code=code):
                self.assertTrue(inspect_article('본문\n```bash\n' + code + '\n```', self.inventory())['passed'])

    def test_lint_resumes_after_heredoc_and_html_block(self):
        content = '본문\n```sh\ncat <<EOF\n<path>data</path>\nEOF\ncat <check-dir>/manifest.json\n```'
        self.assertIn('unresolved_shell_path_placeholder', inspect_article(content, self.inventory())['failures'])
        content = '본문<pre><code class="language-text">&lt;check-dir&gt;</code></pre><pre><code class="language-bash">cat &lt;path&gt;</code></pre>'
        self.assertIn('unresolved_shell_path_placeholder', inspect_article(content, self.inventory())['failures'])


if __name__ == '__main__': unittest.main()
