"""Prepare body-only proposals from fresh REST GET; never update WordPress."""
import hashlib
import html
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

REV = '170c6ba70c419501171ae741b318a2fb6f4ac38d'
client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'), max_retries=0)
def sha(body):
    return hashlib.sha256(body.encode()).hexdigest()
def replace(body, old, new):
    assert body.count(old) == 1, old[:90]
    return body.replace(old, new, 1)
rows = []
for post_id in (50, 96, 290, 373, 698, 699):
    post = client.get_post(post_id)
    assert post['id'] == post_id and post['status'] == 'publish'
    before = post['content']['raw']
    after = before
    if post_id in (50, 290):
        after = replace(after, 'cd blog\npython3 --version', 'cd blog\ngit switch --detach ' + REV + '\npython3 --version')
        marker = '<pre><code class="language-bash">git clone'
        if marker not in after:
            marker = re.search(r'<pre><code[^>]*>git clone', after).group()
        count = '세' if post_id == 50 else '성공·실패 두'
        note = '<p>Python 3.11 이상이 필요하다. 기존 작업 폴더를 바꾸지 말고 빈 별도 디렉터리에서 아래 준비를 실행한다. <a href="https://github.com/sungpyo9053/blog/commit/' + REV + '">검증한 코드 버전</a>의 새 가상환경(Python 3.12.9)에서 2026년 9월 16일 ' + count + ' 테스트가 통과했다. 아래 과거 로그와 실행시간은 당시 기록으로 남긴다. 다운로드에는 네트워크가 필요하지만 테스트는 WordPress에 접속하지 않는다.</p>'
        old_setup = re.search(r'(<aside class="huntlab-reader-setup">)(<p>.*?</p>)', after, re.S).group(2)
        after = replace(after, old_setup, note)
    if post_id == 96:
        code = "python3 - <<'PY'\n" + (HERE / 'backup-example.py').read_text() + 'PY\n'
        section = '''<h2>백업 JSON에 복원할 원문이 있는지 먼저 검사한다</h2>
<p>아래는 2026년 9월 16일 추가한 독자용 검사입니다. Python 3.11 이상에서 블록 전체를 실행하면 정상 입력과 원문이 빈 실패 입력을 비교합니다. 표준 라이브러리만 쓰며 네트워크 요청이나 파일 쓰기는 없습니다. 운영 백업을 외부 서비스에 올릴 필요도 없습니다.</p>
''' + '<pre><code class="language-bash">' + html.escape(code) + '</code></pre>\n' + '''<p>관측 출력은 <code>valid: passed=true</code>, <code>missing_original: passed=false</code>이고 전체 종료 코드는 0이었습니다. 두 판정을 올바르게 구분해야 대조 시험이 통과합니다. 이 합성 예제는 과거 11건 백업의 재실행 결과가 아닙니다.</p>
<p>실제 파일은 첫 줄만 <code>python3 - "backup.json" &lt;&lt;'PY'</code>로 바꿔 로컬 파일을 읽습니다. 경로는 자신의 백업 파일로 지정하고 나머지 블록은 그대로 둡니다. 전체 종료 0과 <code>{"passed": true}</code>면 이 검사의 항목을 통과했고, 1이면 JSON 형식·필수 원문·ID·타깃·본문 차이부터 확인합니다. 10MB를 넘는 파일은 거부합니다. 실패해도 원문이나 경로를 출력하지 않습니다.</p>
<p>여기서 확인하는 것은 복원용 필드와 변경 계획의 기본 일관성뿐입니다. 이 검사는 원문이 실제 WordPress와 같은지, 타깃이 공개 URL로 열리는지, 백업을 복원할 수 있는지 증명하지 않습니다. 본문이 비어 있는 글을 변경하는 계획도 이 예제에서는 보류합니다. 검사가 통과해도 아래의 URL 확인과 부분 실패 대책을 생략하지 않습니다.</p>
'''
        after = replace(after, '<h2>중복 방지는 URL 검색이 아니라 v1 마커로 한다</h2>', section + '<h2>중복 방지는 URL 검색이 아니라 v1 마커로 한다</h2>')
        after = after.replace('idempotency guard', '재삽입 방지 장치')
    if post_id == 373:
        after, redacted = re.subn(r'\$ nl -ba logs/2026-08-13\.log[^\n]*', '# logs/2026-08-13.log 73834~73842행 발췌 (운영 경로 비식별)', after, count=1)
        assert redacted == 1
        after = replace(after, '<p><img alt="하위 agent의 failed=false 직후 topics.md 누락으로 파이프라인이 실패한 운영 로그" src="https://huntlab.app/wp-content/uploads/2026/08/body-1-33.webp"></p>\n', '')
        paragraphs = re.findall(r'<p>.*?</p>', after, re.S)
        old = next(p for p in paragraphs if p.startswith('<p>공개 저장소를 내려받고'))
        new = '<p>앞의 준비를 마친 프로젝트 루트에서 실행한다. 아래 코드는 세 객체를 import하고 임시 디렉터리에서 파일 누락 분기만 재현한다. 첫 조건은 두 번 모두 파일을 쓰지 않고, 두 번째 조건은 재호출에서만 파일을 쓴다. 임시 파일은 실행 종료와 함께 제거된다. 2026년 9월 16일 Python 3.12.9 재확인에서 아래 출력과 마지막 단언의 종료 코드 0을 얻었다. 기존 캡처는 앞서 밝힌 8월 서버 기록이다.</p>'
        after = replace(after, old, new)
        old = next(p for p in paragraphs if p.startswith('<p><strong>2026년 9월 16일 실행 안내:</strong>'))
        after = replace(after, old, '')
    if post_id == 698:
        old = '<p>처음에는 허용 상태 코드 목록만 더 촘촘하게 만들 생각이었다. 하지만 HTML 로그인 페이지도 200을 쓸 수 있으므로 그 방법은 문제를 해결하지 못한다. 그래서 상태 코드 규칙은 유지하되, 응답 형식과 생성된 대상의 ID를 별도 조건으로 추가했다.</p>'
        after = replace(after, old, '<p>허용 상태 코드 목록만 좁혀서는 HTML 로그인 페이지의 200을 구분할 수 없다. 상태 코드 규칙과 함께 응답 형식과 생성된 대상의 ID를 별도로 확인해야 한다.</p>')
        after = replace(after, '네 개 진단 회귀 테스트를 실행한 결과는 모두 통과였다.', '최초 실험에서는 4개가 통과했다. 아래 재실행 명령은 앞서 연결한 ID 보강 버전에서 5개를 검사하므로, 과거 로그의 테스트 수와 구분한다.')
    if post_id == 699:
        after = replace(after, '<code>noindex, follow</code>를 확인한 뒤 작업이 끝났다고 표시하려다 sitemap fixture를 다시 열었다. 같은 URL이 여전히 검색용 목록에 남아 있었다.', '비교용 HTML에는 <code>noindex, follow</code>가 있지만 sitemap fixture에는 같은 URL이 남아 있었다.')
        after = replace(after, '처음에는 HTML의 robots 메타 검사만 배포 게이트로 두려 했다. 그 방식은 페이지 자체의 지시만 확인하고 sitemap 생성 결과를 놓친다.', 'HTML의 robots 메타만 검사하면 페이지 자체의 지시는 확인하지만 sitemap 생성 결과는 놓친다.')
        after = replace(after, '그래서 두 개의 개별 성공 조건을 버리고 URL 단위 교차 검사 하나로 바꿨다.', '두 결과를 URL 단위로 함께 검사해야 이 모순을 찾을 수 있다.')
    if post_id in (373, 698, 699):
        after = replace(after, 'cd blog\npython3 --version', 'cd blog\ngit switch --detach ' + REV + '\npython3 --version')
        old = {373: '새 저장소는 아래처럼 준비하고, 기존 환경에서는 버전부터 확인한다.',
               698: '기존 저장소가 있다면 clone은 생략하고 프로젝트 루트에서 실행한다.',
               699: '이미 내려받은 저장소는 다시 복제하지 말고 해당 폴더에서 시작한다.'}[post_id]
        after = replace(after, old, '재현용 빈 별도 폴더에서 아래 준비를 시작한다. 기존 작업 폴더는 바꾸지 않는다. checkout하는 고정 revision은 재실행 기준이며 위에서 설명한 최초 변경 시점과 구분한다.')
        after = after.replace('# 기존 .venv가 있다면 생성 명령은 건너뛰고 아래에서 Python 버전만 확인한다.\n', '')
    assert before != after
    for kind, body in (('before', before), ('after', after)):
        (HERE / f'post-{post_id}.{kind}.html').write_text(body)
    rows.append({'post_id': post_id, 'slug': post['slug'], 'title': post['title']['raw'], 'url': post['link'],
                 'before_file': f'post-{post_id}.before.html', 'after_file': f'post-{post_id}.after.html',
                 'before_sha256': sha(before), 'after_sha256': sha(after),
                 'reasons': ['Reader completeness, verified revision, or evidence-preserving concise prose; body only.']})
manifest = {'source': 'fresh authenticated WordPress GET content.raw', 'captured_at': datetime.now(UTC).isoformat(), 'wordpress_writes': 0, 'posts': rows}
(HERE / 'content-corrections.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(sha((HERE / 'content-corrections.json').read_text()))
