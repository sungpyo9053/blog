#!/usr/bin/env python3
"""Update public trust and privacy pages for AdSense readiness.

The command is plan-only by default. ``--apply --yes`` is required before it
changes WordPress, and every apply stores the previous page state locally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


PRIVACY_HTML = """
<p><strong>최종 수정일: 2026년 8월 22일</strong></p>
<p>HuntLab은 Hunt News(<a href="https://huntlab.app/">huntlab.app</a>)를 운영하며, 사이트 제공·보안·이용 현황 확인과 문의 처리를 위해 필요한 범위에서 정보를 처리합니다.</p>
<h2>처리될 수 있는 정보</h2>
<ul>
<li>사이트 접속 시 생성되는 IP 주소, 브라우저·기기 정보, 접속 시각, 방문 페이지와 같은 기술 정보</li>
<li>쿠키, 웹 비콘 또는 유사 기술을 통해 생성되는 광고·방문·페이지 이용 정보</li>
<li>댓글이나 문의 기능을 직접 이용할 때 사용자가 입력한 이름, 이메일 주소와 문의 내용</li>
</ul>
<h2>이용 목적</h2>
<p>수집된 정보는 사이트 보안과 오류 분석, 이용 현황 측정, 콘텐츠 개선, 문의·정정 요청 처리, 광고 제공 및 부정 사용 방지를 위해 사용될 수 있습니다. 법적 의무가 있거나 사용자가 동의한 경우를 제외하고 개인정보를 판매하지 않습니다.</p>
<h2>Google AdSense와 제3자 광고</h2>
<p>이 사이트는 Google AdSense를 사용할 수 있습니다. Google을 포함한 제3자 광고 제공업체는 광고 제공·측정·개인 최적화·빈도 제한·부정행위 방지를 위해 사용자의 브라우저에 쿠키를 저장하거나 기존 쿠키를 읽을 수 있으며, 웹 비콘·IP 주소 또는 기타 식별자를 사용할 수 있습니다.</p>
<p>Google이 파트너 사이트에서 수집한 정보를 사용하는 방식은 <a href="https://policies.google.com/technologies/partner-sites?hl=ko" rel="noopener noreferrer">Google 파트너의 사이트 또는 앱을 사용할 때 Google에서 데이터를 사용하는 방식</a>에서 확인할 수 있습니다. 사용자는 <a href="https://adssettings.google.com/" rel="noopener noreferrer">Google 광고 설정</a>에서 개인 맞춤 광고 설정을 관리할 수 있습니다.</p>
<h2>방문 분석과 외부 서비스</h2>
<p>사이트는 WordPress, Jetpack, Google Analytics 및 관련 도구를 사용할 수 있습니다. 서비스가 활성화된 경우 쿠키와 이용 정보는 각 제공자의 개인정보처리방침과 설정에 따라 처리될 수 있습니다. HuntLab은 필요한 설정 범위에서 접근 권한과 보관 기간을 제한합니다.</p>
<h2>보관·삭제와 이용자 선택</h2>
<p>기술 로그와 문의 정보는 운영·보안·문의 처리에 필요한 기간 동안 보관한 뒤 삭제합니다. 외부 서비스가 처리하는 정보의 보관 기간은 해당 제공자의 정책과 사이트 설정을 따릅니다. 사용자는 브라우저 설정에서 쿠키를 차단하거나 삭제할 수 있으나 일부 기능이나 광고 설정이 다르게 작동할 수 있습니다.</p>
<h2>문의</h2>
<p>개인정보 관련 문의와 삭제 요청은 <a href="https://huntlab.app/contact/">문의 페이지</a>의 공개 연락 채널을 이용해 주세요. 공개 채널에는 비밀번호, API 키, 주민등록번호 등 민감정보를 작성하지 마세요.</p>
""".strip()


ABOUT_HTML = """
<p><strong>Hunt News는 복잡한 변화가 내 생활에 어떤 영향을 주는지 쉽게 설명합니다.</strong></p>
<p>정책, 경제, 부동산, 사회, 정치, 문화·엔터와 IT의 변화를 발표 제목으로 끝내지 않습니다. 무엇이 바뀌었는지, 누구에게 언제부터 적용되는지, 내 돈·시간·일·권리·소비·선택에는 무엇이 달라지는지, 지금 무엇을 확인해야 하는지까지 이어서 설명합니다.</p>
<h2>운영과 편집 책임</h2>
<p>HuntLab이 사이트를 운영하고 공개 작성자명인 <strong>Hunt News 편집팀</strong>이 주제 선정, 근거 확인, 원고 검수와 정정 판단을 담당합니다. 공식 문서와 실제 관측 범위를 넘어선 경험·숫자·성과를 만들지 않으며, 오류 제보는 <a href="https://huntlab.app/contact/">문의 페이지</a>에서 받습니다.</p>
<h2>주제는 어떻게 고르나</h2>
<ol>
<li>매시간 누적한 Google Trends 한국 RSS에서 급상승 검색어, 대략적인 검색량, 발생 시각과 관련 기사를 후보 발견 신호로 확인합니다.</li>
<li>정부·공공기관·법령·공시·기업 공식 발표 같은 1차 자료를 우선 확인하고, 공식 원문이 없으면 서로 독립적인 출처를 교차 검토합니다.</li>
<li>Search Console에서 Hunt News에 실제 노출된 검색 의도와 직접 연결되면 제한적으로 가산합니다.</li>
<li>Whereispost는 수집 시각과 상태가 확인된 과거 캐시만 장기 수요 참고값으로 사용합니다. 최신 수집이 잠기거나 실패한 값은 새 관측처럼 취급하지 않습니다.</li>
<li>생활 영향, 지금 할 수 있는 행동, 기존 글과의 중복, 근거의 충분성을 함께 검토해 최종 주제를 정합니다.</li>
</ol>
<p>현재 실제 발행 주제는 기존 Topic Planner가 결정합니다. 별도의 News Worthiness Scorer는 동일 후보를 Shadow Mode로 평가해 비교 기록만 남기며, 검증 기간에는 발행 주제를 바꾸지 않습니다.</p>
<h2>글은 어떻게 확인하나</h2>
<ul>
<li>Research가 출처, 확인 시각, 확정·미확정 정보와 한계를 기록합니다.</li>
<li>Writer는 확인된 범위에서 독자의 대상·금액·시점·선택을 설명합니다.</li>
<li>Reviewer가 사실성, 고유 가치, 출처 연결, 반복성, 이미지와 발행 계약을 승인한 글만 공개합니다.</li>
<li>Publisher가 승인된 원고 해시와 공개 상태를 확인하고, 발행 후 URL과 미디어를 다시 검증합니다.</li>
</ul>
<h2>AI는 어디까지 사용하나</h2>
<p>AI는 후보 구조화, 조사 정리와 초안 작성을 보조합니다. AI의 표현이나 점수를 사실로 간주하지 않으며, 검색 수요는 관측값으로 분리하고 최종 점수 계산과 발행 조건은 재현 가능한 규칙으로 처리합니다. 자세한 기준은 <a href="https://huntlab.app/editorial-policy/">편집 및 AI 활용 원칙</a>에서 공개합니다.</p>
<h2>기존 기술 글</h2>
<p>HuntLab에서 발행한 기존 기술 글은 IT 카테고리에 보존합니다. 기술 이름을 나열하기보다 일반 사용자가 겪는 변화와 선택을 먼저 설명하고, 필요한 독자에게 작동 원리와 시스템 설계를 연결합니다.</p>
""".strip()


CONTACT_HTML = """
<p>HuntLab이 사이트를 운영하고 <strong>Hunt News 편집팀</strong>이 공개된 글의 편집·검수·정정 요청을 담당합니다. 콘텐츠 오류 제보, 정정 요청, 개인정보 요청, 기술적 피드백과 협업 문의를 받습니다.</p>
<h2>공개 문의 채널</h2>
<p><a href="https://github.com/sungpyo9053/blog/issues" rel="noopener noreferrer">HuntLab GitHub Issues에서 새 문의 작성하기</a></p>
<p>관련 글의 URL, 문제가 되는 문장이나 동작, 확인한 날짜와 참고한 공식 자료를 함께 남겨 주세요. 공개 이슈에는 비밀번호, API 키, 주민등록번호, 개인 연락처 등 민감정보를 작성하지 마세요.</p>
<h2>정정 처리 원칙</h2>
<p>사실 오류, 오래된 제도·가격·일정, 깨진 링크 또는 출처 문제를 제보할 수 있습니다. 편집팀은 제보 내용과 공식 원문을 대조해 본문 수정, 정정 내역 반영 또는 변경하지 않는 이유를 검토합니다. 광고·협찬 여부는 사실 판단과 분리하며, 이해관계가 콘텐츠 판단에 영향을 줄 수 있으면 해당 글에 표시합니다.</p>
<h2>개인정보 요청</h2>
<p>개인정보 열람·삭제 등과 관련된 요청은 제목에 ‘개인정보 요청’이라고 표시해 위 채널로 접수해 주세요. 공개 접수가 곤란한 민감정보는 먼저 최소한의 요청 내용만 남기고 별도 전달 방법을 확인하세요. 자세한 내용은 <a href="https://huntlab.app/privacy-policy/">개인정보처리방침</a>을 확인할 수 있습니다.</p>
""".strip()


EDITORIAL_HTML = """
<p>Hunt News는 검색 노출을 위한 양보다 독자가 실제로 판단하고 행동하는 데 필요한 정확성, 고유 가치와 재현 가능한 근거를 우선합니다.</p>
<h2>출처와 검증</h2>
<ul>
<li>정부·공공기관·법령·공시·당사자 공식 문서와 제품 원문을 우선합니다.</li>
<li>정책·가격·일정처럼 달라질 수 있는 정보는 확인 날짜, 적용 대상, 예외와 미확정 부분을 구분합니다.</li>
<li>Google Trends, Search Console과 시점이 확인된 Whereispost 캐시는 후보 발견·검색 의도 신호일 뿐 사실 근거로 사용하지 않습니다.</li>
<li>직접 확인하지 못한 경험, 테스트, 숫자와 성과를 확인한 것처럼 표현하지 않습니다.</li>
</ul>
<h2>AI 활용과 사람의 책임</h2>
<p>AI는 후보 구조화, 조사 정리와 초안 작성을 보조할 수 있습니다. 공개 작성자인 Hunt News 편집팀은 출처 대조, 기존 글 중복, 표현의 오해 가능성, 이미지와 발행 계약을 검수하며 승인된 원고만 공개합니다. AI의 점수나 표현만으로 발행을 결정하지 않습니다.</p>
<h2>반복·중복 방지</h2>
<p>최근 글과 첫 문단의 출발점, H2 진행 논리와 마지막 판단이 함께 반복되는지 검사합니다. 같은 검색 의도의 기존 글이 있으면 새 글을 늘리기보다 보강·통합·후속 관점 분리를 우선합니다. 고유 근거나 독자가 얻는 새 판단이 없으면 발행을 보류합니다.</p>
<h2>업데이트와 정정</h2>
<p>공식 문서 변경, 링크 오류, 검색 의도 변화나 사실 오류가 확인되면 변경 범위와 근거를 검토해 수정합니다. 오류·정정 제보와 개인정보 요청은 <a href="https://huntlab.app/contact/">문의 페이지</a>에서 받습니다.</p>
<h2>광고와 이해관계</h2>
<p>광고나 제휴 관계가 콘텐츠 판단에 영향을 줄 수 있으면 독자가 알아볼 수 있도록 표시합니다. 광고 여부와 기사 선정·사실 판단은 분리합니다. 개인정보와 광고 데이터 처리는 <a href="https://huntlab.app/privacy-policy/">개인정보처리방침</a>에서 설명합니다.</p>
""".strip()


PUBLIC_PAGE_SPECS = {
    "privacy-policy": {"title": "개인정보처리방침", "content": PRIVACY_HTML},
    "about": {"title": "Hunt News 소개", "content": ABOUT_HTML},
    "contact": {"title": "문의", "content": CONTACT_HTML},
    "editorial-policy": {"title": "편집 및 AI 활용 원칙", "content": EDITORIAL_HTML},
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fetch_pages(client: WordPressClient) -> list[dict[str, Any]]:
    return client.request(
        "GET",
        "pages?" + urlencode({"context": "edit", "per_page": "100", "status": "publish"}),
        expected=(200,),
    )


def build_plan(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_slug = {str(page.get("slug", "")): page for page in pages}
    plan: list[dict[str, Any]] = []
    for slug, spec in PUBLIC_PAGE_SPECS.items():
        page = by_slug.get(slug)
        current_content = str((page or {}).get("content", {}).get("raw", ""))
        current_title = str((page or {}).get("title", {}).get("raw", ""))
        plan.append(
            {
                "slug": slug,
                "page_id": int(page["id"]) if page else None,
                "exists": page is not None,
                "needs_update": page is None
                or current_content != spec["content"]
                or current_title != spec["title"],
                "current_sha256": digest(current_content),
                "target_sha256": digest(spec["content"]),
            }
        )
    return plan


def write_backup(path: Path, pages: list[dict[str, Any]], plan: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "contract_version": "adsense-readiness-pages.v1",
        "plan": plan,
        "pages": [
            {
                "id": page.get("id"),
                "slug": page.get("slug"),
                "status": page.get("status"),
                "modified_gmt": page.get("modified_gmt"),
                "title": page.get("title", {}).get("raw", ""),
                "content": page.get("content", {}).get("raw", ""),
            }
            for page in pages
            if page.get("slug") in PUBLIC_PAGE_SPECS
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_plan(client: WordPressClient, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_slug = {str(page.get("slug", "")): page for page in pages}
    applied: list[dict[str, Any]] = []
    for slug, spec in PUBLIC_PAGE_SPECS.items():
        page = by_slug.get(slug)
        payload = {"title": spec["title"], "content": spec["content"], "status": "publish"}
        if page:
            result = client.request(
                "POST", f"pages/{page['id']}", payload=payload, expected=(200,)
            )
        else:
            result = client.request(
                "POST", "pages", payload={**payload, "slug": slug}, expected=(200, 201)
            )
        verified = client.request(
            "GET", f"pages/{result['id']}?context=edit", expected=(200,)
        )
        if verified.get("slug") != slug or verified.get("status") != "publish":
            raise RuntimeError(f"{slug}: identity or publish status verification failed")
        if verified.get("content", {}).get("raw", "") != spec["content"]:
            raise RuntimeError(f"{slug}: content verification failed")
        applied.append(
            {
                "slug": slug,
                "page_id": int(verified["id"]),
                "sha256": digest(spec["content"]),
                "link": verified.get("link"),
            }
        )
    return applied


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Hunt News AdSense trust pages")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--backup-dir", type=Path, default=ROOT / "output" / "backups" / "adsense-readiness"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.apply and not args.yes:
        parser.error("--apply requires --yes")

    client = WordPressClient(WordPressConfig.from_environment(args.env_file))
    pages = fetch_pages(client)
    plan = build_plan(pages)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = args.backup_dir / f"public-pages-{timestamp}.json"
    write_backup(backup_path, pages, plan)
    result: dict[str, Any] = {
        "mode": "apply" if args.apply else "plan",
        "backup_path": str(backup_path),
        "plan": plan,
    }
    if args.apply:
        result["applied"] = apply_plan(client, pages)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
