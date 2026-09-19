import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.physical_ai_quality_gate import PhysicalAIQualityError, enforce_quality


class PhysicalAIQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.publish = Path(self.temp.name) / 'publish.md'
        self.review = Path(self.temp.name) / 'physical-ai-quality-review.json'
        self.publish.write_text('# Observation and action\nA reviewed explanation.\n')
        self.payload = {
            'schema_version': 2,
            'publish_sha256': hashlib.sha256(self.publish.read_bytes()).hexdigest(),
            'writer_id': 'writer-agent-1', 'reviewer_id': 'reviewer-agent-2',
            'reviewed_at': '2026-09-17T10:00:00+09:00',
            'gates': {f'gate_{i}': True for i in range(1, 9)},
            'items': [dict(id=i, score=5, reason=f'Checked criterion {i}',
                           body_location='publish.md:1', evidence_ref='research.md:1')
                      for i in range(1, 21)],
            'total': 100, 'verdict': 'APPROVED',
            # Synthetic contract fixture, never a real content approval.
            'naturalness': {
                'verdict': 'PASS', 'unresolved_issues': [],
                'comparison_refs': ['synthetic recent-article fixture'],
                'checks': [dict(id=name, passed=True, reason='Synthetic checked reason',
                                body_location='fixture paragraph', evidence_ref='synthetic fixture')
                           for name in ('structure', 'rhythm', 'restraint', 'judgment', 'honesty')],
            },
        }

    def check(self):
        self.review.write_text(json.dumps(self.payload))
        return enforce_quality(self.publish, self.review)

    def rejects(self):
        with self.assertRaises(PhysicalAIQualityError):
            self.check()

    def test_accepts_100_and_99(self):
        self.assertEqual(self.check()['total'], 100)
        self.payload['items'][3]['score'] = 4
        self.payload['total'] = 99
        self.assertEqual(self.check()['total'], 99)

    def test_rejects_98_and_fabricated_total(self):
        self.payload['items'][0]['score'] = 3
        self.payload['total'] = 98
        self.rejects()
        self.payload['total'] = 100
        self.rejects()

    def test_changed_document_requires_new_review(self):
        self.publish.write_text('Changed after review')
        self.rejects()

    def test_missing_document_or_review_is_rejected(self):
        with self.assertRaises(PhysicalAIQualityError):
            enforce_quality(self.publish, self.review)
        self.check()
        self.publish.unlink()
        with self.assertRaises(PhysicalAIQualityError):
            enforce_quality(self.publish, self.review)

    def test_missing_unknown_schema_fields_rejected(self):
        for key in list(self.payload):
            value = self.payload.pop(key)
            self.rejects()
            self.payload[key] = value
        self.payload['extra_approval'] = True
        self.rejects()

    def test_invalid_schema_or_verdict_rejected(self):
        for version in (True, '2', 1, 3):
            self.payload['schema_version'] = version
            self.rejects()
        self.payload['schema_version'] = 2
        for verdict in ('HOLD', 'approved', '', None):
            self.payload['verdict'] = verdict
            self.rejects()

    def test_all_gates_must_be_true_booleans(self):
        for value in (False, 1, 'true', None, 'NOT_EVALUATED'):
            self.payload['gates']['gate_1'] = value
            self.rejects()
        self.payload['gates']['gate_1'] = True
        self.payload['gates']['gate_9'] = True
        self.rejects()
        del self.payload['gates']['gate_9']
        del self.payload['gates']['gate_1']
        self.rejects()

    def test_naturalness_cannot_be_missing_or_unresolved_at_100(self):
        original = copy.deepcopy(self.payload)
        for value in (None, {}, [], 'PASS'):
            with self.subTest(value=value):
                self.payload = copy.deepcopy(original)
                self.payload['naturalness'] = value
                self.rejects()
        for verdict in ('HOLD', 'NOT_EVALUATED', 'pass', True):
            self.payload = copy.deepcopy(original)
            self.payload['naturalness']['verdict'] = verdict
            self.rejects()
        self.payload = copy.deepcopy(original)
        self.payload['naturalness']['unresolved_issues'] = ['repeated conclusion']
        self.rejects()

    def test_naturalness_exact_five_unique_checks_and_fields(self):
        original = copy.deepcopy(self.payload['naturalness'])
        for key in original:
            self.payload['naturalness'] = copy.deepcopy(original)
            del self.payload['naturalness'][key]
            self.rejects()
        for count in (0, 4, 6):
            self.payload['naturalness'] = copy.deepcopy(original)
            self.payload['naturalness']['checks'] = (original['checks'] * 2)[:count]
            self.rejects()
        for invalid in ('structure', 'invented', 17, None):
            self.payload['naturalness'] = copy.deepcopy(original)
            self.payload['naturalness']['checks'][-1]['id'] = invalid
            self.rejects()
        self.payload['naturalness'] = copy.deepcopy(original)
        self.payload['naturalness']['checks'][0]['extra'] = True
        self.rejects()

    def test_naturalness_unconfirmed_checks_and_missing_evidence_rejected(self):
        original = copy.deepcopy(self.payload['naturalness'])
        for value in (False, 1, 'true', None, 'NOT_EVALUATED'):
            self.payload['naturalness'] = copy.deepcopy(original)
            self.payload['naturalness']['checks'][0]['passed'] = value
            self.rejects()
        for key in ('reason', 'body_location', 'evidence_ref'):
            for value in ('', ' ', None, 'NOT_EVALUATED', '미확인', '미검증', 'TBD'):
                self.payload['naturalness'] = copy.deepcopy(original)
                self.payload['naturalness']['checks'][0][key] = value
                self.rejects()
        for refs in ([], None, 'fixture', [''], ['NOT_EVALUATED']):
            self.payload['naturalness'] = copy.deepcopy(original)
            self.payload['naturalness']['comparison_refs'] = refs
            self.rejects()

    def test_item_17_four_rejected_even_with_valid_total_99(self):
        self.payload['items'][16]['score'] = 4
        self.payload['total'] = 99
        with self.assertRaisesRegex(PhysicalAIQualityError, 'item 17'):
            self.check()

    def test_item_count_and_ids_are_exact(self):
        item = self.payload['items'].pop()
        self.rejects()
        self.payload['items'].append(item)
        for invalid in (1, 0, 21, True, '20', 20.0):
            self.payload['items'][-1]['id'] = invalid
            self.rejects()

    def test_scores_cannot_be_unknown_boolean_float_or_out_of_range(self):
        for value in (True, 5.0, '5', -1, 6, None, 'NOT_EVALUATED'):
            self.payload['items'][0]['score'] = value
            self.rejects()

    def test_every_item_requires_reason_location_and_evidence(self):
        for key in ('reason', 'body_location', 'evidence_ref'):
            original = self.payload['items'][0][key]
            for value in ('', '  ', None, [], 'NOT_EVALUATED', 'unknown', 'TBD'):
                self.payload['items'][0][key] = value
                self.rejects()
            self.payload['items'][0][key] = original
        self.payload['items'][0]['extra'] = 'unknown'
        self.rejects()

    def test_distinct_named_reviewer_and_timezone_required(self):
        for reviewer in ('writer-agent-1', ' WRITER-AGENT-1 ', '', '  ', None):
            self.payload['reviewer_id'] = reviewer
            self.rejects()
        self.payload['reviewer_id'] = 'separate-reviewer'
        for timestamp in ('2026-09-17T10:00:00', 'today', ''):
            self.payload['reviewed_at'] = timestamp
            self.rejects()

    def test_duplicate_json_fields_rejected(self):
        self.review.write_text(json.dumps(self.payload)[:-1] + ', "total":100}')
        with self.assertRaises(PhysicalAIQualityError):
            enforce_quality(self.publish, self.review)

    def test_nonobject_review_and_malformed_json_rejected(self):
        for raw in ('[]', 'null', '{broken json'):
            self.review.write_text(raw)
            with self.assertRaises(PhysicalAIQualityError):
                enforce_quality(self.publish, self.review)


if __name__ == '__main__':
    unittest.main()
