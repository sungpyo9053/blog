import unittest
import time
from datetime import UTC, datetime, timedelta
from scripts.editorial_gate import inspect_article, style_preservation


class EditorialGateTests(unittest.TestCase):
    def inventory(self, text=""):
        return {"metadata":{"complete":True,"full_content":True,"statuses":{"publish":1,"draft":0},"collected_at":datetime.now(UTC).isoformat()},"posts":[{"post_id":1,"status":"publish","content":text}]}

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


if __name__ == '__main__': unittest.main()
