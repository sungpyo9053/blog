# HuntLab 콘텐츠 운영 시스템 전면 리뷰

> 기준일: 2026-07-28  
> 범위: 저장소의 Agent, Guide, Prompt/Harness, Workflow, Publisher, Image,
> Analytics, 배포 설정, 테스트와 실제 WordPress 출력  
> 원칙: 기존 구조 유지, 새 Agent 추가 금지, 저위험·고효율 변경 우선

## 1. 결론

HuntLab은 단순 생성기를 넘어 `Planner → Research → Writer → Image →
Assembler → Reviewer → Publisher`의 격리된 실행, 승인 해시, 중복 발행 방지,
감사 로그, 재개 기능과 AWS systemd 운영을 갖춘 실사용 시스템이다. 생성·발행
측은 강하지만 발행 후 데이터가 다음 기획과 기존 글 개선으로 돌아오는 폐쇄 루프,
단계 간 구조화 계약, 실제 경험 증거가 상대적으로 약하다.

이번 변경 전 종합 평가는 **72/100**, 1차 변경 적용 후 평가는 **84/100**이다.
GA4 태그 연결, Search Console 실데이터 누적, Core Web Vitals 실측과 Refresh
운영 결과가 쌓이면 88~90점 범위를 목표로 할 수 있다.

| 영역 | 변경 전 | 1차 적용 후 | 판단 |
|---|---:|---:|---|
| 아키텍처 | 75 | 84 | 역할 분리는 좋고 단계 간 문자열 계약이 약했음 |
| 발행 안정성 | 78 | 91 | 승인 해시·격리 우수, 대표 이미지 fail-fast 추가 |
| SEO | 60 | 78 | Google 우선 기준·클러스터 계약 보강, 실데이터는 미성숙 |
| 콘텐츠 품질 | 72 | 81 | 출처 검증 우수, 반복 템플릿과 고유 경험은 추가 개선 필요 |
| 발행 후 운영 | 48 | 72 | Refresh/Gap 큐 추가, 실제 자동 Update는 의도적으로 보류 |
| 유지보수성 | 68 | 79 | 테스트 좋음, Guide 중복과 1,045줄 Harness는 여전히 부담 |
| 인프라 운영 | 84 | 91 | AWS·systemd·재개·로그 정상 |

## 2. 아키텍처 평가

| 검토 항목 | 점수 | 평가 |
|---|---:|---|
| 역할 명확성 | 9/10 | 각 Agent의 Responsible/Not Responsible가 대체로 명확 |
| 책임 중복 최소화 | 7/10 | SEO·문체·발행 검증이 여러 문서에 반복 |
| 병합 필요성 | 9/10 | 현재 Agent 병합/추가 모두 불필요; Analytics 기존 역할 확장이 적절 |
| Workflow 복잡도 | 7/10 | 7단계는 타당하지만 자연어 파일 계약이 실패 지점 |
| 확장성 | 8/10 | run/topic 격리와 구조화 ID가 좋음 |
| 유지보수성 | 7/10 | Harness와 Guide가 길고 날짜·정책 중복 존재 |
| Agent 의존성 | 8/10 | 단방향이며 Publisher 권한 경계가 좋음 |

### 유지할 구조

- Publisher만 외부 변경을 수행하는 권한 경계
- `run_id`, `topic_id`, `source_id` 격리
- Reviewer SHA-256 승인 후 Publish
- 실패 후 `--resume-run-id` 재개
- Image Maker와 Assembler 분리
- Analytics Optimizer의 독립 실행

### 병합하지 않을 Agent

Research/Writer는 사실 근거와 표현 책임이 달라 분리 가치가 크다. Reviewer와
Publisher도 승인과 외부 변경 권한을 분리해야 한다. Image Maker와 Assembler는
비용 최적화 여지는 있지만 시각 검수와 문서 조립의 실패 양상이 달라 유지한다.

### 구조적 부채

1. Harness의 Prompt 문자열이 실질적인 또 하나의 정책 문서다.
2. Frontmatter와 `topics.md`는 스키마가 코드·문서·테스트에 분산돼 있다.
3. Guide의 동일 규칙이 Agent에도 반복돼 변경 시 불일치가 발생한다.
4. Agent 출력이 자유형 Markdown 중심이라 필드 누락을 실행 후에 발견한다.

## 3. SEO Guide 리뷰

Google Search Central 기준에서 유효한 부분은 people-first, 검색 의도, 공식 원문,
E-E-A-T를 순위 공식으로 취급하지 않는 설명, H1 단일화, crawlable 내부 링크,
고유 Meta Description, canonical, 이미지 ALT와 과장 금지다.

### 충돌·오래된 규칙

- 문서 마지막의 “네이버 Primary, Google Secondary”는 WordPress 기술 블로그
  목표와 충돌했다. 이번 변경에서 Google Search Central을 Primary로 수정했다.
- 제목 20~40자 체크리스트와 Writer의 40~65자 규칙이 충돌한다. 숫자는 강제
  조건이 아니라 읽기 쉬운 권장 범위로 통합해야 한다.
- FAQ 최소 3개는 모든 글의 품질/검색 요건이 아니다. FAQ rich result 노출을
  기대해 기계적으로 넣지 말고 실제 후속 질문이 있을 때만 유지하는 편이 좋다.
- 태그 5~10개와 Planner의 3~7개가 충돌한다. 현재 실행 계약인 3~7개를 SSOT로
  삼아야 한다.
- “첫 문단 Primary Keyword 정확히 한 번”은 검증 가능한 품질 기준보다
  기계적 규칙에 가깝다. 자연스러운 제목·도입 일치를 우선한다.

### 빠져 있거나 운영이 약한 요소

- URL별 색인 상태와 sitemap 제출 결과
- Search Console query/page 기반 CTR·순위 추세
- Topic Cluster, Pillar, 고립 글과 링크 방향성
- 작성자/검수자 정보와 Article Schema 정합성
- `dateModified`를 실제 내용 변경시에만 갱신하는 정책
- 이미지 파일명, WebP/AVIF, responsive image와 LCP
- CWV의 LCP/INP/CLS 실측과 템플릿 회귀 감지
- Redirect와 공개 후 slug 변경 절차

Google은 자동화 자체보다 독창성·직접 경험·신뢰·독자 만족을 보며, 선호 단어 수를
두지 않는다. 구조화 데이터는 실제 표시 내용과 정확히 일치할 때만 사용한다.

## 4. Writer와 Human Quality

AI 작성 티가 나는 주원인은 해요체 자체가 아니라 반복 가능한 구조 계약이다.

- 도입 10~15%, 본론 70~80%, 결론 10~15%의 고정 비율
- 매번 문제 제기 → “결론부터” → 목록 → FAQ → 권유형 결론
- 일정한 H2/H3 수와 비슷한 문단 길이
- 공식 문서 요약을 개인 경험처럼 들리게 만드는 후기체
- 모든 글에 FAQ 3개 강제
- 실제 실행 로그·실패·전후 수치가 없는 상태에서 “사람다운 말투”만 강조

이번 변경은 고정 비율을 제거하고 문제 해결 기록, 비교, 타임라인, 판단 근거,
체크리스트 중 주제에 맞는 구조를 선택하도록 했다. 문장 길이도 획일화하지 않고,
Research에 증거가 있을 때만 실제 경험을 전면에 배치하도록 했다.

### 카테고리별 문체 제안

별도 Guide 파일을 지금 추가하지 않고 `style-guide.md` 안의 얇은 프로필로
운영하는 것이 유지보수에 유리하다.

| 유형 | 중심 문체 | 필수 고유 정보 |
|---|---|---|
| 기술 문서 | 결론·환경·재현 순서, 간결한 설명 | 버전, 명령, 기대/실제 결과 |
| AI | 평가 조건과 한계 중심 | 모델·데이터·평가일·비교 기준 |
| 개발 경험 | 시간순 문제 해결 기록 | 실패 로그, 가설, 수정, 재검증 |
| Build Log | 결정과 trade-off 중심 | 커밋/구성, 비용, 전후 측정 |
| 프로젝트 후기 | 회고와 판단 중심 | 선택하지 않은 대안과 배운 점 |
| Economy/사회 | 중립적 사실 설명 | 기준일, 원문, 적용 대상과 예외 |

## 5. Topic Planner와 Cannibalization

기존 Planner는 공개 글/Draft/최근 output의 제목·slug·검색 의도를 확인하고 있어
기본 중복 방지는 있다. 그러나 검색량 수치가 없고, query/page 데이터·클러스터·
내부 링크 후보가 구조화되지 않아 제목이 다른 같은 의도 글을 놓칠 수 있었다.

이번 변경에서 각 후보에 다음 계약을 추가했다.

- `internal_link_candidates`
- `topic_cluster`
- `pillar_candidate`
- 기존 글로 해결 가능한 질의는 신규 글보다 Refresh 우선
- Primary Keyword, 검색 의도, 독자 결과가 같으면 Cannibalization으로 제외

향후에는 Search Console의 동일 query가 여러 URL로 분산되는지도 감지해야 한다.

## 6. 내부 링크 전략

현재 규칙은 공개 URL 검증, 자연스러운 문맥, 구체적 앵커를 요구해 안전하다.
부족한 점은 후보 생성과 방향성이다. Hub & Spoke/Pillar가 데이터 필드가 아니었고,
고립 글 감지나 한 URL에 링크가 과집중되는지 확인하지 않았다.

최소 구조는 다음과 같다.

`Planner(클러스터/후보) → planner-context.json → Research(독자 다음 질문) →
Writer(관련 문맥) → Reviewer(공개 URL·앵커 검증) → Analytics(고립/성과 검토)`

자동 삽입보다 자동 추천 + Reviewer 승인 방식을 유지한다.

## 7. Content Lifecycle와 운영 자동화

변경 전 Analytics는 Search Console/GA4를 읽었지만 단순 임계치를 넘으면 별도의
Daily Pipeline을 실행했다. 이는 Content Gap 분석이 아니며 중복 발행·비용 증가
위험이 있다.

이번 변경 후:

- Search Console 노출 50 이상, CTR 2% 미만: Refresh 검토 후보
- 노출 30 이상, 클릭 0, 평균 순위 8위 이하: Content Gap 검토 후보
- 기존 글 보강을 신규 글보다 우선
- 분석만으로 추가 발행 금지(`disabled_review_required`)
- 다음 정규 Planner가 `latest.md`를 읽어 기획에 반영

외부 인증 없이 임의 구현하지 않은 항목:

- URL Inspection API 기반 색인 확인
- 공개 글 자동 Update
- 공식 문서 diff 크롤러
- GA4 전환 이벤트

이들은 인터페이스와 정책을 먼저 두고, 인증·표본·사람 승인이 준비된 뒤 연결한다.

## 8. 실제 WordPress 운영 점검

2026-07-28 실제 출력 기준:

- AIOSEO: active
- AIOSEO Broken Link Checker: active
- MonsterInsights: active
- Jetpack: active
- canonical: 두 글 모두 출력
- Open Graph: title/description/url 출력
- JSON-LD: 출력
- robots.txt: sitemap URL 선언
- sitemap: AIOSEO 경로 사용
- GA4: 공개 HTML에서 `G-...` 측정 ID 미검출
- Post 72: 대표 이미지 ID 68
- Post 67: 누락 상태에서 미디어 ID 73으로 보정 완료

AIOSEO와 다른 종합 SEO 플러그인을 동시에 활성화하지 않는다. Rank Math/Yoast를
추가 설치할 이유가 없다. Schema·canonical·OG가 실제로 출력되므로 AIOSEO 하나를
SSOT로 유지한다. MonsterInsights는 활성화만으로 측정이 끝난 것이 아니며
WordPress 관리자에서 올바른 GA4 Web Stream 연결이 필요하다.

성능은 캐시 활성 여부만으로 판단하지 않고 PageSpeed Insights/CrUX에서 LCP,
INP, CLS를 모바일 기준으로 측정해야 한다.

## 9. 유지보수성

### 중복

- SEO 제목·Meta·내부 링크 규칙: `seo-guide`, Writer, Reviewer, Publisher Guide
- 대표 이미지: Image Guide, Image Agent, Assembler, Publisher Guide/Agent
- 비밀정보 금지: Harness와 여러 Agent
- 카테고리/태그: Planner, Reviewer, Publisher

### 정리 방향

즉시 파일을 나누거나 이름을 바꾸지 않는다. 다음 단계에서
`guides/content-contract.md` 하나에 필드 스키마와 소유 Agent만 모으고 기존
문서는 링크로 참조하는 방식이 안전하다. Harness 분리는 테스트가 충분해진 뒤
Prompt builder 단위로 진행한다.

## 10. 이번에 실제 반영한 변경

| 파일 | 변경 이유 | 기대 효과 |
|---|---|---|
| `scripts/run_daily_pipeline.py` | 대표 이미지 fail-fast, 클러스터 필드 전달 | 썸네일 누락 방지, 내부 링크 기획 보존 |
| `scripts/run_analytics_optimizer.py` | 자동 추가 발행 제거, Refresh/Gap 분석 | 중복·비용 위험 감소, 발행 후 개선 큐 |
| `agents/topic-planner-agent.md` | 의도 기반 카니벌라이제이션·클러스터 계약 | 신규 글보다 적절한 Refresh 선택 |
| `agents/writer.md` | 고정 구조와 문장 리듬 완화 | AI 템플릿 인상 감소 |
| `agents/reviewer.md` | 대표 이미지·경험 근거·앵커 검증 | 발행 품질 회귀 차단 |
| `guides/analytics-optimization-guide.md` | Refresh 기준과 변경 권한 경계 | 안전한 운영 자동화 |
| `guides/seo-guide.md` | Google Primary로 정책 충돌 해소 | 프로젝트 목표와 SEO 기준 정렬 |
| `tests/test_analytics_optimizer.py` | 임계치 분석 회귀 테스트 | 운영 로직 안정성 |
| `tests/test_daily_pipeline.py` | 대표 이미지 계약 검증 | 누락 재발 방지 |
| `tests/test_seo_contracts.py` | 새 SEO 계약 정적 검증 | 문서/코드 불일치 탐지 |

## 11. ROI TOP 20

| 우선순위 | 개선 | 효과 | 난이도 | ROI | 수정/운영 대상 |
|---:|---|---|---|---|---|
| 1 | 대표 이미지 필수 계약 | CTR·OG·발행 완결성 | 낮음 | 매우 높음 | Pipeline, Reviewer, tests |
| 2 | GA4 Web Stream 연결 | 방문·전환 실측 | 낮음 | 매우 높음 | MonsterInsights 관리자 |
| 3 | Search Console 권한/속성 검증 | query·CTR·순위 확보 | 낮음 | 매우 높음 | GSC, `.env` |
| 4 | Analytics 자동 추가 발행 제거 | 중복·비용 방지 | 낮음 | 매우 높음 | Analytics runner |
| 5 | Refresh 후보 큐 | 기존 자산 성장 | 낮음 | 매우 높음 | Analytics guide/runner |
| 6 | 의도 기반 Cannibalization | URL 경쟁 방지 | 중간 | 매우 높음 | Planner, context |
| 7 | 내부 링크 후보 구조화 | 크롤링·검색 여정 | 중간 | 높음 | Planner→Reviewer |
| 8 | Topic Cluster/Pillar 필드 | 주제 권위·정보 구조 | 중간 | 높음 | Planner |
| 9 | 고정 Writer 구조 제거 | 사람다운 품질 | 낮음 | 높음 | Writer |
| 10 | 실제 경험 증거 계약 | Helpful Content·신뢰 | 중간 | 높음 | Research, Writer, Reviewer |
| 11 | URL별 인덱스 상태 수집 | 색인 장애 조기 탐지 | 중간 | 높음 | Analytics interface |
| 12 | 저CTR 제목 개선 승인 흐름 | 검색 클릭 증가 | 중간 | 높음 | Analytics→Reviewer |
| 13 | 공식 문서 변경 감지 | 노후 정보 방지 | 중간 | 높음 | Research metadata |
| 14 | 고립 글/깨진 링크 리포트 | 크롤링·UX 개선 | 낮음 | 높음 | AIOSEO BLC, Analytics |
| 15 | Article Schema 정합성 검사 | 검색 이해·신뢰 | 낮음 | 높음 | WordPress QA |
| 16 | 저자/About/편집정책 | E-E-A-T 신뢰 | 낮음 | 높음 | WordPress Pages |
| 17 | CWV 모바일 측정 | UX·전환 | 중간 | 중간~높음 | Theme/cache/images |
| 18 | 이미지 WebP/AVIF 파생 | LCP·전송량 | 중간 | 중간 | Image pipeline |
| 19 | Agent별 토큰/원가 리포트 | ROI·비용 통제 | 중간 | 중간 | Harness logs |
| 20 | 공통 계약 SSOT 추출 | 유지보수 | 중간 | 중간 | guides, tests |

## 12. 남은 1회 설정과 완료 기준

1. WordPress `Insights → Setup Wizard`에서 올바른 GA4 Property/Web Stream 연결
2. 공개 HTML에서 측정 ID와 실제 Realtime 이벤트 확인
3. Search Console 속성에 서비스 계정 read 권한 확인
4. 7~28일 데이터 누적 후 Refresh 임계치 재조정
5. PageSpeed Insights 모바일 실측 후 캐시/이미지 최적화

인증되지 않은 상태에서 GA4/GSC 성공을 가장하지 않는다. 자동 Refresh는 분석 큐,
원문 재검증, Reviewer 승인, 명시적 Update 권한이 모두 있을 때만 공개 글을
변경해야 한다.

## 13. 공식 기준

- [Google: Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Google: SEO link best practices](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)
- [Google: Image SEO best practices](https://developers.google.com/search/docs/appearance/google-images)
- [Google: Structured data introduction](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
- [Google: Sitemap overview](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)

