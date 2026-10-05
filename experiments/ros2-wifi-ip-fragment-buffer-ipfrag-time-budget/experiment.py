#!/usr/bin/env python3
"""IP fragment reassembly buffer: how fast it fills and how long large datagrams stall.

Runs inside ros:jazzy-ros-base with --network none. Everything goes over loopback.
A raw socket (CAP_NET_RAW, granted by Docker by default) sends hand-built IPv4
fragments of UDP datagrams to 127.0.0.1. To imitate the ROS 2 DDS tuning document's
worst case on a lossy Wi-Fi link, every datagram of a "1 MiB, 10 Hz" ROS message
loses its last IP fragment, so the kernel has to hold the rest until ipfrag_time.

Measured at run time from the kernel itself:
  - ipfrag_high_thresh / ipfrag_time of this network namespace (read only)
  - FRAG memory and queue count (/proc/net/sockstat) and Ip Reasm* counters (/proc/net/snmp)
  - per-fragment memory charge (truesize) and per-incomplete-64K-datagram charge
  - when the kernel starts refusing fragments, and how long a complete large
    datagram stays undeliverable while a small unfragmented one still arrives

Every number printed is either read from the kernel, timed with time.monotonic(),
or computed from those readings. Each output line is one JSON object.
"""
import json
import os
import select
import socket
import struct
import time

from rclpy.serialization import serialize_message
from std_msgs.msg import UInt8MultiArray

MSG_DATA_BYTES = 1024 * 1024      # assumed topic: 1 MiB payload ...
RATE_HZ = 10                      # ... published at 10 Hz (research.md worst-case example)
FILL_MESSAGES = 10                # one second of publishing
UDP_PAYLOAD = 65500               # research.md assumption for a ~64 kB DDS datagram
IP_MTU = 1500                     # Ethernet / Wi-Fi default MTU
FRAG_DATA = (IP_MTU - 20) // 8 * 8  # 1480 bytes of IP payload per fragment
DOC_HIGH_THRESH = 256 * 1024      # value written in the ROS 2 DDS tuning document
DOC_TUNED_THRESH = 128 * 1024 * 1024
DOC_TUNED_TIME = 3
PROBE_INTERVAL = 0.1
PROBE_WAIT = 0.05
DST = "127.0.0.1"

T0 = time.monotonic()
_ident = 0


def emit(**record):
    record["t"] = round(time.monotonic() - T0, 4)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def read_sysctl(name):
    path = "/proc/sys/net/ipv4/" + name
    try:
        with open(path) as fh:
            value = int(fh.read().split()[0])
    except OSError:
        return None, False
    return value, os.access(path, os.W_OK)


def frag_state():
    """(queues, bytes) of this namespace's IPv4 reassembly memory."""
    with open("/proc/net/sockstat") as fh:
        for line in fh:
            if line.startswith("FRAG:"):
                parts = line.split()
                return int(parts[parts.index("inuse") + 1]), int(parts[parts.index("memory") + 1])
    raise RuntimeError("FRAG line missing in /proc/net/sockstat")


def ip_counters():
    with open("/proc/net/snmp") as fh:
        rows = [line.split() for line in fh if line.startswith("Ip:")]
    names, values = rows[0][1:], rows[1][1:]
    wanted = ("ReasmReqds", "ReasmOKs", "ReasmFails", "ReasmTimeout")
    table = dict(zip(names, values))
    return {k: int(table[k]) for k in wanted}


def delta(after, before):
    return {k: after[k] - before[k] for k in after}


def next_ident():
    global _ident
    _ident += 1
    return _ident


def fragments(udp_datagram, ident):
    """Split one UDP datagram (header included) into IPv4 fragments of FRAG_DATA bytes."""
    src = dst = socket.inet_aton(DST)
    out = []
    for offset in range(0, len(udp_datagram), FRAG_DATA):
        chunk = udp_datagram[offset:offset + FRAG_DATA]
        more = offset + FRAG_DATA < len(udp_datagram)
        flags = (0x2000 if more else 0) | (offset // 8)
        header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(chunk), ident, flags, 64,
                             socket.IPPROTO_UDP, 0, src, dst)
        out.append(header + chunk)
    return out


def udp_datagram(port, data):
    # checksum 0 = "no checksum" for UDP over IPv4, so the kernel accepts the reassembled datagram
    return struct.pack("!HHHH", 40000, port, 8 + len(data), 0) + data


def send_frags(raw, frags):
    for frag in frags:
        raw.sendto(frag, (DST, 0))


def drain(sock, wait, want=()):
    """Return payload tags received within `wait` seconds (early exit once all `want` arrived)."""
    got = []
    end = time.monotonic() + wait
    while not all(any(g.startswith(w) for g in got) for w in want) or not want:
        left = end - time.monotonic()
        if left <= 0:
            break
        ready, _, _ = select.select([sock], [], [], left)
        if not ready:
            break
        data = sock.recv(70000)
        got.append(data[:8].decode(errors="replace") + ":" + str(len(data)))
    return got


def main():
    high, high_w = read_sysctl("ipfrag_high_thresh")
    low, _ = read_sysctl("ipfrag_low_thresh")
    ftime, time_w = read_sysctl("ipfrag_time")
    max_dist, _ = read_sysctl("ipfrag_max_dist")
    with open("/sys/class/net/lo/mtu") as fh:
        lo_mtu = int(fh.read())
    emit(phase="environment", kernel=os.uname().release, ipfrag_high_thresh=high,
         ipfrag_low_thresh=low, ipfrag_time=ftime, ipfrag_max_dist=max_dist,
         sysctl_writable=bool(high_w or time_w), lo_mtu=lo_mtu, frag_ip_payload=FRAG_DATA)
    if not high or not ftime or ftime > 45:
        emit(phase="abort", reason="unexpected ipfrag settings for a 60 s run")
        return 2

    # A real ROS 2 message, serialized by rclpy, is the payload we cut into datagrams.
    msg = UInt8MultiArray()
    msg.data = bytes(range(256)) * (MSG_DATA_BYTES // 256)
    started = time.monotonic()
    wire = serialize_message(msg)
    datagrams_per_msg = -(-len(wire) // UDP_PAYLOAD)
    frags_per_datagram = -(-(8 + UDP_PAYLOAD) // FRAG_DATA)
    emit(phase="message", type="std_msgs/msg/UInt8MultiArray", data_bytes=len(msg.data),
         serialized_bytes=len(wire), serialize_ms=round((time.monotonic() - started) * 1000, 3),
         udp_payload_per_datagram=UDP_PAYLOAD, datagrams_per_message=datagrams_per_msg,
         ip_fragments_per_full_datagram=frags_per_datagram)

    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    rx.bind((DST, 0))
    port = rx.getsockname()[1]
    small_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def probe(tag):
        """Send one small unfragmented and one complete fragmented datagram; report delivery."""
        small_tx.sendto(b"SMALL___" + bytes(92), (DST, port))
        big = udp_datagram(port, b"BIGPROBE" + bytes(UDP_PAYLOAD - 8))
        send_frags(raw, fragments(big, next_ident()))
        got = drain(rx, PROBE_WAIT, ("SMALL", "BIGPROBE"))
        return {"probe": tag, "small_delivered": any(g.startswith("SMALL") for g in got),
                "large_delivered": any(g.startswith("BIGPROBE") for g in got)}

    # 0) Baseline: both kinds of datagram are delivered when the buffer is empty.
    base_c, base_q = ip_counters(), frag_state()
    result = probe("baseline")
    emit(phase="baseline", frag_queues=base_q[0], frag_memory=base_q[1],
         reasm=delta(ip_counters(), base_c), **result)

    # 1) Accounting: what does the kernel charge per held fragment and per incomplete datagram?
    c0, (q0, m0) = ip_counters(), frag_state()
    first_queue_at = time.monotonic()
    one = fragments(udp_datagram(port, wire[:UDP_PAYLOAD]), next_ident())
    send_frags(raw, one[:1])
    q1, m1 = frag_state()
    held = fragments(udp_datagram(port, wire[:UDP_PAYLOAD]), next_ident())
    send_frags(raw, held[:-1])
    q2, m2 = frag_state()
    per_frag = (m2 - m1) / (len(held) - 2) if len(held) > 2 else None
    first_charge = m1 - m0
    incomplete_64k = m2 - m1
    payload_held = sum(len(f) - 20 for f in held[:-1])
    emit(phase="accounting", one_fragment_queue_bytes=first_charge,
         incomplete_datagram_fragments=len(held) - 1, incomplete_datagram_bytes=incomplete_64k,
         incomplete_datagram_ip_payload=payload_held,
         truesize_per_fragment_est=round(per_frag, 1) if per_frag else None,
         queue_overhead_est=round(first_charge - per_frag, 1) if per_frag else None,
         accounting_factor=round(incomplete_64k / payload_held, 4),
         queues=q2 - q0, reasm=delta(ip_counters(), c0))

    # 2) Fill: 1 MiB messages at 10 Hz, every datagram loses its last IP fragment.
    fill_c = ip_counters()
    fill_start = time.monotonic()
    first_refusal = None
    payload_offered = 0
    unfragmented = 0
    for k in range(FILL_MESSAGES):
        target = fill_start + k / RATE_HZ
        pause = target - time.monotonic()
        if pause > 0:
            time.sleep(pause)
        before = ip_counters()
        for d in range(datagrams_per_msg):
            chunk = wire[d * UDP_PAYLOAD:(d + 1) * UDP_PAYLOAD]
            frags = fragments(udp_datagram(port, chunk), next_ident())
            if len(frags) == 1:
                # fits in one 1500-byte packet: no IP fragmentation, so nothing to lose here
                send_frags(raw, frags)
                unfragmented += 1
                continue
            send_frags(raw, frags[:-1])
            payload_offered += sum(len(f) - 20 for f in frags[:-1])
            if first_refusal is None and ip_counters()["ReasmFails"] > fill_c["ReasmFails"]:
                q, m = frag_state()
                first_refusal = time.monotonic()
                emit(phase="first_refusal", message_index=k, datagram_index=d,
                     since_fill_start_s=round(first_refusal - fill_start, 4),
                     ip_payload_offered_bytes=payload_offered, frag_queues=q, frag_memory=m,
                     memory_over_thresh=m - high)
        q, m = frag_state()
        emit(phase="fill", message_index=k, frag_queues=q, frag_memory=m,
             reasm=delta(ip_counters(), before))
    fill_end = time.monotonic()
    emit(phase="fill_total", wall_s=round(fill_end - fill_start, 4), unfragmented_datagrams=unfragmented,
         reasm=delta(ip_counters(), fill_c))
    drain(rx, 0.05)

    # 3) Stall: probe every 0.5 s until a complete large datagram gets through again
    #    and every held queue has expired. Small datagrams never need reassembly.
    stall_c = ip_counters()
    deadline = fill_start + ftime + 4
    recovered_at = empty_at = first_expiry = None
    peak_queues = frag_state()[0]
    blocked_small_ok = blocked_probes = 0
    while time.monotonic() < deadline:
        tick = time.monotonic()
        result = probe("stall")
        q, m = frag_state()
        if first_expiry is None and q < peak_queues:
            first_expiry = tick
            emit(phase="first_expiry", since_first_queue_s=round(tick - first_queue_at, 3),
                 since_fill_start_s=round(tick - fill_start, 3), frag_queues=q, frag_memory=m)
        if not result["large_delivered"] and recovered_at is None:
            blocked_probes += 1
            blocked_small_ok += result["small_delivered"]
        if result["large_delivered"] and recovered_at is None:
            recovered_at = tick
            emit(phase="recovered", since_fill_start_s=round(tick - fill_start, 3),
                 since_first_refusal_s=round(tick - first_refusal, 3) if first_refusal else None,
                 frag_queues=q, frag_memory=m, **result)
        if q == 0 and empty_at is None:
            empty_at = tick
            emit(phase="buffer_empty", since_first_queue_s=round(tick - first_queue_at, 3),
                 since_fill_start_s=round(tick - fill_start, 3))
        if recovered_at and empty_at:
            break
        time.sleep(max(0.0, PROBE_INTERVAL - (time.monotonic() - tick)))
    emit(phase="stall_total", blocked_probes=blocked_probes,
         blocked_probes_small_delivered=blocked_small_ok, reasm=delta(ip_counters(), stall_c))

    # 4) Derived from this run's measured accounting (arithmetic, not a measurement).
    factor = incomplete_64k / payload_held
    rate = MSG_DATA_BYTES * RATE_HZ
    emit(phase="derived", accounting_factor=round(factor, 4),
         incomplete_64k_datagrams_fit_current=round(high / incomplete_64k, 2),
         incomplete_64k_datagrams_fit_doc_256k=round(DOC_HIGH_THRESH / incomplete_64k, 2),
         seconds_to_fill_current_at_1MiB_10Hz=round(high / (rate * factor), 4),
         held_bytes_30s=round(ftime * rate * factor), held_bytes_3s=round(DOC_TUNED_TIME * rate * factor),
         fits_128MiB_with_default_time=ftime * rate * factor <= DOC_TUNED_THRESH,
         fits_128MiB_with_3s=DOC_TUNED_TIME * rate * factor <= DOC_TUNED_THRESH)

    ok = (first_refusal is not None and recovered_at is not None and blocked_probes > 0
          and blocked_small_ok == blocked_probes)
    emit(phase="summary", ok=ok, stall_after_first_refusal_s=round(recovered_at - first_refusal, 3)
         if ok else None, total_runtime_s=round(time.monotonic() - T0, 3))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
