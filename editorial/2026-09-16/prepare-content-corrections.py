"""Build corrections from authenticated GET snapshots; never writes to WordPress."""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX_SHA = "deff84730558152c9290a9ef36af325adaf002dd"
API = "https://huntlab.app/wp-json/wp/v2/posts?include=50,290,373,698,699&per_page=100&_fields=id,title,slug,link,content"

PREP_CODE = """<pre><code class="language-bash">git clone https://github.com/sungpyo9053/blog.git
cd blog
python3 --version
# 3.11 미만이면 여기서 중단하고 Python 3.12 설치 후 python3.12로 생성
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-publisher.txt
.venv/bin/python --version
</code></pre>"""
PREP_TEXT = {
    50: "날짜 파서 테스트에는 Python 3.11 이상이 필요하다. 아래 준비는 새 작업 폴더 기준이며, 기존 저장소와 가상환경이 있다면 버전만 확인한다. 2026년 9월 16일에는 3.12.9로 세 테스트를 다시 통과했다. 과거 장애 출력은 다음 절에서 별도로 읽는다.",
    290: "Fake Client 대조군을 직접 돌리려면 프로젝트 루트와 Python 3.11 이상의 가상환경을 준비한다. 이미 설치했다면 복제·생성은 생략한다. 이번 재확인은 3.12.9에서 성공/실패 두 테스트를 실행했으며, 아래 과거 로그의 실행시간을 새 측정값으로 바꾸지는 않았다.",
    373: "누락 예제의 import에는 Python 3.11 이상이 필요하다. 시스템 python3 대신 준비한 .venv/bin/python을 사용해야 한다. 새 저장소는 아래처럼 준비하고, 기존 환경에서는 버전부터 확인한다. 9월 16일 재현은 3.12.9였고 8월의 서버 환경 기록과 구분한다.",
    698: "HTML 200과 JSON 201 fixture는 Python 3.11 이상에서 비교한다. 저장소가 없다면 아래처럼 새 폴더에 준비하고, 설치한 독자는 기존 .venv의 버전을 확인한다. 9월 16일 로컬 3.12.9 재실행도 외부 WordPress 요청 없이 실패 1·성공 0 종료 코드를 냈다.",
    699: "두 sitemap 파일을 대조하기 전에 Python 3.11 이상과 저장소 의존성을 준비한다. 기존 작업 폴더가 있으면 clone과 venv 생성을 반복하지 않는다. 2026년 9월 16일 3.12.9에서 같은 입력의 충돌→통과를 재확인했으며 실제 검색엔진 색인 측정은 아니다.",
}


def replace_once(body: str, old: str, new: str) -> str:
    if body.count(old) != 1:
        raise ValueError(f"expected exactly one target: {old[:90]}")
    return body.replace(old, new, 1)


def main() -> None:
    snapshot_dir = ROOT.parents[1] / "output/editorial-corrections-20260916"
    posts = [json.loads((snapshot_dir / f"post-{ident}.raw.json").read_text()) for ident in (50, 290, 373, 698, 699)]
    assert {p["id"] for p in posts} == {50, 290, 373, 698, 699}
    manifest = {"captured_at": datetime.now(UTC).isoformat(), "source": "authenticated WordPress GET content.raw snapshot", "wordpress_writes": 0, "publisher_note": "Compare current authenticated raw SHA with before_sha256 immediately before applying. Only content update; preserve ID/title/slug.", "posts": []}
    for p in posts:
        before = p["content"]["raw"]
        after = before
        # Put setup before any executable example, not after a reader has failed.
        prep = '<aside class="huntlab-reader-setup"><p>' + PREP_TEXT[p["id"]] + '</p>' + PREP_CODE + '</aside>'
        first_heading = re.search(r"<h2\b", after)
        pos = first_heading.start() if first_heading else after.index("<pre")
        after = after[:pos] + prep + "\n" + after[pos:]
        reasons = ["Declare Python 3.11+ and verified 3.12.9 before the first example; explicit virtualenv interpreter."]
        if p["id"] == 50:
            old = "git clone https://github.com/sungpyo9053/blog.git\ncd blog\npython3 -m venv .venv\n.venv/bin/pip install -r requirements-publisher.txt\n.venv/bin/python -m unittest tests.test_wordpress_retry -v"
            after = replace_once(after, old, ".venv/bin/python -m unittest tests.test_wordpress_retry -v")
        elif p["id"] == 290:
            old = "python3 -m venv .venv\n.venv/bin/pip install -r requirements-publisher.txt\n.venv/bin/python -m unittest"
            after = replace_once(after, old, ".venv/bin/python -m unittest")
        elif p["id"] == 373:
            # Keep the historical full block in the immutable before artifact;
            # show one current runnable block and distinguish historical captures.
            block = next(b for b in re.findall(r"<pre[^>]*>.*?</pre>", before, re.S) if "def enforce_topics_contract" in b)
            plain = html.unescape(re.sub(r"<[^>]+>", "", block))
            code = plain.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
            after = replace_once(after, "아래 환경·출력은 2026년 8월 14일의 기록이며 실행 환경에 따라 달라진다.", "최초 검증 환경은 2026년 8월 14일의 기록이고, 아래 실행 명령과 출력은 2026년 9월 16일 로컬 재확인 기준이다.")
            current = '<p><strong>2026년 9월 16일 실행 안내:</strong> 아래 명령은 시스템 Python 대신 가상환경 3.12.9에서 같은 누락 분기를 재현하도록 고쳤다. 과거 환경은 Linux 7.0.0-1009-aws·Python 3.12.3이며, 기존 캡처는 그 당시 기록이다. 아래 출력은 이번 로컬 재실행에서도 동일했고 마지막 단언의 종료 코드는 0이었다.</p>\n<pre><code class="language-bash">' + html.escape(".venv/bin/python - <<'PY'\n" + code + "\nPY\n") + "</code></pre>\n<pre><code>missing_twice: status=FAIL calls=2 artifact=False error=missing after retry\ncreated_on_retry: status=PASS calls=2 artifact=True retry_prompt=True\nbounded_contract: status=PASS max_calls=2 third_call=False exit_contract=PipelineError\n</code></pre>"
            current = current.replace("<pre><code>missing_twice", '<pre><code class="language-text">missing_twice')
            after = replace_once(after, block, current)
            reasons.append("Keep historical environment/capture labels; replace displayed console with one copyable current venv command and verified output.")
        elif p["id"] in (698, 699):
            setup_paragraph = next(x for x in re.findall(r"<p>.*?</p>", before, re.S) if "python3 -m venv .venv" in x)
            after = replace_once(after, setup_paragraph, "<p>앞의 실행 준비를 마친 프로젝트 루트에서 다음 명령을 실행한다. 결과 파일 덮어쓰기를 막는 실행기이므로 매번 새 임시 디렉터리를 만들고, 출력된 경로에서 전후 결과와 회귀 테스트를 확인한다.</p>")
            candidate = "rest-html-200-response" if p["id"] == 698 else "noindex-sitemap-consistency"
            old = f".venv/bin/python scripts/run_evidence_lab.py {candidate} \\\n  --output /tmp/{candidate}.json"
            new = f'huntlab_result_dir=$(mktemp -d)\n.venv/bin/python scripts/run_evidence_lab.py {candidate} \\\n  --output "$huntlab_result_dir/result.json"\nprintf \'결과 파일: %s/result.json\\n\' "$huntlab_result_dir"'
            after = replace_once(after, old, html.escape(new, quote=False))
            reasons.append("Use a fresh mktemp directory for each run without deleting existing evidence.")
            if p["id"] == 698:
                old = next(x for x in re.findall(r"<p>.*?</p>", before, re.S) if x.startswith("<p>전체 구현과 fixture는"))
                historical = old.replace("전체 구현과 fixture는", "당시 실험의 구현과 fixture는")
                correction = f'<p><strong>2026년 9월 16일 실행 안내 보정:</strong> 역사 구현은 정수 여부만 검사해 <code>true</code>, <code>0</code>, <code>-1</code> ID를 통과시킬 수 있다. 현재 적용할 코드는 <a href="https://github.com/sungpyo9053/blog/blob/{FIX_SHA}/scripts/huntlab_wp_diagnostics.py">양의 정수 검사를 보강한 전체 진단기</a>와 <a href="https://github.com/sungpyo9053/blog/blob/{FIX_SHA}/tests/test_huntlab_wp_diagnostics.py">잘못된 ID 회귀 테스트</a>다. 불리언을 제외한 실제 정수형인지 확인하고 0보다 커야 통과시킨다. 위 양의 정수 조건은 이 수정 후 구현을 뜻한다. 같은 세 ID는 당시 코드에서 모두 통과했지만 수정 후 코드에서는 모두 거절됐다. 최초 실험의 테스트 4개와 달리 현재 진단 테스트는 이 ID 검사를 포함해 5개이며, 이번 로컬 재실행에서 모두 통과했다.</p>'
                after = replace_once(after, old, historical + "\n" + correction)
                reasons.append("Separate historical pinned code from corrected positive-integer contract and fixed links.")
        before_name = f"post-{p['id']}.before.html"
        after_name = f"post-{p['id']}.after.html"
        for name, body in ((before_name, before), (after_name, after)):
            target = ROOT / name
            with target.open("w", encoding="utf-8") as f:
                f.write(body)
        manifest["posts"].append({"post_id": p["id"], "slug": p["slug"], "title": p["title"]["rendered"], "url": p["link"], "before_file": before_name, "after_file": after_name, "before_sha256": hashlib.sha256(before.encode()).hexdigest(), "after_sha256": hashlib.sha256(after.encode()).hexdigest(), "reasons": reasons})
    with (ROOT / "content-corrections.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"proposed_updates": len(posts), "wordpress_writes": 0}))


if __name__ == "__main__":
    main()
