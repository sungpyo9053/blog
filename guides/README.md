# Hunt News Guide Map

이 문서는 `guides/`의 탐색용 목차다. 콘텐츠·발행 정책을 새로 정의하지 않으며,
각 정책의 실제 기준은 아래 원본 Guide를 따른다.

## Guide 구조

| 영역 | 기준 문서 | 책임 | 주요 소비자 |
|---|---|---|---|
| 편집 원칙 | [`editorial-policy.md`](./editorial-policy.md) | AI 보조 사용, 고유 가치, 실제 근거, 발행 후 관리 | Planner, Researcher, Writer, Reviewer |
| 문체 | [`style-guide.md`](./style-guide.md) | 화자, 문장 리듬, 도입·본문·마무리 표현 | Writer, Reviewer |
| 검색 품질 | [`seo-guide.md`](./seo-guide.md) | 검색 의도, 키워드, 제목, 링크, E-E-A-T, Helpful Content | Writer, Reviewer |
| 이미지 | [`image-guide.md`](./image-guide.md) | 카테고리별 이미지 안전성, 제작 규격, 시각 검증, ALT | Image Maker, Reviewer |
| 수익화 | [`monetization-guide.md`](./monetization-guide.md) | 전환 목표, CTA, 제휴 고지, 금지 표현 | Planner, Researcher, Writer, Reviewer |
| WordPress 발행 | [`publisher-guide.md`](./publisher-guide.md) | 입력 검증, 중복 방지, 미디어, Publish, 오류·감사 로그 | Reviewer, Publisher |
| 발행 후 분석 | [`analytics-optimization-guide.md`](./analytics-optimization-guide.md) | Search Console·GA4 해석, Refresh·Content Gap 검토 경계 | Analytics Optimizer, 다음 Planner 사이클 |

## 파이프라인별 읽기 순서

```text
Topic Planner
  editorial-policy → seo-guide → monetization-guide

Researcher
  editorial-policy → seo-guide → monetization-guide

Writer
  editorial-policy → style-guide → seo-guide → monetization-guide

Image Maker
  editorial-policy → image-guide → monetization-guide

Reviewer
  editorial-policy → style-guide → seo-guide → image-guide
  → monetization-guide → publisher-guide

Publisher
  publisher-guide

Analytics Optimizer
  analytics-optimization-guide
```

실제 Agent가 읽어야 하는 파일과 실행 순서는 `agents/*.md`, `CLAUDE.md`와 Harness가
결정한다. 이 표는 책임을 빠르게 찾기 위한 지도이며 새로운 실행 계약이 아니다.

## 책임 경계

- 콘텐츠를 발행할 가치가 있는지는 `editorial-policy.md`와 Reviewer가 판단한다.
- 검색 의도와 콘텐츠 SEO는 `seo-guide.md`가 담당한다.
- 문체는 `style-guide.md`, 이미지 내용과 제작은 `image-guide.md`가 담당한다.
- 수익화 표현과 CTA는 `monetization-guide.md`가 담당한다.
- WordPress 입력·상태·중복·미디어·오류 처리는 `publisher-guide.md`가 담당한다.
- 발행 후 데이터는 `analytics-optimization-guide.md`가 분석하되 글이나 WordPress를
  직접 변경하지 않는다.
- Publisher 정책의 최종 기준은 기존 선언대로 `publisher-guide.md`다.

## 공통 문서 구성 순서

Guide를 새로 만들거나 다음 정리 주기에 기존 문서를 다듬을 때는 가능한 범위에서
다음 순서를 사용한다.

1. 목적과 적용 대상
2. 최상위 원칙
3. 입력과 전제 조건
4. 실행 규칙
5. 출력 또는 산출물
6. 실패·금지·권한 경계
7. 검증 체크리스트
8. 참고 자료와 변경 기준일

규칙을 다른 문서에 복사하지 않는다. 다른 영역의 세부 기준이 필요하면 원본 Guide를
링크하고, 현재 문서에는 책임 경계만 남긴다.

## 현재 정리 대기 항목

아래 항목은 구조상 확인됐지만 이 목차 추가 작업에서는 정책을 변경하지 않는다.

- `seo-guide.md`의 Google 운영 계약과 과거 네이버 실무 설명을 분리할지 검토
- `style-guide.md`의 네이버 생활 후기체와 WordPress 기술 글 문체를 카테고리별로
  분리할지 검토
- `seo-guide.md`, `publisher-guide.md`, `image-guide.md`에 반복된 제목·이미지·ALT
  규칙을 원본 문서 링크 방식으로 축약할지 검토
- `publisher-guide.md`의 Frontmatter 본문 계약과 현재 Harness의 Markdown 본문 계약을
  대조
- `publisher-guide.md`의 예약 발행 지원 범위와 Draft·Publish 선언을 대조
- `CLAUDE.md`와 `publisher-guide.md`의 신규 카테고리 처리 방식을 대조

정리 대기 항목은 운영 동결 기간의 정책 변경 근거가 아니다. 실제 변경은 참조 관계,
테스트와 운영 데이터를 확인한 뒤 한 계약씩 수행한다.
