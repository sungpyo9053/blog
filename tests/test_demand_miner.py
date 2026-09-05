from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.demand_miner import build


class DemandMinerTests(unittest.TestCase):
    def test_demand_never_becomes_ready_without_lab_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = [{"candidate_id":"rest-html","title_seed":"REST HTML 200","target_reader":"WordPress 개발자","exact_problem":"WordPress REST API가 HTML을 200으로 반환","demand_source":"official_forum","demand_url":"https://wordpress.org/support/topic/example/","commercial_intent":"troubleshooting","proposed_experiment":"fixture 비교","required_evidence":["failure","pass"],"possible_asset":"진단 스크립트","monetization_path":"자동발행 진단 도구","demand_strength":5,"commercial_fit":5,"experiment_cost":1}]
            (root/"source.json").write_text(json.dumps(source), encoding="utf-8")
            (root/"inventory.json").write_text(json.dumps({"posts":[]}), encoding="utf-8")
            payload = build(root/"source.json", root/"inventory.json")
            self.assertEqual(payload["candidate_count"], 1)
            self.assertEqual(payload["candidates"][0]["status"], "HOLD")
            self.assertNotEqual(payload["candidates"][0]["status"], "READY")

    def test_existing_search_intent_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = [{"candidate_id":"pagination","existing_post_id":132,"title_seed":"WordPress REST pagination 누락","target_reader":"개발자","exact_problem":"WordPress REST pagination에서 게시물 누락","demand_source":"repository","demand_url":"https://github.com/example/repo/issues/1","commercial_intent":"troubleshooting","proposed_experiment":"두 페이지","required_evidence":[],"possible_asset":"fixture","monetization_path":"진단 도구","demand_strength":5,"commercial_fit":5,"experiment_cost":1}]
            inventory = {"posts":[{"post_id":132,"title":"WordPress REST pagination 게시물 누락","slug":"wordpress-rest-api-pagination","excerpt":"두 번째 페이지 누락","url":"https://example.test/pagination/"}]}
            (root/"source.json").write_text(json.dumps(source), encoding="utf-8")
            (root/"inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            payload = build(root/"source.json", root/"inventory.json")
            self.assertEqual(payload["candidates"][0]["status"], "REJECT")
            self.assertEqual(payload["candidates"][0]["rejection_reason"], "existing_post_overlap")
