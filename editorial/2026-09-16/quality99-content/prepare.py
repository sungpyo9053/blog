"""Generate proposed body corrections from fresh REST GET; never update WordPress."""
import hashlib
import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

HERE = Path(__file__).resolve().parent
client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'), max_retries=0)

def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()

def example(name):
    code = (HERE / (name + '-example.py')).read_text()
    return '<pre><code class="language-bash">' + html.escape("python3 - <<'PY'\n" + code + 'PY\n') + '</code></pre>\n'

sections = {
132: '''<h2>지금 공개 글 전체를 직접 세는 완결 예제</h2>
<p>앞의 119개는 과거 감사 수치다. 아래는 2026년 9월 16일 추가한 독자용 검사이며 현재 공개 글만 읽는다. Python 3.11 이상이 설치된 터미널에서 블록 전체를 실행한다. 저장소 다운로드·인증·추가 패키지가 필요 없고 파일도 만들지 않지만, 공개 HTTPS에 접근할 네트워크는 필요하다.</p>
<p>페이지 이동을 작은 사이트에서도 확인하도록 한 번에 3개씩 요청한다. <code>orderby=id&amp;order=asc</code>로 정렬하고, 매번 전체 건수·페이지 수가 같은지, 예상한 페이지 길이와 고유 ID가 맞는지 확인한다. 리다이렉트·비JSON·중복 ID·응답 크기 초과는 실패로 끝낸다. 최대 100페이지인 이 예제는 300건을 넘는 사이트에는 그대로 쓰지 않는다.</p>
''' + example('pagination') + '''<p>추가 검증 때는 3·3·3·1건을 읽어 다음 결과를 얻었다. 이 수치는 현재도 10편이어야 한다는 조건이 아니다. 글 수가 바뀌면 헤더에 맞는 새 수가 나와야 한다.</p>
<pre><code class="language-text">page=1 rows=3 total=10 pages=4
page=2 rows=3 total=10 pages=4
page=3 rows=3 total=10 pages=4
page=4 rows=1 total=10 pages=4
{"passed": true, "unique_ids": 10, "pages_requested": 4}
</code></pre>
<p>전체 종료 코드 0과 <code>passed: true</code>가 이 검사의 성공이다. 오류가 나면 출력을 성공으로 바꾸거나 전체 실행을 무작정 반복하지 말고 HTTP 접근, 응답 헤더, 동시에 진행된 발행부터 확인한다. 0건과 마지막 페이지가 정확히 꽉 찬 경우도 별도 대조 입력으로 확인했다. 총수가 같은 채 글이 교체되는 모든 동시 변경까지 감지하는 snapshot은 아니므로, 중요한 감사에서는 쓰기를 멈춘 시점의 백업과 대조해야 한다. 초안·비공개 글·첨부파일 수는 이 공개 검사에 포함되지 않는다.</p>
''',
301: '''<h2>공개 페이지에서 요약 제목과 자동 상자를 직접 센다</h2>
<p>2026년 9월 16일 독자가 현재 응답을 직접 확인할 수 있도록 다음 읽기 전용 예제를 추가했다. Python 3.11 이상이 있는 터미널에 블록 전체를 붙여 넣는다. 패키지 설치·인증·파일 저장은 없고 공개 HTTPS GET 한 번만 보낸다. 페이지의 문자 전체를 검색하면 이 글에 실린 코드 예시까지 중복으로 셀 수 있으므로 <a href="https://docs.python.org/3/library/html.parser.html">Python HTMLParser</a>로 실제 H2 태그를 읽는다.</p>
<p>코드와 스크립트 등의 내용은 세지 않고 H2 안의 인라인 강조 태그는 합쳐서 판단한다. 자동 상자는 클래스 토큰을 정확히 비교한다. 예제는 이 페이지처럼 작성 요약 H2가 하나이고 자동 상자는 없어야 하는 경우의 기준이다. 작성 요약을 쓰지 않는 다른 글에는 같은 기대 개수를 강제하지 않는다.</p>
''' + example('summary') + '''<p>추가 확인에서 전체 종료 코드 0과 아래 응답을 얻었다.</p>
<pre><code class="language-text">{"passed": true, "summary_h2": 1, "automatic_boxes": 0}
</code></pre>
<p>H2가 두 개이거나 자동 상자가 있으면 종료 코드 1이다. 먼저 원문에 요약을 두 번 썼는지 확인하고, 원문이 하나라면 활성 플러그인·테마와 캐시를 점검한다. 이 명령은 원인을 자동 확정하거나 수정하지 않는다. 받아온 HTML만 분석하므로 자바스크립트가 나중에 만든 요소·CSS로 숨긴 제목·fallback 문구 내용까지 검사하지 않으며 PHP 정규식 실행 테스트도 아니다. 응답이 로그인 페이지나 다른 내용으로 바뀌어도 기대 H2가 없어 실패한다. 리다이렉트나 HTTP 오류는 별도로 중단하니 이를 중복 검사의 정상 결과로 간주하지 않는다.</p>
'''
}
rows=[]
for post_id in (132, 301, 749):
    post=client.get_post(post_id)
    assert post['id']==post_id and post['status']=='publish'
    before=post['content']['raw']; after=before
    if post_id in sections:
        marker='<h2>재현 체크리스트</h2>' if post_id==132 else '<h2>운영 결정과 아직 남은 문제</h2>'
        assert before.count(marker)==1
        after=before.replace(marker,sections[post_id]+marker,1)
    else:
        old='그래서 <strong>WordPress DB 복원 뒤 첨부파일 누락을 찾는 검사 만들기</strong>가 별도 작업이 됐다.'
        assert before.count(old)==1
        after=before.replace(old,'DB 복원 확인과 별개로 원본 첨부파일의 누락을 찾는 검사가 필요했다.',1)
        duplicate='<p>정상 판정은 명령 블록 전체의 종료 코드가 0이면서 다음 결과가 그대로 나오는 경우다.</p>\n<pre><code class="language-text">snapshot_exit=0 missing_exit=1 matching_exit=0\n</code></pre>'
        assert after.count(duplicate)==1
        after=after.replace(duplicate,'<p>정상 판정은 블록 전체 종료 코드 0과 위에 나온 단계별 종료 코드 0·1·0을 함께 확인하는 것이다.</p>',1)
    for kind,body in [('before',before),('after',after)]:
        (HERE/f'post-{post_id}.{kind}.html').write_text(body)
    rows.append({'post_id':post_id,'slug':post['slug'],'title':post['title']['raw'],'url':post['link'],
                 'before_file':f'post-{post_id}.before.html','after_file':f'post-{post_id}.after.html',
                 'before_sha256':sha(before),'after_sha256':sha(after),
                 'reasons':['Add independently executed standalone read-only reader example; preserve historical evidence and metadata.'] if post_id!=749 else ['Remove verbatim title repetition in opening and one duplicate expected-output block; preserve commands and evidence.']})
manifest={'source':'fresh authenticated WordPress GET content.raw','captured_at':datetime.now(UTC).isoformat(),'wordpress_writes':0,'posts':rows}
(HERE/'content-corrections.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'proposed','posts':3,'wordpress_writes':0,'manifest_sha256':sha((HERE/'content-corrections.json').read_text())}))
