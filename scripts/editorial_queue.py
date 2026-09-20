"""Frozen reviewed article queue. All mutating callers must hold the lane lock."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import html
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from scripts.evidence_topic_miner import atomic_replace, atomic_write_new

KST = timezone(timedelta(hours=9))
TARGET = 3
MAXIMUM = 7
MAX_AGE = timedelta(days=7)


class SourceCheckError(ValueError):
    """Safe diagnostics: never persist response bodies, credentials or query strings."""

    def __init__(self, reason, url, *, status=None):
        super().__init__(reason)
        self.diagnostic = {
            'reason': reason,
            'failure_stage': 'source_recheck',
            'source_host': urlparse(url).hostname,
            'source_url_sha256': hashlib.sha256(url.encode()).hexdigest(),
        }
        if status is not None:
            self.diagnostic['http_status'] = status


class SourceText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.ignored = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script','style','nav','header','footer'}:
            self.ignored.append(tag)

    def handle_endtag(self, tag):
        if self.ignored and tag == self.ignored[-1]:
            self.ignored.pop()

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def clock():
    return datetime.now(KST)


def enabled(repo):
    path = Path(repo) / 'config/editorial-queue.json'
    return path.is_file() and json.loads(path.read_text()).get('enabled') is True


def directory(repo):
    return Path(repo) / 'output/editorial-queue'


def save(path, data, *, new=False):
    (atomic_write_new if new else atomic_replace)(path, (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode())


def rows(repo):
    result = []
    for path in sorted(directory(repo).glob('*.json')):
        row = json.loads(path.read_text())
        if row.get('schema_version') != 1 or row.get('status') not in {'queued','held','publishing','published'}:
            raise ValueError('queue_state_invalid')
        if row.get('queue_id') != path.stem:
            raise ValueError('queue_identity_invalid')
        result.append(row)
    return result


def reserved_candidate_ids(repo):
    return {row['candidate']['candidate_id'] for row in rows(repo)}


def preparation_allowed(repo, now=None):
    items = rows(repo)
    # Stop preparation too when a publication is unresolved; do not bury its alert.
    if any(row['status'] == 'publishing' for row in items):
        return False
    return sum(row['status'] == 'queued' for row in items) < TARGET


def timestamp(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('queue_timestamp_without_timezone')
    return dt


def safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or not parsed.hostname or parsed.port not in (None,443):
        raise ValueError('source_url_not_public_https')
    for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError('source_url_private_address')


def source_digest(url):
    # Bounded, no credentials, no redirects to private or unreviewed destinations.
    match = re.fullmatch(r'https://github.com/([^/]+)/([^/]+)/blob/([0-9a-f]{40})/(.+)',url)
    if match:
        url='https://raw.githubusercontent.com/'+'/'.join(match.groups())
    safe_url(url)
    with requests.get(url, timeout=(5,20), stream=True, allow_redirects=False,
                      headers={'User-Agent':'HuntLab-EditorialRecheck/1.0'}) as response:
        if response.status_code != 200:
            raise SourceCheckError('source_recheck_http_error', url, status=response.status_code)
        chunks = []; size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 4_000_000:
                raise SourceCheckError('source_too_large', url)
            chunks.append(chunk)
        data = b''.join(chunks)
        # HTML navigation/advertising scripts are not the article's source text.
        if 'text/html' in response.headers.get('Content-Type',''):
            parser = SourceText(); parser.feed(data.decode('utf-8',errors='replace'))
            data = re.sub(r'\s+',' ',' '.join(parser.parts)).strip().encode()
        if not data:
            raise SourceCheckError('source_empty', url)
        return hashlib.sha256(data).hexdigest()


def context_for(prepared, repo):
    from scripts.run_daily_pipeline import TopicContext
    values = dict(prepared['context'])
    path = Path(values['directory']).resolve()
    if (Path(repo)/'output').resolve() not in path.parents:
        raise ValueError('prepared_path_outside_output')
    values['directory'] = path
    values['tags'] = tuple(values.get('tags', []))
    return TopicContext(**values)


def source_urls(text,candidate):
    urls=set(re.findall(r'https://[^\s<>\)\]"\']+',text))
    urls.update(candidate.get('evidence',{}).get('public_urls',[]))
    urls=sorted({url.split('#',1)[0] for url in urls if urlparse(url).hostname!='huntlab.app'})
    if not urls or len(urls)>40:
        raise ValueError('queue_source_set_invalid')
    return urls


def freeze_sources(path, *, candidate, destination, fetch=source_digest):
    from publisher.frontmatter import load_document
    text=load_document(Path(path)).markdown
    sources=[{'url':url,'sha256':fetch(url)} for url in source_urls(text,candidate)]
    by_url={row['url']:row['sha256'] for row in sources}
    contract=candidate.get('foundation_contract',{})
    for name in ('worked_example','verification'):
        reference=contract.get(name)
        if reference and by_url.get(reference['public_url'])!=reference['sha256']:
            raise ValueError('queue_pinned_evidence_mismatch')
    payload={'checked_at':clock().isoformat(),'sources':sources,'mode':'before_independent_final_review'}
    save(Path(destination),payload,new=True)
    repo=Path(__file__).resolve().parents[1]
    queue_inventory=[{'queue_id':row['queue_id'],'candidate':row['candidate'],
                      'content':(context_for(row['prepared'],repo).directory/'publish.md').read_text()}
                     for row in rows(repo) if row['status'] in {'queued','publishing'}]
    save(Path(destination).parent/'queue-inventory.json',{'items':queue_inventory},new=True)
    return payload


def check_queue_overlap(path, repo, *, exclude=None):
    from scripts.editorial_gate import inspect_article
    from publisher.frontmatter import load_document
    own = load_document(path)
    for row in rows(repo):
        if row['queue_id'] == exclude or row['status'] not in {'queued','publishing'}:
            continue
        other = context_for(row['prepared'], repo).directory/'publish.md'
        doc = load_document(other)
        if (own.metadata['slug'] == doc.metadata['slug'] or
                re.sub(r'\W','', own.metadata['title']).casefold() == re.sub(r'\W','',doc.metadata['title']).casefold()):
            raise ValueError('queue_duplicate_identity')
        # Apply the same complete-body overlap detector used for public inventory.
        inventory = {'metadata':{'complete':True,'full_content':True,'collected_at':clock().isoformat(),
                                 'statuses':{'publish':0,'draft':1}},
                     'posts':[{'title':doc.metadata['title'],'slug':doc.metadata['slug'],
                               'content':doc.markdown,'status':'draft','post_id':1}]}
        report = inspect_article(path.read_text(), inventory)
        if not report['passed']:
            raise ValueError('queue_content_overlap_or_invalid')


def enqueue(candidate, prepared, *, repo, now=None, fetch=source_digest):
    from publisher.frontmatter import load_document
    from scripts.run_daily_pipeline import validate_prepared_artifacts
    now = now or clock()
    if len([r for r in rows(repo) if r['status']=='queued']) >= MAXIMUM:
        raise ValueError('queue_capacity_reached')
    if candidate['candidate_id'] in reserved_candidate_ids(repo):
        raise ValueError('queue_candidate_already_reserved')
    context = context_for(prepared, repo)
    validate_prepared_artifacts(context)
    path = context.directory/'publish.md'
    doc = load_document(path)
    if doc.metadata.get('existing_post_id'):
        raise ValueError('queue_existing_post_forbidden')
    check_queue_overlap(path, repo)
    # Include every external cited document, not only the candidate's primary URL.
    urls=source_urls(doc.markdown,candidate)
    baseline=json.loads((context.directory/'source-baseline.json').read_text())
    sources=baseline['sources']
    if set(urls)!=set(row['url'] for row in sources):
        raise ValueError('queue_sources_changed_after_review')
    quality=json.loads((context.directory/'physical-ai-quality-review.json').read_text())
    if timestamp(baseline['checked_at'])>timestamp(quality['reviewed_at']):
        raise ValueError('queue_sources_not_independently_reviewed')
    if any(fetch(row['url'])!=row['sha256'] for row in sources):
        raise ValueError('queue_source_changed')
    ident = hashlib.sha256(candidate['candidate_id'].encode()).hexdigest()[:24]
    row = {'schema_version':1,'queue_id':ident,'status':'queued','prepared_at':now.isoformat(),
           'candidate':candidate,'prepared':prepared,'sources':sources}
    directory(repo).mkdir(parents=True,exist_ok=True)
    save(directory(repo)/f'{ident}.json',row,new=True)
    return {'queue_id':ident,'status':'queued','wordpress_write_count':0}


def preflight(row, *, repo, inventory_path, now, fetch=source_digest):
    from scripts.run_daily_pipeline import validate_prepared_artifacts, validate_publish_contract
    from scripts.editorial_gate import enforce_prepublication
    context = context_for(row['prepared'], repo)
    if row['candidate'].get('candidate_origin') == 'foundation_concept':
        from scripts.foundation_candidates import foundation_activation_ready
        if not foundation_activation_ready(Path(repo)):
            raise ValueError('queue_foundation_activation_required')
    age = now-timestamp(row['prepared_at'])
    if age < timedelta(0) or age > MAX_AGE:
        raise ValueError('queue_review_expired')
    validate_prepared_artifacts(context)
    validate_publish_contract(context)
    quality = json.loads((context.directory/'physical-ai-quality-review.json').read_text())
    if not timedelta(0) <= now-timestamp(quality['reviewed_at']) <= MAX_AGE:
        raise ValueError('queue_review_expired')
    if not row.get('sources') or not isinstance(row['sources'],list):
        raise ValueError('queue_sources_missing')
    for source in row['sources']:
        if fetch(source['url']) != source['sha256']:
            raise ValueError('queue_source_changed')
    enforce_prepublication(context.directory/'publish.md',Path(inventory_path))
    check_queue_overlap(context.directory/'publish.md',repo,exclude=row['queue_id'])
    return context


def audit_queued_public(published, candidate):
    from scripts.run_evidence_deep_article import audit_public
    from publisher.config import WordPressConfig
    from publisher.wordpress import WordPressClient
    from scripts.run_daily_pipeline import PROJECT_ROOT
    audit = audit_public(published,candidate)
    client = WordPressClient(WordPressConfig.from_environment(PROJECT_ROOT/'.env'),max_retries=0)
    post = client.get_post(published['post_id'])
    raw = post.get('content',{}).get('raw')
    if not isinstance(raw,str) or hashlib.sha256(raw.encode()).hexdigest()!=published.get('expected_html_sha256'):
        raise ValueError('queue_readback_content_changed')
    response = requests.get(published['url'],timeout=30)
    response.raise_for_status()
    def plain(text):
        parser=SourceText(); parser.feed(text)
        value=html.unescape(' '.join(parser.parts))
        return re.sub(r'\s+','',value).translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'",'–':'-','—':'-'}))
    public = plain(response.text)
    blocks=re.findall(r'<(?:p|pre|h[2-6])\b[^>]*>(.*?)</(?:p|pre|h[2-6])>',raw,re.S|re.I)
    if not blocks or any(plain(block) not in public for block in blocks if plain(block)):
        raise ValueError('queue_public_body_mismatch')
    images=re.findall(r'<img\b[^>]*src="([^"]+)"',raw,re.I)
    if any(html.unescape(url) not in html.unescape(response.text) for url in images):
        raise ValueError('queue_public_images_missing')
    return {**audit,'approved_body_blocks_present':True,'stored_content_sha256':published['expected_html_sha256']}


def review_fresh_context(context, candidate, inventory_path, run_dir, repo, logger):
    """Independent read-only meaning check; never rewrite frozen approved articles."""
    from scripts.run_daily_pipeline import Stage, resolve_codex, run_stage
    queue_path=run_dir/'queue-review-inventory.json'
    save(queue_path,{'items':[{'candidate':r['candidate'],'content':(context_for(r['prepared'],repo).directory/'publish.md').read_text()}
                            for r in rows(repo) if r['status'] in {'queued','publishing'}]},new=True)
    target=run_dir/'release-review.json'
    content_hash=hashlib.sha256((context.directory/'publish.md').read_bytes()).hexdigest()
    inventory_hash=hashlib.sha256(Path(inventory_path).read_bytes()).hexdigest()
    queue_hash=hashlib.sha256(queue_path.read_bytes()).hexdigest()
    prompt=f'''Read agents/reviewer.md and guides/publisher-guide.md. You are the independent final pre-release checker, NOT Writer or Publisher.
Read the complete frozen article {context.directory/'publish.md'}, research, source-baseline, and schema2 approval in that directory.
Compare search intent against ALL published/draft full bodies in {inventory_path} and all OTHER candidate articles in {queue_path}; exclude this candidate {candidate['candidate_id']} only from queue.
Check changed source/version assumptions and duplicate reader question, not just repeated wording. Do not edit any article, review, image, config, or WordPress. Do not invoke Publisher.
Write only {target} as JSON with exact keys: verdict (APPROVED or HOLD), reason (concrete), publish_sha256={content_hash}, inventory_sha256={inventory_hash}, queue_sha256={queue_hash}.
Approve only if the current full-context comparison supports publication of the unchanged previously approved article. Unknown facts or unmet conditions mean HOLD. No new score or invented checks.'''
    run_stage(resolve_codex(),Stage('Queue Release Reviewer',Path(repo)/'agents/reviewer.md',prompt),logger,timeout_seconds=900,topic=context.title)
    review=json.loads(target.read_text())
    if (set(review)!={'verdict','reason','publish_sha256','inventory_sha256','queue_sha256'}
            or review['verdict']!='APPROVED' or not review['reason']
            or review['publish_sha256']!=content_hash or review['inventory_sha256']!=inventory_hash or review['queue_sha256']!=queue_hash):
        raise ValueError('queue_fresh_context_review_hold')
    return review


def release(*, run_id, inventory_path, apply, repo, output_root, logger, now=None,
            fetch=source_digest, publisher=None, auditor=None, reviewer=None):
    from scripts.run_evidence_deep_article import published_today, write_progress, audit_public
    from scripts.run_daily_pipeline import publish_prepared_topic
    from scripts.editorial_epoch import reject_legacy_run
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id):
        raise ValueError('queue_run_id_invalid')
    reject_legacy_run(run_id,Path(output_root),Path(repo))
    now = now or clock(); day = now.astimezone(KST).date().isoformat()
    run_dir = Path(output_root)/run_id
    run_dir.mkdir(parents=True,exist_ok=False)
    progress = run_dir/'progress.json'
    write_progress(progress,stage='queue_preflight',wordpress_write_count=0)
    base = {'run_id':run_id,'kst_date':day,'failed':False,'wordpress_write_count':0,
            'publication_mode':'briefing_only','candidate_count':0}
    if published_today(Path(output_root),day,repo=Path(repo)) >= 1:
        return {**base,'deep_article':'daily_limit_reached'}
    items = rows(repo)
    if any(row['status']=='publishing' for row in items):
        raise ValueError('queue_publication_reconciliation_required')
    if apply and now.astimezone(KST).hour != 10:
        return {**base,'deep_article':'outside_publication_window'}
    held = []
    for row in sorted((r for r in items if r['status']=='queued'),key=lambda r:r['prepared_at']):
        try:
            context = preflight(row,repo=repo,inventory_path=inventory_path,now=now,fetch=fetch)
        except Exception as exc:
            reason=str(exc) if re.fullmatch(r'queue_[a-z_]+',str(exc)) else type(exc).__name__
            held.append({'queue_id':row['queue_id'],'reason':reason})
            if apply:
                row.update(status='held',held_at=now.isoformat(),reason=reason)
                save(directory(repo)/f"{row['queue_id']}.json",row)
            continue
        if not apply:
            return {**base,'candidate_count':1,'deep_article':'ready_not_published','queue_id':row['queue_id'],'held':held}
        review_dir=run_dir/row['queue_id']; review_dir.mkdir()
        try:
            (reviewer or review_fresh_context)(context,row['candidate'],inventory_path,review_dir,repo,logger)
            # Independent review must not have modified the approved artifacts.
            preflight(row,repo=repo,inventory_path=inventory_path,now=clock(),fetch=fetch)
        except Exception as exc:
            row.update(status='held',held_at=clock().isoformat(),reason='release_review_hold')
            save(directory(repo)/f"{row['queue_id']}.json",row)
            held.append({'queue_id':row['queue_id'],'reason':'release_review_hold'})
            continue
        # Persist both barriers before the first possible media/tag/post write.
        row.update(status='publishing',release_run_id=run_id)
        save(directory(repo)/f"{row['queue_id']}.json",row)
        write_progress(progress,stage='publisher_started',wordpress_write_count='unknown')
        published = (publisher or publish_prepared_topic)(context,logger,inventory_path=Path(inventory_path))
        if not published.get('post_id'):
            raise ValueError('queue_publisher_result_unknown')
        write_progress(progress,stage='publisher_completed',wordpress_write_count=1)
        row.update(status='published',publication=published,published_at=clock().isoformat())
        save(directory(repo)/f"{row['queue_id']}.json",row)
        result = {**base,'candidate_count':1,'candidate_id':row['candidate']['candidate_id'],
                  'publication_mode':'dual_lane','wordpress_write_count':1,'publication':published,
                  'queue_id':row['queue_id'],'candidate':row['candidate']}
        save(run_dir/'publication.json',result,new=True)
        if published.get('content_verified') is not True or not published.get('url'):
            raise ValueError('queue_saved_content_verification_failed')
        audit = (auditor or audit_queued_public)(published,row['candidate'])
        return {**result,'deep_article':'published','public_audit':audit,'held':held}
    return {**base,'deep_article':'no_publishable_topic','held':held}
