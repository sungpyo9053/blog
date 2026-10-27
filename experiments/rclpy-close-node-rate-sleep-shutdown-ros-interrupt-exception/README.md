# rclpy-close-node-rate-sleep-shutdown-ros-interrupt-exception

글: https://huntlab.app/rclpy-close-node-rate-sleep-shutdown-ros-interrupt-exception/

`results.json`은 하네스가 ros:jazzy-ros-base 컨테이너(네트워크 없음)에서 5회 실행한 원본 출력과 환경 기록이다.

## 재현

```bash
docker run --rm --network none --cpus 1 --memory 1g -v "$PWD":/work ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617 \
  bash -c "source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py"
```
