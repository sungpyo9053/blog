"""GET current raw posts and prepare narrow reader-facing title proposals."""
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
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"), max_retries=0)
    titles = {
        706: "자동발행은 성공했는데 글이 없다면: 미발행과 실패 구분하기",
        373: "AI 작업이 끝났는데 결과 파일이 없다면: 재시도와 중단 기준",
    }
    intro = '<p>AI 작업이 끝났다는 로그가 있는데 다음 단계에서 필요한 파일을 찾지 못한다면, 실행 완료와 결과 파일 생성을 따로 검사해야 한다. 이 글은 파일이 없을 때 한 번만 재시도하고, 다시 없으면 다음 단계로 넘어가지 않고 중단하는 방법을 다룬다. HuntLab의 글쓰기 준비 단계인 <code>Topic Planner</code>가 넘겨야 할 <code>topics.md</code>를 사례로 삼았다. 파일이 있다는 사실만으로 내용이 올바른 것은 아니므로, 파일 존재 검사와 내용 파싱도 분리한다.</p>'
    manifest = {"source": "fresh authenticated WordPress GET content.raw", "captured_at": datetime.now(UTC).isoformat(), "wordpress_writes": 0, "posts": []}
    for ident in (706, 373):
        post = client.request("GET", f"posts/{ident}?context=edit", expected=(200,))
        before = post["content"]["raw"]
        after = before
        if ident == 373:
            original = re.match(r"<p>.*?</p>", before, re.S)
            assert original and 'scripts/run_daily_pipeline.py' in original.group(0)
            after = intro + before[original.end():]
        row = {"post_id": ident, "slug": post["slug"], "title": post["title"]["rendered"], "new_title": titles[ident], "url": post["link"], "before_file": f"post-{ident}.title.before.html", "after_file": f"post-{ident}.title.after.html", "before_sha256": hashlib.sha256(before.encode()).hexdigest(), "after_sha256": hashlib.sha256(after.encode()).hexdigest(), "reasons": ["Replace internal terminology in title with reader symptom; preserve slug and ID."]}
        if ident == 373:
            row["reasons"].append("Rewrite only opening paragraph to explain missing-file symptom, one retry, stop condition, and Planner terminology; preserve all evidence.")
        else:
            row["reasons"].append("Title-only correction: body is byte-identical to current verified reader-value update.")
        for kind, body in (("before", before), ("after", after)):
            with (folder / row[kind + "_file"]).open("x", encoding="utf-8") as f:
                f.write(body)
        manifest["posts"].append(row)
    with (folder / "content-title-corrections.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"proposals": 2, "fresh_authenticated_gets": 2, "wordpress_writes": 0}))


if __name__ == "__main__":
    main()
