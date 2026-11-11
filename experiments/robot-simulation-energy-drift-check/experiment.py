#!/usr/bin/env python3
"""ROS 2 Jazzy: read energy drift of a one-joint robot link the way the article says.

A simulator node integrates a torque-free uniform-rod pendulum (one revolute joint) with several
integrators and time steps, then streams 0.1 s samples as /tf (world -> com_<run>) and
/link_state. A separate monitor node computes K + U only from those messages (U from the tf2
height of the centre of mass). Every printed line is a JSON object observed at run time.

Numbers in this file are model inputs (mass, length, g, the article's K0 = 4 J and U0 = 6 J,
damping, time steps, sample interval, potential offsets) and wait limits, not results.
"""
import json
import math
import re
import statistics
import sys
import threading
import time

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from std_msgs.msg import Float64MultiArray
from tf2_ros import Buffer, TransformBroadcaster, TransformListener

T_START = time.monotonic()

# Model inputs (SI units).
MASS = 2.0
LENGTH = 1.0
GRAV = 9.81
INERTIA = MASS * LENGTH ** 2 / 3          # uniform rod about the pivot
INERTIA_COM = MASS * LENGTH ** 2 / 12     # same rod about its centre (used only for the bug case)
K0, U0 = 4.0, 6.0                         # article's illustrative initial energies [J]
DAMPING = 0.02                            # joint viscous damping for the damped runs [N m s/rad]
E_SCALE = MASS * GRAV * LENGTH            # declared before the run: full potential range of the link
PLUS_C = 100.0                            # article's +100 J potential offset

T_END_NS = 10_000_000_000
H_NS = (4_000_000, 2_000_000, 1_000_000)  # h, h/2, h/4
H_REF_NS = 62_500                         # reference trajectory step (h/64)
SAMPLE_NS = 100_000_000                   # log interval sent over ROS
STAMP_OFFSET_NS = 1_000_000_000           # tf2 treats stamp 0 as "latest", so sample stamps start at 1 s
WAIT_S = 2.0
LAST_WINDOW_NS = 2_000_000_000            # "where T happens to fall": min |dE| over the last 2 s
SERIES_EVERY = 10                         # history line: every 10th sample (1 s)

C_GRAV = MASS * GRAV * (LENGTH / 2) / INERTIA


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False, separators=(",", ":")), flush=True)


def r(x, n=4):
    if x is None or isinstance(x, bool):
        return x
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return float(f"{x:.{n}g}")


def version_of(pkg):
    try:
        from ament_index_python.packages import get_package_share_directory
        xml = open(get_package_share_directory(pkg) + "/package.xml").read()
        return re.search(r"<version>([^<]+)</version>", xml).group(1)
    except Exception as exc:  # noqa: BLE001
        return f"unknown:{type(exc).__name__}"


# ---------------------------------------------------------------- dynamics and integrators
def accel(th, om, b):
    return -C_GRAV * math.sin(th) - (b / INERTIA) * om


def energy(th, om):
    return 0.5 * INERTIA * om * om + MASS * GRAV * (LENGTH / 2) * (1 - math.cos(th))


def step_fe(th, om, w, h, b):
    return th + h * om, om + h * accel(th, om, b), w - h * b * om * om


def step_se(th, om, w, h, b):
    om1 = om + h * accel(th, om, b)
    return th + h * om1, om1, w - h * b * om1 * om1


def step_rk4(th, om, w, h, b):
    def f(t_, o_):
        return o_, accel(t_, o_, b), -b * o_ * o_
    k1 = f(th, om)
    k2 = f(th + h / 2 * k1[0], om + h / 2 * k1[1])
    k3 = f(th + h / 2 * k2[0], om + h / 2 * k2[1])
    k4 = f(th + h * k3[0], om + h * k3[1])
    return (th + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
            om + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]),
            w + h / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]))


def step_ie(th, om, w, h, b):
    """Backward Euler: om1 = om + h*accel(th + h*om1, om1), solved by Newton iteration."""
    om1 = om
    for _ in range(50):
        g = om1 - om - h * accel(th + h * om1, om1, b)
        dg = 1 + h * (C_GRAV * h * math.cos(th + h * om1) + b / INERTIA)
        delta = g / dg
        om1 -= delta
        if abs(delta) < 1e-15:
            break
    return th + h * om1, om1, w - h * b * om1 * om1


STEPPERS = {"fe": step_fe, "se": step_se, "rk4": step_rk4, "ie": step_ie}


def simulate(name, h_ns, b, th0, om0):
    """Integrate to T_END; full-step energy statistics plus samples every SAMPLE_NS."""
    step, h = STEPPERS[name], h_ns * 1e-9
    n_steps = T_END_NS // h_ns
    stride = SAMPLE_NS // h_ns
    assert stride * h_ns == SAMPLE_NS and n_steps * h_ns == T_END_NS
    th, om, w = th0, om0, 0.0
    e0 = energy(th, om)
    half = n_steps // 2
    mx = mx1 = mx2 = 0.0
    tail_from = n_steps - LAST_WINDOW_NS // h_ns
    tail_min = math.inf
    t_mx = 0.0
    sign_changes, last_sign = 0, 0
    st = stt = sde = stde = 0.0
    crossings = []
    samples = [(0, 0.0, th, om, w)]
    cpu0 = time.process_time()
    for k in range(1, n_steps + 1):
        th_prev = th
        th, om, w = step(th, om, w, h, b)
        t = k * h_ns * 1e-9
        de = energy(th, om) - e0 - (w if b else 0.0)   # damped runs: ledger residual
        a = abs(de)
        if a > mx:
            mx, t_mx = a, t
        if k >= tail_from:
            tail_min = min(tail_min, a)
        if k <= half:
            mx1 = max(mx1, a)
        else:
            mx2 = max(mx2, a)
        s = (de > 0) - (de < 0)
        if s and last_sign and s != last_sign:
            sign_changes += 1
        if s:
            last_sign = s
        st += t
        stt += t * t
        sde += de
        stde += t * de
        if th_prev < 0 <= th:
            crossings.append(t - h * th / (th - th_prev))
        if k % stride == 0:
            samples.append((k // stride, t, th, om, w))
    cpu_ms = (time.process_time() - cpu0) * 1000
    slope = (n_steps * stde - st * sde) / (n_steps * stt - st * st)
    period = (crossings[-1] - crossings[0]) / (len(crossings) - 1) if len(crossings) > 1 else None
    return {"name": name, "h_ns": h_ns, "b": b, "steps": n_steps, "e0": e0,
            "dE_T": energy(th, om) - e0, "resid_T": energy(th, om) - e0 - w, "w_T": w,
            "mxF": mx, "tmax": t_mx, "tail_min": tail_min, "sgn": sign_changes, "slope": slope,
            "h2h1": (mx2 / mx1) if mx1 else None, "period": period, "cpu_ms": cpu_ms,
            "samples": samples}


# ---------------------------------------------------------------- ROS nodes
class LinkSim(Node):
    def __init__(self):
        super().__init__("link_sim")
        self.tf = TransformBroadcaster(self)
        qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
        self.pub = self.create_publisher(Float64MultiArray, "/link_state", qos)

    def send(self, run_idx, k, t, th, om, w):
        stamp = Time(nanoseconds=STAMP_OFFSET_NS + k * SAMPLE_NS).to_msg()
        tf = TransformStamped()
        tf.header.frame_id = "world"
        tf.header.stamp = stamp
        tf.child_frame_id = f"com_{run_idx}"
        tf.transform.translation.x = (LENGTH / 2) * math.sin(th)
        tf.transform.translation.z = -(LENGTH / 2) * math.cos(th)
        tf.transform.rotation.y = -math.sin(th / 2)      # rotation about y by -theta
        tf.transform.rotation.w = math.cos(th / 2)
        self.tf.sendTransform(tf)
        self.pub.publish(Float64MultiArray(data=[float(run_idx), float(k), t, th, om, w]))


class EnergyMonitor(Node):
    def __init__(self):
        super().__init__("energy_monitor")
        self.buffer = Buffer(cache_time=Duration(seconds=30))
        self.listener = TransformListener(self.buffer, self, spin_thread=False)
        self.cond = threading.Condition()
        self.state = {}
        qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Float64MultiArray, "/link_state", self.on_state, qos)

    def on_state(self, msg):
        run_idx, k = int(msg.data[0]), int(msg.data[1])
        with self.cond:
            self.state[(run_idx, k)] = tuple(msg.data[2:])
            self.cond.notify_all()

    def height(self, run_idx, k):
        stamp = Time(nanoseconds=STAMP_OFFSET_NS + k * SAMPLE_NS)
        return self.buffer.lookup_transform("world", f"com_{run_idx}", stamp).transform.translation.z


def stream(sim, mon, run_idx, result, stats):
    """Send every sample in lock-step; the monitor computes energy terms from messages only."""
    rows = []
    for k, t, th, om, w in result["samples"]:
        t0 = time.monotonic()
        sim.send(run_idx, k, t, th, om, w)
        with mon.cond:
            ok = mon.cond.wait_for(lambda: (run_idx, k) in mon.state, timeout=WAIT_S)
        stamp = Time(nanoseconds=STAMP_OFFSET_NS + k * SAMPLE_NS)
        deadline = time.monotonic() + WAIT_S
        while ok and not mon.buffer.can_transform("world", f"com_{run_idx}", stamp):
            if time.monotonic() > deadline:
                ok = False
                break
            time.sleep(0.0005)
        stats["rtt"].append(time.monotonic() - t0)
        if not ok:
            stats["timeouts"] += 1
            continue
        _, m_th, m_om, m_w = mon.state.pop((run_idx, k))
        z = mon.height(run_idx, k)
        z_prev = mon.height(run_idx, k - 1) if k > 0 else z
        rows.append({"k": k, "th": m_th, "om": m_om, "w": m_w, "z": z, "z_prev": z_prev})
    return rows


def monitor_energy(rows, variant="bottom"):
    out = []
    for row in rows:
        kin = 0.5 * INERTIA * row["om"] ** 2
        u_bottom = MASS * GRAV * (row["z"] + LENGTH / 2)
        if variant == "bottom":
            e = kin + u_bottom
        elif variant == "pivot":
            e = kin + MASS * GRAV * row["z"]
        elif variant == "plus100":
            e = kin + u_bottom + PLUS_C
        elif variant == "bug_inertia":
            e = 0.5 * INERTIA_COM * row["om"] ** 2 + u_bottom
        elif variant == "bug_gravity_sign":
            e = kin - u_bottom
        elif variant == "bug_lag":
            e = kin + MASS * GRAV * (row["z_prev"] + LENGTH / 2)
        out.append(e)
    return out


def ratios(values):
    return [r(values[i] / values[i + 1]) if values[i + 1] else None for i in range(len(values) - 1)]


def orders(values):
    return [r(math.log2(values[i] / values[i + 1]), 3) if values[i] > 0 and values[i + 1] > 0 else None
            for i in range(len(values) - 1)]


def main():
    emit("env", python=sys.version.split()[0], rclpy=version_of("rclpy"), tf2_ros=version_of("tf2_ros_py"),
         rmw=rclpy.utilities.get_rmw_implementation_identifier())

    # Initial joint state from the article's K0 and U0 (computed, not typed in).
    th0 = math.acos(1 - U0 / (MASS * GRAV * LENGTH / 2))
    om0 = math.sqrt(2 * K0 / INERTIA)

    # Reference trajectories (RK4, h/64), undamped and damped.
    ref = {b: simulate("rk4", H_REF_NS, b, th0, om0) for b in (0.0, DAMPING)}
    ref_th = {b: [s[2] for s in ref[b]["samples"]] for b in ref}

    rclpy.init()
    sim, mon = LinkSim(), EnergyMonitor()
    ex = SingleThreadedExecutor()
    ex.add_node(sim)
    ex.add_node(mon)
    def spin():
        try:
            ex.spin()
        except ExternalShutdownException:
            pass

    spinner = threading.Thread(target=spin, daemon=True)
    spinner.start()
    deadline = time.monotonic() + 10
    while (sim.count_subscribers("/tf") < 1 or sim.count_subscribers("/link_state") < 1) \
            and time.monotonic() < deadline:
        time.sleep(0.05)
    time.sleep(0.5)

    plan = [(n, h, 0.0) for n in ("fe", "se", "rk4", "ie") for h in H_NS] + \
           [(n, h, DAMPING) for n in ("fe", "rk4") for h in H_NS]
    stats = {"rtt": [], "timeouts": 0}
    results = []
    wall0 = time.monotonic()
    for idx, (name, h_ns, b) in enumerate(plan):
        res = simulate(name, h_ns, b, th0, om0)
        res["id"] = f"{name}_h{h_ns // 1_000_000}" + ("_b" if b else "")
        res["rows"] = stream(sim, mon, idx, res, stats)
        results.append(res)
    wall_ros = time.monotonic() - wall0

    def th_err(res):
        ref_series = ref_th[res["b"]]
        errs = [abs(row["th"] - ref_series[row["k"]]) for row in res["rows"]]
        return max(errs), errs[-1]

    # Undamped runs: energy as the monitor sees it.
    cols = ["id", "steps", "E0mon", "dE_T", "pct", "mxF", "mxS", "tmax", "endmax", "min2s", "sgn", "slope", "h2h1",
            "thE", "thT", "perE", "cpu_ms", "mon_sim"]
    rows = []
    by = {}
    for res in results:
        if res["b"]:
            continue
        e = monitor_energy(res["rows"])
        de = [x - e[0] for x in e]
        mx_s = max(abs(x) for x in de)
        the, tht = th_err(res)
        per_e = (res["period"] - ref[0.0]["period"]) if res["period"] and ref[0.0]["period"] else None
        rows.append([res["id"], res["steps"], r(e[0], 6), r(de[-1]), r(100 * de[-1] / abs(e[0])), r(res["mxF"]),
                     r(mx_s), r(res["tmax"]), r(abs(res["dE_T"]) / res["mxF"]) if res["mxF"] else None,
                     r(res["tail_min"] / res["mxF"]) if res["mxF"] else None, res["sgn"], r(res["slope"]),
                     r(res["h2h1"]), r(the), r(tht), r(per_e), r(res["cpu_ms"], 3), r(abs(de[-1] - res["dE_T"]), 2)])
        by.setdefault(res["name"], []).append((res, de, the, mx_s))
    series = {res["id"]: (res["rows"], de) for lst in by.values() for res, de, _, _ in lst if res["h_ns"] == H_NS[0]}
    first_rows = next(iter(series.values()))[0]
    emit("series", note="monitor dE [J] every 1 s, h = 4 ms",
         t_s=[r(row["k"] * SAMPLE_NS * 1e-9) for row in first_rows[::SERIES_EVERY]],
         dE={rid: [r(d) for d in de[::SERIES_EVERY]] for rid, (_, de) in series.items()})
    emit("runs", T_s=T_END_NS * 1e-9, sample_s=SAMPLE_NS * 1e-9, cols=cols, rows=rows)

    ocols = ["int", "r_mxF", "p_mxF", "r_dET", "r_mxS", "r_thE"]
    orows = []
    for name, lst in by.items():
        mxf = [x[0]["mxF"] for x in lst]
        orows.append([name, ratios(mxf), orders(mxf), ratios([abs(x[0]["dE_T"]) for x in lst]),
                      ratios([x[3] for x in lst]), ratios([x[2] for x in lst])])
    emit("order", note="ratio of value at h to value at h/2, then h/2 to h/4", cols=ocols, rows=orows)

    # Potential zero points on the same logs.
    zrows, zdiff = [], 0.0
    for res in results:
        if res["b"] or res["h_ns"] != H_NS[0] or res["name"] not in ("fe", "se"):
            continue
        des = []
        for variant in ("bottom", "pivot", "plus100"):
            e = monitor_energy(res["rows"], variant)
            de = e[-1] - e[0]
            des.append(de)
            zrows.append([res["id"], variant, r(e[0], 6), r(de), r(100 * de / abs(e[0])), r(de / E_SCALE)])
        zdiff = max(zdiff, max(des) - min(des))
    emit("zero", E_scale=r(E_SCALE, 6), cols=["id", "zero", "E0", "dE_T", "pct", "dE_over_Escale"], rows=zrows,
         max_dE_diff=r(zdiff, 2))

    # Damped runs: K+U falls physically; the ledger residual should converge to zero.
    dcols = ["id", "dE_T", "pct", "Wnc_T", "resid_T", "mx_resid_full", "mx_resid_log", "thE"]
    drows, dres = [], {}
    for res in results:
        if not res["b"]:
            continue
        e = monitor_energy(res["rows"])
        de = [x - e[0] for x in e]
        resid = [de[i] - res["rows"][i]["w"] for i in range(len(de))]
        the, _ = th_err(res)
        drows.append([res["id"], r(de[-1]), r(100 * de[-1] / abs(e[0])), r(res["rows"][-1]["w"]), r(resid[-1]),
                      r(res["mxF"]), r(max(abs(x) for x in resid)), r(the)])
        dres.setdefault(res["name"], []).append((de[-1], res["mxF"]))
    ref_d = ref[DAMPING]
    emit("damped", b=DAMPING, ref_dE_T=r(ref_d["dE_T"], 6), ref_Wnc_T=r(ref_d["w_T"], 6),
         cols=dcols, rows=drows,
         conv={n: {"r_mx_resid": ratios([x[1] for x in v]),
                   "dE_T_spread": r(max(x[0] for x in v) - min(x[0] for x in v))} for n, v in dres.items()})

    # Bookkeeping mistakes on the RK4 logs: does shrinking h help?
    brows = []
    rk4 = [res for res in results if res["name"] == "rk4" and not res["b"]]
    for variant in ("bottom", "bug_inertia", "bug_gravity_sign", "bug_lag"):
        mxs = []
        for res in rk4:
            e = monitor_energy(res["rows"], variant)
            mxs.append(max(abs(x - e[0]) for x in e))
        brows.append([variant, [r(x) for x in mxs], ratios(mxs)])
    emit("bug", runs=[res["id"] for res in rk4], cols=["energy", "mxS_by_h", "ratio"], rows=brows)

    emit("reference", h_ms=H_REF_NS / 1e6, th0_deg=r(math.degrees(th0), 6), om0=r(om0, 6),
         mxF=r(ref[0.0]["mxF"], 3), period=r(ref[0.0]["period"], 6), cpu_ms=r(ref[0.0]["cpu_ms"], 3))
    rtt = sorted(stats["rtt"])
    emit("ros", samples=len(rtt), timeouts=stats["timeouts"], wall_s=r(wall_ros, 3),
         rtt_ms_median=r(1000 * statistics.median(rtt), 3), rtt_ms_max=r(1000 * rtt[-1], 3))

    # Stop the spin thread before tearing down nodes; destroying them mid-spin aborted one trial run.
    rclpy.try_shutdown()
    spinner.join(timeout=5)
    ex.shutdown(timeout_sec=2)
    sim.destroy_node()
    mon.destroy_node()
    emit("done", seconds=r(time.monotonic() - T_START, 3))
    return 0 if stats["timeouts"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
