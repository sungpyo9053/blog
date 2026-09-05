# Hunt News 콘텐츠 자동화 시스템

## 목적

운영은 두 lane으로 분리한다. Lane A는 AI·개발 변화를 한 페이지에 정리하는 매일의
Daily Briefing이며 항상 `noindex, follow`다. Lane B는 Git·test·log·배포·결정 기록에서
실제 사건을 찾는 Evidence-first Deep Article이다. 하루 두 번 평가하되 READY가 있을
때만 회당 최대 한 편을 처리하며, READY가 없으면 `no_publishable_topic`으로 정상 종료한다.
뉴스·RSS·Trends만으로 독립 글 주제를 만들지 않는다.

## 폴더 구조

- `agents/`: 단계별 서브 에이전트 지침
- `guides/`: 문체, SEO, 이미지 제작 및 WordPress 발행 가이드
- `output/[주제]/`: 주제별 중간 및 최종 산출물

## 공식 Agent 목록

- Topic Planner Agent(Editor): `agents/topic-planner-agent.md`
- Research Agent: `agents/researcher.md`
- Writer Agent: `agents/writer.md`
- Image Maker Agent: `agents/image-maker.md`
- Assembler Agent: `agents/assembler.md`
- Reviewer Agent: 최종 콘텐츠 품질 검토 및 승인
- Publisher Agent: `agents/publisher-agent.md`

## 주제 처리 순서

현재 운영 기본 경로는 다음과 같다.

1. 04:00 Daily Briefing을 `briefing_only`로 실행한다.
2. 10:00과 22:00 Evidence-first Topic Miner를 실행한다.
3. 실제 사건을 묶고 현재 공개 글·Draft와 검색 의도를 대조한다.
4. READY가 없으면 Publisher를 호출하지 않고 `failed=false`로 종료한다.
5. READY가 있으면 최대 한 편만 Research → Writer → Image Maker → Assembler →
   Reviewer → Publisher로 전달하고 공개 HTML을 다시 감사한다.

아래 TOP2 흐름은 과거 호환 코드이며 Evidence-first 운영의 토픽 소스로 사용하지 않는다.

1. `agents/topic-planner-agent.md`의 편집장(Editor)에 따라 10개 카테고리 후보 생성 → 평가 → TOP10 → TOP2 → `output/topics.md`
2. 전체 수집 자료, TOP2와 전일 보고서 스냅샷을 `agents/daily-briefing-agent.md`에 전달 → 전일 핵심 신호 3개 재검증을 포함한 필수 일일 보고서 분석 생성
3. `agents/researcher.md`에 따라 TOP2만 리서치 위임 → `output/[주제]/research.md`
4. `agents/writer.md`에 따라 글쓰기 위임 → `output/[주제]/draft.md`
5. `agents/image-maker.md`에 따라 이미지 제작 위임 → 이미지 생성 및 `draft.md` 마커 치환
6. `agents/assembler.md`에 따라 최종 조립 위임 → `output/[주제]/final.md`, `final.html`
7. Reviewer Agent에 최종 콘텐츠 검토 위임 → 승인 또는 수정 요청
8. Reviewer 승인 후 `agents/publisher-agent.md`에 따라 WordPress 발행 위임 → 일일 자동 파이프라인은 Publish
9. 보고서와 상세글 2개의 완전한 매니페스트를 WordPress에 동기화하고 저장 확인

매주 일요일 20:30 KST에는 해당 주의 유효한 일일 브리핑 분석이 5개 이상일 때만
`Weekly Review Planner Agent`가 반복된 변화, 달라진 판단, 다음 주 확인 신호를 하나의
계획으로 합친다. 이후 Research → Writer → Image Maker → Assembler → Reviewer →
Publisher 계약을 그대로 재사용해 `주간 기술 회고` 카테고리에 독립 글 한 건을 발행한다.
이 경로의 실패는 다음 날 02시 일일 파이프라인을 변경하거나 보충 발행하지 않는다.

매주 수요일과 토요일 20:30 KST에는 최근 7일의 유효한 일일 브리핑 3개 이상과
6시간 이내 Google Trends 또는 14일 이내 Search Console 관측값이 연결될 때만
`Technical Explainer Planner Agent`가 예제 중심의 독립 기술 해설 한 건을 계획한다.
Research → Writer → Image Maker → Assembler → Reviewer → Publisher 계약을 재사용하되,
`기술 해설` 카테고리에 문제·예제·정상 및 실패 판정·적용 조건을 갖춘 글만 발행한다.
검색 수요나 근거가 부족하면 발행량을 채우지 않고 건너뛰며, 이 경로의 실패도 일일
파이프라인과 주간 회고를 변경하거나 보충 발행하지 않는다.

일일 보고서 생성, 근거 검증, 매니페스트 완전성 또는 WordPress 저장 확인이 실패하면
해당 실행은 성공으로 기록하지 않는다.

Research Agent는 사용자가 별도 주제를 명시하지 않은 일일 자동 파이프라인에서 Topic Planner가 `output/topics.md`에 선정한 TOP2만 입력으로 사용한다. 각 TOP2의 `category`, `tags`, `reason`, `research_focus`를 그대로 전달받아 조사 범위와 출처 우선순위에 반영한다.

각 단계가 시작되거나 완료될 때 사용자에게 진행 상황을 짧게 알린다.

## 메인 에이전트 원칙

메인 에이전트는 오케스트레이터로만 행동한다. 직접 리서치하거나 블로그 글을 쓰지 말고, 반드시 해당 서브 에이전트에 위임한다.

# Agent Architecture

```text
Topic Planner Agent
→
Research Agent
→ Writer Agent
→ Reviewer Agent
→ Publisher Agent
```

Image Maker Agent와 Assembler Agent는 기존 주제 처리 순서에 따라 Writer와 Reviewer 사이에서 이미지 제작과 최종 조립을 담당한다. 기존 Agent의 역할과 산출물은 변경하지 않는다.

# Agent Responsibilities

Publisher Agent는 WordPress 발행 전용 Agent이며 다음 작업에 책임을 가진다.

- `guides/publisher-guide.md` 적용
- Frontmatter 검증
- Validation
- Draft 생성
- Publish
- 기존 글 Update
- Audit Log 기록

Publisher Agent는 글 작성, 리서치, 사실 검증, SEO 전략 생성, 문체 수정 또는 Reviewer 역할을 수행하지 않는다. 발행 정책을 정의하지 않고 `guides/publisher-guide.md`에 정의된 정책을 해석하고 실행한다.

# Workflow

```text
Topic Planner
↓
Research
↓
Writer
↓
Image Maker
↓
Assembler
↓
Reviewer
↓
Publisher
```

Reviewer의 명시적인 승인 없이는 Publisher Agent를 실행하지 않는다. 작성 또는 조립 완료 상태를 Reviewer 승인으로 간주하지 않는다.

Topic Planner Agent는 생활, 경제, 부동산, 사회, 정치, 문화·엔터, IT의 편집장으로서
Whereispost 수요 신호, 공식 원문, 생활 영향과 기존 글 중복을 확인하고 후보 생성 →
평가 → TOP10 → TOP2 → `topics.md` 순서로 결정한다.

일일·주간 자동 파이프라인의 Publisher는 `publish.md`에 전달된 Editor의 `category`와 `tags`를 WordPress에 반영하고 실제 Publish를 수행한다. 카테고리는 이름으로 조회하며 없으면 실패하고, 자동 생성하거나 Uncategorized로 대체하지 않는다. Publish는 `guides/publisher-guide.md`가 정의한 조건과 Reviewer 승인 해시 검증을 모두 만족하는 경우에만 수행한다.

# Source of Truth

WordPress 발행 정책은 `guides/publisher-guide.md`만 사용한다. 이 문서는 Publisher 정책의 Single Source of Truth(SSOT)다.

Publisher Agent는 발행 정책을 생성하거나 수정하지 않는다. 정책 변경이 필요하면 사람의 명시적인 승인을 받고 `guides/publisher-guide.md`를 먼저 변경해야 한다.

# Failure Handling

- Publisher Agent가 실패하면 Workflow를 중단하고 오류와 현재 WordPress 리소스 상태를 보고한다.
- Validation 실패 시 임의로 발행하지 않는다.
- Validation 실패 시 Draft 생성 가능 여부를 포함한 모든 후속 처리는 `guides/publisher-guide.md`를 따른다.
- API 실패, 네트워크 오류 및 Retry는 `guides/publisher-guide.md`의 오류 처리 정책을 따른다.
- 실패를 우회하기 위해 Publisher Agent가 새로운 예외 정책을 만들면 안 된다.

# Future Extension

향후 SNS 자동 발행, Search Console 연동, Analytics 및 Newsletter는 Publisher 이후 단계에서 확장한다. 확장 단계는 Publisher의 성공 결과를 입력으로 사용하며, 기존 Agent의 책임과 WordPress 발행 정책을 변경하지 않는다.
