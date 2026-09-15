#!/usr/bin/env python3
"""Anonymous public checks for the scoped editorial release, never an approval score."""
from __future__ import annotations
import argparse,json,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC,datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from xml.etree import ElementTree
BASE='https://huntlab.app/'
KEEP={50,96,132,290,301,373,698,699,706}

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
            return {'url':url,'final_url':response.url,'status':response.status,'type':response.headers.get_content_type(),'body':response.read().decode('utf-8',errors='replace')}
    except Exception as error:return {'url':url,'status':getattr(error,'code',None),'error':type(error).__name__}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    inventory=fetch(BASE+'?rest_route=/wp/v2/posts&per_page=100&_fields=id,link,categories,status')
    posts=json.loads(inventory['body']);assert isinstance(posts,list)
    failures=[]
    if {p['id'] for p in posts}!=KEEP:failures.append('unexpected_public_post_inventory')
    urls=[BASE,*[BASE+s+'/' for s in ('about','contact','editorial-policy','privacy-policy','wordpress-response-check','category/rest-api-publishing','category/automation-testing','category/wordpress-operations')],*[p['link'] for p in posts]]
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
        root=ElementTree.fromstring(response['body']);locations=[e.text for e in root.iter() if e.tag.rsplit('}',1)[-1]=='loc' and e.text]
        if root.tag.endswith('sitemapindex'):pending.extend(u for u in locations if u.startswith(BASE))
        else:sitemap_urls.update(locations)
    for p in posts:
        if p['link'] not in sitemap_urls:failures.append('missing_post_sitemap:'+p['link'])
    plan_path=Path('output/editorial-restructure-20260915/plan.json')
    if plan_path.exists():
        old=json.loads(plan_path.read_text())
        for row in old['changes']:
            if row['status']=='draft' and row['before']['link'] in sitemap_urls:failures.append('archived_in_sitemap:'+str(row['id']))
    ads=fetch(BASE+'ads.txt')
    if ads['status']!=200 or 'pub-6970683716237249' not in ads.get('body',''):failures.append('ads_txt')
    report={'checked_at':datetime.now(UTC).isoformat(),'passed':not failures,'failures':failures,'public_post_ids':sorted(p['id'] for p in posts),'pages_checked':len(responses),'internal_urls_checked':len(links),'sitemap_documents':len(sitemap_seen),'sitemap_urls':len(sitemap_urls),'pages':[{'url':r['url'],'status':r['status'],'h1':parsed[r['url']].h1,'canonical':parsed[r['url']].canonical,'robots':parsed[r['url']].robots} for r in responses],'ads_txt_ok':'ads_txt' not in failures}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='pages'},ensure_ascii=False));return int(bool(failures))
if __name__=='__main__':sys.exit(main())
