"""Same-host half of the ROS 2 discovery table, measured with real rclpy nodes.

Two worker processes (node A, node B) run in one container. For each of the 36 cells
(A setting x B setting) both workers open their own rclpy Context with the cell's
ROS_AUTOMATIC_DISCOVERY_RANGE / ROS_STATIC_PEERS, in a ROS_DOMAIN_ID reserved for that
cell, then watch the ROS graph and a String topic from the other side. Every time and
count printed below is measured while running; nothing is precomputed.
"""
import json
import os
import re
import subprocess
import sys
import time

RANGES = ("OFF", "LOCALHOST", "SUBNET")
# Table order of the official doc: rows 1-3 without static peers, rows 4-6 with them.
SETTINGS = [(peer, rng) for peer in (False, True) for rng in RANGES]
PEER = "127.0.0.1"          # the only interface in a --network none container
DOMAIN_BASE = 20            # cell k uses domain DOMAIN_BASE + k
BATCH = 9                   # cells per worker pair
WINDOW = 4.0                # seconds each worker watches after its nodes exist
TICK = 0.1
# Exact rcl (Jazzy) log texts. The two debug lines report what rcl_init actually decided.
OFF_PEER_WARN = "ROS_STATIC_PEERS will be ignored"
INVALID_WARN = "Invalid value"
LOCALHOST_ONLY_WARN = "'localhost_only' is enabled"
EFFECTIVE_RANGE = re.compile(r"Automatic discovery range is (\S+) \(")
EFFECTIVE_PEERS = re.compile(r"Static peers count is (\d+)")


def label(setting):
    peer, rng = setting
    return ("p" if peer else "-") + rng[0]


def worker(role, cells, window):
    """cells: list of [domain, range, peer_or_empty, localhost_only]."""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from std_msgs.msg import String

    other = "b" if role == "a" else "a"
    from rclpy.logging import LoggingSeverity, set_logger_level

    started = time.monotonic()
    slots = []
    # rcl_init logs the effective range / peer count at DEBUG before rclpy configures logging,
    # so raise the "rcl" logger level up front as well as through --ros-args.
    try:
        set_logger_level("rcl", LoggingSeverity.DEBUG)
    except Exception as exc:  # noqa: BLE001 - reported, not hidden
        print(json.dumps({"log_level_error": repr(exc)}), flush=True)
    for domain, rng, peer, localhost_only in cells:
        # rcl reads these variables inside rclpy.init(), so each Context keeps its own.
        os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = rng
        for key, value in (("ROS_STATIC_PEERS", peer), ("ROS_LOCALHOST_ONLY", localhost_only)):
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        ctx = Context()
        rclpy.init(args=["--ros-args", "--log-level", "rcl:=debug"], context=ctx, domain_id=domain)
        node = rclpy.create_node(f"node_{role}", context=ctx)
        slot = {"d": domain, "node": node, "ctx": ctx, "seen": None, "rx": None, "n": 0}
        node.create_subscription(String, f"probe_{other}",
                                 lambda msg, s=slot: s.update(n=s["n"] + 1), 10)
        slot["pub"] = node.create_publisher(String, f"probe_{role}", 10)
        slot["ex"] = SingleThreadedExecutor(context=ctx)
        slot["ex"].add_node(node)
        slots.append(slot)
    ready = time.monotonic()
    with open("/proc/self/status") as status:
        threads = next(int(line.split()[1]) for line in status if line.startswith("Threads:"))
    seq = 0
    while time.monotonic() - ready < window:
        seq += 1
        for slot in slots:
            slot["pub"].publish(String(data=f"{role}{slot['d']}#{seq}"))
            slot["ex"].spin_once(timeout_sec=0)
            now = round(time.monotonic() - ready, 2)
            if slot["seen"] is None and any(
                    name == f"node_{other}" for name, _ in slot["node"].get_node_names_and_namespaces()):
                slot["seen"] = now
            if slot["rx"] is None and slot["n"] > 0:
                slot["rx"] = now
        time.sleep(TICK)
    for slot in slots:
        print(json.dumps({"d": slot["d"], "seen": slot["seen"], "rx": slot["rx"], "n": slot["n"]}), flush=True)
    print(json.dumps({"worker": role, "setup_s": round(ready - started, 2), "threads": threads}), flush=True)
    for slot in slots:
        slot["ex"].shutdown()
        slot["node"].destroy_node()
        rclpy.try_shutdown(context=slot["ctx"])


def run_pair(a_cells, b_cells, window):
    procs = {}
    for role, cells in (("a", a_cells), ("b", b_cells)):
        procs[role] = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--worker", role, json.dumps(cells), str(window)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = {}
    for role, proc in procs.items():
        stdout, stderr = proc.communicate(timeout=40)
        rows = [json.loads(line) for line in stdout.splitlines() if line.startswith("{")]
        # Contexts are initialised in order, so the n-th debug pair belongs to the n-th cell.
        ranges = [r.split("_")[-1] for r in EFFECTIVE_RANGE.findall(stderr)]
        peers = [int(n) for n in EFFECTIVE_PEERS.findall(stderr)]
        cells = role == "a" and a_cells or b_cells
        effective = {}
        if len(ranges) == len(cells) and len(peers) == len(cells):
            effective = {c[0]: (rng, n) for c, rng, n in zip(cells, ranges, peers)}
        out[role] = {"cells": {r["d"]: r for r in rows if "d" in r}, "eff": effective,
                     "log_errors": [r for r in rows if "log_level_error" in r],
                     "meta": next((r for r in rows if "worker" in r), {}),
                     "code": proc.returncode, "stderr": stderr}
    return out


def fmt_eff(side):
    """Effective setting rcl reported, e.g. 'L1' = LOCALHOST with one static peer."""
    return None if side.get("eff") is None else f"{side['eff'][0][0]}{side['eff'][1]}"


def same_host_rule(a, b):
    """research.md rule for the same-host table: O unless either side is OFF."""
    return a[1] != "OFF" and b[1] != "OFF"


def main():
    t0 = time.monotonic()
    cells = [(i, j) for i in range(len(SETTINGS)) for j in range(len(SETTINGS))]
    result, warn_seen, warn_expected, meta = {}, 0, 0, []
    eff_missing = eff_range_mismatch = off_peer_dropped = peer_kept = log_errors = 0
    for start in range(0, len(cells), BATCH):
        batch = cells[start:start + BATCH]
        side = {"a": [], "b": []}
        for i, j in batch:
            domain = DOMAIN_BASE + i * len(SETTINGS) + j
            for role, (peer, rng) in (("a", SETTINGS[i]), ("b", SETTINGS[j])):
                side[role].append([domain, rng, PEER if peer else "", ""])
                warn_expected += int(peer and rng == "OFF")
        out = run_pair(side["a"], side["b"], WINDOW)
        for role in "ab":
            warn_seen += out[role]["stderr"].count(OFF_PEER_WARN)
            meta.append(dict(out[role]["meta"], code=out[role]["code"]))
            if out[role]["code"] != 0:
                print(json.dumps({"worker_error": role, "stderr": out[role]["stderr"][-600:]}), flush=True)
        for (i, j), a_cell, b_cell in zip(batch, side["a"], side["b"]):
            domain = a_cell[0]
            result[(i, j)] = tuple(dict(out[r]["cells"].get(domain, {}), eff=out[r]["eff"].get(domain))
                                   for r in "ab")
            for r, (peer, rng) in (("a", SETTINGS[i]), ("b", SETTINGS[j])):
                eff = out[r]["eff"].get(domain)
                if eff is None:
                    eff_missing += 1
                    continue
                eff_range_mismatch += eff[0] != rng
                if peer and rng == "OFF":
                    off_peer_dropped += eff[1] == 0
                elif peer:
                    peer_kept += eff[1] == 1
            log_errors += len(out["a"]["log_errors"]) + len(out["b"]["log_errors"])

    rows_ok, rows_seen, mismatch, asym, partial, seen_times, rx_times = [0] * 6, [0] * 6, [], 0, [], [], []
    for (i, j), (a, b) in sorted(result.items()):
        seen = a.get("seen") is not None and b.get("seen") is not None
        ok = seen and a.get("rx") is not None and b.get("rx") is not None
        pred = same_host_rule(SETTINGS[i], SETTINGS[j])
        rows_ok[i] += ok
        rows_seen[i] += seen
        if ok != pred:
            mismatch.append([label(SETTINGS[i]), label(SETTINGS[j])])
        if (a.get("seen") is None) != (b.get("seen") is None) or (a.get("rx") is None) != (b.get("rx") is None):
            partial.append([label(SETTINGS[i]), label(SETTINGS[j])])
        if ok:
            seen_times += [a["seen"], b["seen"]]
            rx_times += [a["rx"], b["rx"]]
        print(json.dumps({"A": label(SETTINGS[i]), "B": label(SETTINGS[j]), "ae": fmt_eff(a), "be": fmt_eff(b),
                          "as": a.get("seen"), "bs": b.get("seen"),
                          "ar": a.get("rx"), "br": b.get("rx"), "an": a.get("n"), "bn": b.get("n"),
                          "ok": int(ok), "pred": int(pred)}), flush=True)
    def cell_ok(key):
        return all(side.get(k) is not None for side in result[key] for k in ("seen", "rx"))
    # The table is claimed symmetric: swapping A and B settings must not change O/X.
    asym = sum(cell_ok((i, j)) != cell_ok((j, i)) for i, j in result if i < j)
    sweep_s = round(time.monotonic() - t0, 2)

    # Traps outside the table: each runs alone so its stderr warnings belong to one setting.
    traps = {"lowercase_subnet": ["subnet", "", ""], "localhost_only_1": ["SUBNET", PEER, "1"]}
    trap_rows = []
    for k, (name, (rng, peer, lo)) in enumerate(traps.items()):
        domain = DOMAIN_BASE + len(cells) + k
        out = run_pair([[domain, rng, peer, lo]], [[domain, "SUBNET", "", ""]], WINDOW)
        a = out["a"]["cells"].get(domain, {})
        b = out["b"]["cells"].get(domain, {})
        err = out["a"]["stderr"]
        eff = out["a"]["eff"].get(domain)
        trap_rows.append({"trap": name, "ae": None if eff is None else f"{eff[0]}/{eff[1]}",
                          "invalid_warn": err.count(INVALID_WARN),
                          "localhost_only_warn": err.count(LOCALHOST_ONLY_WARN),
                          "as": a.get("seen"), "bs": b.get("seen"), "ar": a.get("rx"), "br": b.get("rx"),
                          "code": [out["a"]["code"], out["b"]["code"]]})
    for row in trap_rows:
        print(json.dumps(row), flush=True)

    print(json.dumps({
        "summary": "same_host_table",
        "cells": len(result),
        "o_cells": sum(rows_ok),
        "o_by_row": rows_ok,
        "seen_by_row": rows_seen,
        "rule_mismatch": mismatch,
        "asymmetric_cells": asym,
        "one_sided_cells": partial,
        "off_peer_warnings": warn_seen,
        "off_peer_contexts": warn_expected,
        "off_peer_contexts_peers_dropped": off_peer_dropped,
        "peer_contexts_not_off_peer_kept": peer_kept,
        "effective_range_mismatch": eff_range_mismatch,
        "effective_missing": eff_missing,
        "log_level_errors": log_errors,
        "first_seen_s_min_max": [min(seen_times), max(seen_times)] if seen_times else None,
        "first_rx_s_min_max": [min(rx_times), max(rx_times)] if rx_times else None,
        "worker_setup_s_max": max(m.get("setup_s", 0) for m in meta),
        "worker_threads_max": max(m.get("threads", 0) for m in meta),
        "worker_failures": sum(m["code"] != 0 for m in meta),
        "window_s": WINDOW,
        "sweep_s": sweep_s,
        "total_s": round(time.monotonic() - t0, 2),
        "rmw": os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp(default)"),
    }), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker(sys.argv[2], json.loads(sys.argv[3]), float(sys.argv[4]))
    else:
        main()
