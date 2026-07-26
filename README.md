# Blog Content Pipeline

주제 하나를 입력하면 리서치부터 글쓰기, 이미지 제작, 최종 조립까지 순서대로 수행하는 블로그 콘텐츠 파이프라인입니다.

## 구성

- `CLAUDE.md`: 전체 파이프라인과 오케스트레이션 규칙
- `agents/`: researcher, writer, image-maker, assembler 역할별 지침
- `guides/`: 문체, SEO, 이미지 제작 가이드
- `output/[주제]/`: 실행 중 생성되는 산출물(저장소에는 포함하지 않음)

## 실행

이 저장소를 열고 다음처럼 주제와 함께 전체 파이프라인 실행을 요청합니다.

```text
주제: "후쿠오카 여행"

이 주제로 전체 파이프라인을 처음부터 끝까지 실행해줘.
```

파이프라인은 다음 순서로 진행됩니다.

1. 리서치 → `output/[주제]/research.md`
2. 글쓰기 → `output/[주제]/draft.md`
3. 이미지 제작 및 초안 이미지 마커 치환
4. 최종 조립 → `output/[주제]/final.md`, `final.html`

생성 결과는 로컬 `output/`에만 남고 Git에는 커밋되지 않습니다.

## 일일 자동 파이프라인

Topic Planner가 후보 10개 이상을 평가해 TOP2를 선정하고, 각 주제를 Research부터 WordPress Draft 생성까지 순서대로 처리합니다.
실행기는 Codex CLI의 비대화식 `codex exec`를 사용하며 승인 정책은 `never`, 샌드박스는 `danger-full-access`로 고정합니다. 승인 없이 수행할 수 없는 단계는 대기하지 않고 실패합니다. Agent에는 프로젝트 외부 변경, Git push 및 공개 Publish를 금지하며 Publisher는 Draft만 생성합니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py
```

추가 키워드는 선택적으로 전달할 수 있습니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py --keywords "AWS,FastAPI"
```

외부 호출이나 WordPress 변경 없이 Topic Planner 출력 계약, TOP2 파싱 및 단계별 Codex 명령 생성을 확인할 수 있습니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py --dry-run
```

macOS 자동 실행은 `deploy/com.huntlab.daily-pipeline.plist`를 `~/Library/LaunchAgents/`에 설치하고 launchd에 등록합니다. 매일 오전 2시에 실행되며 로그는 `logs/launchd.out.log`와 `logs/launchd.err.log`에 기록됩니다. `deploy/crontab.example`은 deprecated된 과거 예시로만 보존합니다.
