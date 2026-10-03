# colcon-build-executor-sequential-memory-budget

글: https://huntlab.app/colcon-build-executor-sequential-memory-budget/

`results.json`은 하네스가 ros:jazzy-ros-base 컨테이너(네트워크 없음)에서 5회 실행한 원본 출력과 환경 기록이다.

## 재현

```bash
docker run --rm --network none --cpus 1 --memory 1g -v "$PWD":/work ros@sha256:066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca \
  bash -c "source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py"
```
