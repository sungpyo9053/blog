# 자체 2D 좌표 예제 실행 기록

- verification_date: 2026-09-16 UTC, 공식 자료 조사 이후 실행
- environment: Darwin x86_64, Python 3.12.9, 표준 라이브러리 `fractions`만 사용
- evidence_origin: purpose_built_test
- verification_mode: not_directly_tested (로봇·ROS·카메라는 미실행; 산술 코드는 실제 실행)
- code_sha256: `2de591a309b09eb76fbfaa38de30c5ca7615fc206eca96f6a73877c132577922`

Python 3.12.9를 `python3`로 선택한 환경에서 저장소 루트 기준으로 다음 명령을 실행했다. 준비물은 같은 디렉터리에 제공한 `coordinate_example.py`이며 외부 패키지·가상환경·비밀 설정은 필요 없다. 특정 개인의 인터프리터 설치 위치는 공개 기록에서 제외했다.

```sh
python3 --version
python3 -I editorial/2026-09-16/physical-ai-coordinate-frames/coordinate_example.py
```

실제 출력:

```text
Python 3.12.9
point B -> W: (2, 2)
wrong translation-only: (3, 1)
inverse W -> B: (1, 0)
point C -> B: (7/10, 1/5)
point C -> B -> W: (9/5, 17/10)
point C -> W directly: (9/5, 17/10)
```

종료 코드 0. 6개 assert 문이 정답·의도적인 오답의 구별·역변환 복원·센서 경유와 직접 합성의 일치를 확인했다. 마지막 assert 문은 세 값의 연쇄 동등 비교다. `-I`로 사용자 환경과 site 패키지 의존성을 줄였으며 파일은 표준 라이브러리만 import한다. 최적화 옵션 `-O`는 사용하지 않았다.

## 관측과 해석의 경계

- method: 직접 정의한 90도 회전 함수와 Fraction 연산으로 같은 입력을 계산한다.
- observed_result: B→W는 (2, 2), 회전 생략 대조는 (3, 1), 역변환은 (1, 0), C→B→W와 C→W는 모두 (9/5, 17/10)이다.
- operator_judgment: 분수로 정확하게 비교해 부동소수점 허용오차가 교육의 핵심을 가리지 않게 했다. 이 숫자를 본문에 쓸 수 있지만 로봇 성능의 근거로 쓸 수는 없다.
- docs_vs_observed: 공식 자료의 회전 후 원점 이동 및 변환 합성 원리를 이 정적 2D 예제에서 수치로 확인했다. ROS 구현이나 센서 장치의 동작을 검증한 것은 아니다.
- failure_or_limit: `wrong translation-only`는 의도적으로 만든 산술 대조이며 실제 장애·비정상 프로세스 종료가 아니다. 런타임 실패를 발견했다고 기록하지 않는다. 일반 각도·3D·추정된 보정값·동적 시간차를 시험하지 않았다.
- capture_evidence: 위 두 명령과 7줄 출력의 연속 구간을 사용할 수 있다. 문서의 코드 종료 상태 설명을 실제 터미널 출력인 것처럼 덧붙이지 않는다.

## 재사용 시 조건

실제 물리 단위는 m로 가정했다. W는 설명용 평면, B는 90도 회전한 프레임, C는 B와 축이 평행한 평면 센서 프레임이다. C를 카메라 화소 좌표 또는 ROS `_optical` 프레임이라고 바꾸면 이 예제의 가정이 달라진다. 센서→로봇 변환값은 실측치가 아닌 설명용 상수다. 이 검산은 작성자의 로봇 사용 경험이나 현장 실험을 뜻하지 않는다.
