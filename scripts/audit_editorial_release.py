#!/usr/bin/env python3
"""Anonymous public checks for the scoped editorial release, never an approval score."""
from __future__ import annotations
import argparse,json,sys
from math import ceil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC,datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from xml.etree import ElementTree
BASE='https://huntlab.app/'
KEEP={50,96,132,290,301,373,698,699,706}
CATEGORY_SLUGS={'rest-api-publishing','automation-testing','wordpress-operations'}

class AuditError(ValueError):
    """A check cannot establish a complete, internally consistent public state."""

def fetch_collection(endpoint, fields, fetcher=None):
    """Read all pages with stable WordPress totals; never accept a partial snapshot."""
    fetcher = fetcher or fetch
    rows=[]; seen=set(); expected=None; page=1
    while True:
        response=fetcher(BASE+'?rest_route=/wp/v2/'+endpoint+
                         f'&per_page=100&page={page}&orderby=id&order=asc&_fields={fields}')
        if response.get('status')!=200:
            raise AuditError('inventory_http:'+endpoint+':'+str(page))
        try:
            headers=response['headers']
            total=int(headers['x-wp-total']); pages=int(headers['x-wp-totalpages'])
            batch=json.loads(response['body'])
        except (KeyError,ValueError,TypeError) as error:
            raise AuditError('inventory_metadata:'+endpoint) from error
        if total<0 or pages!=ceil(total/100) or pages>1000:
            raise AuditError('inventory_totals:'+endpoint)
        if expected is None:expected=(total,pages)
        if expected!=(total,pages):raise AuditError('inventory_changed:'+endpoint)
        count=min(100,max(0,total-(page-1)*100))
        if not isinstance(batch,list) or len(batch)!=count:
            raise AuditError('inventory_page_count:'+endpoint+':'+str(page))
        for row in batch:
            if not isinstance(row,dict) or type(row.get('id')) is not int or row['id']<=0 or row['id'] in seen:
                raise AuditError('inventory_identity:'+endpoint)
            seen.add(row['id']); rows.append(row)
        if page>=pages:break
        page+=1
    return rows

def validate_public_posts(posts,categories):
    """Baseline stays required; new posts need the deployed lane and category contract.

    This checks public eligibility only, not Reviewer approval or factual quality.
    """
    failures=[]
    ids={p['id'] for p in posts}
    if not KEEP<=ids:failures.append('missing_curated_baseline')
    selected=[c for c in categories if c.get('slug') in CATEGORY_SLUGS]
    if len(selected)!=3 or {c.get('slug') for c in selected}!=CATEGORY_SLUGS:
        failures.append('editorial_categories_missing_or_ambiguous')
    allowed={c['id'] for c in selected}; links=set()
    for post in posts:
        post_id=str(post['id']); link=post.get('link','')
        if not isinstance(link,str):link=''
        try:parts=urlsplit(link)
        except ValueError:
            failures.append('post_link:'+post_id)
            parts=urlsplit('')
        if parts.scheme!='https' or parts.netloc!='huntlab.app' or parts.path=='/' or parts.query or parts.fragment or link in links:
            failures.append('post_link:'+post_id)
        links.add(link)
        if post.get('status')!='publish':failures.append('post_status:'+post_id)
        assigned=post.get('categories')
        if not isinstance(assigned,list) or not assigned or any(type(c) is not int or c not in allowed for c in assigned):
            failures.append('post_editorial_category:'+post_id)
        if post['id'] not in KEEP:
            meta=post.get('meta')
            if not isinstance(meta,dict) or meta.get('_hunt_news_content_type')!='evidence_deep_article':
                failures.append('unexpected_public_post:'+post_id)
    return failures

def check_archived_sitemap(plan_path,sitemap_urls):
    """Missing private archival evidence is an explicit failure, not a skipped check."""
    try:
        plan=json.loads(plan_path.read_text())
        changes=plan['changes']
        archived=[row for row in changes if row['status']=='draft']
        if not archived:raise ValueError('empty archive baseline')
        return ['archived_in_sitemap:'+str(row['id']) for row in archived if row['before']['link'] in sitemap_urls]
    except (OSError,ValueError,KeyError,TypeError):
        return ['archive_baseline_unavailable_or_invalid']

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.images=[];self.robots=[];self.canonical='';self.ids=set();self.h1=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag=='img' and a.get('src'):self.images.append(a['src'])
        if tag=='h1':self.h1+=1
        if tag=='meta' and a.get('name','').lower()=='robots':self.robots.append(a.get('content',''))
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href','')

def fetch(url):
    try:
        with urlopen(Request(url,headers={'User-Agent':'HuntLab-PublicQA/1.0'}),timeout=25) as response:
            return {'url':url,'final_url':response.url,'status':response.status,'headers':{k.lower():v for k,v in response.headers.items()},'type':response.headers.get_content_type(),'body':response.read().decode('utf-8',errors='replace')}
    except Exception as error:return {'url':url,'status':getattr(error,'code',None),'error':type(error).__name__}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--archive-plan',type=Path,default=Path('output/editorial-restructure-20260915/plan.json'))
    args=parser.parse_args()
    failures=[]
    posts=[];inventory_complete=False
    try:
        posts=fetch_collection('posts','id,link,categories,status,meta')
        categories=fetch_collection('categories','id,slug')
        failures.extend(validate_public_posts(posts,categories));inventory_complete=True
    except AuditError as error:failures.append(str(error))
    urls=[BASE,*[BASE+s+'/' for s in ('about','contact','editorial-policy','privacy-policy','wordpress-response-check','category/rest-api-publishing','category/automation-testing','category/wordpress-operations')],*[p['link'] for p in posts if isinstance(p.get('link'),str) and p['link'].startswith(BASE)]]
    with ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(fetch,urls))
    by_url={r['url']:r for r in responses}; links=set();parsed={}
    for response in responses:
        url=response['url'];page=Page();page.feed(response.get('body',''));parsed[url]=page
        if response['status']!=200:failures.append('http:'+url)
        if page.h1!=1:failures.append('h1:'+url)
        if 'noindex' in ','.join(page.robots):failures.append('noindex:'+url)
        if page.canonical.rstrip('/')!=url.rstrip('/'):failures.append('canonical:'+url)
        if url==BASE and ('class="no-results' in response.get('body','') or '찾으시는 것을 찾을 수' in response.get('body','')):failures.append('empty_loop_home')
        for href in page.links+page.images:
            target=urljoin(url,href);parts=urlsplit(target)
            if parts.netloc=='huntlab.app' and parts.scheme in ('http','https'):
                target=target.split('#',1)[0]
                if not parts.query and '/wp-json/' not in parts.path:links.add(target)
    remaining_links = sorted(links - set(by_url))
    with ThreadPoolExecutor(max_workers=4) as pool:
        linked = list(pool.map(fetch, remaining_links))
    for response in linked:
        if response['status']!=200:failures.append('internal_link:'+response['url'])
    sitemap_urls=set();sitemap_seen=set();pending=[BASE+'sitemap.xml']
    while pending:
        url=pending.pop()
        if url in sitemap_seen:continue
        sitemap_seen.add(url);response=fetch(url)
        if response['status']!=200:failures.append('sitemap_http:'+url);continue
        try:root=ElementTree.fromstring(response['body'])
        except (ElementTree.ParseError,KeyError):failures.append('sitemap_invalid:'+url);continue
        if root.tag.rsplit('}',1)[-1] not in ('sitemapindex','urlset'):failures.append('sitemap_invalid:'+url);continue
        locations=[e.text for e in root.iter() if e.tag.rsplit('}',1)[-1]=='loc' and e.text]
        if root.tag.endswith('sitemapindex'):pending.extend(u for u in locations if u.startswith(BASE))
        else:sitemap_urls.update(locations)
    for p in posts:
        if p.get('link') not in sitemap_urls:failures.append('missing_post_sitemap:'+str(p.get('link')))
    failures.extend(check_archived_sitemap(args.archive_plan,sitemap_urls))
    ads=fetch(BASE+'ads.txt')
    if ads['status']!=200 or 'pub-6970683716237249' not in ads.get('body',''):failures.append('ads_txt')
    report={'checked_at':datetime.now(UTC).isoformat(),'passed':not failures,'failures':failures,'public_post_ids':sorted(p['id'] for p in posts),'pages_checked':len(responses),'internal_urls_checked':len(links),'sitemap_documents':len(sitemap_seen),'sitemap_urls':len(sitemap_urls),'pages':[{'url':r['url'],'status':r['status'],'h1':parsed[r['url']].h1,'canonical':parsed[r['url']].canonical,'robots':parsed[r['url']].robots} for r in responses],'ads_txt_ok':'ads_txt' not in failures}
    report.update(inventory_complete=inventory_complete,curated_baseline_ids=sorted(KEEP),additional_public_post_ids=sorted(p['id'] for p in posts if p['id'] not in KEEP),scope='Public technical eligibility; not editorial approval or AdSense approval')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='pages'},ensure_ascii=False));return int(bool(failures))
if __name__=='__main__':sys.exit(main())
