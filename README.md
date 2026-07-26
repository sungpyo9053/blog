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
