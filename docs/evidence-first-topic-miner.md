# Evidence-first Topic Miner

이 도구는 Git 변경에서만 사건을 시작한다. RSS, 뉴스, Google Trends, 검색량,
WordPress 글 목록, 로그 파일은 독립적인 토픽 씨앗이 될 수 없다. WordPress에는
인벤토리 수집에는 읽기 전용 `GET`만 사용한다. 독립 글 lane은 READY 후보 한 건만
Writer와 Publisher 경로에 전달하며, 후보가 없으면 Publisher를 호출하지 않는다.

## 사건 연결 규칙

- 소스를 변경한 commit 하나를 사건의 시작점으로 삼는다.
- 후속 test-only commit은 import/call 경로, 변경 symbol, commit ancestry가 모두
  일치하고 가능한 사건이 하나일 때만 연결한다.
- 시간상 가까운 것은 연결 근거로 사용하지 않는다.
- merge commit은 자동 사건에서 제외한다.
- rename, revert, 다중 파일 변경, 다중 사건 가능성이 있는 변경은 명시적 검토
  기록 없이는 READY가 될 수 없다.
- 같은 commit, test, log 증거는 둘 이상의 READY 후보에 재사용하지 않는다.

## READY 실행 증거 계약

자동 READY에는 `output/topic-miner/evidence-events/*.json`의 구조화된 실행
기록이 필요하다. 이 파일도 이미 Git으로 시작된 사건만 보강할 수 있다.

```json
{
  "trigger_commit": "40-character commit SHA",
  "anchor": "scripts/example.py",
  "recommended_format": "feature_build",
  "fix_commit": "40-character commit SHA",
  "fix_at": "2026-09-05T10:30:00+09:00",
  "target_reader": "같은 자동화를 운영하는 개발자",
  "reader_action": "전체 페이지 수를 확인하고 후속 페이지를 순회한다",
  "unique_takeaway": "첫 응답의 길이는 전체 건수가 아니다",
  "public_access_verified": true,
  "public_urls": ["https://github.com/example/repo/commit/40-character-sha"],
  "contract_fields": {
    "requirement": "실제 작업 요청",
    "completion_result": "완성된 로컬 결과",
    "unsupported_scope": "지원하지 않는 범위"
  },
  "before_after": {"before": "page1=100", "after": "page1=100,page2=19,total=119"},
  "test_runs": [
    {
      "test": "tests.test_example.test_case",
      "status": "PASS",
      "exit_code": 0,
      "recorded_at": "2026-09-05T11:00:00+09:00",
      "output_sha256": "64 lowercase hex characters"
    }
  ]
}
```

`debugging_log`만 실패→수정→동일 조건 통과를 요구한다. 다른 유형은
`guides/content-types/evidence-deep-article.md`의 유형별 계약을 적용한다. 실행
결과 해시가 없거나 현재 publish와 draft 인벤토리 확인이 불완전하거나
기존 글과 검색 의도가 겹치면 READY가 될 수 없다.

## 실행

```bash
.venv/bin/python scripts/snapshot_topic_inventory.py
.venv/bin/python scripts/evidence_topic_miner.py --date YYYY-MM-DD --dry-run
.venv/bin/python scripts/evidence_topic_miner.py --date YYYY-MM-DD
.venv/bin/python scripts/run_evidence_deep_article.py --dry-run
```

각 REST 인벤토리는 `output/topic-miner/inventory/`에 불변 보관하고
`inventory-latest.json` 포인터만 원자 교체한다. 일자별 후보 결과는 기존 파일을
덮어쓰지 않는다. checkpoint에는 마지막 commit,
처리한 사건 ID, 입력 인벤토리 해시, Miner 코드 해시, 결과 해시를 기록한다.
