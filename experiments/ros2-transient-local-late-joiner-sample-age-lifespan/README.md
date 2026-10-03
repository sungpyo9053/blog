# transient local 늦은 구독자가 받는 과거 표본 수 실측

글: https://huntlab.app/ros2-transient-local-late-joiner-sample-age-lifespan/#measured-2026-10-03

10 Hz 발행자, 3초 늦게 붙는 구독자, 양쪽 transient local · reliable · keep last.
`results.jsonl`은 2026-10-03에 설정별 5회씩 실행한 원본 출력이다.

## 재현

```bash
for cfg in "10 0" "10 0.45" "100 0.45"; do
  docker run --rm --network none -v "$PWD":/work ros:jazzy-ros-base \
    bash -c "source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py $cfg"
done
```

인자는 `depth` `발행자 lifespan(초, 0이면 없음)`이다. 측정 환경: ROS 2 Jazzy 공식 이미지, 기본 RMW(Fast DDS), Python 3.12.3, 한 머신·한 프로세스.
