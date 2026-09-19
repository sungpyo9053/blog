"""Fail-closed structural contract for an independent Physical AI review.

This validates the review artifact and its binding to final publication bytes.
It does NOT establish that claims, evidence, scores, or reviewer identity are true;
the independent Reviewer and existing Publisher approval remain required.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


class PhysicalAIQualityError(ValueError):
    """The article lacks a complete, current, passing quality review."""


FIELDS = {
    'schema_version', 'publish_sha256', 'writer_id', 'reviewer_id', 'reviewed_at',
    'gates', 'items', 'total', 'verdict', 'naturalness',
}
ITEM_FIELDS = {'id', 'score', 'reason', 'body_location', 'evidence_ref'}
GATES = {f'gate_{number}' for number in range(1, 9)}
NATURALNESS_CHECKS = {'structure', 'rhythm', 'restraint', 'judgment', 'honesty'}


def enforce_naturalness(value, items):
    """Validate a semantic review record, not an AI-authorship detector."""
    _require(isinstance(value, dict) and set(value) == {
        'verdict', 'checks', 'comparison_refs', 'unresolved_issues'},
        'Naturalness review is required with exact fields')
    _require(value['verdict'] == 'PASS' and value['unresolved_issues'] == [],
             'Naturalness review must pass without unresolved issues')
    refs = value['comparison_refs']
    _require(isinstance(refs, list) and bool(refs) and all(_nonempty(ref) for ref in refs),
             'Naturalness review requires recent-article comparison evidence')
    checks = value['checks']
    _require(isinstance(checks, list) and len(checks) == len(NATURALNESS_CHECKS),
             'All five naturalness checks are required')
    seen = set()
    for check in checks:
        _require(isinstance(check, dict) and set(check) == {
            'id', 'passed', 'reason', 'body_location', 'evidence_ref'},
            'Naturalness check has missing or unknown fields')
        name = check['id']
        _require(isinstance(name, str) and name in NATURALNESS_CHECKS and name not in seen,
                 'Naturalness check IDs must be unique and complete')
        seen.add(name)
        _require(check['passed'] is True, 'Unconfirmed naturalness check')
        _require(all(_nonempty(check[field]) for field in ('reason', 'body_location', 'evidence_ref')),
                 'Naturalness check requires reason, location and evidence')
    _require(any(item.get('id') == 17 and item.get('score') == 5 for item in items),
             'Natural prose quality item 17 must score five')


def _require(condition, message):
    if not condition:
        raise PhysicalAIQualityError(message)


def _nonempty(value):
    return (isinstance(value, str) and bool(value.strip())
            and value.strip().casefold() not in
            {'not_evaluated', 'unknown', 'unverified', 'not_verified', 'n/a', 'todo', 'tbd', '미확인', '미검증'})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate JSON field in quality review')
        result[key] = value
    return result


def enforce_quality(publish_path, review_path):
    """Return a validated review, or raise before any publishing side effect."""
    try:
        document = Path(publish_path).read_bytes()
        review = json.loads(Path(review_path).read_text(encoding='utf-8'),
                            object_pairs_hook=_unique_object)
    except PhysicalAIQualityError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise PhysicalAIQualityError('Final document or quality review is unreadable') from exc
    _require(isinstance(review, dict) and set(review) == FIELDS,
             'Quality review has missing or unknown fields')
    _require(type(review['schema_version']) is int and review['schema_version'] == 2,
             'Unknown quality review schema')
    _require(review['publish_sha256'] == hashlib.sha256(document).hexdigest(),
             'Quality review does not match final publish.md SHA256')
    for field in ('writer_id', 'reviewer_id', 'reviewed_at'):
        _require(_nonempty(review[field]), f'Quality review requires {field}')
    _require(review['writer_id'].strip().casefold() != review['reviewer_id'].strip().casefold(),
             'Writer cannot approve their own quality review')
    try:
        reviewed_at = datetime.fromisoformat(review['reviewed_at'].replace('Z', '+00:00'))
    except ValueError as exc:
        raise PhysicalAIQualityError('Quality review timestamp is not ISO8601') from exc
    _require(reviewed_at.tzinfo is not None and reviewed_at.utcoffset() is not None,
             'Quality review timestamp must include timezone')
    gates = review['gates']
    _require(isinstance(gates, dict) and set(gates) == GATES,
             'All eight indexed quality gates are required')
    _require(all(value is True for value in gates.values()),
             'All eight quality gates must be confirmed true')
    items = review['items']
    _require(isinstance(items, list) and len(items) == 20,
             'Exactly twenty quality items are required')
    ids = set()
    total = 0
    for item in items:
        _require(isinstance(item, dict) and set(item) == ITEM_FIELDS,
                 'Quality item has missing or unknown fields')
        index, score = item['id'], item['score']
        _require(type(index) is int and 1 <= index <= 20 and index not in ids,
                 'Quality items must have unique integer IDs 1 through 20')
        _require(type(score) is int and 0 <= score <= 5,
                 'Quality item scores must be integers from zero to five')
        for field in ('reason', 'body_location', 'evidence_ref'):
            _require(_nonempty(item[field]), f'Quality item requires {field}')
        ids.add(index)
        total += score
    _require(type(review['total']) is int and review['total'] == total and total >= 99,
             'Quality review total must equal item sum and reach 99')
    _require(review['verdict'] == 'APPROVED', 'Quality review verdict must be APPROVED')
    enforce_naturalness(review['naturalness'], items)
    return review
