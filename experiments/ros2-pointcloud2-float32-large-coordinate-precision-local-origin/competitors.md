# 경쟁 글 대비 차별점: ros2-pointcloud2-float32-large-coordinate-precision-local-origin

같은 질문(큰 좌표의 float32 정밀도, PointCloud2·UTM·원점 이동)으로 검색되는 문서를 직접 열어 읽었다(2026-11-08).

1. [ros-visualization/rviz #502 "Large transforms lead to unstable visualizations"](https://github.com/ros-visualization/rviz/issues/502) (영어, 2012 보고)
   - 다루는 것: UTM(약 590만 m) 좌표의 PointCloud2를 RViz에서 볼 때 떨림. 관리자 설명은 RViz(Ogre)가 단정밀도로 그리고 TF는 배정밀도라는 것, 해법은 대상 근처(약 1 km 안)에 중간 프레임을 발행하는 것.
   - 빠진 것: 간격 수치 계산 없음. PointCloud2 필드 자료형 자체(FLOAT32 저장 시점의 손실)는 다루지 않는다. 화면 렌더링 문제와 메시지 저장 문제를 구분하지 않는다.
   - 이 글이 더할 것: 렌더링 이전, `create_cloud`에서 메시지 바이트에 저장되는 순간 손실이 생기는 코드 위치와 간격 계산, 원점 빼기 순서, 왕복 테스트(하네스 실측).
2. [PointCloudLibrary/pcl #4756 "Is all pcl point type's x y z base on float?"](https://github.com/PointCloudLibrary/pcl/issues/4756) (영어, 2021 개설·2024 종료)
   - 다루는 것: 3,375,876.5445가 3,375,876.5로 바뀐다는 사용자 보고, 관리자는 PCL 기본 점 타입 xyz가 float이며 오프셋 빼기·사용자 정의 double 타입·PDAL을 제안.
   - 빠진 것: 왜 0.5 단위가 아니라 특정 간격이 되는지 계산 없음(참고: 3,375,876은 [2^21, 2^22) 구간이라 간격 0.25 m가 되어야 하며, 보고된 .5는 0.25의 배수라 이 규칙과 모순되지 않는다 — 손계산). ROS 2 메시지 경로와 빼기 순서는 다루지 않는다.
   - 이 글이 더할 것: 구간 규칙으로 보고 수치를 독자가 스스로 설명하게 하고, ROS 2 Python 경로로 옮긴다.
3. [Godot 엔진 문서(한국어) "큰 세계 좌표"](https://docs.godotengine.org/ko/4.x/tutorials/physics/large_world_coordinates.html) (한국어 번역 공식 문서)
   - 다루는 것: 원점 거리 구간별 단정밀도 정밀도 표, 배정밀도 빌드와 원점 이동(origin shifting) 대안.
   - 빠진 것: 게임 엔진 범위라 ROS·PointCloud2·지도 좌표(UTM) 단위는 없다. 표의 구간이 게임 거리(수천~수십만) 중심이라 400만 m대 지도 좌표는 직접 다루지 않는다.
   - 이 글이 더할 것: 수백만 m 지도 좌표 구간(2^21~2^23)의 간격, ROS 2 메시지 직렬화 지점, REP-103 권고와의 연결.
4. [warhammer50K/WebPointCloud README](https://github.com/warhammer50K/WebPointCloud) (영어, 웹 포인트 클라우드 뷰어)
   - 다루는 것: UTM 좌표를 float32로 저장하면 계단 현상이 생기므로 float64로 읽고 경계 상자 중심을 float64에서 뺀 뒤 float32로 바꾸는 절차.
   - 빠지거나 과장된 것: "절대 크기와 관계없이 sub-millimeter 정밀도"라고 쓰지만, 중심을 뺀 뒤 남는 정밀도는 클라우드가 퍼진 범위에 달려 있다(예: 중심에서 100 km 떨어진 점은 위 손계산처럼 약 7.8 mm 간격). 간격 계산은 없다.
   - 이 글이 더할 것: 원점 이동 후에도 남는 간격을 거리로 계산하는 방법, "빼기는 float64에서"라는 순서를 같은 수로 대비.
5. 참고(경쟁이 아닌 근거 문서): [py4dgeo FAQ](https://github.com/3dgeo-heidelberg/py4dgeo/blob/main/doc/faq.rst)는 단정밀도 저장에는 신중한 좌표 이동이 필요하다는 이유로 전역 좌표를 double로 저장하는 선택을 설명한다. 간격 수치는 없다. "FLOAT64로 저장"이라는 대안의 실제 사례로만 짧게 쓸 수 있다.

판정: 위 문서들은 "큰 좌표 + float32 = 정밀도 손실 → 오프셋/원점 이동"이라는 결론을 공유하지만, ROS 2 Python(`sensor_msgs_py`)에서 손실이 생기는 정확한 코드 지점, 독자가 직접 하는 구간 계산, 빼기 순서의 숫자 대비, 왕복 테스트를 함께 제공하지 않는다. 이 글이 실측(하네스 results.json)과 검산으로 더할 것이 있으므로 INSUFFICIENT가 아니다.
