# Purpose-built educational example

설명용으로 정한 정렬된(organized) 깊이 카메라 클라우드를 쓴다. width 640, height 480이고 필드는 x, y, z(float32, offset 0, 4, 8), point_step은 16바이트다. read_points는 data 버퍼를 width*height개의 점으로 보고, 각 점을 point_step 크기의 구조화 dtype으로 해석한다. 그래서 점 i의 필드는 i*point_step + offset 바이트에서 시작한다. 단위는 개수(점), 바이트, 미터(좌표값)다. NaN 점 40000개라는 수는 is_dense가 False일 때와 True일 때를 비교하려고 고른 가정이다. 라이다 예시는 x, y, z, intensity(float32, 0~12)와 ring(uint16, offset 16)을 가진 point_step 32 레이아웃을 가정했다. 실제 장치에서 잰 값이 아니다.

PointCloud2를 xyz 배열로 바꾸는 일은 바이트 위치 계산으로 풀린다. 점 i의 필드 위치는 i*point_step + offset이다. 점 수는 width*height이고, 빈 바이트까지 포함하면 data 길이는 그 수에 point_step을 곱한 값이다. read_points_numpy(field_names=['x','y','z'], skip_nans=True)는 (N, 3) 배열을 돌려주지만 N이 줄어드는 것은 is_dense가 False일 때뿐이다. 그래서 독자는 받은 클라우드의 is_dense와 실제 NaN 개수를 먼저 확인해야 한다. 타입이 다른 필드가 섞여 있으면 x, y, z만 골라야 한다. 작은 ROS 2 실험은 이렇게 짤 수 있다. create_cloud로 NaN 점을 일부러 넣은 합성 클라우드를 is_dense True와 False 두 가지로 발행하고, 구독 노드에서 read_points_numpy 결과의 행 수를 세어 위 계산과 비교한다.

이 예제는 sensor_msgs_py Jazzy 소스의 동작을 사칙연산으로 따라간 교육 모델이다. 실제 카메라나 라이다 드라이버가 point_step, 필드 순서, is_dense를 어떻게 채우는지는 장치마다 다르며, 여기서는 확인하지 않았다. 변환 속도와 메모리 성능, 빅엔디언 처리, 좌표 프레임 변환(tf2)은 다루지 않는다. 같은 소스의 reshape_organized_cloud는 (width, height) 순서로 reshape하고 uvs 인자는 평탄화된 인덱스로 쓰인다. 이 두 동작은 소스에 적힌 대로만 설명할 수 있고, 다른 배포판에서도 같다고 단정할 수 없다. NaN 40000개와 point_step 32 라이다 레이아웃은 설명용 가정이다.
