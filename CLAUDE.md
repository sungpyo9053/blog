# 블로그 글 작성 자동화 시스템

## 목적

사용자가 준 주제를 리서치, 글쓰기, 이미지 제작, 최종 조립 서브 에이전트에 순서대로 위임해 완성된 블로그 글을 만든다. 완성된 글은 Reviewer 승인 이후 Publisher Agent가 WordPress 발행 정책에 따라 처리한다.

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

1. `agents/topic-planner-agent.md`의 편집장(Editor)에 따라 10개 카테고리 후보 생성 → 평가 → TOP10 → TOP2 → `output/topics.md`
2. `agents/researcher.md`에 따라 TOP2만 리서치 위임 → `output/[주제]/research.md`
3. `agents/writer.md`에 따라 글쓰기 위임 → `output/[주제]/draft.md`
4. `agents/image-maker.md`에 따라 이미지 제작 위임 → 이미지 생성 및 `draft.md` 마커 치환
5. `agents/assembler.md`에 따라 최종 조립 위임 → `output/[주제]/final.md`, `final.html`
6. Reviewer Agent에 최종 콘텐츠 검토 위임 → 승인 또는 수정 요청
7. Reviewer 승인 후 `agents/publisher-agent.md`에 따라 WordPress 발행 위임 → 일일 자동 파이프라인은 Publish

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

Topic Planner Agent는 Tech, AI, ML Algorithms, Harness Engineering, System Architecture,
Economy, Society, Politics, Hot Issue, Build Log의 편집장으로서 후보 생성 → 평가 →
TOP10 → TOP2 → `topics.md` 순서로 결정한다.

일일 자동 파이프라인의 Publisher는 `publish.md`에 전달된 Editor의 `category`와 `tags`를 WordPress에 반영하고 실제 Publish를 수행한다. 카테고리는 이름으로 조회하며 없으면 생성하고, Uncategorized로 대체하지 않는다. Publish는 `guides/publisher-guide.md`가 정의한 조건과 Reviewer 승인 해시 검증을 모두 만족하는 경우에만 수행한다.

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
