#!/usr/bin/env python3
"""Jazzy가 녹화·변환한 bag 4칸의 파일 형식을 재고, Humble 0.15.17 판독 규칙을 대입한다.

칸: sqlite3 원본, mcap 원본, mcap -> sqlite3 convert, sqlite3 -> mcap convert.
모든 값은 실행 중에 만든 bag 파일을 읽어서 얻는다. 결과는 JSON 줄로 출력한다.
Humble 실행은 하지 않는다. 판정은 아래 두 코드 줄을 파일 내용에 적용한 것이다.
  - rosbag2 0.15.17 metadata_io.cpp L70-L71: node["offered_qos_profiles"].as<std::string>()
  - rosbag2 0.15.17 rosbag2_transport/qos.cpp L85-L88: history·reliability·durability·liveliness .as<int>()
"""
import json
import os
import re
import shutil
import signal
import sqlite3
import struct
import subprocess
import sys
import time
from pathlib import Path

import yaml  # noqa: E402
import rclpy  # noqa: E402
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, LivelinessPolicy,  # noqa: E402
                       ReliabilityPolicy)
from geometry_msgs.msg import TransformStamped  # noqa: E402
from std_msgs.msg import String  # noqa: E402
from tf2_ros import StaticTransformBroadcaster  # noqa: E402

WORK = Path("/tmp/bags")
TOPICS = ["/chatter", "/tf_static"]
CHATTER_COUNT = 20
INT_POLICIES = {"history": HistoryPolicy, "reliability": ReliabilityPolicy,
                "durability": DurabilityPolicy, "liveliness": LivelinessPolicy}


def emit(**fields):
    print(json.dumps(fields, ensure_ascii=False, separators=(",", ":")), flush=True)


def package_version(name):
    xml = Path(f"/opt/ros/{os.environ.get('ROS_DISTRO', 'jazzy')}/share/{name}/package.xml")
    found = re.search(r"<version>([^<]+)</version>", xml.read_text()) if xml.is_file() else None
    return found.group(1) if found else None


# ---------- 1. 녹화: rclpy 발행자 + ros2 bag record 두 개(sqlite3, mcap) ----------
def record_bags():
    rclpy.init()
    node = rclpy.create_node("bag_source")
    chatter = node.create_publisher(String, "/chatter", 10)
    static = StaticTransformBroadcaster(node)
    tf = TransformStamped()
    tf.header.stamp = node.get_clock().now().to_msg()
    tf.header.frame_id, tf.child_frame_id = "base_link", "camera_link"
    tf.transform.translation.x = 0.1
    tf.transform.rotation.w = 1.0
    static.sendTransform(tf)  # transient_local: 녹화기가 늦게 붙어도 받는다

    started = time.monotonic()
    recorders = {}
    for storage in ("sqlite3", "mcap"):
        out = WORK / f"rec_{storage}"
        recorders[storage] = subprocess.Popen(
            ["ros2", "bag", "record", "-s", storage, "-o", str(out), *TOPICS],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    # 두 녹화기가 두 토픽을 모두 구독할 때까지 기다린다
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if chatter.get_subscription_count() >= 2 and node.count_subscribers("/tf_static") >= 2:
            break
    discovered = chatter.get_subscription_count() >= 2 and node.count_subscribers("/tf_static") >= 2
    discovery_seconds = round(time.monotonic() - started, 2)
    if not discovered:
        for proc in recorders.values():
            os.killpg(proc.pid, signal.SIGINT)
        logs = {k: p.communicate(timeout=10)[0][-600:] for k, p in recorders.items()}
        emit(event="error", stage="record_discovery", seconds=discovery_seconds, logs=logs)
        sys.exit(2)

    for index in range(CHATTER_COUNT):
        chatter.publish(String(data=f"hello {index}"))
        rclpy.spin_once(node, timeout_sec=0.02)
    end = time.monotonic() + 1.0
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    for storage, proc in recorders.items():
        os.killpg(proc.pid, signal.SIGINT)
    for storage, proc in recorders.items():
        try:
            log, _ = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            log, _ = proc.communicate()
        if not (WORK / f"rec_{storage}" / "metadata.yaml").is_file():
            emit(event="error", stage="record_close", storage=storage, log=log[-800:])
            sys.exit(3)
    node.destroy_node()
    rclpy.shutdown()
    emit(event="record", storages=["sqlite3", "mcap"], published={"/chatter": CHATTER_COUNT, "/tf_static": 1},
         discovery_seconds=discovery_seconds, total_seconds=round(time.monotonic() - started, 2))


# ---------- 2. Jazzy ros2 bag convert (저장 형식을 반대로) ----------
def convert(src_storage, dst_storage):
    src = WORK / f"rec_{src_storage}"
    dst = WORK / f"conv_{src_storage}_to_{dst_storage}"
    options = WORK / f"out_{dst_storage}.yaml"
    options.write_text(yaml.safe_dump({"output_bags": [
        {"uri": str(dst), "storage_id": dst_storage, "all_topics": True}]}))
    started = time.monotonic()
    done = subprocess.run(["ros2", "bag", "convert", "-i", str(src), "-o", str(options)],
                          capture_output=True, text=True, timeout=40)
    seconds = round(time.monotonic() - started, 2)
    if done.returncode != 0 or not (dst / "metadata.yaml").is_file():
        emit(event="error", stage="convert", src=src_storage, dst=dst_storage,
             exit_code=done.returncode, stderr=(done.stderr + done.stdout)[-800:])
        sys.exit(4)
    emit(event="convert", src=src_storage, dst=dst_storage, exit_code=done.returncode, seconds=seconds,
         input_storage_bytes=storage_bytes(src), output_storage_bytes=storage_bytes(dst))
    return dst


# ---------- 파일 읽기 도구 ----------
def storage_files(folder):
    return sorted(p for p in folder.iterdir() if p.suffix in (".db3", ".mcap"))


def storage_bytes(folder):
    return sum(p.stat().st_size for p in storage_files(folder))


def mapping_get(node, key):
    for k, v in node.value:
        if k.value == key:
            return v
    return None


def node_kind(node):
    return {yaml.ScalarNode: "scalar", yaml.SequenceNode: "sequence",
            yaml.MappingNode: "mapping"}.get(type(node), type(node).__name__)


def metadata_topics(text):
    """[(topic name, offered_qos_profiles YAML 노드)] — yaml.compose로 노드 종류를 그대로 본다."""
    root = mapping_get(yaml.compose(text), "rosbag2_bagfile_information")
    out = []
    for entry in mapping_get(root, "topics_with_message_count").value:
        meta = mapping_get(entry, "topic_metadata")
        out.append((mapping_get(meta, "name").value, mapping_get(meta, "offered_qos_profiles"), meta))
    return root, out


def is_int_scalar(value):
    return re.fullmatch(r"[-+]?\d+", str(value).strip()) is not None


def policy_values(qos_list):
    """QoS 목록에서 정수로 읽혀야 하는 정책 값만 모은다."""
    return [(key, profile.get(key)) for profile in qos_list for key in INT_POLICIES if key in profile]


def play_rule(qos_text):
    """Humble 재생 경로: 문자열을 YAML로 풀고 정책 값을 as<int>()로 읽는다. 빈 문자열이면 기본 QoS."""
    if qos_text == "":
        return {"pass": True, "qos_used": "default (empty string)"}
    parsed = yaml.safe_load(qos_text)
    values = policy_values(parsed or [])
    bad = sorted({f"{k}={v}" for k, v in values if not is_int_scalar(v)})
    return {"pass": not bad, "non_integer_values": bad}


def durability_of(qos_text):
    if qos_text == "":
        return None
    values = [p.get("durability") for p in (yaml.safe_load(qos_text) or [])]
    return values


def is_transient_local(value):
    return str(value).lower() == "transient_local" or (
        is_int_scalar(value) and int(value) == DurabilityPolicy.TRANSIENT_LOCAL.value)


def read_mcap_channels(path):
    """MCAP summary 영역의 Channel(0x04)·Metadata(0x0C) 레코드를 직접 읽는다(외부 파서 없이)."""
    data = path.read_bytes()
    magic = b"\x89MCAP0\r\n"
    if data[:8] != magic or data[-8:] != magic:
        return {"error": "bad magic"}
    summary_start = struct.unpack_from("<Q", data, len(data) - 8 - 20)[0]

    def string(buf, pos):
        n = struct.unpack_from("<I", buf, pos)[0]
        return buf[pos + 4:pos + 4 + n].decode(), pos + 4 + n

    def str_map(buf, pos):
        total = struct.unpack_from("<I", buf, pos)[0]
        pos += 4
        end, result = pos + total, {}
        while pos < end:
            key, pos = string(buf, pos)
            value, pos = string(buf, pos)
            result[key] = value
        return result, end

    channels, metadata_records = {}, {}
    pos = summary_start if summary_start else 8
    end = len(data) - 8
    while pos < end:
        opcode = data[pos]
        length = struct.unpack_from("<Q", data, pos + 1)[0]
        body = data[pos + 9:pos + 9 + length]
        if opcode == 0x04:
            topic, p = string(body, 4)
            _, p = string(body, p)
            meta, _ = str_map(body, p)
            channels[topic] = meta
        elif opcode == 0x0C:
            name, p = string(body, 0)
            meta, _ = str_map(body, p)
            metadata_records[name] = sorted(meta)
        pos += 9 + length
    return {"channels": channels, "metadata_records": metadata_records,
            "summary_section": bool(summary_start)}


def storage_qos(folder):
    """저장 파일 안의 토픽별 QoS 문자열과 저장 형식별 부가 정보."""
    file = storage_files(folder)[0]
    if file.suffix == ".db3":
        con = sqlite3.connect(f"file:{file}?mode=ro", uri=True)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        qos = dict(con.execute("SELECT name, offered_qos_profiles FROM topics"))
        schema = con.execute("SELECT schema_version, ros_distro FROM schema").fetchone() if "schema" in tables else None
        con.close()
        return qos, {"sqlite_tables": len(tables), "sqlite_schema_version": schema[0] if schema else None,
                     "sqlite_ros_distro": schema[1] if schema else None}
    info = read_mcap_channels(file)
    qos = {t: m.get("offered_qos_profiles") for t, m in info.get("channels", {}).items()}
    keys = sorted({k for m in info.get("channels", {}).values() for k in m})
    return qos, {"mcap_channel_metadata_keys": keys}


# ---------- 3. 칸별 측정 ----------
def policies_text(qos_list):
    """첫 QoS 프로필의 정수형 정책 값을 'key=value' 한 줄로(출력 크기를 줄이기 위해)."""
    return " ".join(f"{k}={v}" for k, v in policy_values((qos_list or [])[:1]))


def measure_cell(label, folder):
    meta_path = folder / "metadata.yaml"
    text = meta_path.read_text()
    _, topics = metadata_topics(text)
    plain = yaml.safe_load(text)["rosbag2_bagfile_information"]
    by_name = {t["topic_metadata"]["name"]: t for t in plain["topics_with_message_count"]}
    file_qos, extra = storage_qos(folder)
    per_topic = {}
    for name, qos_node, _ in topics:
        meta_plain = by_name[name]["topic_metadata"]
        qos_value = meta_plain["offered_qos_profiles"]
        listed = qos_value if isinstance(qos_value, list) else (yaml.safe_load(qos_value) or [])
        folder_info = node_kind(qos_node) == "scalar"
        file_text = file_qos.get(name)
        file_list = yaml.safe_load(file_text) if isinstance(file_text, str) and file_text else None
        per_topic[name] = {
            "count": by_name[name]["message_count"],
            "qos_node": node_kind(qos_node),
            "policies": policies_text(listed),
            "storage_policies": policies_text(file_list) if file_list else None,
            "folder_info": folder_info,
            "folder_play": folder_info and play_rule(qos_value)["pass"],
            "file_play": isinstance(file_text, str) and play_rule(file_text)["pass"],
        }
    cell = {
        "event": "cell", "cell": label, "version": plain.get("version"), "ros_distro": plain.get("ros_distro"),
        "type_description_hash_topics": sum("type_description_hash" in t["topic_metadata"]
                                            for t in plain["topics_with_message_count"]),
        "metadata_bytes": meta_path.stat().st_size, "storage_bytes": storage_bytes(folder), **extra,
        "topics": per_topic,
        "humble_folder_info_pass": all(t["folder_info"] for t in per_topic.values()),
        "humble_folder_play_pass": all(t["folder_play"] for t in per_topic.values()),
        "humble_file_play_pass": all(t["file_play"] for t in per_topic.values()),
    }
    print(json.dumps(cell, ensure_ascii=False, separators=(",", ":")), flush=True)
    return cell


# ---------- 4. 우회법 A·B를 metadata.yaml 복사본에 적용 ----------
def to_int_string(qos_list):
    converted = []
    for profile in qos_list:
        item = dict(profile)
        for key, enum in INT_POLICIES.items():
            if key in item and not is_int_scalar(item[key]):
                item[key] = enum[str(item[key]).upper()].value
        converted.append(item)
    return yaml.safe_dump(converted, default_flow_style=False, sort_keys=False)


def replace_qos_blocks(text, rewrite):
    """metadata.yaml에서 offered_qos_profiles 블록만 글자 단위로 바꾼다(다른 줄은 그대로 둔다)."""
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        found = re.match(r"^(\s*)offered_qos_profiles:(.*)$", line)
        if not found:
            out.append(line)
            i += 1
            continue
        indent, block, i = len(found.group(1)), [line], i + 1
        while i < len(lines):
            nxt = lines[i]
            depth = len(nxt) - len(nxt.lstrip())
            if nxt.strip() and (depth > indent or (depth == indent and nxt.lstrip().startswith("- "))):
                block.append(nxt)
                i += 1
            else:
                break
        old = yaml.safe_load("\n".join(b[indent:] for b in block))["offered_qos_profiles"]
        out.append(" " * indent + "offered_qos_profiles: " + json.dumps(rewrite(old)))
    return "\n".join(out) + "\n"


def jazzy_info(folder):
    """Jazzy ros2 bag info <폴더>: 종료 코드, 첫 오류 줄, 오류가 가리키는 metadata.yaml 줄."""
    started = time.monotonic()
    info = subprocess.run(["ros2", "bag", "info", str(folder)], capture_output=True, text=True, timeout=30)
    message = (info.stderr if info.returncode else "").strip().splitlines()
    first = message[0][:200] if message else ""
    pointed = None
    where = re.search(r"line (\d+), column (\d+)", first)
    if where:
        meta_lines = (folder / "metadata.yaml").read_text().splitlines()
        row = int(where.group(1)) - 1  # yaml-cpp는 줄 번호를 1부터 세어 출력한다
        pointed = meta_lines[row].strip()[:80] if 0 <= row < len(meta_lines) else None
    return {"jazzy_info_exit_code": info.returncode, "jazzy_info_first_error_line": first,
            "jazzy_info_error_points_to": pointed, "jazzy_info_seconds": round(time.monotonic() - started, 2)}


def apply_workaround(name, source, rewrite):
    target = WORK / f"workaround_{name}"
    shutil.copytree(source, target)
    meta_path = target / "metadata.yaml"
    before = meta_path.read_text()
    text = replace_qos_blocks(before, rewrite)
    meta_path.write_text(text)
    _, topics = metadata_topics(text)
    plain = {t["topic_metadata"]["name"]: t["topic_metadata"]["offered_qos_profiles"]
             for t in yaml.safe_load(text)["rosbag2_bagfile_information"]["topics_with_message_count"]}
    result = {}
    for topic, qos_node, _ in topics:
        folder_info = node_kind(qos_node) == "scalar"
        durability = durability_of(plain[topic]) if isinstance(plain[topic], str) else None
        result[topic] = {"metadata_qos_node": node_kind(qos_node), "humble_folder_info_pass": folder_info,
                         "humble_folder_play_pass": folder_info and play_rule(plain[topic])["pass"],
                         "durability_recorded": durability,
                         "transient_local_kept": bool(durability) and any(is_transient_local(d) for d in durability)}
    emit(event="workaround", name=name, source=source.name, metadata_bytes_before=len(before.encode()),
         metadata_bytes_after=meta_path.stat().st_size, topics=result, **jazzy_info(target))


def qos_excerpt(folder):
    """원본 metadata.yaml에서 /tf_static의 offered_qos_profiles 블록 줄을 그대로 보여 준다."""
    lines = (folder / "metadata.yaml").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "name: /tf_static")
    qos = next(i for i in range(start, len(lines)) if "offered_qos_profiles:" in lines[i])
    indent = len(lines[qos]) - len(lines[qos].lstrip())
    end = qos + 1
    while end < len(lines):
        depth = len(lines[end]) - len(lines[end].lstrip())
        if depth > indent or (depth == indent and lines[end].lstrip().startswith("- ")):
            end += 1
        else:
            break
    return lines[qos:end]


def main():
    started = time.monotonic()
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    emit(event="env", ros_distro=os.environ.get("ROS_DISTRO"), rosbag2_py=package_version("rosbag2_py"),
         rosbag2_storage=package_version("rosbag2_storage"),
         rosbag2_storage_mcap=package_version("rosbag2_storage_mcap"),
         rosbag2_storage_sqlite3=package_version("rosbag2_storage_sqlite3"),
         python=sys.version.split()[0], sqlite=sqlite3.sqlite_version,
         discovery_range=os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE"))
    record_bags()
    convert("mcap", "sqlite3")
    convert("sqlite3", "mcap")
    cells = [measure_cell("sqlite3/original", WORK / "rec_sqlite3"),
             measure_cell("mcap/original", WORK / "rec_mcap"),
             measure_cell("sqlite3/converted_from_mcap", WORK / "conv_mcap_to_sqlite3"),
             measure_cell("mcap/converted_from_sqlite3", WORK / "conv_sqlite3_to_mcap")]
    emit(event="jazzy_control", folder="rec_mcap", **jazzy_info(WORK / "rec_mcap"))
    emit(event="metadata_excerpt", folder="rec_mcap", topic="/tf_static", lines=qos_excerpt(WORK / "rec_mcap"))
    apply_workaround("A_empty_string", WORK / "rec_mcap", lambda qos: "")
    apply_workaround("B_integer_string", WORK / "rec_mcap",
                     lambda qos: to_int_string(qos if isinstance(qos, list) else yaml.safe_load(qos)))
    emit(event="summary", cells=len(cells),
         metadata_versions=sorted({c["version"] for c in cells}),
         humble_folder_info_pass_cells=sum(c["humble_folder_info_pass"] for c in cells),
         humble_folder_play_pass_cells=sum(c["humble_folder_play_pass"] for c in cells),
         humble_file_play_pass_cells=sum(c["humble_file_play_pass"] for c in cells),
         total_seconds=round(time.monotonic() - started, 2))


if __name__ == "__main__":
    main()
