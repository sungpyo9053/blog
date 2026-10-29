#!/usr/bin/env python3
"""합성 sensor_msgs/Image(rgb8)를 목표 30 Hz로 발행하고, 다른 프로세스의 구독자가
실제로 받은 바이트/초와 Hz를 W x H x 3 x fps 계산과 비교한다.

- Gazebo 없이 메시지 경로(직렬화·DDS·Python 구독자)만의 부담을 본다.
- 구독자는 `ros2 topic bw`처럼 raw=True로 직렬화 바이트열을 받아 len()을 더하고,
  벽시계(time.monotonic) 기준으로 나눈다.
- 모든 측정값은 실행 중에 잰다. 출력은 JSON 한 줄씩이다.
"""
import array
import json
import statistics
import subprocess
import sys
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, qos_profile_sensor_data
from rclpy.serialization import serialize_message
from sensor_msgs.msg import Image

TARGET_HZ = 30.0
BYTES_PER_PIXEL = 3  # rgb8: 3채널 x 8비트
RESOLUTIONS = [(640, 480), (1280, 720), (1920, 1080)]
# (가로, 세로, QoS, 목표 Hz). 큰 해상도는 1 GiB 한도 때문에 작은 depth로만 돌린다.
CONDITIONS = (
    [(w, h, "sensor_data", TARGET_HZ) for w, h in RESOLUTIONS + [(3840, 2160)]]
    + [(w, h, "default", TARGET_HZ) for w, h in RESOLUTIONS]
    # 질문자 설정(4512x4512, update_rate 19)을 best effort depth 1로 한 번 보낸다.
    + [(4512, 4512, "best_effort_depth1", 19.0), (4512, 4512, "reliable_depth1", 19.0)]
)
WINDOW_S = 2.5          # 구독자가 첫 수신 이후 기록하는 벽시계 시간
FIRST_MSG_TIMEOUT_S = 6.0
MATCH_TIMEOUT_S = 8.0
TOTAL_BUDGET_S = 48.0   # 이 시간을 넘기면 남은 조건은 건너뛴다(1회 60초 제한)
MB = 1_000_000          # ros2 topic bw와 같은 10^6 기반


def qos_for(name):
    if name == "sensor_data":
        return qos_profile_sensor_data
    if name == "best_effort_depth1":
        return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                          reliability=ReliabilityPolicy.BEST_EFFORT)
    if name == "reliable_depth1":
        return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                          reliability=ReliabilityPolicy.RELIABLE)
    # rclpy create_publisher(..., 10)과 같은 기본: keep last 10, reliable, volatile
    return QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                      reliability=ReliabilityPolicy.RELIABLE)


def peak_rss_mb():
    """/proc/self/status의 VmHWM(최대 상주 메모리, kB). exec 이후 새로 시작한다."""
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmHWM:"):
                return round(int(line.split()[1]) * 1000 / MB, 1)
    return None


def reset_peak_rss():
    """VmHWM을 현재 RSS로 되돌린다(Linux clear_refs 5). 실패하면 False."""
    try:
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
        return True
    except OSError:
        return False


def make_image(width, height):
    msg = Image()
    msg.header.frame_id = "camera"
    msg.width = width
    msg.height = height
    msg.encoding = "rgb8"
    msg.is_bigendian = 0
    msg.step = width * BYTES_PER_PIXEL
    pattern = bytes(range(256))
    n = msg.step * height
    payload = (pattern * (n // len(pattern) + 1))[:n]
    # array.array('B')로 넘겨야 원소별 범위 검사 없이 바로 대입된다.
    msg.data = array.array("B", payload)
    return msg


def run_subscriber(topic, qos_name):
    """자식 프로세스: raw 구독으로 받은 크기와 시각을 기록해 JSON 한 줄을 출력한다."""
    rclpy.init()
    node = rclpy.create_node("bw_probe_sub")
    stamps, sizes = [], []

    def on_msg(raw):
        stamps.append(time.monotonic())
        sizes.append(len(raw))

    node.create_subscription(Image, topic, on_msg, qos_for(qos_name), raw=True)
    print(json.dumps({"ready": True}), flush=True)
    t0 = time.monotonic()
    while not stamps and time.monotonic() - t0 < FIRST_MSG_TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.05)
    if stamps:
        end = stamps[0] + WINDOW_S
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
    # 구독 프로세스는 조건마다 새로 뜨므로 VmHWM이 이 조건만의 최대 상주 메모리다.
    out = {"received": len(stamps), "window_s": WINDOW_S if stamps else 0.0,
           "peak_rss_MB": peak_rss_mb()}
    if len(stamps) >= 2:
        span = stamps[-1] - stamps[0]
        # 첫 메시지는 시작 시각 기준점이므로 바이트 합에서 뺀다(간격 n-1개에 대응).
        out.update({
            "span_s": round(span, 4),
            "rx_hz": round((len(stamps) - 1) / span, 3),
            "rx_MBps": round(sum(sizes[1:]) / span / MB, 3),
            "msg_bytes_min": min(sizes),
            "msg_bytes_max": max(sizes),
        })
    elif stamps:
        out.update({"msg_bytes_min": sizes[0], "msg_bytes_max": sizes[0]})
    print(json.dumps(out), flush=True)
    node.destroy_node()
    rclpy.shutdown()


def run_condition(width, height, qos_name, target_hz, index):
    topic = f"/bw_probe/c{index}_{width}x{height}_{qos_name}"
    rss_reset = reset_peak_rss()
    msg = make_image(width, height)
    frame_bytes = width * height * BYTES_PER_PIXEL
    qos = qos_for(qos_name)

    sub = subprocess.Popen([sys.executable, __file__, "sub", topic, qos_name],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sub.stdout.readline()  # {"ready": true}

    node = rclpy.create_node(f"bw_probe_pub_{index}")
    pub = node.create_publisher(Image, topic, qos)
    t0 = time.monotonic()
    while pub.get_subscription_count() == 0 and time.monotonic() - t0 < MATCH_TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.05)
    match_s = time.monotonic() - t0
    matched = pub.get_subscription_count() > 0

    period = 1.0 / target_hz
    publish_times = []
    pub_call_s = 0.0
    start = time.monotonic()
    next_t = start
    # 구독자가 첫 수신 후 WINDOW_S 동안 기록하므로 그보다 조금 더 오래 발행한다.
    while matched and time.monotonic() - start < WINDOW_S + 1.0 \
            and time.monotonic() - BEGAN < TOTAL_BUDGET_S + 6:
        now = time.monotonic()
        if now < next_t:
            time.sleep(min(next_t - now, period))
            continue
        msg.header.stamp = node.get_clock().now().to_msg()
        c0 = time.monotonic()
        pub.publish(msg)
        pub_call_s += time.monotonic() - c0
        publish_times.append(c0)
        next_t += period
        if time.monotonic() > next_t + period:  # 밀렸으면 따라잡기 대신 다음 주기로
            next_t = time.monotonic()

    try:
        sub_out, sub_err = sub.communicate(timeout=FIRST_MSG_TIMEOUT_S + WINDOW_S + 5)
    except subprocess.TimeoutExpired:
        sub.kill()
        sub_out, sub_err = sub.communicate()
    node.destroy_publisher(pub)
    node.destroy_node()

    lines = [l for l in sub_out.strip().splitlines() if l.startswith("{")]
    rx = json.loads(lines[-1]) if lines else {"received": 0, "error": sub_err[-300:]}

    n_pub = len(publish_times)
    pub_span = publish_times[-1] - publish_times[0] if n_pub >= 2 else 0.0
    pub_hz = (n_pub - 1) / pub_span if pub_span > 0 else 0.0
    predicted_MBps = frame_bytes * target_hz / MB
    row = {
        "kind": "condition",
        "width": width, "height": height, "qos": qos_name,
        "reliability": qos.reliability.name.lower(), "depth": qos.depth,
        "target_hz": target_hz,
        "frame_bytes": frame_bytes,
        "predicted_MBps_at_target": round(predicted_MBps, 3),
        "depth_bound_MB": round(qos.depth * frame_bytes / MB, 3),
        "match_s": round(match_s, 3), "matched": matched,
        "published": n_pub,
        "pub_hz": round(pub_hz, 3),
        "pub_call_ms_mean": round(pub_call_s / n_pub * 1000, 3) if n_pub else None,
        # rss_reset이 false면 이전 조건까지의 최대치가 섞인 값이다.
        "pub_peak_rss_MB": peak_rss_mb(), "pub_rss_reset": rss_reset,
    }
    row.update({f"sub_{k}": v for k, v in rx.items()})
    if "rx_MBps" in rx:
        row["rx_over_predicted"] = round(rx["rx_MBps"] / predicted_MBps, 3)
        row["rx_hz_over_pub_hz"] = round(rx["rx_hz"] / pub_hz, 3) if pub_hz else None
    if "msg_bytes_max" in rx:
        row["overhead_bytes"] = rx["msg_bytes_max"] - frame_bytes
    return row


BEGAN = time.monotonic()


def main():
    began = BEGAN
    rclpy.init()
    print(json.dumps({
        "kind": "env",
        "rmw": rclpy.get_rmw_implementation_identifier(),
        "python": sys.version.split()[0],
        "target_hz": TARGET_HZ, "window_s": WINDOW_S,
        "sensor_data_depth": qos_profile_sensor_data.depth,
        "sensor_data_reliability": qos_profile_sensor_data.reliability.name.lower(),
    }), flush=True)

    # 1) 전송 없이 직렬화만 했을 때의 크기와 시간(같은 프로세스, 1회씩)
    for width, height in RESOLUTIONS + [(4512, 4512)]:
        msg = make_image(width, height)
        serialize_message(msg)  # 첫 호출의 타입 지원 로딩 비용을 빼기 위한 예열
        times = []
        for _ in range(3):
            c0 = time.monotonic()
            raw = serialize_message(msg)
            times.append((time.monotonic() - c0) * 1000)
            if _ < 2:
                del raw
        ser_ms = statistics.median(times)
        frame_bytes = width * height * BYTES_PER_PIXEL
        print(json.dumps({
            "kind": "serialize", "width": width, "height": height,
            "frame_bytes": frame_bytes, "serialized_bytes": len(raw),
            "overhead_bytes": len(raw) - frame_bytes,
            "serialize_ms_median3": round(ser_ms, 3),
            "depth10_bound_MB": round(10 * frame_bytes / MB, 3),
            "depth5_bound_MB": round(qos_profile_sensor_data.depth * frame_bytes / MB, 3),
        }), flush=True)
        del raw, msg

    # 2) 프로세스 간 발행·구독: CONDITIONS 순서대로
    for index, (width, height, qos_name, target_hz) in enumerate(CONDITIONS, start=1):
        if time.monotonic() - began > TOTAL_BUDGET_S:
            print(json.dumps({"kind": "skipped", "width": width, "height": height,
                              "qos": qos_name, "reason": "time_budget"}), flush=True)
            continue
        print(json.dumps(run_condition(width, height, qos_name, target_hz, index)), flush=True)

    print(json.dumps({"kind": "done", "total_s": round(time.monotonic() - began, 2)}), flush=True)
    rclpy.shutdown()


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "sub":
        run_subscriber(sys.argv[2], sys.argv[3])
    else:
        main()
