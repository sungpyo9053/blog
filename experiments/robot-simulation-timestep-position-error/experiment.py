#!/usr/bin/env python3
"""시간 간격(Δt)에 따라 1초 뒤 위치가 달라지는지를 ROS 2 TF 경로로 잰다.

  sim      : 1차원 등가속도 물체를 적분기(전진 오일러·준암시적 오일러·운동학식)로 갱신한다.
             방송하는 단계마다 world -> <시나리오> TF(translation.x = x)와 /sim_state [번호, 단계, x, v]를 보낸다.
             observer가 그 단계를 받은 것을 확인한 뒤 다음 단계로 간다(락스텝).
  observer : tf2_ros.Buffer에서 t=1.0 s, t=0.75 s, 최신 시각의 위치를 조회한다.

입력(a=2 m/s², T=1 s, x0=0, v0=0, Δt 목록)만 정하고 결과는 정하지 않는다. 기준값은 실행 중에
Fraction으로 계산한다. 결과는 JSON 줄로 출력한다.
"""
import json
import math
import statistics
import threading
import time
from fractions import Fraction

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.time import Time
from rclpy.utilities import get_rmw_implementation_identifier
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Float64MultiArray
from tf2_ros import Buffer, TransformBroadcaster, TransformListener

A = 2.0          # m/s²
T = 1.0          # s
X0 = 0.0         # m
V0 = 0.0         # m/s
A_F, T_F, X0_F, V0_F = Fraction(2), Fraction(1), Fraction(0), Fraction(0)
TOL = 1e-12      # 글의 assertion 허용치
STEP_TIMEOUT = 2.0


def step(method, x, v, dt, a):
    if method == "fe":       # 전진 오일러: 현재 속도로 위치, 그다음 속도
        return x + v * dt, v + a * dt
    if method == "si":       # 준암시적 오일러: 새 속도로 위치
        v2 = v + a * dt
        return x + v2 * dt, v2
    if method == "kin":      # 구간 안 일정 가속도 반영
        return x + v * dt + a * dt * dt / 2, v + a * dt
    raise ValueError(method)


def replay(method, dt, steps):
    x, v = X0_F, V0_F
    for _ in range(steps):
        x, v = step(method, x, v, dt, A_F)
    return x, v


def scenario(name, method, dt, dt_intended, stamp="count", every=1, probes=(1.0,), trace=False):
    return dict(name=name, method=method, dt=dt, dt_f=dt_intended, stamp=stamp, every=every,
                probes=probes, trace=trace)


SCENARIOS = []
ROS_FE_MAX_K = 8   # ROS 락스텝은 2⁻⁸까지, 더 작은 Δt는 cpu_cost 반복문으로 잰다
for k in range(1, ROS_FE_MAX_K + 1):
    SCENARIOS.append(scenario(f"fe_{k}", "fe", 2.0 ** -k, Fraction(1, 2 ** k), trace=(k == 2)))
for method in ("si", "kin"):
    for k in (1, 2, 3):
        SCENARIOS.append(scenario(f"{method}_{k}", method, 2.0 ** -k, Fraction(1, 2 ** k)))
SCENARIOS += [
    scenario("nd_0.3_count", "fe", 0.3, Fraction(3, 10)),
    scenario("nd_0.1_count", "fe", 0.1, Fraction(1, 10)),
    scenario("nd_0.1_accum", "fe", 0.1, Fraction(1, 10), stamp="accum"),
    scenario("nd_1/3_count", "fe", 1.0 / 3.0, Fraction(1, 3)),
    scenario("nd_1/3_accum", "fe", 1.0 / 3.0, Fraction(1, 3), stamp="accum"),
    scenario("pub_dt0.5_every1", "fe", 0.5, Fraction(1, 2), probes=(1.0, 0.75)),
    scenario("pub_dt0.125_every4", "fe", 0.125, Fraction(1, 8), every=4, probes=(1.0, 0.75)),
    scenario("pub_dt0.125_every1", "fe", 0.125, Fraction(1, 8), probes=(1.0, 0.75)),
]


def frame_of(name):
    return "s_" + name.replace(".", "p").replace("/", "_")


def r12(value):
    return None if value is None else round(value, 12)


class Observer:
    def __init__(self):
        self.node = rclpy.create_node("observer")
        self.buffer = Buffer(node=self.node)
        self.listener = TransformListener(self.buffer, self.node)
        self.lock = threading.Lock()
        self.states = {}
        self.arrived = threading.Condition(self.lock)
        self.node.create_subscription(Float64MultiArray, "/sim_state", self.on_state, 100)

    def on_state(self, msg):
        idx, k, x, v = msg.data
        with self.lock:
            self.states[(int(idx), int(k))] = (x, v)
            self.arrived.notify_all()

    def wait_state(self, idx, k, timeout):
        with self.arrived:
            return self.arrived.wait_for(lambda: (idx, k) in self.states, timeout)

    def lookup(self, frame, when):
        try:
            t = self.buffer.lookup_transform("world", frame, when)
            stamp = Time.from_msg(t.header.stamp).nanoseconds
            return {"x": t.transform.translation.x, "stamp_ns": stamp}
        except Exception as exc:  # tf2 예외 이름을 그대로 기록한다
            return {"error": type(exc).__name__, "msg": str(exc)[:90]}


class Sim:
    def __init__(self):
        self.node = rclpy.create_node("sim")
        self.tf = TransformBroadcaster(self.node)
        self.state = self.node.create_publisher(Float64MultiArray, "/sim_state", 100)

    def emit(self, idx, k, frame, stamp, x, v):
        t = TransformStamped()
        t.header.stamp = stamp.to_msg()
        t.header.frame_id = "world"
        t.child_frame_id = frame
        t.transform.translation.x = x
        t.transform.rotation.w = 1.0
        self.tf.sendTransform(t)
        self.state.publish(Float64MultiArray(data=[float(idx), float(k), x, v]))


def wait_until(predicate, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.0005)
    return predicate()


def run(sim, obs, idx, sc):
    frame = frame_of(sc["name"])
    dt, method = sc["dt"], sc["method"]
    steps = int(T / dt)                 # 글의 코드와 같은 단계 수 규칙
    x, v, t_acc = X0, V0, 0.0
    timeouts, sent, last_stamp = 0, 0, None
    computed = {}                       # 시뮬레이터가 실제로 계산한 (stamp_ns -> x)
    started = time.perf_counter()
    for k in range(0, steps + 1):
        if k > 0:
            x, v = step(method, x, v, dt, A)
            t_acc += dt
        if sc["stamp"] == "count":
            stamp = Time(nanoseconds=round(k * dt * 1e9))
        else:
            stamp = Time(seconds=t_acc)
        computed[stamp.nanoseconds] = x
        if k % sc["every"] != 0:
            continue
        sim.emit(idx, k, frame, stamp, x, v)
        sent += 1
        last_stamp = stamp
        ok = obs.wait_state(idx, k, STEP_TIMEOUT) and wait_until(
            lambda: obs.buffer.can_transform("world", frame, stamp), STEP_TIMEOUT)
        timeouts += 0 if ok else 1
    wall_ms = (time.perf_counter() - started) * 1000
    final_k = steps - steps % sc["every"]
    rx = obs.states.get((idx, final_k), (None, None))
    probes = {str(p): obs.lookup(frame, Time(nanoseconds=round(p * 1e9))) for p in sc["probes"]}
    latest = obs.lookup(frame, Time())
    exact_ref = X0_F + V0_F * T_F + A_F * T_F * T_F / 2
    rep_bin_x, rep_bin_v = replay(method, Fraction(dt), steps)       # float Δt의 정확한 2진 값
    rep_int_x, rep_int_v = replay(method, sc["dt_f"], steps)         # 의도한 Δt
    res = dict(name=sc["name"], dt=dt, steps=steps, sent=sent, timeouts=timeouts, wall_ms=round(wall_ms, 2),
               x_sim=x, v_sim=v, x_rx=rx[0], v_rx=rx[1], t_accum=t_acc,
               last_stamp_ns=last_stamp.nanoseconds if last_stamp else None,
               probes=probes, latest=latest,
               ref=float(exact_ref),
               end_time_intended=float(steps * sc["dt_f"]),
               float_minus_replay_bin=float(Fraction(x) - rep_bin_x),
               float_minus_replay_intended=float(Fraction(x) - rep_int_x),
               v_minus_replay_intended=float(Fraction(v) - rep_int_v))
    if method == "fe":
        formula = (A_F / 2) * (T_F * T_F - T_F * sc["dt_f"])           # 글의 식 (a/2)(T²−TΔt)
        res["formula"] = float(formula)
        res["minus_formula"] = float(Fraction(x) - formula)
        res["article_assert_ok"] = abs(x - float(formula)) <= TOL and abs(v - 2.0) <= TOL
    if sc["trace"]:
        res["trace_tf"] = []
        for ns in sorted(computed):
            got = obs.lookup(frame, Time(nanoseconds=ns))
            res["trace_tf"].append([ns / 1e9, got.get("x"), computed[ns]])
    if sc["every"] > 1 or "0.75" in probes:
        res["computed_at_0.75"] = computed.get(750_000_000)
    return res


def cpu_cost():
    rows = []
    for k in range(1, 17):
        dt = 2.0 ** -k
        steps = int(T / dt)
        samples = []
        x = v = 0.0
        for _ in range(7):
            began = time.perf_counter()
            x, v = X0, V0
            for _ in range(steps):
                x, v = x + v * dt, v + A * dt
            samples.append(time.perf_counter() - began)
        med = statistics.median(samples)
        rows.append([k, dt, steps, round(med * 1e6, 2), round(med * 1e9 / steps, 1), 1.0 - x])
    for i in range(1, len(rows)):
        rows[i].append(round(rows[i][3] / rows[i - 1][3], 3) if rows[i - 1][3] else None)
    rows[0].append(None)
    return rows


def main():
    began = time.monotonic()
    rclpy.init()
    obs, sim = Observer(), Sim()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(obs.node)
    executor.add_node(sim.node)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    matched = wait_until(lambda: sim.node.count_subscribers("/tf") >= 1
                         and sim.state.get_subscription_count() >= 1, 10.0)
    time.sleep(0.5)

    results = [run(sim, obs, i, sc) for i, sc in enumerate(SCENARIOS)]
    by = {r["name"]: r for r in results}

    def x_at(r, p="1.0"):
        return r["probes"][p].get("x")

    fe_rows = []
    prev_err = None
    for k in range(1, ROS_FE_MAX_K + 1):
        r = by[f"fe_{k}"]
        x_tf = x_at(r)
        err = None if x_tf is None else r["ref"] - x_tf
        ratio = None if (prev_err in (None, 0) or err is None) else prev_err / err
        order = None if not ratio or ratio <= 0 else math.log2(ratio)
        fe_rows.append([r["dt"], r["steps"], x_tf, r["v_rx"], err, r["minus_formula"], ratio, order,
                        r["float_minus_replay_bin"], r["article_assert_ok"], r["sent"], r["timeouts"], r["wall_ms"]])
        prev_err = err
    print(json.dumps({"line": "forward_convergence", "ref_x": by["fe_1"]["ref"],
                      "cols": ["dt", "steps", "x_tf_at_1", "v_rx", "err", "minus_formula", "ratio_prev_over_this",
                               "order", "float_minus_fraction", "article_assert_ok", "tf_sent", "timeouts", "wall_ms"],
                      "rows": fe_rows,
                      "trace_dt0.25": [[r12(a), r12(b), r12(c)] for a, b, c in by["fe_2"]["trace_tf"]],
                      "trace_cols": ["t", "x_tf", "x_sim"],
                      "trace_note": "t=0 is queried as Time(0), which tf2 treats as latest"}, ensure_ascii=False))

    integ = []
    for method in ("fe", "si", "kin"):
        for k in (1, 2, 3):
            r = by[f"{method}_{k}"]
            x_tf = x_at(r)
            integ.append([method, r["dt"], x_tf, r["v_rx"], None if x_tf is None else x_tf - r["ref"],
                          r["float_minus_replay_bin"], r["timeouts"]])
    print(json.dumps({"line": "integrators", "cols": ["method", "dt", "x_tf_at_1", "v_rx", "x_minus_ref",
                                                       "float_minus_fraction", "timeouts"],
                      "rows": integ}, ensure_ascii=False))

    nd = []
    for name in ("nd_0.3_count", "nd_0.1_count", "nd_0.1_accum", "nd_1/3_count", "nd_1/3_accum"):
        r = by[name]
        at1 = r["probes"]["1.0"]
        nd.append({"name": name, "steps": r["steps"], "end_time_intended": r["end_time_intended"],
                   "t_accum": r["t_accum"], "last_stamp_ns": r["last_stamp_ns"],
                   "lookup_at_1": at1, "latest": r["latest"], "x_sim": r["x_sim"], "v_sim": r["v_sim"],
                   "err_vs_ref": r["ref"] - r["x_sim"], "formula": r["formula"],
                   "minus_formula": r["minus_formula"], "float_minus_fraction_bin": r["float_minus_replay_bin"],
                   "within_1e-12": r["article_assert_ok"], "v_minus_2": r["v_sim"] - 2.0,
                   "timeouts": r["timeouts"]})
    print(json.dumps({"line": "nondividing", "rows": nd}, ensure_ascii=False))

    pub = []
    for name in ("pub_dt0.5_every1", "pub_dt0.125_every4", "pub_dt0.125_every1"):
        r = by[name]
        pub.append({"name": name, "tf_sent": r["sent"], "at_1.0": x_at(r), "at_0.75": x_at(r, "0.75"),
                    "at_0.75_err": r["probes"]["0.75"].get("error"),
                    "sim_computed_at_0.75": r.get("computed_at_0.75"),
                    "err_at_1": None if x_at(r) is None else r["ref"] - x_at(r), "timeouts": r["timeouts"]})
    print(json.dumps({"line": "publish_rate", "ref_at_0.75": float(A_F * Fraction(3, 4) ** 2 / 2),
                      "rows": pub}, ensure_ascii=False))

    print(json.dumps({"line": "cpu_cost", "note": "pure Python forward Euler loop, median of 7",
                      "cols": ["k", "dt", "steps", "median_us", "ns_per_step", "err_at_1", "time_ratio_vs_prev"],
                      "rows": cpu_cost()}, ensure_ascii=False))

    tf_ok = all(r["timeouts"] == 0 for r in results)
    print(json.dumps({"line": "summary", "rmw": get_rmw_implementation_identifier(), "matched": matched,
                      "inputs": {"a": A, "T": T, "x0": X0, "v0": V0}, "scenarios": len(results),
                      "tf_messages": sum(r["sent"] for r in results), "all_steps_received": tf_ok,
                      "tf_x_equals_sim_x": all(x_at(r) == r["x_sim"] for r in results if x_at(r) is not None
                                               and r["probes"]["1.0"].get("stamp_ns") == r["last_stamp_ns"]),
                      "elapsed_s": round(time.monotonic() - began, 2)}, ensure_ascii=False))
    executor.shutdown()
    obs.node.destroy_node()
    sim.node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
