# 제어 시간 간격 산술 검증

- verification_date: 2026-09-20 KST (2026-09-19 22:40 UTC)
- verification_mode: controlled_comparison
- evidence_origin: purpose_built_test
- environment: Darwin 23.0.0 x86_64, Python 3.12.9, 표준 라이브러리만 사용
- code: `interval_example.py`
- code_sha256: `627043cb976e78ee4398c1ffed5a9b096b41a7c57c2871e5a25cf6a5e60ada99`

아래 명령은 코드가 있는 폴더에서 실제 실행했다. Python 3.12.9를 PATH로 선택한 개인 절대경로만 공개 기록에서 제외했다. 출력과 종료 상태는 그대로다. Python 3.12 이상이 설치된 새 폴더에 파일을 저장하면 패키지 설치 없이 재현할 수 있다. 공개 커밋 URL은 아직 발급되지 않았으며 공개 다운로드 재현은 후속 확인 대상이다.

```bash
python3 --version
python3 interval_example.py
python3 -m unittest interval_example -v
```

첫 명령의 실제 출력은 `Python 3.12.9`, 종료 코드는 0이었다. `platform.python_version()`으로도 같은 런타임을 확인했다.

예제 명령 실제 출력, exit 0:

```text
elapsed_ms=90
interval_aware_displacement_m=0.036
nominal_20ms_displacement_m=0.024
nominal_minus_interval_aware_m=-0.012
same_duration_subdivision_m=0.024
```

테스트 명령 실제 출력, exit 0:

```text
test_direction (interval_example.IntervalTests.test_direction) ... ok
test_invalid_intervals (interval_example.IntervalTests.test_invalid_intervals) ... ok
test_nominal_assumption (interval_example.IntervalTests.test_nominal_assumption) ... ok
test_stationary (interval_example.IntervalTests.test_stationary) ... ok
test_subdivision (interval_example.IntervalTests.test_subdivision) ... ok
test_variable_intervals (interval_example.IntervalTests.test_variable_intervals) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.001s

OK
```

의도적으로 잘못된 시간 간격을 넣은 명령:

```bash
python3 interval_example.py --interval-ms 20 0 40
```

실제 출력, exit 2:

```text
usage: interval_example.py [-h] [--interval-ms INTERVAL_MS [INTERVAL_MS ...]]
interval_example.py: error: intervals must be nonempty and strictly positive
```

이 실패는 운영 장애가 아니라 교육용 입력 검사의 대조군이다. 이 모델은 0 이하 간격을 거절한다. ROS에서 시뮬레이션 시간이 정지·역행하는 모든 경우의 올바른 처리 정책이라는 뜻은 아니다.

## 손검산과 판정

속도는 모든 구간에서 0.4m/s로 일정하고, 한 축에서 방향이 변하지 않는다고 정했다.

| 구간 | 시간(ms) | 시간(s) | 변위(m) | 누적 변위(m) |
| --- | --- | --- | --- | --- |
| 1 | 20 | 0.020 | 0.008 | 0.008 |
| 2 | 30 | 0.030 | 0.012 | 0.020 |
| 3 | 40 | 0.040 | 0.016 | 0.036 |

모든 간격을 20ms라고 가정하면 0.4 × 0.060 = 0.024m다. 입력된 90ms 기준값과의 차이는 -0.012m다. 입력 간격은 인위적으로 정했으며 실제 제어기의 jitter를 측정하지 않았다.

같은 60ms를 20ms 세 구간 또는 10ms 여섯 구간으로 나누면 둘 다 0.024m다. 이것은 일정 속도에서 총 시간이 같다는 조건의 결과다. 일반적인 제어 시스템에서 주기가 성능에 영향을 주지 않는다는 결론으로 확대할 수 없다.

- docs_vs_observed: ros2_control 문서는 period 인수를 이전 반복 이후 측정 시간으로 설명한다. 여기서는 그 API를 실행하지 않고, 시간 간격을 직접 입력한 별도의 산술 모델만 비교했다.
- operator_judgment: 반복 횟수만 세지 말고 단위와 구간별 시간을 함께 검산한다. 명령 속도로 구한 값은 기준/예상 변위다. 실물 변위라고 부르려면 실제 속도·미끄러짐·센서·시계 검증이 추가로 필요하다.
- limitations: 실제 시계 측정·ROS·하드웨어·동역학·가속도·충돌·실시간 성능을 검증하지 않았다. `Fraction`은 이 유리수 계산의 반올림 오차를 피할 뿐 물리 모델의 정확도를 보증하지 않는다. CLI는 정수 ms 입력만 받는다.
- capture_evidence: 위 예제 명령/출력/exit 0과 의도적 실패/exit 2가 실제 캡처 원문이다. 서로 다른 실행을 한 실행처럼 합치지 않는다.
