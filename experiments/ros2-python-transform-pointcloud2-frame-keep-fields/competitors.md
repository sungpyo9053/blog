# 경쟁 글 대비 차별점: ros2-python-transform-pointcloud2-frame-keep-fields

1. https://robotics.stackexchange.com/questions/104522/transform-pointcloud-message (2023-10-05, 조회 799회, Stack Exchange API로 본문·답변 확인)
   - 다루는 것: ROS 2 Foxy C++에서 `sensor_msgs::msg::PointCloud`를 받아 camera_frame으로 바꾸려는 질문. 채택 답변은 콜백을 PointCloud2로 바꾸고 `pcl_conversions::toPCL` 후 `pcl_ros::transformPointCloud`를 쓰라고 한다.
   - 빠진 것: Python 경로, 변환 후 다른 필드·`point_step`·`frame_id` 확인, 결과 메시지가 올바른지 판정하는 방법.
   - 이 글이 실측으로 더할 것: Python(sensor_msgs_py·tf2_sensor_msgs)에서 재생성 방식별 point_step·len(data)·필드·frame_id를 같은 합성 클라우드로 측정.
2. https://robotics.stackexchange.com/questions/23937/ros2-transform-pointcloud2-data-from-one-frame-to-another-in-python (2022-10-24, 조회 1588회)
   - 다루는 것: ROS 2 Python에서 `tf2_sensor_msgs.tf2_sensor_msgs.do_transform_cloud`를 못 찾는다는 질문. 유일한 답(2023-09-19)은 geometry2 PR #507로 Iron부터 `from tf2_sensor_msgs import do_transform_cloud`가 가능하니 업그레이드하라고 한다.
   - 빠졌거나 낡은 것: Humble에도 #507 백포트(geometry2 PR #778, 2025-04-12 병합)가 들어갔다는 사실, Jazzy에서 끝 패딩 클라우드가 실패하는 문제(#305), 결과 메시지 검증 방법.
   - 이 글이 실측으로 더할 것: Jazzy 이미지에서 `do_transform_cloud`의 frame_id·필드 유지와 패딩 클라우드 실패 여부, `point_step` 명시 재생성과의 비교.
3. https://robotics.stackexchange.com/questions/29622/how-to-transform-pointcloud2-with-tf (ROS Answers 이전 글, 2011~2020 답변)
   - 다루는 것: ROS 1에서 PointCloud2를 PointCloud로 바꿔 변환하던 우회, `pcl_ros` 추천, peci1 답변의 `do_transform_cloud`와 "x,y,z 채널만 변환하므로 normal·viewpoint는 직접 변환해야 한다"는 경고, 당시 Python 구현 버그(read_cloud) 댓글.
   - 빠진 것: ROS 2의 sensor_msgs_py 구조(NumPy dtype, point_step 재계산), frame_id 처리, 바이트 수 판정.
   - 이 글이 실측으로 더할 것: normal 경고는 Jazzy 소스 docstring으로 재확인하고, 바이트·필드 판정을 측정값으로 보탬.
4. https://github.com/lucasw/transform_point_cloud/blob/master/scripts/transform_point_cloud_py.py
   - 다루는 것: ROS 1 rospy 노드. `lookup_transform(target, source, stamp+offset, timeout)` 후 `do_transform_cloud` 결과를 그대로 publish.
   - 빠진 것: ROS 2 API, 결과 필드·point_step 검사, 패딩 조건.
   - 이 글이 실측으로 더할 것: ROS 2 Jazzy에서 같은 호출 순서가 어떤 메시지를 만드는지 측정하고, 발행 전 검사 코드를 제시.
5. https://limhyungtae.github.io/2021/09/10/pcl-tutorial-02-toros-fromros-msg/ (한국어, 2021-09-10)
   - 다루는 것: C++에서 PointCloud2↔PCL 변환(`fromROSMsg`/`toROSMsg`), LaserScan→PointCloud2, 예제에서 `cloudmsg.header.frame_id = "map"` 지정.
   - 빠진 것: tf 변환, Python, point_step·필드 보존.
   - 이 글이 더할 것: 한국어로 Python 변환 노드의 필드·frame_id·바이트 판정을 설명. 한국어 검색(두 가지 질의)에서 이 질문을 직접 다룬 한국어 글은 찾지 못했다.

참고: 위 Stack Exchange URL 세 개는 이 runner의 `source_digest` 재확인에서 HTTP 오류(접근 차단)로 실패했다. 내용은 Stack Exchange 공개 API로 읽었다. 공개 본문의 근거 링크로 쓰지 말고, 필요하면 질문 제목만 언급한다.
