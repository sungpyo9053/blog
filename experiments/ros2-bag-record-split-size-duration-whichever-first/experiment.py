#!/usr/bin/env python3
"""ros2 bag record -b(크기)와 -d(시간)를 함께 줄 때 어느 쪽이 먼저 자르는지 실제 녹화로 잰다.

같은 `-b 8000000 -d 6` 설정으로 데이터율이 다른 두 토픽을 각각 녹화한다.
  - high: 200,000 B 페이로드 x 20 Hz (약 4 MB/s)  -> 계산상 크기 기준이 먼저
  - low :   1,000 B 페이로드 x 50 Hz (약 50 kB/s) -> 계산상 시간 기준이 먼저
녹화 전에 /tf_static(transient local)을 한 번만 발행해, 분할된 파일마다 남는지 센다.
저장 플러그인별 -b 하한과 Jazzy CLI의 --repeat-transient-local 유무도 확인한다.
모든 값은 실행 중에 측정해 JSON 줄로 출력한다.
"""
import array
import json
import os
import shutil
import signal
import subprocess
import time

import yaml
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.serialization import serialize_message
from std_msgs.msg import UInt8MultiArray
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster
import rosbag2_py

MAX_BAG_SIZE = 8_000_000   # -b, bytes
MAX_BAG_DURATION = 6       # -d, seconds
SCENARIOS = [
    # name, payload bytes, publish Hz, recording seconds
    ("high", 200_000, 20, 9.0),
    ("low", 1_000, 50, 14.0),
]


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def min_size_check(storage, size):
    """SequentialWriter.open()이 -b 값을 받아들이는지(하한 검사) 확인한다."""
    uri = f"/tmp/min_{storage}_{size}"
    shutil.rmtree(uri, ignore_errors=True)
    writer = rosbag2_py.SequentialWriter()
    storage_options = rosbag2_py.StorageOptions(uri=uri, storage_id=storage)
    storage_options.max_bagfile_size = size
    try:
        writer.open(storage_options, rosbag2_py.ConverterOptions("cdr", "cdr"))
        accepted, error = True, ""
    except Exception as exc:  # rosbag2 raises std::runtime_error -> RuntimeError
        accepted, error = False, str(exc).strip().splitlines()[0][:200]
    del writer
    shutil.rmtree(uri, ignore_errors=True)
    emit({"check": "min_split_size", "storage": storage, "max_bag_size": size,
          "accepted": accepted, "error": error})


def cli_help_check():
    out = subprocess.run(["ros2", "bag", "record", "--help"], capture_output=True, text=True,
                         timeout=30).stdout
    emit({"check": "jazzy_cli_options",
          "has_max_bag_size": "--max-bag-size" in out,
          "has_max_bag_duration": "--max-bag-duration" in out,
          "has_repeat_transient_local": "repeat-transient-local" in out,
          "has_max_bag_files": "--max-bag-files" in out,
          "max_cache_size_default_in_help": "104857600" in out or "100 MiB" in out or "100*1024*1024" in out})


def read_file(path):
    """분할 파일 하나만 열어 토픽별 메시지 수와 첫/마지막 수신 시각을 센다."""
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=path, storage_id="mcap"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    counts, first, last, data_bytes, first_data = {}, None, None, 0, None
    while reader.has_next():
        topic, data, stamp = reader.read_next()[:3]
        counts[topic] = counts.get(topic, 0) + 1
        if topic.endswith("/data"):
            data_bytes += len(data)
            first_data = stamp if first_data is None else min(first_data, stamp)
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
    del reader
    return counts, first, last, data_bytes, first_data


def run_scenario(node, name, payload, hz, record_s):
    topic = f"/{name}/data"
    pub = node.create_publisher(UInt8MultiArray, topic,
                                QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
    msg = UInt8MultiArray()
    msg.data = array.array("B", bytes(payload))
    serialized = len(serialize_message(msg))

    uri = f"/tmp/bag_{name}"
    shutil.rmtree(uri, ignore_errors=True)
    log = open(f"/tmp/record_{name}.log", "w")
    cmd = ["ros2", "bag", "record", "-o", uri, "-s", "mcap",
           "-b", str(MAX_BAG_SIZE), "-d", str(MAX_BAG_DURATION), topic, "/tf_static"]
    started = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    while pub.get_subscription_count() == 0:
        if proc.poll() is not None or time.monotonic() - started > 20:
            raise RuntimeError(f"recorder did not subscribe to {topic}: {open(log.name).read()[-500:]}")
        time.sleep(0.05)
    subscribe_wait = time.monotonic() - started
    time.sleep(0.5)  # recorder가 /tf_static 구독도 마치도록 짧게 기다린다

    period = 1.0 / hz
    t0 = time.monotonic()
    published = 0
    while True:
        now = time.monotonic()
        if now - t0 >= record_s:
            break
        target = t0 + published * period
        if target > now:
            time.sleep(target - now)
        pub.publish(msg)
        published += 1
    elapsed = time.monotonic() - t0
    time.sleep(0.5)
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    log.close()
    node.destroy_publisher(pub)

    rate = serialized * published / elapsed
    t_size = MAX_BAG_SIZE / rate
    emit({"scenario": name, "event": "published", "payload_bytes": payload,
          "serialized_bytes": serialized, "target_hz": hz, "published": published,
          "publish_seconds": round(elapsed, 3), "achieved_hz": round(published / elapsed, 3),
          "data_rate_Bps": round(rate), "recorder_exit_code": proc.returncode,
          "subscribe_wait_s": round(subscribe_wait, 3),
          "B": MAX_BAG_SIZE, "D": MAX_BAG_DURATION, "T_size_s": round(t_size, 3),
          "predicted_first": "size" if t_size < MAX_BAG_DURATION else "duration"})

    with open(os.path.join(uri, "metadata.yaml")) as fh:
        meta = yaml.safe_load(fh)["rosbag2_bagfile_information"]
    files = meta["files"]
    starts = [f["starting_time"]["nanoseconds_since_epoch"] for f in files]
    total_data_msgs = 0
    rows = []
    for index, entry in enumerate(files):
        path = os.path.join(uri, entry["path"])
        size = os.path.getsize(path)
        counts, first, last, data_bytes, first_data = read_file(path)
        total_data_msgs += counts.get(topic, 0)
        closed = index < len(files) - 1  # 마지막 파일은 Ctrl+C로 닫혀 기준에 닿지 않았다
        span = (starts[index + 1] - starts[index]) / 1e9 if closed else None
        row = {"scenario": name, "event": "file", "index": index, "closed_by_split": closed,
               "size_bytes": size, "size_minus_B": size - MAX_BAG_SIZE,
               "data_payload_bytes": data_bytes,
               "data_msgs": counts.get(topic, 0), "tf_static_msgs": counts.get("/tf_static", 0),
               "start_offset_s": round((starts[index] - starts[0]) / 1e9, 3),
               # 파일 시작(첫 메시지) 뒤 첫 데이터 메시지까지: 첫 파일은 /tf_static이 먼저 들어온다
               "first_data_after_file_start_s": round((first_data - starts[index]) / 1e9, 3)
               if first_data is not None else None,
               "meta_duration_s": round(entry["duration"]["nanoseconds"] / 1e9, 3),
               "split_interval_s": round(span, 3) if span is not None else None}
        if closed:
            row["size_reached_B"] = size >= MAX_BAG_SIZE
            row["interval_exceeded_D"] = span > MAX_BAG_DURATION
        rows.append(row)
        emit(row)

    closed_rows = [r for r in rows if r["closed_by_split"]]
    intervals = [r["split_interval_s"] for r in closed_rows]
    by_size = sum(1 for r in closed_rows if r["size_reached_B"] and not r["interval_exceeded_D"])
    by_time = sum(1 for r in closed_rows if r["interval_exceeded_D"] and not r["size_reached_B"])
    observed = "size" if by_size and not by_time else "duration" if by_time and not by_size else "mixed"
    emit({"scenario": name, "event": "summary", "files": len(files),
          "closed_files": len(closed_rows),
          "mean_split_interval_s": round(sum(intervals) / len(intervals), 3) if intervals else None,
          "min_split_interval_s": min(intervals) if intervals else None,
          "max_split_interval_s": max(intervals) if intervals else None,
          "closed_split_by_size": by_size, "closed_split_by_duration": by_time,
          "observed_first": observed, "predicted_first": "size" if t_size < MAX_BAG_DURATION else "duration",
          "max_size_minus_B": max((r["size_minus_B"] for r in closed_rows), default=None),
          "recorded_data_msgs": total_data_msgs, "published": published,
          "files_with_tf_static": [r["index"] for r in rows if r["tf_static_msgs"] > 0]})
    shutil.rmtree(uri, ignore_errors=True)


def main():
    wall = time.monotonic()
    for storage, size in (("mcap", 1023), ("mcap", 1024), ("sqlite3", 86015), ("sqlite3", 86016)):
        min_size_check(storage, size)
    cli_help_check()

    rclpy.init()
    node = rclpy.create_node("split_experiment_pub")
    tf = TransformStamped()
    tf.header.stamp = node.get_clock().now().to_msg()
    tf.header.frame_id = "base_link"
    tf.child_frame_id = "camera_link"
    tf.transform.translation.x = 0.1
    tf.transform.rotation.w = 1.0
    broadcaster = StaticTransformBroadcaster(node)  # QoS: transient local, 1번만 발행
    broadcaster.sendTransform(tf)
    for name, payload, hz, record_s in SCENARIOS:
        run_scenario(node, name, payload, hz, record_s)
    node.destroy_node()
    rclpy.shutdown()
    emit({"event": "done", "total_seconds": round(time.monotonic() - wall, 2)})


if __name__ == "__main__":
    main()
