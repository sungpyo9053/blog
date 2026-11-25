# ros2-simulation-time-backward-jump-timer

글: https://huntlab.app/ros2-simulation-time-backward-jump-timer/

`results.json`은 하네스가 ros:jazzy-ros-base 컨테이너(네트워크 없음)에서 5회 실행한 원본 출력과 환경 기록이다.

## 재현

```bash
docker run --rm --network none --cpus 1 --memory 1g -v "$PWD":/work ros@sha256:00b8d47a6e6384a2834e3d01fa87ae767876543baa574f2d64a75c04ea33c698 \
  bash -c "source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py"
```
