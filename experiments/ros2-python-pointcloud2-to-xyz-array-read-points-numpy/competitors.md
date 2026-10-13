# 경쟁 글 대비 차별점: ros2-python-pointcloud2-to-xyz-array-read-points-numpy

1. Robotics Stack Exchange 질문 23782 (`https://robotics.stackexchange.com/questions/23782/pointcloud2-parse-to-xyz-array-in-ros2-with-python`, 공식 API로 판독. 원 페이지는 runner에서 403이므로 본문 링크 금지)
   - 다루는 것: ROS 2에서 `from sensor_msgs_py import point_cloud2`를 써야 한다는 점, `read_points_list(pc2_msg, field_names=["x","y","z","reflectivity"], skip_nans=True)` → `np.array(...)`.
   - 빠졌거나 틀린 것: `read_points_numpy`를 언급하지 않는다. namedtuple 리스트를 거쳐 다시 배열로 만드는 불필요한 경로다(L186-L187에서 이미 구조화 배열을 리스트로 바꾼 것). `skip_nans`가 `is_dense=False`일 때만 동작한다는 조건이 없다. 섞인 타입 필드를 `np.array`로 묶으면 NumPy가 공통 타입으로 승격한다는 점도 설명하지 않는다. `point_step`·`offset`이 무엇인지 설명하지 않는다.
   - 이 글이 실측으로 더할 것: 같은 Jazzy 이미지에서 `is_dense` True/False별 `skip_nans` 행 수 차이, 바이트 위치 공식과 `read_points_numpy` 값의 일치 여부.
2. Box-Robotics ros2_numpy ([README](https://github.com/Box-Robotics/ros2_numpy/blob/6233f90b80dc636ff2a5f1eae4f856a8e4eb5676/README.md), [point_cloud2.py](https://github.com/Box-Robotics/ros2_numpy/blob/6233f90b80dc636ff2a5f1eae4f856a8e4eb5676/ros2_numpy/point_cloud2.py#L115-L138), 마지막 커밋 2026-10-11)
   - 다루는 것: `numpify(msg)`로 구조화 배열을 만들고 `(height, width)`로 reshape한다. `pointcloud2_to_xyz_array(cloud_msg, remove_nans=True)`가 `np.isfinite`로 x, y, z의 NaN·inf를 `is_dense`와 무관하게 거른다([L250-L271](https://github.com/Box-Robotics/ros2_numpy/blob/6233f90b80dc636ff2a5f1eae4f856a8e4eb5676/ros2_numpy/point_cloud2.py#L250-L271)).
   - 빠졌거나 틀린 것: 별도 패키지 설치가 필요하다(ros-base 기본 미포함). `get_xyz_points` 기본 `dtype=float`이라 float64로 복사된다. docstring은 "3xN matrix"라고 하지만 코드는 `shape + (3,)`, 즉 N×3을 만든다. `np.frombuffer(cloud_msg.data, ...)`로 `row_step`을 쓰지 않는다. 바이트 레이아웃 설명이 없다. 반면 reshape 순서 `(height, width)`는 메시지 정의와 맞는다. sensor_msgs_py와 대조하기 좋은 지점이다.
   - 이 글이 실측으로 더할 것: 표준 `sensor_msgs_py`만으로 같은 결과를 얻는 방법, 그리고 `skip_nans`(isnan, is_dense 의존)와 `isfinite` 마스크의 차이를 inf 포함 합성 클라우드로 보여 주기. ros2_numpy 자체는 실행하지 않는다(문서·코드 판독만).
3. SebastianGrans/ROS2-Point-Cloud-Demo ([pcd_subscriber_node.py](https://github.com/SebastianGrans/ROS2-Point-Cloud-Demo/blob/38eff4a34b309bf08a1e003287891b16de10f814/pcd_demo/pcd_subscriber/pcd_subscriber_node.py#L33-L40), 마지막 커밋 2025-04-19)
   - 다루는 것: ROS 1 `read_points`를 파일 안에 이식해(`struct.unpack_from` 점별 해석, `row_step*v + point_step*u`) `np.array(list(read_points(msg)))`로 변환하고 Open3D로 시각화한다.
   - 빠졌거나 틀린 것: README가 subscriber 데모에 "This seems to be broken!"이라고 직접 적어 두었다. 표준 `sensor_msgs_py`를 쓰지 않는다. 이식본의 `skip_nans`는 ROS 2 표준과 달리 `is_dense`를 보지 않으므로, 표준 함수로 바꿀 때 결과가 달라질 수 있다는 점을 알리지 않는다. 필드를 고르지 않으면 모든 필드가 들어간다.
   - 이 글이 실측으로 더할 것: ROS 1식(row_step 사용, is_dense 무시)과 Jazzy 표준(row_step 미사용, is_dense 의존)의 차이를 줄 번호와 합성 입력의 행 수로 보여 주기.
4. (참고, 공식) docs.ros.org Jazzy `sensor_msgs_py.point_cloud2` API — 검색 상위 공식 문서
   - 다루는 것: 함수 시그니처와 인자 설명, "limited to fields with the same dtype".
   - 빠진 것: `skip_nans`의 `is_dense` 조건, 타입 비교 기준이 `fields[0]`이라는 점, `uvs`가 필터 후 평탄 인덱스라는 점, reshape 순서, `row_step` 미사용.
   - 이 글이 더할 것: 문서 문장과 소스 줄의 차이를 표로 대조하고, 실측으로 어느 쪽이 실제 동작인지 보여 주기.
- 한국어 상위 자료: "ROS2 PointCloud2 파이썬 numpy 변환", "ROS2 포인트클라우드 PointCloud2 파이썬 xyz 추출 sensor_msgs_py", "\"read_points_numpy\" 포인트 클라우드"로 검색했지만 이 질문을 직접 다루는 한국어 글을 찾지 못했다(검색 결과는 영어 Q&A·Open3D 문서 위주). 한국어 경쟁 글이 없다는 것은 수요가 크다는 증거가 아니며, 검색 도구 범위의 관측일 뿐이다.
- 판정: 더할 것이 있다(바이트 위치 공식의 실측 일치, is_dense 대조, Jazzy 타입 검사 기준, reshape·uvs 함정). → READY 유지.
