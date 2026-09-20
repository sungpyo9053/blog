# Purpose-built educational example

실제 ROS 2를 실행하지 않는 제한된 산술 모델이다. 공식 호환표에 따라 각 정책이 호환되면 1, 호환되지 않으면 0으로 둔다. 전체 연결 플래그는 reliability 플래그 × durability 플래그이며 단위가 없는 0 또는 1이다. reliability는 publisher가 best effort이고 subscriber가 reliable이면 0이며, 그 밖의 표에 제시된 조합은 1이다. durability는 publisher가 volatile이고 subscriber가 transient local이면 0이며, 그 밖의 표에 제시된 조합은 1이다. depth는 keep last에서 보관할 표본 수이고 여기서는 10 또는 100으로만 비교한다. 입력은 두 정책이 모두 맞는 기준 사례, reliability만 틀린 사례, durability만 틀린 사례, 둘 다 틀린 사례, 그리고 depth만 늘린 반례를 포함하도록 골랐다. 독자는 각 식의 결과가 1이면 이 두 정책만 놓고 연결 가능, 0이면 연결 불가로 읽고, 0을 만든 정책을 수정 후보로 표시한다.

기준 사례는 1이지만 어느 한 정책이라도 호환되지 않으면 결과는 0이다. 특히 reliability 불일치 상태에서 depth를 10에서 100으로 늘려도 호환성 플래그는 계속 0이므로, 독자는 자신의 publisher와 subscriber 설정에서 reliability와 durability를 먼저 표로 대조하고 불일치 항목을 하나 기록한 뒤에 queue depth를 검토해야 한다.

이 계산은 reliability와 durability 두 정책만 포함한 교육용 판정 모델이며 실제 DDS 연결이나 메시지 전달률을 측정한 결과가 아니다. deadline·liveliness·lease duration 등 다른 호환 정책, history, middleware의 resource limit, 네트워크 손실, 발견 과정, 토픽 이름과 메시지 형식 오류는 제외한다. 결과 1은 실제 전달·지연·무손실을 보장하지 않고, reliable도 응용 전체의 실시간 성능을 보장하지 않는다. depth 10과 100은 저장 개수 비교용 숫자일 뿐 권장 설정값이 아니다.
