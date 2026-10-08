# 경쟁 글 대비 차별점: ros2-nested-message-array-vs-primitive-arrays-serialization

같은 질문(“ROS 2 커스텀 메시지 배열/중첩 메시지 성능”, “rclpy publish slow large array”, “ROS2 커스텀 메시지 배열”)으로 검색되는 상위 자료를 직접 열어 읽었다(2026-10-08).

1. https://github.com/ros2/rmw_cyclonedds/issues/346 (영어, 2021-10-14 개설, closed)
   - 다루는 것: `TestElement`(uint16 두 개, timestamp, bool) 5000개 이상 배열을 담은 커스텀 메시지를 1000 msg/s로 발행하려 했으나 발행·수신 주기가 크게 떨어진 보고. Cyclone DDS 협업자(eboasson)가 "`ros2 topic hz`가 데이터를 Python으로 복사하느라 시간의 97%를 쓴다"고 분석했다. 이후 "array of non-primitive types가 Python에서 객체 리스트로 매핑돼 객체 생성·삭제 비용이 든다"는 가설도 냈다. 기여자(clalancette)는 Python 직렬화가 타입에 따라 아직 느리다고 답했다.
   - 빠졌거나 틀린 것: 같은 값을 기본형 배열로 나눈 비교가 없다. 원인 코드 위치(요소별 `__convert_from_py`)가 명시되지 않았다. hz 분석은 2021년 당시 hz의 동작 기준이다. Jazzy hz는 `--filter`가 없으면 raw 구독이라 같은 원인이 그대로 적용된다고 볼 수 없다. 직렬화 크기 차이(정렬 패딩)는 언급이 없다.
   - 이 글이 실측으로 더할 것: Jazzy·rmw_fastrtps_cpp·고정 이미지에서 같은 N·같은 값으로 `Foo[]`와 `uint64[]+uint32[]`의 `publish()` 시간과 `serialize_message` 길이를 나란히 잰다. 수신 측은 raw 구독과 역직렬화 구독을 나눠 수신 개수/주기를 잰다.
2. https://github.com/ros2/rclpy/issues/836 (영어, 2021-10-13 개설, open/backlog)
   - 다루는 것: `Quadrilateral`(Point3D 4개) 2000개 배열을 담은 `Path` 메시지에서 Python 노드 지연이 C++ 노드보다 약 100배 크다는 Foxy 보고.
   - 빠졌거나 틀린 것: 해결책·원인 분석이 이슈 본문에 없다. 구조를 기본형 배열로 바꿨을 때의 비교가 없다. Foxy 기준이라 Jazzy 상태를 알 수 없다.
   - 이 글이 실측으로 더할 것: Jazzy rclpy에서 구조만 바꾼(값·N·주기 동일) 대조 실험. Python 객체 생성 비용(메시지 구성 시간)과 `publish()` 호출 시간을 분리해 기록한다.
3. https://github.com/ros2/rosidl_python/issues/192 (영어, 2023-01-31 개설, open)
   - 다루는 것: 100개 중첩 요소를 가진 `TestArrayComplex`의 Python 역직렬화를 C 확장 기반 클래스로 바꾸면 빨라진다는 제안과 Galactic 벤치마크.
   - 빠졌거나 틀린 것: 수신(역직렬화) 쪽 제안이며 머지되지 않았다. 발행 `publish()` 경로나 사용자가 지금 할 수 있는 메시지 구조 변경은 다루지 않는다.
   - 이 글이 실측으로 더할 것: 현재 배포된 Jazzy 코드 그대로에서 사용자가 메시지 정의만 바꿨을 때의 발행·수신 차이.
4. https://velog.io/@717lumos/ROS-%EC%BB%A4%EC%8A%A4%ED%85%80-%EB%A9%94%EC%8B%9C%EC%A7%80custom-msg-%EB%A7%8C%EB%93%A4%EA%B8%B02 (한국어, 2022-01-13)
   - 다루는 것: ROS 1에서 `Coordinate[] location`처럼 커스텀 메시지 배열을 정의·발행·구독하는 절차.
   - 빠졌거나 틀린 것: ROS 1 전용. 직렬화 비용, 기본형 배열 대안, ROS 2 DDS tuning 경고를 다루지 않는다. ROS 1에서 ROS 2로 그대로 옮길 때 성능이 떨어질 수 있다는 공식 경고(문서 L69)와 연결되지 않는다.
   - 이 글이 실측으로 더할 것: 같은 "커스텀 메시지 배열" 패턴을 ROS 2 Jazzy에서 기본형 배열 구조와 비교한 측정과 판단 기준.
5. https://refstop.github.io/ros2-custom-msgsrv.html (한국어, 2021-01-26)
   - 다루는 것: ROS 2(Dashing/Eloquent 이후)에서 `int64 num` 같은 기본형 필드의 `.msg`/`.srv` 패키지 만들기.
   - 빠졌거나 틀린 것: 배열·중첩 메시지·성능을 다루지 않는다. 배포판이 오래됐다.
   - 이 글이 실측으로 더할 것: 문서 예시 그대로의 `Foo`/`FooArray`/`FooSplit` 패키지를 Jazzy에서 빌드해(하네스 조건의 `/tmp` noexec 함정 포함) 측정까지 잇는 재현 경로.

참고로 공식 [DDS tuning 문서](https://docs.ros.org/en/jazzy/How-To-Guides/DDS-tuning.html) 자체도 원인을 한 문단으로만 설명하고 수치·언어별 차이를 주지 않는다. 이 글은 그 문단을 코드 위치와 측정으로 보강하는 역할이다.
