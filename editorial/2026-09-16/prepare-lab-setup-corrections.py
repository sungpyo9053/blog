"""Read current authenticated article bodies and propose stdlib-only setup."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


def main():
    folder = Path(__file__).resolve().parent
    approved = json.loads((folder / "content-corrections.json").read_text())
    previous = {p["post_id"]: p for p in approved["posts"]}
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"), max_retries=0)
    manifest = {"source": "fresh authenticated WordPress GET content.raw", "captured_at": datetime.now(UTC).isoformat(), "wordpress_writes": 0, "posts": []}
    prose = {
        698: "이 HTML/JSON 비교는 Python 표준 라이브러리만 사용한다. Python 3.11 이상을 준비하되 운영 발행기용 requirements는 설치하지 않는다. 9월 16일 Python 3.12.9의 새 가상환경에 pip와 외부 패키지 없이 실행해 실패·성공 대조 및 진단 테스트가 통과했다. 기존 저장소가 있다면 clone은 생략하고 프로젝트 루트에서 실행한다.",
        699: "sitemap 충돌 재현에는 별도 패키지가 필요 없다. Python 3.11 이상이면 XML·JSON을 읽는 표준 라이브러리로 실행할 수 있다. 2026년 9월 16일에는 pip 없는 새 3.12.9 가상환경에서 두 fixture와 진단 테스트를 확인했다. 이미 내려받은 저장소는 다시 복제하지 말고 해당 폴더에서 시작한다.",
    }
    setup_code = '<pre><code class="language-bash">git clone https://github.com/sungpyo9053/blog.git\ncd blog\npython3 --version\n# 3.11 미만이면 중단하고 Python 3.12 설치 후 python3.12로 생성\n# 아래는 새 작업 폴더 기준이며 기존 가상환경을 덮어쓰지 않는다.\npython3 -m venv --without-pip .venv\n.venv/bin/python --version\n</code></pre>'
    for ident in (698, 699):
        post = client.request("GET", f"posts/{ident}?context=edit", expected=(200,))
        before = post["content"]["raw"]
        before_sha = hashlib.sha256(before.encode()).hexdigest()
        assert before_sha == previous[ident]["after_sha256"], "current article differs from approved five-post update"
        blocks = re.findall(r'<aside class="huntlab-reader-setup">.*?</aside>', before, re.S)
        assert len(blocks) == 1
        after = before.replace(blocks[0], '<aside class="huntlab-reader-setup"><p>' + prose[ident] + '</p>' + setup_code + '</aside>', 1)
        assert 'requirements-publisher.txt' not in after
        row = {"post_id": ident, "slug": post["slug"], "title": post["title"]["rendered"], "url": post["link"], "before_file": f"post-{ident}.stdlib.before.html", "after_file": f"post-{ident}.stdlib.after.html", "before_sha256": before_sha, "after_sha256": hashlib.sha256(after.encode()).hexdigest(), "reasons": ["Replace unnecessary full production requirements with verified Python-stdlib-only setup; preserve existing evidence and IDs."]}
        for kind, body in (("before", before), ("after", after)):
            with (folder / row[kind + "_file"]).open("x", encoding="utf-8") as f:
                f.write(body)
        manifest["posts"].append(row)
    with (folder / "content-stdlib-corrections.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"proposals": 2, "fresh_authenticated_gets": 2, "wordpress_writes": 0}))


if __name__ == "__main__":
    main()
