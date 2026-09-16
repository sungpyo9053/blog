# 좌표계 기초 후보 독립 검토

- 검토 시각: 2026-09-16 10:00:55 UTC / 19:00:55 KST
- 작성자: `physical_kakao`; 독립 검토 에이전트: `physical_editorial` (사람 검토가 아님).
- 판정: **APPROVED — 작성 후보 근거 충분**. 최종 원고는 아직 검토하지 않았으며 99점·발행 승인·AdSense 승인 확률을 뜻하지 않는다.
- 대상: `editorial/physical-ai-candidates/physical-ai-coordinate-frames.json`
- 대상 SHA256: `85b54a09ae4ab336f7664cbf38e0a8ac9162cea5587cbfdb115a432e1b97bef7`

## 독립 확인한 근거

공식 원문을 직접 열어 manifest의 주장 범위와 대조했다. [REP 103](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst)의 SI·오른손 좌표계와 몸체/optical 축은 **ROS의 관례**로 한정한다. [Modern Robotics 3.3.1](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)의 프레임 위치·방향, 역변환과 합성 원리를 자체 2D 예제로 축소하는 구분은 적절하다. [tf2 공식 문서](https://raw.githubusercontent.com/ros2/ros2_documentation/rolling/source/ROS-Framework/interfaces/About-Tf2/About-Tf2.rst)의 시간별 관계 관리와 변환 기능은 소개만 하며 설치·실행·동적 변환 검증으로 주장하지 않는다. REP 105 및 Modern Robotics 3.2.1도 보조 확인했다.

자체 코드 전체를 읽고 Python 3.12.9의 격리 모드로 `python -I editorial/2026-09-16/physical-ai-coordinate-frames/coordinate_example.py`를 독립 실행했다. assert를 제거하는 `-O`는 쓰지 않았다. 종료 0, 6개 assert가 실행되었고 출력은 다음과 같았다.

```text
point B -> W: (2, 2)
wrong translation-only: (3, 1)
inverse W -> B: (1, 0)
point C -> B: (7/10, 1/5)
point C -> B -> W: (9/5, 17/10)
point C -> W directly: (9/5, 17/10)
```

계산도 별도로 대조했다. `(-y, x) + (2, 1)`에 `(1, 0)`을 넣으면 `(2, 2)`이며, 이동만 적용한 `(3, 1)`은 다른 답이다. 역변환은 먼저 원점을 뺀 뒤 반대 회전한다. 센서 점 `(1/2, 1/5)`에 원점 `(1/5, 0)`을 더하면 `(7/10, 1/5)`이고 이를 회전·이동하면 `(9/5, 17/10)`이다. 이는 정적 분수 산술 검증이지 실제 로봇·카메라·물리 시뮬레이터 실험이 아니다.

다음 공개 pinned artifact를 검토자가 직접 HTTP GET 했다. 두 raw URL 모두 200이며 로컬 바이트, 공개 raw 바이트, `git show 1b45bbc1eab1f35249cbc389d9de346d858f3665:<path>` 바이트가 정확히 같았다.

- [coordinate_example.py](https://github.com/sungpyo9053/blog/blob/1b45bbc1eab1f35249cbc389d9de346d858f3665/editorial/2026-09-16/physical-ai-coordinate-frames/coordinate_example.py): SHA256 `2de591a309b09eb76fbfaa38de30c5ca7615fc206eca96f6a73877c132577922`.
- [verification.md](https://github.com/sungpyo9053/blog/blob/1b45bbc1eab1f35249cbc389d9de346d858f3665/editorial/2026-09-16/physical-ai-coordinate-frames/verification.md): SHA256 `1fcba7ee1f2a128eda1b0864a85e4eba65d9765386e7d7dad4455d924bfe3104`.

manifest·예제·검증 기록의 `contains_secret` 검사는 모두 false였다. 수동 확인에서도 인증정보·고객정보·내부 로그를 발견하지 않았다. 예제는 표준 라이브러리 산술과 출력뿐이며 네트워크·파일 쓰기·장치 제어를 하지 않는다. 외부 설명을 자체 실행 결과로 바꾸거나 외부 문장을 번역 복제하는 후보가 아니다.

## 전체 WordPress 목록 비교

기존 인증 도구 `scripts/snapshot_topic_inventory.py`를 GET 전용으로 실행했다. 공개/초안의 전체 페이지와 본문을 가져왔으며 WordPress 쓰기는 하지 않았다.

- snapshot: `output/physical-ai-transition/coordinate-inventory.json`
- 보관본: `output/physical-ai-transition/inventory/20260916T095726679387Z.json`
- 수집 시각: `2026-09-16T09:57:26.612851+00:00`
- SHA256: `f8c6e376a7887a2fb529b68ba68b43a27e72f870784b2343cb99fb9583628140`
- 공개 10건 + 초안 114건 = 고유 ID 124건. 본문 누락 0건, 본문 합계 2,077,386 UTF-8 bytes.

방법은 전체 제목·요약 검토, 전체 본문 키워드/중복 검사, 가까운 글의 문맥 비교다. 2 MB 전체를 사람이 한 줄씩 정독했다는 주장이 아니다. `inspect_article`는 124건을 검사하여 passed=true, duplicates=[]였고 `existing_overlap` 결과는 none이었다. 숫자·단어가 같다는 이유만으로 신규성을 인정하지 않고 질문과 학습 결과를 함께 비교했다.

| 가까운 글 | 기존 질문 | 이번 후보와 구분 |
| --- | --- | --- |
| Draft 761, 피지컬 AI 작동 원리 | 관측·행동·피드백 및 측정 편향이 성공 판단에 미치는 영향 | 1차원 값의 흐름이 중심이다. 이번에는 같은 점을 서로 다른 기준으로 표현하는 2D 회전·이동·역변환·합성을 배운다. |
| Draft 611, 휴머노이드 정부 투자 | 정책 대응과 인터페이스·데이터 준비 | 좌표계는 준비 목록에 등장할 뿐 수치 변환 원리를 가르치지 않는다. |
| Draft 397, 내비게이션 시스템 설계 | 경로 탐색·교통·지도·GPS 오차 | 서비스 구조와 경로 문제이며 프레임 간 점 좌표 계산을 해결하지 않는다. |
| Draft 408 / 412, 배달 / 지역 중고거래 | 위치·ETA / 동네 인증·개인정보 | 위치 데이터를 사용하지만 로봇 좌표 변환의 입문 학습과 다른 검색 의도다. |

신규 기초 글로 진행할 근거가 충분하다. 기존 761의 용어 설명을 길게 반복하지 말고 원점·축·단위와 변환 방향에서 시작한다. 761은 아직 초안이므로 공개 URL인 것처럼 학습 링크를 넣지 않는다.

## Writer / 런타임 경계

Writer는 `foundation_concept` 가이드에 따라 정의 → 방향과 단위 → 자체 숫자 풀이 → 회전 생략 오답 → 역변환/합성 검산 → 적용 한계 순서로 독립 원고를 작성할 수 있다. C는 가상의 2D 센서 프레임이며 optical 프레임이나 픽셀 좌표가 아니다. 세계 평면의 오른쪽/위쪽 설명은 예제 정의이지 보편 ROS 축 지정이 아니다. 본문에서는 프레임의 상대 자세와 점 좌표의 변환 방향을 명시하고, `zip`을 쓰는 보조 함수는 고정 2차원 예제용이지 임의 입력을 검증하는 범용 라이브러리로 소개하지 않는다.

승인 JSON은 manifest에만 묶인다. 최종 글은 별도 독립 Reviewer의 20개 항목·8개 gate와 최종 publish 해시 검토를 받아야 한다. 후보 manifest/review 파일이 HEAD에 커밋되기 전에는 `foundation_artifact_not_committed` 등 provenance gate로 런타임 READY가 막히는 것이 정상이다. 커밋·배포 후 현재 inventory와 epoch seal을 이용한 실제 evaluator 결과를 다시 확인한다. 10:00 KST 평가, 하루 최대 1건, READY 없으면 `no_publishable_topic` 규칙은 바뀌지 않는다.
