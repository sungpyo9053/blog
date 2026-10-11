# 경쟁 글 대비 차별점: rgbd-camera-pixel-depth-to-xyz-camera-info-k

모두 2026-10-11에 원문을 직접 열어 확인했다. Medium의 "Converting 2D image coordinates to 3D coordinates using ROS + Intel Realsense D435/Kinect"(검색 상위)는 HTTP 403으로 본문을 읽지 못해 비교 대상에서 제외했다.

1. https://refstop.github.io/realsense2.html (한국어, Refstop, 2020-11-03 "Camera_calibration(1) 내부 파라미터의 구성요소")
   - 다루는 것: fx, fy(픽셀 단위 초점거리), cx, cy(주점), skew와 투영식 `x = fx·X/Z + cx` 유도 소개.
   - 빠졌거나 틀린 것: 깊이로 거꾸로 푸는 식, ROS CameraInfo 인덱스, 깊이 단위, optical 축, 검산이 없다. 초점거리 예시 문장에서 "초점거리가 500mm면 … 50mm"로 단위가 섞여 있다(픽셀 500배를 말하려던 것으로 보인다).
   - 이 글이 실측으로 더할 것: ROS 2 Jazzy 환경에서 CameraInfo 메시지를 실제로 만들어 K 인덱스로 fx, cx를 꺼내고, 역투영 → 재투영 잔차를 실행 중에 재서 보여 준다.
2. https://ralpioxxcs.github.io/post/etc/camera_calibration_2/ (한국어, ralpioxxcs, 2022-04-05 "카메라 캘리브레이션 - 좌표변환")
   - 다루는 것: 정규화 좌표 ↔ 영상 좌표 변환식 `x_norm = (x_img − cx)/fx`, `s[u v 1]ᵀ = K[R|t][X Y Z 1]ᵀ`, mm 초점거리 → 픽셀 초점거리 환산 예.
   - 빠졌거나 틀린 것: 정규화 좌표에 깊이를 곱해 미터 좌표를 얻는 단계, 스케일 s가 곧 Z라는 연결, 깊이 영상 단위(16UC1 mm / 32FC1 m), 깊이와 직선 거리의 차이, K와 P의 차이가 없다.
   - 이 글이 실측으로 더할 것: 같은 픽셀에서 정답·주점 누락·mm 깊이·단위 광선 방식이 만드는 좌표와 재투영 잔차, Z 차이를 하네스 실행값으로 나란히 보여 준다.
3. https://dev.realsenseai.com/docs/projection-texture-mapping-and-occlusion-with-intel-realsense-depth-cameras/ (영어, RealSense 공식 문서)
   - 다루는 것: 픽셀 좌표 원점, 3D 좌표 m·x 오른쪽·y 아래·z 앞, 내부 파라미터(ppx, ppy, fx, fy, 왜곡 모델), "Depth는 Z 성분이고 거리는 √(x²+y²+z²)", `rs2_deproject_pixel_to_point`.
   - 빠졌거나 틀린 것: RealSense SDK 구조체 기준이라 ROS CameraInfo의 K/P 인덱스, 16UC1 토픽 단위, K와 P 중 무엇을 쓰는지가 연결되지 않는다. 틀린 결과를 판정하는 검산 방법도 없다.
   - 이 글이 실측으로 더할 것: "깊이 = Z"를 어겼을 때(단위 광선 × 깊이) 영상 중심과 모서리에서 Z가 얼마나 짧아지는지와, 그 오류가 재투영 검산을 통과한다는 사실을 실행값으로 보인다.
4. https://robotics.stackexchange.com/questions/8400/using-an-rgb-depth-camera-to-locate-x-y-z-coordinates-of-a-ball (영어, 출발 질문. Stack Exchange API로 질문·답변 원문 확인. 현재 runner에서 웹 페이지는 HTTP 403이므로 본문 링크 금지)
   - 다루는 것: 채택 답변이 정합(registration)의 중요성, 서브픽셀 보간, 카메라 행렬 사용, RGB 왜곡 고려를 언급. 다른 답변은 PCL 사용을 권함.
   - 빠졌거나 틀린 것: 식이 없고, 질문의 "DPI로 변환" 오해(픽셀→미터 비율이 거리에 따라 변함)를 직접 바로잡지 않는다. 깊이 단위·검산이 없다.
   - 이 글이 실측으로 더할 것: 1픽셀 오차가 깊이에 비례해 미터 오차로 커지는 값을 하네스에서 여러 Z로 재서 보여 준다.
5. https://robotics.stackexchange.com/questions/52783/converting-kinect-depth-image-to-real-world-coordinate (영어, ROS Answers 이관 글, 2013. API로 확인. runner 403, 본문 링크 금지)
   - 다루는 것: 질문자가 `x = z`, `y = −(u − ox)·z/fx`, `z = −(v − oy)·z/fy`처럼 몸체 규약으로 축을 바꾼 식을 쓰며 "Z가 진짜 Z가 아니라 카메라 중심까지 거리 아닌가" 묻는다. 채택 답변은 드라이버가 image_raw(uint16 mm), image(float m), image_rect, points를 이미 제공한다고만 답한다.
   - 빠졌거나 틀린 것: 질문자의 의문(깊이 = Z인가 거리인가)에 대한 직접 답과 근거 문서가 없다.
   - 이 글이 실측으로 더할 것: REP-118과 RealSense 문서로 "깊이는 Z"를 확정하고, 거리로 오해했을 때의 차이를 실행값으로 보인다.
6. https://robotics.stackexchange.com/questions/61789/how-to-retrieve-xyz-co-ordinates-from-a-raw-depth-image (영어, ROS Answers 이관 글, 2014. API로 확인. runner 403, 본문 링크 금지)
   - 다루는 것: 채택 답변은 외부 코드 링크만 주고, 댓글에서 RGB 카메라와 IR(깊이) 카메라의 내부 파라미터가 다르다고 지적한다.
   - 빠졌거나 틀린 것: 식, 단위, 어떤 camera_info를 짝지어야 하는지(정합 토픽과 그 camera_info)가 정리되지 않았다.
   - 이 글이 실측으로 더할 것: 짝이 맞지 않는 K(다른 fx, cx)를 넣었을 때 재투영 잔차가 어떻게 드러나는지 하네스에서 잰다.

공통 차별점: 경쟁 글 어느 것도 "재투영 검산이 거리(스케일) 오류는 잡지 못한다"는 점을 다루지 않는다. 이 글은 그 판정 규칙을 ROS 2 Jazzy 컨테이너 실행값으로 보여 주는 것이 핵심 고유 가치다.
