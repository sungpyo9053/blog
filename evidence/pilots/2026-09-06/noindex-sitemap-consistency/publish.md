---
title: noindex 글이 sitemap에 남는 배포 불일치 잡기
slug: wordpress-noindex-sitemap-consistency
category: 기술 해설
tags:
  - WordPress
  - noindex
  - sitemap
  - 배포 검증
publish_mode: publish
run_id: evidence-lab-20260906-indexability
topic_id: noindex-sitemap-consistency
source_id: demand-evidence-lab-v1
meta_description: WordPress 페이지에 noindex를 적용해도 sitemap에 URL이 남을 수 있다. 같은 URL 집합을 비교해 충돌을 실패 처리하는 진단 스크립트와 회귀 테스트를 공개한다.
excerpt: noindex 적용 여부와 sitemap 포함 여부를 따로 확인하면 배포 불일치를 놓칩니다. 두 URL 집합을 하나의 계약으로 비교해 충돌을 실패 처리했습니다.
content_type: verified_case
problem_group: 인덱싱·사이트맵
verification_method: controlled_comparison
evidence_date: '2026-09-06'
evidence_badges:
  - 통제 비교
  - 회귀 테스트
  - 공개 코드
evidence_url: https://github.com/sungpyo9053/blog/tree/601ac6386f7ad20168ef450e47ca6c1a71daea9e/evidence/lab-fixtures
asset_url: https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/huntlab_wp_diagnostics.py
monetization_intent: monitoring
conversion_goal: checklist_use
recommended_cta: GitHub에서 진단 명령 확인하기
affiliate_disclosure: 없음
---

페이지 HTML에 `noindex, follow`가 보인다고 인덱싱 정리가 끝난 것은 아니다. sitemap 생성기가 그 URL을 계속 내보내면 검색엔진에는 서로 다른 신호를 보낸다. HuntLab은 이 상태를 사람 눈으로 두 번 확인하는 대신, 페이지 판정과 sitemap URL을 같은 검사에서 대조하는 fixture를 만들었다.

이번 기록은 운영 장애를 재현한 것이 아니다. 공개 서비스에 영향을 주지 않는 두 개의 sitemap fixture로 배포 전후 계약을 통제 비교했다.

## 비교 대상

페이지 목록에는 두 URL이 있다.

- `/verified-guide/`: indexable이며 canonical이 자기 자신을 가리킨다.
- `/private-report/`: `noindex, follow`이며 검색용 sitemap에 없어야 한다.

변경 전 fixture에는 두 URL이 모두 들어 있고, 변경 후 fixture에서는 `/private-report/`만 빠진다. 페이지의 ID, URL과 canonical은 바꾸지 않았다.

## 변경 전: 두 개의 개별 검사는 통과처럼 보인다

`noindex` 메타만 찾으면 `/private-report/`는 올바르게 설정된 것처럼 보인다. sitemap XML만 파싱해도 문법 오류는 없다. 문제는 둘을 합쳤을 때 드러난다.

```bash
.venv/bin/python scripts/huntlab_wp_diagnostics.py indexability \
  --pages evidence/lab-fixtures/indexability-pages.json \
  --sitemap evidence/lab-fixtures/sitemap-before.xml
```

실행 결과는 종료 코드 1이다.

```text
passed=false
reason=indexability_conflict
checked_pages=2
sitemap_urls=2
conflict=https://example.test/private-report/
conflict_reason=noindex_url_in_sitemap
```

이렇게 해야 CI나 Publisher가 모순을 경고만 남기고 성공 처리하지 않는다.

## 수정은 문서가 아니라 sitemap 집합에 적용했다

해결 후 fixture는 indexable URL 하나만 포함한다. 같은 페이지 판정 파일과 같은 명령을 사용했다.

```bash
.venv/bin/python scripts/huntlab_wp_diagnostics.py indexability \
  --pages evidence/lab-fixtures/indexability-pages.json \
  --sitemap evidence/lab-fixtures/sitemap-after.xml
```

```text
passed=true
reason=consistent
checked_pages=2
sitemap_urls=1
conflicts=[]
```

수정 전에는 충돌 1건, 수정 후에는 0건이다. 네트워크 쓰기와 WordPress 쓰기는 모두 0회였다. 테스트한 입력과 실행기는 [고정 커밋](https://github.com/sungpyo9053/blog/tree/601ac6386f7ad20168ef450e47ca6c1a71daea9e/evidence/lab-fixtures)에 남겼다.

## 진단기가 확인하는 두 방향

검사는 noindex URL의 sitemap 포함만 찾지 않는다. indexable 페이지라면 canonical이 자기 URL인지도 확인한다. 외부 URL이나 다른 내부 URL을 canonical로 가리키면서 sitemap에 포함된 경우 역시 일관된 검색 대상이라고 단정할 수 없기 때문이다.

```python
if page["noindex"] and url in sitemap_urls:
    conflicts.append((url, "noindex_url_in_sitemap"))
if not page["noindex"] and page["canonical"] != url:
    conflicts.append((url, "indexable_non_self_canonical"))
```

전체 분기는 [진단 코드](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/huntlab_wp_diagnostics.py), 실패 후 통과 조건은 [회귀 테스트](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/tests/test_huntlab_wp_diagnostics.py)에 있다.

## 적용 범위와 한계

이 도구는 제공된 페이지 목록과 sitemap snapshot의 일관성을 검사한다. 검색엔진이 URL을 실제로 색인했는지, robots.txt에 다른 차단이 있는지, 렌더링 뒤 noindex가 삽입되는지까지 대신 확인하지 않는다. 공개 배포에서는 HTTP 응답, 렌더링된 HTML, sitemap, Search Console 상태를 별도로 기록해야 한다.

sitemap index가 여러 child sitemap을 가리키는 사이트라면 모든 child URL을 먼저 펼쳐야 한다. 첫 sitemap만 검사하면 페이지네이션을 첫 응답만 읽는 것과 같은 누락이 생긴다.

## 배포 전에 실행할 명령 모음

1. indexable/noindex 판정과 canonical을 URL별 JSON으로 저장한다.
2. sitemap index와 모든 child sitemap의 URL을 합친다.
3. noindex URL과 sitemap URL의 교집합이 0인지 확인한다.
4. indexable URL의 canonical이 자기 자신인지 확인한다.
5. 배포 후 공개 HTML과 sitemap을 다시 받아 같은 검사를 반복한다.

[진단 스크립트와 fixture로 직접 재현하기](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/huntlab_wp_diagnostics.py)
