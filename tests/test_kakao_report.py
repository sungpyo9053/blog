import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.send_kakao_report import deep_status, message_for, run_day, send


class KakaoReportTests(unittest.TestCase):
    def test_seven_includes_today_briefing_only(self):
        message=message_for('2026-09-13','07',('발행 완료','https://huntlab.app/briefing/2026-09-13/'))
        self.assertIn('브리핑: 발행 완료',message)
        self.assertNotIn('심층글',message)

    def test_eleven_includes_in_progress_not_success(self):
        message=message_for('2026-09-13','11',('발행 완료',''),('진행 중',''))
        self.assertIn('심층글: 진행 중',message)

    def test_run_day_uses_kst_not_utc_filename(self):
        self.assertEqual(run_day('20260912T190001Z-test'),'2026-09-13')

    def test_missing_result_and_no_topic_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertIn('실행 결과 없음',deep_status(root,'2026-09-13')[0])
            run=root/'output/evidence-deep-article-runs/20260913T010000Z-test'
            run.mkdir(parents=True)
            (run/'result.json').write_text(json.dumps({'failed':False,'deep_article':'no_publishable_topic'}))
            self.assertIn('READY 0건',deep_status(root,'2026-09-13')[0])
            self.assertEqual(deep_status(root,'2026-09-13',True)[0],'진행 중')

    def test_unconfirmed_send_never_counts_as_success(self):
        with patch('scripts.send_kakao_report.subprocess.run') as run:
            run.return_value.returncode=0
            run.return_value.stdout='{"isError":true,"message":"auth required"}'
            with self.assertRaises(RuntimeError):
                send('test','mcporter')

    def test_links_omitted_without_corrupting_status_or_limit(self):
        message=message_for('2026-09-13','11',('조회 실패(발행 여부 미확인)','https://huntlab.app/'+'x'*200),('실행 결과 없음(누락/중단 확인 필요)',''))
        self.assertLessEqual(len(message),200)
        self.assertNotIn('https://',message)
