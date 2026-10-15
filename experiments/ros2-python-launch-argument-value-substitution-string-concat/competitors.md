# 경쟁 글 대비 차별점: ros2-python-launch-argument-value-substitution-string-concat

1. https://robotics.stackexchange.com/questions/104340/getting-the-value-of-launchargument-inside-python-launch-file (원 질문, 2023-09-26, 채택 답 1개 + 추가 답 1개; Stack Exchange API로 본문 확인)
   - 다루는 것: `DeclareLaunchArgument` 값을 `generate_launch_description()` 안에서 문자열로 얻고 싶다는 질문. 채택 답은 `OpaqueFunction(function=launch_setup)` 안에서 `LaunchConfiguration('config').perform(context)`. 두 번째 답(점수 0)은 `sys.argv[4:]`를 argparse로 직접 파싱하는 우회.
   - 빠졌거나 틀린 것: 왜 그 시점에 값이 없는지(평가 시점) 설명이 없고, 숫자 계산·조건 분기·리스트 연결은 다루지 않는다. argparse 우회는 `sys.argv` 위치에 기대는 비공식 방법이며 `IncludeLaunchDescription`으로 포함될 때의 인자 전달과 맞지 않을 수 있다(이 부분은 직접 검증하지 않았으므로 본문에서는 "공식 API가 아니다" 수준으로만 말한다).
   - 이 글이 더할 것: 평가 시점을 공식 문서·소스 줄로 설명하고, 리스트 연결로 '2'+'5'가 25(Node 파라미터에선 정수 25)가 되는 경로와 산술/조건/임의 로직별 선택 기준을 하네스 실측과 함께 제시한다.
2. https://robotics.stackexchange.com/questions/102325/use-value-of-launchconfiguration-in-ros2-launch-file-like-a-variable (2022-08-30, 조회 994회, 채택 답 1개)
   - 다루는 것: 두 LaunchConfiguration 문자열을 더하고 싶다는 질문, `OpaqueFunction`+`context.perform_substitution()` 답.
   - 빠졌거나 틀린 것: 채택 답 코드가 그대로는 실행되지 않는다. 함수 인자는 `arg1`인데 본문은 정의되지 않은 `namespace`를 쓰고(2023-05-12 댓글도 지적), `OpaqueFunction` 함수가 entity *리스트*(또는 None)를 돌려줘야 하는데(opaque_function.py 시그니처 `Optional[List[LaunchDescriptionEntity]]`) `Node` 하나를 돌려준다. 숫자 연산·연결 규칙 설명 없음.
   - 이 글이 더할 것: 실행 가능한 최소 `OpaqueFunction` 예제(리스트 반환)와, 문자열 연결이 목적이면 OpaqueFunction 없이 리스트만으로 충분하다는 구분을 소스 근거로 제시한다.
3. https://github.com/MetroRobots/rosetta_launch (ROS 1/2 launch 대조 가이드, BSD-3)
   - 다루는 것: `DeclareLaunchArgument`/`LaunchConfiguration` 기본 사용, "lists of strings/substitutions are concatenated", `PythonExpression(['2.*3.1415*', LaunchConfiguration('radius')])` 산술 예.
   - 빠졌거나 틀린 것: 연결 규칙을 한 줄로 언급하지만, 숫자처럼 보이는 두 인자를 연결하면 무엇이 되는지, Node 파라미터에서 YAML로 타입이 정해지는 지점, `PythonExpression`이 eval 전에 연결한다는 점, `IfCondition`의 허용 문자열은 다루지 않는다.
   - 이 글이 더할 것: "연결 → (PythonExpression이면 eval) → (Node 파라미터면 YAML)" 3단계 변환을 '2','5' 예제로 끝까지 계산하고 각 단계를 소스 줄과 하네스 출력으로 확인한다.
4. https://github.com/chargerKong/learning_ros2_launch_by_example/blob/main/docs/How%20to%20use%20pythonexpression.md (중국어권 예제 저장소, 작성일 미표시)
   - 다루는 것: `PythonExpression(["'test_name1' if ", num, "==2 else 'test_name2'"])`와 `IfCondition` 조합, 문자열은 따옴표로 감싸야 한다는 주의.
   - 빠졌거나 틀린 것: 따옴표가 왜 필요한지(연결된 문자열이 Python 소스로 eval되기 때문)와, 연산자를 빼면 숫자가 이어 붙는다는 함정은 설명하지 않는다. 작성일이 없어 버전 적합성을 판단할 수 없다.
   - 이 글이 더할 것: `PythonExpression`이 "문자열을 만든 뒤 eval"한다는 소스 근거로 따옴표·연산자 규칙을 한 원리로 묶어 설명한다.
5. https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Substitutions.html (공식 튜토리얼, Jazzy)
   - 다루는 것: substitution 정의, turtlesim 예제, `IfCondition(PythonExpression([...' == 200'...]))`.
   - 빠졌거나 틀린 것: Jazzy 판에는 Rolling 판의 "리스트는 문자열 하나로 연결된다" 팁이 없고, 인자 값을 Python 변수로 꺼내는 방법(`OpaqueFunction`)과 숫자 인자의 연결 함정은 다루지 않는다. 튜토리얼은 turtlesim GUI 실행을 전제로 한다.
   - 이 글이 더할 것: GUI 없이 네트워크 차단 컨테이너에서 재현 가능한 최소 실험으로 연결/산술/조건 결과를 실측 로그로 보여 준다.

판정: 경쟁 글 5개 대비 소스 근거 + 3단계 타입 변환 계산 + 하네스 실측이라는 추가 가치가 있으므로 INSUFFICIENT 아님.
