#!/usr/bin/env python3
"""Explicit, reversible September editorial migration. Dry-run unless --apply.

Archive means draft, never DELETE. Review the private plan before applying.
All existing IDs, slugs, original dates, media and original taxonomy records stay.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from datetime import UTC, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.audit_adsense_content import fetch_all

DEST = ROOT / 'output/editorial-restructure-20260915'
CONTENT = ROOT / 'editorial/2026-09-15'
CATEGORIES = {
    'rest-api-publishing': ('REST API 발행', '응답 판별, 재시도, 전체 목록 수집에서 발생하는 WordPress REST API 문제를 재현 코드와 함께 다룹니다.'),
    'automation-testing': ('자동화·테스트', '산출물 계약, 발행 조건과 실패 경로를 테스트로 확인하는 작업 기록입니다.'),
    'wordpress-operations': ('WordPress 운영', '본문 변경 전 백업, 플러그인 렌더링과 검색 설정을 검증하는 운영 기록입니다.'),
}
# Explicit editorial scope, not a score-derived AdSense quality verdict.
KEEP = {
    50: ('rest-api-publishing', '통제된 예제 비교', '2026-09-05', 'publisher/wordpress.py', 'Retry-After 날짜값에서 실패하는 파서를 고친 기록입니다. POST 중복과 대기 상한은 별도 문제로 남깁니다.'),
    132: ('rest-api-publishing', '목록 감사·통제 비교', '2026-09-05', 'scripts/audit_adsense_content.py', '첫 100개 응답만 확인해 빠진 글을 찾고, 모든 페이지의 고유 ID와 전체 건수를 대조합니다.'),
    698: ('rest-api-publishing', '통제된 예제 비교', '2026-09-05', 'scripts/huntlab_wp_diagnostics.py', 'HTTP 200 로그인 HTML을 성공으로 오판하는 조건과 JSON 글 ID를 확인하는 방법을 비교합니다.'),
    290: ('automation-testing', 'Fake Client 테스트', '2026-08-06', 'tests/test_publisher.py', '실제 글을 만들지 않고 정상 payload와 validation 실패 시 생성 차단을 한 쌍으로 검사합니다.'),
    373: ('automation-testing', '운영 로그·격리 테스트', '2026-08-14', 'scripts/run_daily_pipeline.py', '프로세스 성공과 필수 파일 생성을 분리하고, 누락 시 한 번만 재시도하는 산출물 계약입니다.'),
    706: ('automation-testing', '공개 코드·로그 대조', '2026-09-08', 'scripts/run_evidence_deep_article.py', '근거 있는 후보가 없으면 발행하지 않는 조건, 하루 한도와 체크포인트의 책임을 구분합니다.'),
    96: ('wordpress-operations', '코드·백업 기록 검토', '2026-07-29', 'scripts/backfill_internal_links.py', '내부 링크 일괄 변경에서 백업과 공개 URL 검사, 부분 적용과 복원의 경계를 나눕니다.'),
    301: ('wordpress-operations', '코드·공개 DOM 기록', '2026-08-06', 'deploy/wordpress/huntlab-article-toc/huntlab-article-toc.php', '요약 제목의 정규식 두 곳을 함께 수정하고, 저장된 본문과 공개 렌더링을 따로 검사합니다.'),
    699: ('wordpress-operations', '통제된 예제 비교', '2026-09-05', 'scripts/huntlab_wp_diagnostics.py', 'noindex 페이지와 sitemap URL을 같은 스냅샷으로 대조해 검색 설정의 불일치를 찾습니다.'),
}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def body(post):
    return post['content']['raw']

def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x', encoding='utf-8') as handle:
        os.chmod(path, 0o600)
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush(); os.fsync(handle.fileno())

def stamp():
    return datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')

def target_content(post, all_posts):
    path = CONTENT / f'post-{post["id"]}.html'
    text = path.read_text() if path.is_file() else body(post)
    # Remove the former unrelated link graph; contextual links are retained.
    text = re.sub(r'<!-- huntlab-related-links:v1 -->\s*<section\b.*?</section>', '', text, flags=re.S)
    hidden_urls = {p['link'].rstrip('/') for p in all_posts if p['id'] not in KEEP}
    def prune(match):
        return match[2] if match[1].rstrip('/') in hidden_urls else match[0]
    text = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', prune, text, flags=re.S)
    if post['id'] in (50,132,698) and 'huntlab-tool-link:20260915' not in text:
        label = {50:'Retry-After 값을 계산하기',132:'모은 글 ID와 전체 건수 비교하기',698:'HTML 200과 JSON 201 응답 비교하기'}[post['id']]
        text += f'\n<!-- huntlab-tool-link:20260915 --><p><a href="https://huntlab.app/wordpress-response-check/">{label}</a> — 입력값만 검사하는 브라우저 도구이며 실제 사이트에 요청하지 않습니다.</p>\n'
    return text

def make_plan(client):
    posts = fetch_all(client,'posts',status='publish') + fetch_all(client,'posts',status='draft')
    pages = fetch_all(client,'pages')
    assert set(KEEP) <= {p['id'] for p in posts}, 'Reviewed posts missing'
    assert all(p['status']=='publish' for p in posts if p['id'] in KEEP), 'Reviewed status changed'
    changes=[]
    for post in posts:
        if post['id'] not in KEEP and post['status'] != 'publish': continue
        reason = 'retain_reviewed_project_record' if post['id'] in KEEP else 'outside_current_editorial_scope_or_evidence_review_pending'
        changes.append({'id':post['id'],'slug':post['slug'],'before':post,'reason':reason,
                        'content':target_content(post,posts) if post['id'] in KEEP else None,
                        'status':'publish' if post['id'] in KEEP else 'draft'})
    plan={'created_at':datetime.now(UTC).isoformat(),'changes':changes,'pages_before':pages,'categories_before':fetch_all(client,'categories'),
          'page_files':{slug:(CONTENT/f'{slug}.html').read_text() for slug in ('about','editorial-policy','wordpress-response-check')}}
    private_json(DEST/'plan.json',plan)
    print(json.dumps({'plan':str(DEST/'plan.json'),'keep':len(KEEP),'to_draft':sum(c['status']=='draft' for c in changes),'sha256':digest(plan)}))

def apply_plan(client):
    plan=json.loads((DEST/'plan.json').read_text())
    receipt_dir=DEST/'receipts'; receipt_dir.mkdir(exist_ok=True,mode=0o700)
    # Refuse stale plans before the first write. Re-runs check each uncompleted item.
    for row in plan['changes']:
        if (receipt_dir/f'post-{row["id"]}.json').exists(): continue
        current=client.request('GET',f'posts/{row["id"]}?context=edit')
        assert current['slug']==row['slug'] and current['status']==row['before']['status'] and body(current)==body(row['before']), f'Stale post {row["id"]}'
    for original in plan['pages_before']:
        slug=original['slug']
        if slug not in ('about','editorial-policy','contact') or (receipt_dir/f'page-{slug}.json').exists(): continue
        current=client.request('GET',f'pages/{original["id"]}?context=edit')
        assert current['status']==original['status'] and body(current)==body(original),f'Stale page {slug}'
    categories={}
    for slug,(name,description) in CATEGORIES.items():
        rows=client.request('GET',f'categories?slug={slug}&context=edit')
        category=rows[0] if rows else client.request('POST','categories',payload={'name':name,'slug':slug,'description':description},expected=(201,))
        assert category['slug']==slug
        categories[slug]=category['id']
    # Update retained content before withdrawing old targets.
    for row in sorted(plan['changes'],key=lambda item:item['status']!='publish'):
        receipt=receipt_dir/f'post-{row["id"]}.json'
        if receipt.exists(): continue
        payload={'status':row['status']}
        if row['id'] in KEEP:
            slug,method,date,source,excerpt=KEEP[row['id']]
            date = row['before'].get('meta',{}).get('_hunt_news_evidence_date') or date
            payload.update(content=row['content'],categories=[categories[slug]],excerpt=excerpt,meta={
                '_hunt_news_content_type':'verified_case','_hunt_news_problem_group':CATEGORIES[slug][0],
                '_hunt_news_verification_method':method,'_hunt_news_evidence_date':date,
                '_hunt_news_evidence_badges':json.dumps([method,'공개 코드'],ensure_ascii=False),
                '_hunt_news_evidence_url':'https://github.com/sungpyo9053/blog/blob/main/'+source,
                '_hunt_news_asset_url':'https://huntlab.app/wordpress-response-check/' if row['id'] in (50,132,698) else '',
            })
        client.request('POST',f'posts/{row["id"]}',payload=payload)
        current=client.request('GET',f'posts/{row["id"]}?context=edit')
        assert current['status']==row['status'] and current['slug']==row['slug']
        if row['id'] in KEEP:
            assert current['categories']==payload['categories'] and body(current)==payload['content']
            assert current['excerpt']['raw']==payload['excerpt']
            assert all(current.get('meta',{}).get(key)==value for key,value in payload['meta'].items()),f'Metadata readback mismatch {row["id"]}'
        private_json(receipt,{'id':row['id'],'status':current['status'],'url':current['link'],'before_sha256':digest(row['before']),'payload_sha256':digest(payload),'verified_at':datetime.now(UTC).isoformat()})
        print(f'post={row["id"]} status={current["status"]} verified=true',flush=True)
    for slug,content in plan['page_files'].items():
        receipt=receipt_dir/f'page-{slug}.json'
        if receipt.exists(): continue
        rows=client.request('GET',f'pages?slug={slug}&context=edit&status=publish,draft')
        title={'about':'운영자와 작성 방식','editorial-policy':'검증·정정 원칙','wordpress-response-check':'WordPress 응답 진단 도구'}[slug]
        if rows:
            original=next((p for p in plan['pages_before'] if p['id']==rows[0]['id']),None)
            assert original and body(original)==body(rows[0]),f'Stale page {slug}'
            page=client.request('POST',f'pages/{rows[0]["id"]}',payload={'title':title,'content':content})
        else:
            page=client.request('POST','pages',payload={'title':title,'slug':slug,'status':'draft','content':content},expected=(201,))
            assert page['slug']==slug
            page=client.request('POST',f'pages/{page["id"]}',payload={'status':'publish'})
        current=client.request('GET',f'pages/{page["id"]}?context=edit')
        assert current['status']=='publish' and current['slug']==slug and body(current)==content
        private_json(receipt,{'id':page['id'],'url':page['link'],'status':'publish','content_sha256':digest(content),'verified_at':datetime.now(UTC).isoformat()})
        print(f'page={slug} id={page["id"]} verified=true',flush=True)
    # Fix false team attribution without altering privacy commitments.
    for original in plan['pages_before']:
        if original['slug']!='contact':continue
        receipt=receipt_dir/'page-contact.json'
        if receipt.exists(): continue
        content=body(original).replace('<strong>Hunt News 편집팀</strong>','<strong>HuntLab 운영자</strong>').replace('편집팀은','운영자는')
        current=client.request('GET',f'pages/{original["id"]}?context=edit')
        if body(current)==body(original): client.request('POST',f'pages/{original["id"]}',payload={'content':content})
        verified=client.request('GET',f'pages/{original["id"]}?context=edit')
        assert body(verified)==content and verified['status']=='publish'
        private_json(receipt,{'id':original['id'],'url':verified['link'],'content_sha256':digest(content),'verified_at':datetime.now(UTC).isoformat()})
    print('migration_complete=true posts_deleted=0 backup='+str(DEST/'plan.json'))

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--apply',action='store_true'); args=parser.parse_args()
    client=WordPressClient(WordPressConfig.from_environment(ROOT/'.env'),max_retries=0)
    if args.apply: apply_plan(client)
    else: make_plan(client)
if __name__=='__main__':main()
