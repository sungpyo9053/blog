# ros2-deadline-qos-average-rate-vs-max-interval

글: https://huntlab.app/ros2-deadline-qos-average-rate-vs-max-interval/

`results.json`은 하네스가 ros:jazzy-ros-base 컨테이너(네트워크 없음)에서 5회 실행한 원본 출력과 환경 기록이다.

## 재현

```bash
docker run --rm --network none -v "$PWD":/work ros:jazzy-ros-base \
  bash -c "source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py"
```
