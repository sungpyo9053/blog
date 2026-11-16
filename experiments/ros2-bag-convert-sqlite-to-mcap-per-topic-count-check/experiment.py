#!/usr/bin/env python3
"""sqlite3 bag -> MCAP: ros2 bag convert 전후 토픽별 Count 비교 실험 (ROS 2 Jazzy).

1) rosbag2_py SequentialWriter로 sqlite3 입력 bag을 만든다(60 s 구간, 토픽 4개, 숨김 토픽 1개 포함).
2) 같은 입력에 YAML만 바꿔 `ros2 bag convert`를 실행한다.
3) 각 bag에 `ros2 bag info`를 실행해 Storage id, Messages, 토픽별 Count를 파싱하고,
   SequentialReader로 메시지를 끝까지 읽어 토픽별 개수를 직접 센다.
4) 총합 비교 판정과 토픽별 비교 판정을 함께 출력한다.
모든 숫자는 실행 중 측정값이며 JSON 한 줄씩 stdout으로 낸다.
"""
import json
import os
import re
import subprocess
import tempfile
import time

import rosbag2_py
from rclpy.serialization import serialize_message
from builtin_interfaces.msg import Time
from sensor_msgs.msg import Image, Imu, LaserScan
from std_msgs.msg import String

DURATION_S = 60
# (토픽, 타입 문자열, 주기 Hz, 메시지 생성 함수)
TOPICS = [
    ("/imu", "sensor_msgs/msg/Imu", 200),
    ("/scan", "sensor_msgs/msg/LaserScan", 10),
    ("/camera/image_raw", "sensor_msgs/msg/Image", 15),
    ("/camera/_debug", "std_msgs/msg/String", 1),
]


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def make_msg(type_name, stamp_ns, seq):
    stamp = Time(sec=stamp_ns // 1_000_000_000, nanosec=stamp_ns % 1_000_000_000)
    if type_name.endswith("Imu"):
        m = Imu()
        m.header.stamp = stamp
        m.header.frame_id = "imu_link"
        m.linear_acceleration.z = 9.81
        return m
    if type_name.endswith("LaserScan"):
        m = LaserScan()
        m.header.stamp = stamp
        m.header.frame_id = "laser"
        m.angle_min, m.angle_max, m.angle_increment = -1.57, 1.57, 3.14 / 89
        m.range_min, m.range_max = 0.1, 10.0
        m.ranges = [1.0 + 0.001 * seq] * 90
        return m
    if type_name.endswith("Image"):
        m = Image()
        m.header.stamp = stamp
        m.header.frame_id = "camera"
        m.height, m.width, m.encoding, m.step = 4, 4, "rgb8", 12
        m.data = bytes([seq % 256]) * 48
        return m
    return String(data=f"debug {seq}")


def make_topic_metadata(i, name, type_name):
    # Jazzy TopicMetadata는 id 인자를 받는다. 다른 시그니처면 id 없이 만든다.
    try:
        return rosbag2_py.TopicMetadata(id=i, name=name, type=type_name, serialization_format="cdr")
    except TypeError:
        return rosbag2_py.TopicMetadata(name=name, type=type_name, serialization_format="cdr")


def write_input_bag(uri):
    writer = rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    events = []
    written = {}
    for i, (name, type_name, hz) in enumerate(TOPICS):
        writer.create_topic(make_topic_metadata(i, name, type_name))
        period_ns = 1_000_000_000 // hz
        n = DURATION_S * hz
        written[name] = 0
        for k in range(n):
            events.append((1_700_000_000_000_000_000 + k * period_ns, name, type_name, k))
    events.sort()
    for stamp_ns, name, type_name, k in events:
        writer.write(name, serialize_message(make_msg(type_name, stamp_ns, k)), stamp_ns)
        written[name] += 1
    del writer  # metadata.yaml 기록(소멸 시 close)
    return written


INFO_TOPIC = re.compile(r"Topic:\s*(\S+)\s*\|\s*Type:\s*(\S+)\s*\|\s*Count:\s*(\d+)")


def bag_info(uri):
    t0 = time.monotonic()
    p = subprocess.run(["ros2", "bag", "info", uri], capture_output=True, text=True, timeout=30)
    out = p.stdout
    storage = re.search(r"Storage id:\s*(\S+)", out)
    messages = re.search(r"Messages:\s*(\d+)", out)
    counts = {m.group(1): int(m.group(3)) for m in INFO_TOPIC.finditer(out)}
    lines = [ln.rstrip() for ln in out.splitlines()
             if ln.strip().startswith(("Storage id", "Messages", "Topic information", "Topic:"))
             or "Topic:" in ln]
    return {
        "exit_code": p.returncode,
        "seconds": round(time.monotonic() - t0, 2),
        "storage_id": storage.group(1) if storage else None,
        "messages": int(messages.group(1)) if messages else None,
        "counts": counts,
        "raw_lines": lines,
        "stderr_tail": p.stderr.strip().splitlines()[-3:],
    }


def reader_counts(uri):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id=""),
                rosbag2_py.ConverterOptions("", ""))
    counts = {}
    while reader.has_next():
        topic, _data, _t = reader.read_next()
        counts[topic] = counts.get(topic, 0) + 1
    del reader
    return counts


def storage_files(uri):
    if not os.path.isdir(uri):
        return []
    return sorted(f for f in os.listdir(uri) if f != "metadata.yaml")


CASES = [
    ("a_all_topics", ["storage_id: mcap", "all_topics: true"]),
    ("b_all_topics_hidden", ["storage_id: mcap", "all_topics: true", "include_hidden_topics: true"]),
    ("c_no_selection_fastwrite", ["storage_id: mcap", "storage_preset_profile: fastwrite"]),
    ("d_all_legacy", ["storage_id: mcap", "all: true"]),
    ("e_storage_id_empty", ['storage_id: ""', "all_topics: true"]),
]


def main():
    t_start = time.monotonic()
    work = tempfile.mkdtemp(prefix="convert_exp_", dir="/tmp")
    in_uri = os.path.join(work, "in_sqlite")

    t0 = time.monotonic()
    written = write_input_bag(in_uri)
    write_s = round(time.monotonic() - t0, 2)
    before = bag_info(in_uri)
    before_reader = reader_counts(in_uri)
    input_ok = (before["exit_code"] == 0 and before["counts"] == written and before_reader == written)
    emit({"event": "input_bag", "storage_id": before["storage_id"], "files": storage_files(in_uri),
          "written_per_topic": written, "written_total": sum(written.values()),
          "info_messages": before["messages"], "info_counts": before["counts"],
          "reader_counts": before_reader, "write_s": write_s,
          "input_ok": input_ok, "info_raw": before["raw_lines"]})
    if not input_ok:
        emit({"event": "error", "reason": "input bag info/reader counts differ from written counts"})
        raise SystemExit(2)

    base_total = before["messages"]
    summary = []
    for name, keys in CASES:
        out_uri = os.path.join(work, f"out_{name}")
        yaml_path = os.path.join(work, f"{name}.yaml")
        yaml_text = "output_bags:\n- uri: " + out_uri + "\n" + "".join(f"  {k}\n" for k in keys)
        with open(yaml_path, "w") as f:
            f.write(yaml_text)
        t0 = time.monotonic()
        p = subprocess.run(["ros2", "bag", "convert", "-i", in_uri, "-o", yaml_path],
                           capture_output=True, text=True, timeout=40)
        conv_s = round(time.monotonic() - t0, 2)
        stderr_lines = [ln.strip() for ln in (p.stderr + p.stdout).splitlines() if ln.strip()]
        warn_lines = [ln for ln in stderr_lines if "WARN" in ln or "ERROR" in ln or "hidden" in ln.lower()]
        exists = os.path.isdir(out_uri)
        after = bag_info(out_uri) if exists else None
        after_reader = reader_counts(out_uri) if exists else {}
        after_counts = after["counts"] if after else {}
        per_topic = {}
        for topic, n_before in before["counts"].items():
            n_after = after_counts.get(topic, 0)
            per_topic[topic] = {"before": n_before, "after_info": n_after,
                                "after_reader": after_reader.get(topic, 0),
                                "diff": n_before - n_after,
                                "loss_ratio": round((n_before - n_after) / n_before, 4)}
        after_total = after["messages"] if after else 0
        total_drop = base_total - (after_total or 0)
        per_topic_pass = (all(v["diff"] == 0 for v in per_topic.values())
                          and set(after_counts) == set(before["counts"]))
        # 하네스는 stdout 끝 8000자만 보관하므로 케이스 줄은 짧게 유지한다.
        # per_topic 값: [변환 전 info Count, 변환 후 info Count, 변환 후 reader 개수, 손실 비율]
        rec = {"event": "convert_case", "case": name, "yaml_keys": keys,
               "exit_code": p.returncode, "convert_s": conv_s,
               "out_storage_id": after["storage_id"] if after else None,
               "out_files": storage_files(out_uri),
               "info_messages": after_total, "total_drop": total_drop,
               "total_drop_ratio": round(total_drop / base_total, 4),
               "per_topic": {t: [v["before"], v["after_info"], v["after_reader"], v["loss_ratio"]]
                             for t, v in per_topic.items()},
               "missing_topics": sorted(t for t, v in per_topic.items() if v["after_info"] == 0),
               "info_equals_reader": after_counts == after_reader,
               "per_topic_pass": per_topic_pass,
               "warn": [re.sub(r"^\[(\w+)\] \[[0-9.]+\] ", r"[\1] ", ln) for ln in warn_lines][:3]}
        if name == "a_all_topics" and after:
            rec["info_raw"] = after["raw_lines"]
        emit(rec)
        summary.append([name, p.returncode, after_total, rec["total_drop_ratio"], per_topic_pass])
    emit({"event": "summary", "fields": ["case", "exit_code", "info_messages", "total_drop_ratio",
                                         "per_topic_pass"], "cases": summary,
          "elapsed_seconds": round(time.monotonic() - t_start, 2)})


if __name__ == "__main__":
    main()
