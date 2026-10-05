# 경쟁 글 대비 차별점: ros2-wifi-ip-fragment-buffer-ipfrag-time-budget

한국어 상위 글은 "ROS2 와이파이 ipfrag_high_thresh", "ROS2 DDS 튜닝 ipfrag_time 와이파이" 등으로 검색했으나 이 주제를 직접 다룬 한국어 글을 찾지 못했다(검색 결과에 영어 문서만 노출). 영어 상위 글을 직접 열어 읽었다(2026-10-05).

1. https://docs.ros.org/en/rolling/Developer-Tools/Build/DDS-tuning.html (ROS 2 공식)
   - 다루는 것: 현상, best-effort, ipfrag_time=3, ipfrag_high_thresh=128MB, "모든 패킷이 조각 하나를 잃으면 상당히 커야 한다"는 정성적 경고.
   - 빠졌거나 틀린 것: 기본값 256KB는 Linux 3.8 이하 값(현재 4 MiB). 메시지 크기·주기와의 계산 없음. 효과 확인 방법 없음.
   - 이 글이 더할 것: 커널 소스·커밋 대조로 기본값 정정, truesize 보정 계산, 30초 vs 3초 예산 비교, Reasm 카운터 측정 계획.
2. https://breq.dev/2024/05/17/dds/ (Brooke Chalmers, 2024-05-17)
   - 다루는 것: DDS/QoS 전반, ipfrag_time 3초 권장, ipfrag_high_thresh "By default it's 256 KiB … up to 128 MB", rmem_max 4 MiB~2 GiB, 메시지 오버헤드 예(138 bytes).
   - 빠졌거나 틀린 것: 256 KiB 기본값을 그대로 반복(현재 커널과 불일치). 크기·주기 계산 없음. 커널 버전 언급 없음.
   - 이 글이 더할 것: 위와 동일 + 원인 분기(작은 메시지도 안 되면 discovery).
3. https://docs.stereolabs.com/docs/integrations/ros-2/dds-and-network-tuning (Stereolabs ZED 문서, 날짜 표시 없음)
   - 다루는 것: ipfrag_time 30→3, ipfrag_high_thresh "Default value: 4194304 B (4 MB)" → 128 MB, rmem_max 208 KiB → 2 GiB, 영구 설정.
   - 빠졌거나 틀린 것: 기본값 4MB는 맞지만 ROS 2 문서의 256KB와 왜 다른지 설명 없음. 128MB가 왜 필요한지 계산 없음. 측정 없음.
   - 이 글이 더할 것: 두 기본값 차이의 출처(2013 커밋), 128MB가 30초 대기에선 부족하고 3초에선 충분한 이유를 수치로.
4. https://docs.autoware.org/main/installation/additional-settings-for-developers/network-configuration/dds-settings/ (Autoware 문서)
   - 다루는 것: ipfrag_time 3("default is 30 s"), ipfrag_high_thresh 134217728("default is 256 KiB"), rmem_max 2 GiB("default is 208 KiB"), Cyclone DDS 권장.
   - 빠졌거나 틀린 것: 256 KiB 기본값 반복. 근거 계산 없음. Wi-Fi 언급 없음.
   - 이 글이 더할 것: 동일.
- 보조로 확인한 사례(경쟁 글 아님): https://github.com/ros2/ros2/issues/1544 (2024-04-19, Humble·Fast-RTPS, 약 15 MB 이미지 2 fps, 사용자가 `ipfrag_time=1`, `ipfrag_high_thresh=10737418240` 적용, 미해결). 실제 사용자가 극단값을 쓰는 사례이나 결과 근거가 없어 본문 근거로 쓰지 않는다. https://discourse.openrobotics.org/t/ros-2-and-large-data-transfer-on-lossy-networks/36598 (eProsima, 2024-03-12)는 RTPS 조각·TCP 전환을 다루며 IP 조각 sysctl은 다루지 않는다.
- 판정: 이 글은 실측을 더하지 않는다(not_directly_tested). 대신 경쟁 글 4개가 모두 놓친 기본값 불일치의 출처 대조와, 문서의 정성적 경고를 크기·주기로 수치화한 계산·측정 계획을 더한다. foundation_concept 계약상 고유 가치로 충분하다고 판단한다.
