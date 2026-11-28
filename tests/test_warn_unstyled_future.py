import unittest
from datetime import UTC, datetime

from scripts.warn_unstyled_future import due_warnings, exempt_ids

OLD = '<p>2026년 11월 28일 복지부 고시로 확인했습니다.</p><h2>30초 핵심 요약</h2><p>x</p>'
NOW = datetime(2026, 12, 2, 11, 30, tzinfo=UTC)


def post(pid, when, raw=OLD):
    return {"id": pid, "date_gmt": when, "content": {"raw": raw}}


class WarnTest(unittest.TestCase):
    def test_due_old_template_warns(self):
        out = due_warnings({"posts": [post(1, "2026-12-02T12:00:00")]}, NOW, set(), set())
        self.assertEqual([p for p, _ in out], [1])

    def test_exempt_later_and_already_warned_skip(self):
        posts = {"posts": [post(2, "2026-12-02T12:00:00"), post(3, "2026-12-02T15:00:00"), post(4, "2026-12-02T12:10:00")]}
        self.assertEqual(due_warnings(posts, NOW, {2}, {4}), [])

    def test_clean_post_no_warning(self):
        clean = '<p>부부가 둘 다 받으면 20%가 줄어든다.</p><h2>국민연금을 받으면 얼마나 줄어드나</h2><p>x</p>'
        self.assertEqual(due_warnings({"posts": [post(5, "2026-12-02T12:00:00", clean)]}, NOW, set(), set()), [])

    def test_exempt_ids_from_queue_table(self):
        table = "| 3 | 1944 | 12-04 12:00 | 복리 | 비교용(그대로) | 대기 |\n| 4 | 1950 | 12-05 12:00 | 적금 | 고침 | 대기 |\n"
        self.assertEqual(exempt_ids(table), {1944})


if __name__ == "__main__":
    unittest.main()
