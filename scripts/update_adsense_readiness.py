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
<p><strong>최종 수정일: 2026년 9월 2일</strong></p>
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
<p><strong>Hunt News는 AI와 개발 기술의 변경점을 실제 적용 판단으로 바꾸는 기술 해설 매체입니다.</strong></p>
<p>발표를 다시 요약하는 대신 공식 원문과 독립 자료를 대조하고, 기존 방식과의 차이·적용 환경·실패 조건을 한 글 안에서 설명합니다.</p>
<h2>공개하는 콘텐츠</h2>
<ul>
<li><strong>기술 해설:</strong> 검색 수요가 확인된 문제를 설정, 코드, 비교표나 판단 체크리스트와 함께 주 2회 설명합니다.</li>
<li><strong>주간 기술 회고:</strong> 한 주 동안 반복된 변화와 판단이 실제로 어떻게 달라졌는지를 주 1회 정리합니다.</li>
<li><strong>날짜별 브리핑:</strong> 매일 수집한 기술 신호와 근거 원문을 한 장의 보고서로 보관합니다. 브리핑을 여러 개의 검색용 글로 쪼개지 않습니다.</li>
</ul>
<h2>해설 한 편의 기준</h2>
<ol>
<li>공식 원문에서 실제 변경점과 대상 버전을 확인합니다.</li>
<li>기존 방식·제품·판단과 비교해 무엇이 달라졌는지 밝힙니다.</li>
<li>누구에게, 어떤 환경에서 적용되는지 범위를 제한합니다.</li>
<li>반례, 실패 조건과 롤백 시점을 함께 남깁니다.</li>
</ol>
<h2>직접 검증과 원문 종합의 구분</h2>
<p>직접 실행한 경우에는 검증 환경과 결과를 밝힙니다. 직접 실행하지 못한 주제는 공식 문서와 독립 자료를 종합한 편집 판단이라고 표시하며, 사용 후기나 실험 결과처럼 표현하지 않습니다.</p>
<h2>AI 활용</h2>
<p>AI는 후보 분류, 자료 정리와 초안 작성을 보조합니다. 공개 글의 주제 선택, 출처 대조, 적용 범위와 정정 책임은 <strong>Hunt News 편집팀</strong>에 있습니다. 자세한 기준은 <a href="https://huntlab.app/editorial-policy/">편집 및 AI 활용 원칙</a>에서 확인할 수 있습니다.</p>
<h2>운영과 정정</h2>
<p>HuntLab이 사이트를 운영합니다. 오류, 오래된 버전, 깨진 링크나 적용 조건 누락은 <a href="https://huntlab.app/contact/">문의 페이지</a>로 알려 주세요. 공식 원문을 다시 대조해 수정 여부를 검토합니다.</p>
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
<li>기술 뉴스 RSS·Atom, Google Trends와 Search Console은 후보 발견·검색 의도 신호일 뿐 사실 근거로 사용하지 않습니다.</li>
<li>직접 확인하지 못한 경험, 테스트, 숫자와 성과를 확인한 것처럼 표현하지 않습니다.</li>
</ul>
<h2>AI 활용과 사람의 책임</h2>
<p>AI는 후보 구조화, 조사 정리와 초안 작성을 보조할 수 있습니다. 공개 작성자인 Hunt News 편집팀은 출처 대조, 기존 글 중복, 표현의 오해 가능성, 이미지와 발행 계약을 검수하며 승인된 원고만 공개합니다. AI의 점수나 표현만으로 발행을 결정하지 않습니다.</p>
<h2>발행 빈도와 고유 가치</h2>
<p>일일 자동 수집 결과는 날짜별 브리핑 한 곳에 보관합니다. 이를 여러 개의 독립 검색 글로 나누지 않습니다. 독립 해설은 관측된 독자 수요, 복수 근거, 재사용 가능한 예제나 판단 도구, 실패 조건을 모두 갖춘 경우에만 발행합니다.</p>
<h2>반복·중복 방지</h2>
<p>최근 글과 첫 문단의 출발점, H2 진행 논리와 마지막 판단이 함께 반복되는지 검사합니다. 같은 검색 의도의 기존 글이 있으면 새 글을 늘리기보다 보강·통합·후속 관점 분리를 우선합니다. 고유 근거나 독자가 얻는 새 판단이 없으면 발행을 보류합니다.</p>
<h2>업데이트와 정정</h2>
<p>공식 문서 변경, 링크 오류, 검색 의도 변화나 사실 오류가 확인되면 변경 범위와 근거를 검토해 수정합니다. 오류·정정 제보와 개인정보 요청은 <a href="https://huntlab.app/contact/">문의 페이지</a>에서 받습니다.</p>
<h2>광고와 이해관계</h2>
<p>광고나 제휴 관계가 콘텐츠 판단에 영향을 줄 수 있으면 독자가 알아볼 수 있도록 표시합니다. 광고 여부와 기사 선정·사실 판단은 분리합니다. 개인정보와 광고 데이터 처리는 <a href="https://huntlab.app/privacy-policy/">개인정보처리방침</a>에서 설명합니다.</p>
""".strip()


PUBLIC_PAGE_SPECS = {
    "privacy-policy": {"title": "개인정보처리방침", "content": PRIVACY_HTML},
    "about": {"title": "Hunt News 이용 가이드", "content": ABOUT_HTML},
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


def apply_plan(
    client: WordPressClient,
    pages: list[dict[str, Any]],
    *,
    selected_slugs: set[str] | None = None,
) -> list[dict[str, Any]]:
    by_slug = {str(page.get("slug", "")): page for page in pages}
    applied: list[dict[str, Any]] = []
    for slug, spec in PUBLIC_PAGE_SPECS.items():
        if selected_slugs is not None and slug not in selected_slugs:
            continue
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


def sync_about_menu_label(client: WordPressClient) -> list[dict[str, Any]]:
    """Keep every public menu link to /about/ aligned with the page title."""
    items = client.request(
        "GET", "menu-items?context=edit&per_page=100", expected=(200,)
    )
    updated: list[dict[str, Any]] = []
    target_title = PUBLIC_PAGE_SPECS["about"]["title"]
    for item in items:
        url = str(item.get("url", "")).rstrip("/")
        if not url.endswith("/about"):
            continue
        current_title = str(item.get("title", {}).get("raw", ""))
        if current_title != target_title:
            client.request(
                "POST",
                f"menu-items/{item['id']}",
                payload={"title": target_title},
                expected=(200,),
            )
        verified = client.request(
            "GET", f"menu-items/{item['id']}?context=edit", expected=(200,)
        )
        if str(verified.get("title", {}).get("raw", "")) != target_title:
            raise RuntimeError("about menu label verification failed")
        updated.append(
            {
                "menu_item_id": int(item["id"]),
                "title": target_title,
                "url": verified.get("url", item.get("url")),
            }
        )
    if not updated:
        raise RuntimeError("about menu item was not found")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Hunt News AdSense trust pages")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--backup-dir", type=Path, default=ROOT / "output" / "backups" / "adsense-readiness"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument(
        "--slug",
        action="append",
        choices=tuple(PUBLIC_PAGE_SPECS),
        help="Limit planning and application to one page; may be repeated.",
    )
    args = parser.parse_args()
    if args.apply and not args.yes:
        parser.error("--apply requires --yes")

    client = WordPressClient(WordPressConfig.from_environment(args.env_file))
    pages = fetch_pages(client)
    selected_slugs = set(args.slug) if args.slug else None
    plan = [
        row
        for row in build_plan(pages)
        if selected_slugs is None or row["slug"] in selected_slugs
    ]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = args.backup_dir / f"public-pages-{timestamp}.json"
    write_backup(backup_path, pages, plan)
    result: dict[str, Any] = {
        "mode": "apply" if args.apply else "plan",
        "backup_path": str(backup_path),
        "plan": plan,
    }
    if args.apply:
        result["applied"] = apply_plan(
            client, pages, selected_slugs=selected_slugs
        )
        if selected_slugs is None or "about" in selected_slugs:
            result["menu_applied"] = sync_about_menu_label(client)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
