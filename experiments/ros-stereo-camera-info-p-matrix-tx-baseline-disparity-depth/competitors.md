# 경쟁 글 대비 차별점: ros-stereo-camera-info-p-matrix-tx-baseline-disparity-depth

같은 질문으로 검색되는 상위 글을 2026-11-22에 직접 열어 읽었다(영어 4, 한국어 2). 경쟁 글은 Writer의 본문
인용 출처가 아니라 차별점 판단용이다. 본문 근거는 공식 1차 자료로만 쓴다.

1. https://answers.ros.org/question/248509/ (ROS Answers archive, "stereo images - baseline, units, depth map
   generation...", 2016-11-20 질문)
   - 다루는 것: 단안 카메라를 옮겨 만든 가짜 스테레오에서 오른쪽 P에 `P[3] = Tx = -fx' * B`를 넣는 방법까지
     질문자가 스스로 찾았고, B의 단위(mm? m? px?)에서 막혔다. 센서 크기로 baseline을 픽셀로 바꾸는 잘못된
     시도가 적혀 있다.
   - 빠졌거나 틀린 것: 아카이브 페이지에 답변 본문이 없다(확인 시 Answers 비어 있음). 단위가 "보정에 쓴 길이
     단위 × 픽셀"이고 B 자체는 미터(ROS 관례)로 넣어야 한다는 결론, 왼쪽 0, 시차→깊이 계산이 없다.
   - 이 글이 더할 것: Tx 단위 분해(px × m), fx'로 나누는 이유, 같은 입력에서 Tx·fx·0 오답 수치 대비,
     Z = −Tx/d 검산.
2. https://answers.ros.org/question/329302/ (ROS Answers archive, "Stereo camera standards in ROS", 2019-07-25)
   - 다루는 것: 비표준 드라이버(nerian)가 오른쪽 P의 Tx를 비우거나 이상하게 채우는 문제, "Tx left = 0 and
     Tx right = -fx' * baseline" 관례를 질문자가 인용. 예시 메시지에서 right P의 네 번째 값이 **양수**
     (111.018…)이고 별도 T_left_right x가 0.0987…로 적혀 있다.
   - 빠졌거나 틀린 것: 아카이브에 답변이 없다. 양수 Tx가 왜 문제인지(B가 음수가 됨), 어떻게 검증하는지 정리가 없다.
   - 이 글이 더할 것: 부호 점검 규칙(B = −Tx/fx' < 0이면 좌우 뒤바뀜 또는 비표준 채움을 의심 — 정의에서
     도출한 편집자 추론으로 표시), 라이브러리가 기대하는 입력 형태.
3. https://github.com/dilipkumar25/see3cam/issues/9 ("Stereo Baseline evaluates to 60m…", 2017)
   - 다루는 것: 오른쪽 P의 Tx = −44485.417…, fx' = 739.04…에서 B = 60.19를 미터로 읽어 RTAB-Map 포인트가
     멀리 찍힌 사례. 저장소 소유자가 "60 mm가 맞고 mm 단위"라고 답했다.
   - 빠졌거나 틀린 것: 공식 사양상 ROS 길이 단위는 meter(REP 103)이고 ROS 보정기의 `--square`는 meter라는 점,
     따라서 mm로 보정된 camera_info는 ROS 소비자(깊이·포인트클라우드)에게 1000배 오차를 준다는 해석이 없다.
     "mm가 맞다"는 답은 하드웨어 치수로는 맞지만 ROS 메시지 관례로는 재보정·변환이 필요하다는 점을 놓친다
     (편집자 해석).
   - 이 글이 더할 것: "B가 사양의 1000배면 보정 길이 단위 mm" 진단 규칙과 그 공식 근거.
     (이 사례의 숫자를 본문에 쓰지 말고, 단위 원리는 1차 자료로 설명한다.)
4. https://docs.ros.org/en/jazzy/p/image_pipeline/camera_info.html (image_pipeline 3.2.1 문서 "Camera Info")
   - 다루는 것: P = K'[I|t], 오른쪽 스테레오 카메라의 translational offset t가 외부 위치를 반영, K'은 K와 다를
     수 있음.
   - 빠졌거나 틀린 것: Tx = fx'·t_x라는 성분 수준의 연결, baseline 계산식, 시차→깊이, 왼쪽 0의 이유가 없다.
     "I is the 3x3 rotation matrix … not the identity"라는 문장은 표기(I)와 설명이 엇갈려 입문자에게 혼란을 줄 수 있다.
   - 이 글이 더할 것: P의 각 칸을 행 우선 인덱스(p[0], p[2], p[3])로 짚고 숫자 예제로 투영을 계산.
5. https://dev.to/richard_minsoogo/perception-and-sensor-architecture-ch02-stereo-camera-kr-2k5l
   (DEV Community, STATERA Library Vol.15 Ch.02 Stereo Camera [KR], 2026-11-14 게시)
   - 다루는 것: 한국어로 Z = fB/d, 깊이 오차 ∝ Z²/(fB)·시차 오차, 베이스라인 설계(기구 강성, 열팽창, 동기화) 일반론.
   - 빠졌거나 틀린 것: ROS camera_info의 어디에 B가 있는지, Tx 부호·단위, 왼쪽 0, K vs P, 수치 예제·검산이 없다.
     설계 관점 문서라 받은 메시지에서 값을 꺼내는 독자 질문에 답하지 않는다.
   - 이 글이 더할 것: 메시지 필드 수준의 위치와 계산, 검산된 수치, 실제 1픽셀 차이(정확값 0.2 m / 7 m)와 1차 근사식의
     관계.
6. https://velog.io/@shj4901/Stereo-Depth-Estimation-간단-이해 (velog, 2024-02-10)
   - 다루는 것: 닮음비로 Z = (f/d)·(T/D) 유도(물리 초점거리 f와 픽셀 크기 d를 따로 둠), 템플릿 매칭 개요.
   - 빠졌거나 틀린 것: 변수 정의 목록에서 n_2를 n_1과 같은 "left camera" 설명으로 적어 혼동 소지가 있고, ROS·camera_info·
     픽셀 단위 초점거리 fx'(이미 f/픽셀 크기가 합쳐진 값) 연결이 없다. 예제 숫자가 없다.
   - 이 글이 더할 것: fx'가 이미 "픽셀 단위 초점거리"라 센서 크기가 필요 없다는 점, ROS 값으로 바로 계산하는 절차.

판정: 경쟁 글 6개 모두 이 글의 핵심 결합(위치 p[3] → B = −Tx/fx' → 세 가지 오답 수치 → 투영으로 시차 유도 →
Z = −Tx/d → cx 차이·Python/C++ 차이·DisparityImage → 진단 규칙)을 제공하지 않는다. 더할 것이 있으므로
INSUFFICIENT 사유가 아니다.
