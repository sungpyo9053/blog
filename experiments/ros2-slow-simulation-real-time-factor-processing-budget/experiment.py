#!/usr/bin/env python3
"""RTF를 낮추면 느린 노드가 16 Hz 카메라 프레임을 몇 개나 처리하는지 ROS 2 Jazzy에서 잰다.

- 시뮬레이터 역할(자식 프로세스): sim 스텝마다 /clock을 발행하고, sim 시간 T = 1/16 s마다
  std_msgs/Header 프레임을 발행한다. 벽시계 주기 = sim 스텝 / 목표 RTF (gz-sim의 period 계산과
  같은 방식, 늦으면 다음 갱신 시각을 now + period로 재설정). 노드를 기다리지 않는다.
- 처리 노드(부모 프로세스): keep last depth N 구독 콜백에서 프레임마다 벽시계 p초를 쓴다.
- 두 프로세스는 같은 CLOCK_MONOTONIC을 쓰므로 프레임 나이(발행→콜백 시작, 벽시계)를 잴 수 있다.
모든 숫자는 실행 중 측정하거나 아래 식·모델로 계산한다. 결과는 JSON 줄로 출력한다.
"""
import json
import subprocess
import sys
import time

T = 1.0 / 16.0          # 카메라 sim 주기 [s]
STEPS_PER_FRAME = 16    # sim 스텝 = T / 16 (RTF 1에서 /clock 256 Hz)
P_NORMAL = 0.25         # 평소 처리 시간 [s, wall]
P_SPIKE = 0.375         # 튀는 처리 시간 [s, wall]

# (id, 목표 RTF, depth, 처리 방식, 튀는 주기(0=없음), sim 길이 [s])
CONDITIONS = [
    ("A", 1.0, 1, "sleep", 0, 2.0),
    ("B", 0.5, 1, "sleep", 0, 2.0),
    ("C", 0.25, 1, "sleep", 0, 2.0),
    ("D", 1.0, 10, "sleep", 0, 2.0),
    ("E", 0.25, 1, "sleep", 4, 2.0),
    ("F", 0.2, 1, "sleep", 4, 2.0),
    ("G", 0.5, 1, "busy", 0, 2.0),
]


def proc_time(frame_id, spike_every):
    if spike_every and frame_id % spike_every == spike_every - 1:
        return P_SPIKE
    return P_NORMAL


def drain_seconds(depth, spike_every):
    return (depth + 1) * (P_SPIKE if spike_every else P_NORMAL) + 0.3


def model_processed(rtf, depth, spike_every, n):
    """Research와 같은 이산 사건 모델: 도착 k*T/r, keep last depth, 끝나면 큐의 가장 오래된 것부터."""
    arrivals = [k * T / rtf for k in range(n)]
    queue, done, busy_until, k = [], [], 0.0, 0
    now = 0.0
    while k < n or queue:
        if not queue and k < n and arrivals[k] > busy_until:
            busy_until = max(busy_until, arrivals[k])
        now = busy_until
        while k < n and arrivals[k] <= now + 1e-12:   # 같은 시각 도착은 처리 시작 전에 큐에 넣는다
            queue.append(k)
            if len(queue) > depth:
                queue.pop(0)
            k += 1
        if not queue:
            continue
        f = queue.pop(0)
        done.append(f)
        busy_until = now + proc_time(f, spike_every)
    return done


# ---------------------------------------------------------------- 시뮬레이터 프로세스
def run_simulator():
    import rclpy
    from rclpy.node import Node
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import Header

    rclpy.init()
    node = Node("fake_sim")
    clock_pub = node.create_publisher(Clock, "/clock", 10)
    pubs = {c[0]: node.create_publisher(Header, f"/camera_{c[0]}", 10) for c in CONDITIONS}
    deadline = time.monotonic() + 15.0
    while any(p.get_subscription_count() < 1 for p in pubs.values()):
        if time.monotonic() > deadline:
            print(json.dumps({"error": "subscriber discovery timeout"}), flush=True)
            sys.exit(2)
        time.sleep(0.05)
    time.sleep(0.5)

    dt = T / STEPS_PER_FRAME
    sim_ns = 0
    out = []
    for cid, rtf, depth, mode, spike_every, sim_len in CONDITIONS:
        period = dt / rtf
        n_frames = int(round(sim_len / T))
        sim_start_ns = sim_ns
        wall_start = time.monotonic()
        next_update = wall_start
        late_steps = 0
        published = 0
        step = 0
        while published < n_frames:
            now = time.monotonic()
            if now < next_update:
                time.sleep(next_update - now)
            if step % STEPS_PER_FRAME == 0:
                msg = Header()
                msg.stamp.sec, msg.stamp.nanosec = divmod(sim_ns, 1_000_000_000)
                msg.frame_id = f"{published}:{time.monotonic_ns()}"
                pubs[cid].publish(msg)
                published += 1
            clk = Clock()
            clk.clock.sec, clk.clock.nanosec = divmod(sim_ns, 1_000_000_000)
            clock_pub.publish(clk)
            sim_ns += int(round(dt * 1e9))
            step += 1
            next_update += period
            now = time.monotonic()
            if next_update < now:          # gz-sim처럼 늦으면 따라잡지 않고 now + period로 재설정
                next_update = now + period
                late_steps += 1
        wall_end = time.monotonic()
        sim_elapsed = (sim_ns - sim_start_ns) / 1e9
        out.append({"id": cid, "published": published, "sim_elapsed_seconds": round(sim_elapsed, 6),
                    "wall_seconds": round(wall_end - wall_start, 4),
                    "achieved_rtf": round(sim_elapsed / (wall_end - wall_start), 4),
                    "late_steps": late_steps, "steps": step})
        time.sleep(drain_seconds(depth, spike_every))   # sim 일시정지: 남은 큐를 비우는 동안 /clock 멈춤
    for row in out:
        print(json.dumps(row), flush=True)
    node.destroy_node()
    rclpy.shutdown()


# ---------------------------------------------------------------- 처리 노드 프로세스
def run_processor():
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import Header

    t0 = time.monotonic()
    rclpy.init()
    node = Node("slow_detector")
    records = {c[0]: [] for c in CONDITIONS}

    def make_cb(cid, mode, spike_every):
        def cb(msg):
            start = time.monotonic_ns()
            k, pub_ns = (int(x) for x in msg.frame_id.split(":"))
            p = proc_time(k, spike_every)
            if mode == "sleep":
                time.sleep(p)
            else:
                end_at = time.monotonic() + p
                while time.monotonic() < end_at:
                    pass
            end = time.monotonic_ns()
            records[cid].append({"k": k, "age": (start - pub_ns) / 1e9,
                                 "latency": (end - pub_ns) / 1e9, "p": (end - start) / 1e9})
        return cb

    subs = []
    for cid, rtf, depth, mode, spike_every, _ in CONDITIONS:
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=depth,
                         reliability=ReliabilityPolicy.RELIABLE)
        subs.append(node.create_subscription(Header, f"/camera_{cid}", make_cb(cid, mode, spike_every), qos))

    executor = SingleThreadedExecutor()
    executor.add_node(node)
    sim = subprocess.Popen([sys.executable, __file__, "--sim"], stdout=subprocess.PIPE, text=True)
    while sim.poll() is None:
        executor.spin_once(timeout_sec=0.05)
    end_drain = time.monotonic() + 0.5
    while time.monotonic() < end_drain:
        executor.spin_once(timeout_sec=0.05)
    sim_rows = {}
    for line in sim.stdout.read().splitlines():
        row = json.loads(line)
        if "error" in row:
            print(line, flush=True)
            sys.exit(3)
        sim_rows[row["id"]] = row
    if sim.returncode != 0:
        print(json.dumps({"error": f"simulator exit {sim.returncode}"}), flush=True)
        sys.exit(4)

    for cid, rtf, depth, mode, spike_every, sim_len in CONDITIONS:
        s = sim_rows[cid]
        recs = records[cid]
        n = s["published"]
        ids = [r["k"] for r in recs]
        missed = sorted(set(range(n)) - set(ids))
        model = model_processed(rtf, depth, spike_every, n)
        ages = [r["age"] for r in recs]
        lat = [r["latency"] for r in recs]
        ps = [r["p"] for r in recs]
        row = {
            "condition": cid, "target_rtf": rtf, "depth": depth, "processing": mode,
            "spike_every": spike_every, "sim_length_nominal": sim_len,
            "sim_elapsed_seconds": s["sim_elapsed_seconds"], "published": n,
            "processed": len(ids), "dropped": len(missed),
            "processed_ratio": round(len(ids) / n, 4) if n else None,
            "formula_ratio": round(min(1.0, T / (P_NORMAL * rtf)), 4) if not spike_every else None,
            "rtf_bound_normal": round(T / P_NORMAL, 4), "rtf_bound_worst": round(T / P_SPIKE, 4),
            "model_processed": len(model), "model_dropped": n - len(model),
            "achieved_rtf": s["achieved_rtf"], "sim_wall_seconds": s["wall_seconds"],
            "sim_late_steps": s["late_steps"], "sim_steps": s["steps"],
            "callback_p_mean": round(sum(ps) / len(ps), 4) if ps else None,
            "callback_p_max": round(max(ps), 4) if ps else None,
            "frame_age_wall_mean": round(sum(ages) / len(ages), 4) if ages else None,
            "frame_age_wall_max": round(max(ages), 4) if ages else None,
            "result_latency_wall_max": round(max(lat), 4) if lat else None,
            "result_latency_sim_max": round(max(lat) * s["achieved_rtf"], 4) if lat else None,
            "processed_ids": ids, "missed_ids": missed, "model_ids": model,
        }
        print(json.dumps(row), flush=True)
    print(json.dumps({"summary": True, "total_wall_seconds": round(time.monotonic() - t0, 2),
                      "python": sys.version.split()[0]}), flush=True)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    if "--sim" in sys.argv:
        run_simulator()
    else:
        run_processor()
