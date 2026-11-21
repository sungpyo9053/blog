"""ros2 topic list에는 보이는데 일부 토픽만 받아질 때: QoS 불일치와 큰 메시지 조각 손실을 토픽별 수신 수로 가르기.

ROS 2 Jazzy(rmw_fastrtps_cpp), 네트워크 없는 컨테이너, 한 번 실행 60초 이내.
모든 값은 실행 중에 센 값이며 JSON 한 줄씩 출력한다.

1) qos: best effort 발행자를 reliable/best effort 구독자로 받아 토픽별 수신 수와
   incompatible QoS 이벤트 수를 센다. 같은 구독 노드에서 토픽 목록 노출 여부도 기록한다.
2) echo_choose_qos / echo_cli: Jazzy ros2topic의 실제 echo 코드가 옵션 없이 고르는
   reliability와, 별도 프로세스의 `ros2 topic echo` 수신 줄 수를 옵션 유무로 비교한다.
3) link_emulation: 실제 와이파이가 없으므로 중계 노드가 메시지마다 직렬화 크기를 재고,
   UDP 데이터그램(MaxMessageSize) → IP 조각(MTU 1500) 수를 계산한 뒤 조각마다 독립 손실
   확률 p로 버릴지 정한다(모델). p=0(유선 대조)과 p=1/32를 같은 창에서 비교한다.
"""
import json
import math
import os
import random
import signal
import subprocess
import sys
import threading
import time

os.environ.setdefault("ROS_DOMAIN_ID", "42")
os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "LOCALHOST"
os.environ["FASTDDS_BUILTIN_TRANSPORTS"] = "UDPv4"  # 공유 메모리 대신 UDP 루프백 경로

import rclpy  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, qos_profile_sensor_data  # noqa: E402
from rclpy.qos import QoSHistoryPolicy, QoSDurabilityPolicy  # noqa: E402
from rclpy.event_handler import SubscriptionEventCallbacks  # noqa: E402
from rclpy.serialization import serialize_message  # noqa: E402
from sensor_msgs.msg import Imu, LaserScan, PointCloud2, PointField  # noqa: E402

T0 = time.monotonic()
WINDOW = 4.0
GRACE = 0.6
MTU = 1500
IP_HEADER = 20
UDP_HEADER = 8
TOPICS = {"/imu/data": 20.0, "/scan": 10.0, "/points": 10.0}
POINTS = 20000  # x,y,z,intensity float32 = 16 B/점


def emit(**record):
    record["t"] = round(time.monotonic() - T0, 3)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def reasm_counters():
    with open("/proc/net/snmp") as handle:
        rows = [line.split() for line in handle if line.startswith("Ip:")]
    return {k: int(v) for k, v in zip(rows[0][1:], rows[1][1:]) if k.startswith(("Reasm", "Frag"))}


def ip_fragments(payload):
    per_fragment = (MTU - IP_HEADER) // 8 * 8
    return max(1, math.ceil((payload + UDP_HEADER) / per_fragment))


def sample_fragments(serialized, max_message):
    """한 샘플을 max_message 이하 UDP 데이터그램으로 나눈다고 가정한 총 IP 조각 수."""
    full, rest = divmod(serialized, max_message)
    return full * ip_fragments(max_message) + (ip_fragments(rest) if rest else 0), full + (1 if rest else 0)


def make_msg(topic, seq, stamp):
    if topic == "/imu/data":
        msg = Imu()
        msg.orientation.w = 1.0
    elif topic == "/scan":
        msg = LaserScan()
        msg.angle_min, msg.angle_max, msg.angle_increment = -math.pi, math.pi, 2 * math.pi / 720
        msg.range_min, msg.range_max = 0.1, 30.0
        msg.ranges = [1.0 + (seq % 7) * 0.01] * 720
    else:
        msg = PointCloud2()
        msg.height, msg.width = 1, POINTS
        msg.fields = [PointField(name=n, offset=4 * i, datatype=PointField.FLOAT32, count=1)
                      for i, n in enumerate("xyz") ] + [PointField(name="intensity", offset=12,
                                                                    datatype=PointField.FLOAT32, count=1)]
        msg.point_step, msg.row_step, msg.is_dense = 16, 16 * POINTS, True
        msg.data = PAYLOAD
    msg.header.frame_id = f"seq={seq}"
    msg.header.stamp = stamp
    return msg


MSG_TYPES = {"/imu/data": Imu, "/scan": LaserScan, "/points": PointCloud2}
TYPE_NAMES = {"/imu/data": "sensor_msgs/msg/Imu", "/points": "sensor_msgs/msg/PointCloud2"}


def sensor_qos():
    """공유 프리셋 객체 대신 매번 새로 만든 sensor_data 동등 프로필(best effort, keep last 5)."""
    return QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=5,
                      reliability=QoSReliabilityPolicy.BEST_EFFORT, durability=QoSDurabilityPolicy.VOLATILE)
PAYLOAD = bytes(16 * POINTS)


class Robot(Node):
    """센서 드라이버처럼 sensor_data(best effort) QoS로 발행한다."""

    def __init__(self):
        super().__init__("robot")
        self.seq = {t: 0 for t in TOPICS}
        self.pubs = {t: self.create_publisher(MSG_TYPES[t], t, sensor_qos()) for t in TOPICS}
        for topic, hz in TOPICS.items():
            self.create_timer(1.0 / hz, lambda t=topic: self.tick(t))

    def tick(self, topic):
        self.pubs[topic].publish(make_msg(topic, self.seq[topic], self.get_clock().now().to_msg()))
        self.seq[topic] += 1


class Counter:
    def __init__(self):
        self.seqs = []
        self.lock = threading.Lock()

    def __call__(self, msg):
        with self.lock:
            self.seqs.append(int(msg.header.frame_id[4:]))

    def in_window(self, lo, hi):
        with self.lock:
            return len({s for s in self.seqs if lo <= s < hi})


def window(robot, seconds=WINDOW):
    start = dict(robot.seq)
    time.sleep(seconds)
    end = dict(robot.seq)
    time.sleep(GRACE)
    return start, end


def phase_qos(robot, laptop):
    counters, incompatible = {}, {}
    for topic in TOPICS:
        for name, rel in (("reliable", QoSReliabilityPolicy.RELIABLE),
                          ("best_effort", QoSReliabilityPolicy.BEST_EFFORT)):
            key = (topic, name)
            counters[key] = Counter()
            incompatible[key] = 0

            def on_incompatible(event, key=key):
                incompatible[key] = event.total_count

            laptop.create_subscription(
                MSG_TYPES[topic], topic, counters[key], QoSProfile(depth=10, reliability=rel),
                event_callbacks=SubscriptionEventCallbacks(incompatible_qos=on_incompatible))
    time.sleep(1.5)  # 발견 대기
    start, end = window(robot)
    listed = dict(laptop.get_topic_names_and_types())
    for topic in TOPICS:
        pubs = laptop.get_publishers_info_by_topic(topic)
        for name in ("reliable", "best_effort"):
            key = (topic, name)
            emit(phase="qos", topic=topic, publisher_reliability=[p.qos_profile.reliability.name for p in pubs],
                 subscriber_reliability=name, in_topic_list=topic in listed,
                 expected=end[topic] - start[topic], received=counters[key].in_window(start[topic], end[topic]),
                 incompatible_qos_events=incompatible[key])


def phase_echo_choose_qos(laptop):
    from ros2topic.verb.echo import EchoVerb
    import argparse
    verb = EchoVerb()
    preset_before = qos_profile_sensor_data.reliability.name
    for extra in ([], ["--qos-reliability", "reliable"]):
        parser = argparse.ArgumentParser()
        verb.add_arguments(parser, "ros2")
        args = parser.parse_args(["/points"] + extra)
        chosen = verb.choose_qos(laptop, args)
        emit(phase="echo_choose_qos", topic="/points", options=" ".join(extra) or "(none)",
             chosen_reliability=chosen.reliability.name, chosen_durability=chosen.durability.name,
             sensor_data_preset_before=preset_before,
             sensor_data_preset_after=qos_profile_sensor_data.reliability.name)


def phase_echo_cli(robot, topic, extra, seconds=7.0):
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    cmd = ["ros2", "topic", "echo", topic, TYPE_NAMES[topic], "--no-daemon",
           "--field", "header.frame_id", "--csv"] + extra
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    first_pub = robot.seq[topic]
    time.sleep(seconds)
    last_pub = robot.seq[topic]
    proc.send_signal(signal.SIGINT)
    try:
        out, err = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
    seqs = sorted({int(line.strip()[4:]) for line in out.splitlines() if line.strip().startswith("seq=")})
    emit(phase="echo_cli", topic=topic, options=" ".join(extra) or "(none)",
         published_while_running=last_pub - first_pub, received_lines=len(seqs),
         received_span=(seqs[-1] - seqs[0] + 1) if seqs else 0,
         incompatible_warning="incompatible QoS" in err,
         stderr_tail=err.strip().splitlines()[-1][:160] if err.strip() else "")


class LossyRelay(Node):
    """실제 링크 대신 조각 손실 모델을 적용해 다시 발행하는 중계 노드."""

    def __init__(self, max_message):
        super().__init__("wifi_model")
        self.max_message = max_message
        self.loss = 0.0
        self.rng = random.Random()
        self.seed = self.rng.randrange(1 << 30)
        self.rng.seed(self.seed)
        self.sizes = {}
        self.out = {t: self.create_publisher(MSG_TYPES[t], "/wifi" + t, sensor_qos()) for t in TOPICS}
        for topic in TOPICS:
            self.create_subscription(MSG_TYPES[topic], topic, lambda m, t=topic: self.relay(t, m),
                                     sensor_qos())

    def relay(self, topic, msg):
        size = len(serialize_message(msg))
        fragments, datagrams = sample_fragments(size, self.max_message)
        self.sizes[topic] = (size, datagrams, fragments)
        if all(self.rng.random() >= self.loss for _ in range(fragments)):
            self.out[topic].publish(msg)


def phase_link(robot, laptop, relay):
    counters = {t: Counter() for t in TOPICS}
    for topic in TOPICS:
        laptop.create_subscription(MSG_TYPES[topic], "/wifi" + topic, counters[topic], sensor_qos())
    time.sleep(1.5)
    for label, loss in (("wired_control_p0", 0.0), ("wifi_model_p1_32", 1 / 32)):
        relay.loss = loss
        time.sleep(0.3)
        start, end = window(robot)
        for topic in TOPICS:
            size, datagrams, fragments = relay.sizes.get(topic, (0, 0, 0))
            emit(phase="link_emulation", condition=label, fragment_loss=round(loss, 6), seed=relay.seed,
                 topic=topic, serialized_bytes=size, max_message_size=relay.max_message,
                 udp_datagrams_per_sample=datagrams, ip_fragments_per_sample=fragments,
                 model_survival=round((1 - loss) ** fragments, 6) if fragments else None,
                 expected=end[topic] - start[topic], received=counters[topic].in_window(start[topic], end[topic]))


def main():
    rclpy.init()
    with open("/sys/class/net/lo/mtu") as handle:
        lo_mtu = int(handle.read())
    before = reasm_counters()
    emit(phase="env", rmw=os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp (default)"),
         transports=os.environ["FASTDDS_BUILTIN_TRANSPORTS"], discovery_range="LOCALHOST", lo_mtu=lo_mtu,
         python=sys.version.split()[0])
    robot, laptop, relay = Robot(), Node("laptop"), LossyRelay(14720)
    executor = MultiThreadedExecutor(num_threads=4)
    for node in (robot, laptop, relay):
        executor.add_node(node)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    try:
        phase_qos(robot, laptop)
        phase_echo_choose_qos(laptop)
        phase_echo_cli(robot, "/imu/data", [])
        phase_echo_cli(robot, "/imu/data", ["--qos-reliability", "reliable"])
        phase_echo_cli(robot, "/points", [], seconds=6.0)
        phase_link(robot, laptop, relay)
        after = reasm_counters()
        emit(phase="kernel_counters", lo_mtu=lo_mtu,
             delta={k: after[k] - before.get(k, 0) for k in after})
    finally:
        executor.shutdown(timeout_sec=1.0)
        for node in (robot, laptop, relay):
            node.destroy_node()
        rclpy.try_shutdown()
    emit(phase="done", elapsed_s=round(time.monotonic() - T0, 2))


if __name__ == "__main__":
    main()
