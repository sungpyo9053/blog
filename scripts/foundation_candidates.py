"""Curated, independently checked concept candidates; never fabricated Git incidents.

This module is read-only. The shared Lane B runner owns locking, daily limits,
publication, and consumption. Structural checks do not authenticate authorship
or establish that a primary-source interpretation is correct.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from scripts.editorial_epoch import EpochError, evidence_fingerprint, git, identity, timestamp
from scripts.editorial_gate import inspect_article
from scripts.evidence_topic_miner import Event, contains_secret, existing_overlap, safe_relative_path


class FoundationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FoundationError(message)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def fresh(value, now, days=7):
    moment = timestamp(value)
    require(-300 <= (now - moment).total_seconds() <= days * 86400, 'stale_or_future_review')
    return moment


def https_url(value):
    require(isinstance(value, str), 'invalid_public_url')
    url = urlsplit(value)
    require(url.scheme == 'https' and url.hostname and not url.username and not url.password
            and not url.query and not any(c.isspace() for c in value), 'invalid_public_url')
    return value


def artifact(repo, reference):
    require(isinstance(reference, dict) and set(reference) == {'path', 'sha256', 'public_url'}, 'invalid_artifact_contract')
    relative = safe_relative_path(repo, reference['path'])
    require(relative.startswith(('editorial/', 'evidence/')), 'artifact_outside_editorial_evidence')
    path = repo / relative
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 2_000_000, 'invalid_artifact_file')
    raw = path.read_bytes()
    require(raw and hashlib.sha256(raw).hexdigest() == reference['sha256'], 'artifact_hash_mismatch')
    text = raw.decode('utf-8')
    require(not contains_secret(text), 'unsafe_artifact')
    url = https_url(reference['public_url'])
    require(re.search(r'/blob/[0-9a-f]{40}/' + re.escape(relative) + r'$', url), 'artifact_requires_pinned_public_url')
    revision = url.split('/blob/', 1)[1].split('/', 1)[0]
    require(git(repo, 'show', f'{revision}:{relative}') == raw, 'artifact_public_revision_mismatch')
    return text


def validate_foundation_epoch(candidate, seal, repo):
    """Retirement identities still apply; provenance describes docs, not an incident."""
    require(candidate.get('candidate_origin') == 'foundation_concept', 'wrong_candidate_origin')
    paths = candidate['_foundation_artifacts']
    for reference in paths:
        relative = safe_relative_path(repo, reference['path'])
        require(hashlib.sha256((repo / relative).read_bytes()).hexdigest() == reference['sha256'], 'foundation_artifact_changed')
        require(git(repo, 'show', f'HEAD:{relative}') == (repo / relative).read_bytes(), 'foundation_artifact_not_committed')
    if not seal:
        return
    denied = seal['denied']
    require(candidate['candidate_id'] not in denied['candidate_ids'], 'retired_candidate')
    require(identity(candidate['title_seed']) not in {identity(x) for x in denied['titles']}, 'retired_title')
    require(identity(candidate['slug']) not in {identity(x) for x in denied['slugs']}, 'retired_slug')
    require(evidence_fingerprint(candidate) not in denied['evidence_fingerprints'], 'retired_evidence')
    cutoff = seal['cutoff_commit']
    cutoff_time = timestamp(git(repo, 'show', '-s', '--format=%cI', cutoff).decode().strip())
    for reference in paths:
        relative = reference['path']
        latest = git(repo, 'log', '-1', '--format=%H', '--', relative).decode().strip()
        require(latest and latest != cutoff, 'foundation_provenance_not_new')
        git(repo, 'merge-base', '--is-ancestor', cutoff, latest)
        git(repo, 'merge-base', '--is-ancestor', latest, 'HEAD')
        require(timestamp(git(repo, 'show', '-s', '--format=%cI', latest).decode().strip()) > cutoff_time,
                'foundation_provenance_predates_cutoff')
    # Moving an old worked example to a new filename is not new provenance.
    example_path = candidate['foundation_contract']['worked_example']['path']
    example_blob = git(repo, 'rev-parse', f'HEAD:{example_path}').strip()
    old_blobs = {row.split()[2] for row in git(repo, 'ls-tree', '-r', cutoff).splitlines()}
    require(example_blob not in old_blobs, 'replayed_foundation_example')


def evaluate_foundation(path, *, repo, inventory_path, seal=None, now=None):
    now = now or datetime.now(UTC)
    safe_relative_path(repo, path.relative_to(repo).as_posix())
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 2_000_000, 'invalid_manifest_file')
    raw = path.read_bytes(); manifest = load_json(path)
    fields = {'schema_version', 'candidate_id', 'title', 'slug', 'reader_question', 'target_reader',
              'learning_outcome', 'unique_takeaway', 'primary_sources', 'worked_example', 'verification', 'author_id'}
    require(isinstance(manifest, dict) and set(manifest) == fields and type(manifest['schema_version']) is int
            and manifest['schema_version'] == 1, 'invalid_foundation_manifest')
    for key in fields - {'schema_version', 'primary_sources', 'worked_example', 'verification'}:
        require(isinstance(manifest[key], str) and manifest[key].strip(), 'missing_' + key)
    require(re.fullmatch(r'foundation-[a-z0-9-]{3,100}', manifest['candidate_id']), 'invalid_foundation_id')
    require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', manifest['slug']), 'invalid_foundation_slug')
    require(not contains_secret(raw.decode()), 'unsafe_manifest')
    sources = manifest['primary_sources']
    require(isinstance(sources, list) and sources, 'missing_primary_sources')
    for source in sources:
        require(isinstance(source, dict) and set(source) == {'url', 'publisher', 'claim_scope', 'checked_at'}, 'invalid_primary_source')
        https_url(source['url']); fresh(source['checked_at'], now)
        require(all(isinstance(source[k], str) and source[k].strip() for k in ('publisher', 'claim_scope')), 'missing_source_scope')
    example = artifact(repo, manifest['worked_example'])
    artifact(repo, manifest['verification'])
    review_path = path.with_suffix('.review.json')
    require(not review_path.is_symlink() and review_path.is_file() and review_path.stat().st_size <= 2_000_000, 'invalid_review_file')
    review = load_json(review_path)
    require(set(review) == {'schema_version', 'manifest_sha256', 'reviewer_id', 'reviewed_at', 'verdict',
                           'primary_sources_verified', 'worked_example_verified', 'public_evidence_verified', 'secret_safe'}, 'invalid_candidate_review')
    require(type(review['schema_version']) is int and review['schema_version'] == 1, 'invalid_review_version')
    require(review['manifest_sha256'] == hashlib.sha256(raw).hexdigest(), 'candidate_review_hash_mismatch')
    require(isinstance(review['reviewer_id'], str) and review['reviewer_id'].strip()
            and review['reviewer_id'].strip().casefold() != manifest['author_id'].strip().casefold(), 'candidate_self_approval')
    fresh(review['reviewed_at'], now)
    require(review['verdict'] == 'APPROVED' and all(review[k] is True for k in
            ('primary_sources_verified', 'worked_example_verified', 'public_evidence_verified', 'secret_safe')), 'candidate_review_not_approved')
    inventory = load_json(inventory_path)
    inspection = inspect_article(example, inventory, now=now)
    require(inspection['passed'], 'inventory_or_example_rejected:' + ','.join(inspection['failures']))
    event = Event('foundation')
    event.title = manifest['title']; event.slug = manifest['slug']
    event.subjects = [manifest['reader_question']]
    event.unique_takeaway = manifest['unique_takeaway']; event.reader_action = manifest['learning_outcome']
    overlap = existing_overlap(event, inventory['posts'])
    require(overlap['result'] == 'none', 'existing_search_intent_overlap')
    references = [manifest['worked_example'], manifest['verification']]
    candidate = {
        'candidate_origin': 'foundation_concept', 'candidate_id': manifest['candidate_id'],
        'title_seed': manifest['title'], 'slug': manifest['slug'],
        'real_trigger': '검토된 교육 질문: ' + manifest['reader_question'],
        'target_reader': manifest['target_reader'], 'problem': manifest['reader_question'],
        'why_it_matters': manifest['learning_outcome'], 'unique_takeaway': manifest['unique_takeaway'],
        'recommended_format': 'foundation_concept', 'publishability': 'READY', 'missing_evidence': [],
        'rejection_reason': None, 'before_after': {}, 'existing_post_overlap': overlap,
        'source_anchor': path.relative_to(repo).as_posix(),
        'evidence': {'commits': [], 'files': [r['path'] for r in references], 'tests': [],
                     'logs': [manifest['verification']['path']],
                     'public_urls': [s['url'] for s in sources] + [r['public_url'] for r in references]},
        'evidence_contract': {'type': 'foundation_concept', 'requirements': {
            'primary_sources_verified': True, 'worked_example_verified': True,
            'independent_candidate_review': True, 'public_access_verified': True,
            'current_public_and_draft_overlap_checked': True}},
        'foundation_contract': manifest,
        '_foundation_artifacts': [{'path': p.relative_to(repo).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                                  for p in [path, review_path, *(repo / r['path'] for r in references)]],
    }
    validate_foundation_epoch(candidate, seal, repo)
    return candidate


def load_foundation_candidates(*, repo, inventory_path, seal=None, consumed_ids=(), now=None):
    records, rejections = [], []
    directory = repo / 'editorial/physical-ai-candidates'
    for path in sorted(directory.glob('*.json')):
        if path.name.endswith('.review.json'):
            continue
        try:
            candidate = evaluate_foundation(path, repo=repo, inventory_path=inventory_path, seal=seal, now=now)
            if candidate['candidate_id'] not in set(consumed_ids):
                records.append(candidate)
        except (FoundationError, EpochError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            # No raw data/error output: invalid private artifacts may contain secrets.
            # Only a small static allowlist may leave the exception boundary.
            safe_reasons = {'existing_search_intent_overlap', 'stale_or_future_review',
                            'candidate_review_hash_mismatch', 'artifact_hash_mismatch',
                            'candidate_review_not_approved', 'foundation_artifact_not_committed'}
            reason = str(exc) if type(exc) is FoundationError and str(exc) in safe_reasons else 'foundation_contract_not_ready'
            rejections.append({'manifest': path.name, 'reason': reason})
    return records, rejections


def foundation_activation_ready(repo):
    """An explicit, evidence-bound first-draft acceptance is required to publish."""
    try:
        path = repo / 'output/foundation-workflow/activation.json'
        activation = load_json(path)
        require(set(activation) == {'schema_version', 'workflow', 'status', 'draft_post_id',
                'source_run_id', 'checked_at', 'reviewer_id', 'evidence'}, 'invalid_activation')
        require(type(activation['schema_version']) is int and activation['schema_version'] == 1
                and activation['workflow'] == 'foundation_concept'
                and activation['status'] == 'DRAFT_WORKFLOW_VERIFIED', 'activation_not_approved')
        require(type(activation['draft_post_id']) is int and activation['draft_post_id'] > 0, 'invalid_draft_id')
        require(all(isinstance(activation[k], str) and activation[k].strip() for k in
                    ('source_run_id', 'reviewer_id')), 'missing_activation_identity')
        moment = timestamp(activation['checked_at'])
        require((datetime.now(UTC) - moment).total_seconds() >= -300, 'future_activation')
        evidence = activation['evidence']
        relative = safe_relative_path(repo, evidence['path'])
        require(relative.startswith('output/'), 'activation_evidence_not_private_output')
        target = repo / relative
        require(not target.is_symlink(), 'symlink_activation_evidence')
        require(hashlib.sha256(target.read_bytes()).hexdigest() == evidence['sha256'], 'activation_evidence_changed')
        proof = load_json(target)
        draft = proof['draft']; raw = draft['content']['raw']
        require(draft['id'] == activation['draft_post_id'] and draft['status'] == 'draft'
                and isinstance(raw, str) and raw.strip() and proof['render_validation']['passed'] is True
                and proof['reread_body_sha256'] == hashlib.sha256(raw.encode()).hexdigest(), 'draft_verification_incomplete')
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def consumed_foundation_ids(output_root):
    """Confirmed writes consume even when the later public audit/receipt failed.

    A content rejection also consumes the candidate: otherwise the refill picks
    the same rejected candidate again on every attempt.
    """
    consumed = set()
    for directory in output_root.iterdir() if output_root.exists() else ():
        selected = directory / 'selected-candidate.json'
        if not directory.is_dir() or not selected.is_file():
            continue
        candidate = load_json(selected)
        records = [load_json(directory / name) for name in ('progress.json', 'result.json', 'publication.json')
                   if (directory / name).is_file()]
        if candidate.get('candidate_origin') == 'foundation_concept' and any(
                (type(row.get('wordpress_write_count')) is int and row['wordpress_write_count'] == 1)
                or row.get('error_type') == 'ContentQualityRejection'
                or row.get('reason') == 'editorial_gate_rejected' for row in records):
            consumed.add(candidate['candidate_id'])
    return consumed
