#!/bin/bash
# Run inside ros:<distro>-ros-base:
#   docker run --rm --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# A broadcaster publishes static map->odom once (/tf_static) and dynamic odom->base_link
# at RATE Hz stamped with now(). A second process (the listener) runs the lookups.
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
python3 -c "import tf2_ros" 2>/dev/null || { apt-get update -qq >/dev/null && apt-get install -y -qq ros-$ROS_DISTRO-tf2-ros >/dev/null; }
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros ros-$ROS_DISTRO-tf2-ros-py ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rmw-implementation 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"
echo "--- Buffer.can_transform timeout loop (installed source):"
grep -n "sleep(0.02)" $(python3 -c "import tf2_ros.buffer as b; print(b.__file__)")
export ROS_DOMAIN_ID=42
cat > /tmp/tfx.py <<'PY'
import sys, time, threading, re, statistics, random
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
import tf2_ros
from tf2_ros import Buffer, TransformListener, TransformBroadcaster, StaticTransformBroadcaster

def tf(n, parent, child, x):
    t = TransformStamped()
    t.header.stamp = n.get_clock().now().to_msg()
    t.header.frame_id = parent; t.child_frame_id = child
    t.transform.translation.x = x; t.transform.rotation.w = 1.0
    return t

def bcast(rate):
    rclpy.init(); n = Node('bcast')
    br = TransformBroadcaster(n); sb = StaticTransformBroadcaster(n)
    sb.sendTransform(tf(n, 'map', 'odom', 2.0))
    n.create_timer(1.0 / rate, lambda: br.sendTransform(tf(n, 'odom', 'base_link', 1.0)))
    try: rclpy.spin(n)
    except BaseException: pass

def ms(v): return round(v * 1000.0, 1)
def nowsec(n): return n.get_clock().now().nanoseconds / 1e9
def stats(xs):
    if not xs: return 'n/a'
    xs = sorted(xs)
    return 'min=%s median=%s p95=%s max=%s' % (xs[0], statistics.median(xs), xs[int(0.95 * (len(xs) - 1))], xs[-1])

EXECS = []
def listener_node(name, cache=None, spin=True):
    n = Node(name)
    b = Buffer(cache_time=cache) if cache else Buffer()
    l = TransformListener(b, n)
    if spin:
        ex = SingleThreadedExecutor(); ex.add_node(n)
        th = threading.Thread(target=ex.spin); th.start()
        EXECS.append((ex, th))
    return n, b, l

def trial(n, label, N, fn):
    ok = 0; errs = {}; sample = {}; gaps = []; blocks = []; ages = []
    for _ in range(N):
        time.sleep(random.uniform(0, 0.02))
        t0 = time.monotonic()
        try:
            r = fn()
            ok += 1
            if r is not None and hasattr(r, 'header'):
                ages.append(ms(nowsec(n) - (r.header.stamp.sec + r.header.stamp.nanosec / 1e9)))
        except Exception as e:
            k = type(e).__name__; errs[k] = errs.get(k, 0) + 1; sample.setdefault(k, str(e))
            m = re.search(r'Requested time ([\d.]+) but the (?:latest|earliest) data is at time ([\d.]+)', str(e))
            if m: gaps.append(ms(float(m.group(1)) - float(m.group(2))))
        blocks.append(ms(time.monotonic() - t0))
    print('RESULT %s: ok=%d/%d errors=%s' % (label, ok, N, errs))
    for k, v in sample.items(): print('  SAMPLE %s: %s' % (k, v))
    if gaps: print('  requested-minus-latest ms: %s' % stats(gaps))
    if ages: print('  age of returned transform ms: %s' % stats(ages))
    print('  call duration ms: %s' % stats(blocks))

def rate_test(rate):
    rclpy.init()
    n, b, l = listener_node('lis')
    cnt = [0]
    n.create_subscription(TFMessage, '/tf', lambda m: cnt.__setitem__(0, cnt[0] + 1), 100)
    time.sleep(2.0)
    c0 = cnt[0]; t0 = time.monotonic()
    now = lambda: n.get_clock().now()
    trial(n, 'rate=%d now() no timeout' % rate, 200, lambda: b.lookup_transform('odom', 'base_link', now()))
    trial(n, 'rate=%d Time() latest' % rate, 200, lambda: b.lookup_transform('odom', 'base_link', Time()))
    trial(n, 'rate=%d now() timeout=0.1s' % rate, 100, lambda: b.lookup_transform('odom', 'base_link', now(), timeout=Duration(seconds=0.1)))
    trial(n, 'rate=%d stamp=now()-50ms no timeout' % rate, 200, lambda: b.lookup_transform('odom', 'base_link', now() - Duration(seconds=0.05)))
    trial(n, 'rate=%d static map->odom now() no timeout' % rate, 200, lambda: b.lookup_transform('map', 'odom', now()))
    trial(n, 'rate=%d chain map->base_link now() no timeout' % rate, 200, lambda: b.lookup_transform('map', 'base_link', now()))
    def canT():
        if not b.can_transform('odom', 'base_link', now()): raise RuntimeError('can_transform returned False')
    trial(n, 'rate=%d can_transform now() no timeout' % rate, 200, canT)
    if hasattr(b, 'wait_for_transform_async'):
        def wfa():
            f = b.wait_for_transform_async('odom', 'base_link', now())
            t = time.monotonic()
            while not f.done():
                if time.monotonic() - t > 1.0: raise TimeoutError('future not done after 1 s')
                time.sleep(0.0005)
            return b.lookup_transform('odom', 'base_link', Time())
        trial(n, 'rate=%d wait_for_transform_async(now()) then lookup' % rate, 100, wfa)
    el = time.monotonic() - t0
    print('MEASURED /tf rate during tests: %.1f msg/s' % ((cnt[0] - c0) / el))
    print('HAS tf2_ros.MessageFilter: %s' % hasattr(tf2_ros, 'MessageFilter'))

def startup():
    rclpy.init()
    n, b, l = listener_node('lis_start')
    t0 = time.monotonic()
    for label, fn in [('immediate lookup Time()', lambda: b.lookup_transform('odom', 'base_link', Time())),
                      ('immediate can_transform Time()', lambda: print('  can_transform ->', b.can_transform('odom', 'base_link', Time())))]:
        try: fn(); print('RESULT startup %s: ok' % label)
        except Exception as e: print('RESULT startup %s: %s: %s' % (label, type(e).__name__, e))
    t = time.monotonic()
    try:
        b.lookup_transform('odom', 'base_link', Time(), timeout=Duration(seconds=2.0))
        print('RESULT startup lookup Time() timeout=2s: ok after %s ms (listener age %s ms)' % (ms(time.monotonic() - t), ms(time.monotonic() - t0)))
    except Exception as e: print('RESULT startup lookup Time() timeout=2s: %s after %s ms' % (type(e).__name__, ms(time.monotonic() - t)))
    for label, args in [('missing frame Time() timeout=0.5s', ('odom', 'camera_link', Time(), Duration(seconds=0.5))),
                        ('missing frame Time() no timeout', ('odom', 'camera_link', Time(), Duration())),
                        ('existing frames now()+5s timeout=0.5s', ('odom', 'base_link', n.get_clock().now() + Duration(seconds=5), Duration(seconds=0.5)))]:
        t = time.monotonic()
        try: b.lookup_transform(args[0], args[1], args[2], timeout=args[3]); print('RESULT %s: ok after %s ms' % (label, ms(time.monotonic() - t)))
        except Exception as e: print('RESULT %s: %s after %s ms: %s' % (label, type(e).__name__, ms(time.monotonic() - t), e))

def nospin():
    # buffer + listener created, but nobody spins the node
    rclpy.init()
    n, b, l = listener_node('lis_nospin', spin=False)
    time.sleep(1.0)
    t = time.monotonic()
    try: b.lookup_transform('odom', 'base_link', Time(), timeout=Duration(seconds=1.0)); print('RESULT no-spin lookup Time() timeout=1s: ok after %s ms' % ms(time.monotonic() - t))
    except Exception as e: print('RESULT no-spin lookup Time() timeout=1s: %s after %s ms: %s' % (type(e).__name__, ms(time.monotonic() - t), e))

def callback(how):
    # lookup with now() + timeout=0.2s inside a 2 Hz timer callback of node 'lis_cb'
    #   single:      rclpy.spin_once on one node (default single-threaded executor)
    #   multi:       MultiThreadedExecutor spinning that node
    #   own_thread:  TransformListener on a separate node with spin_thread=True
    rclpy.init()
    n = Node('lis_cb'); b = Buffer()
    if how == 'own_thread': l = TransformListener(b, Node('lis_cb_tf'), spin_thread=True)
    else: l = TransformListener(b, n)
    res = []
    def cb():
        t = time.monotonic()
        try: b.lookup_transform('odom', 'base_link', n.get_clock().now(), timeout=Duration(seconds=0.2)); res.append(('ok', ms(time.monotonic() - t)))
        except Exception as e: res.append((type(e).__name__, ms(time.monotonic() - t)))
    n.create_timer(0.5, cb)
    end = time.monotonic() + 6.0
    if how == 'multi':
        from rclpy.executors import MultiThreadedExecutor
        ex = MultiThreadedExecutor(num_threads=4); ex.add_node(n)
        while time.monotonic() < end: ex.spin_once(timeout_sec=0.1)
        ex.shutdown()
    else:
        while time.monotonic() < end: rclpy.spin_once(n, timeout_sec=0.1)
    oks = [d for k, d in res if k == 'ok']; bad = [(k, d) for k, d in res if k != 'ok']
    print('RESULT callback timeout=0.2s %s: ok=%d/%d failures=%s' % (how, len(oks), len(res), sorted(set(k for k, _ in bad))))
    print('  ok durations ms: %s' % stats(oks))
    print('  failed durations ms: %s' % stats([d for _, d in bad]))
    if how == 'own_thread':
        l.executor.shutdown(); l.dedicated_listener_thread.join(timeout=2)

def past():
    rclpy.init()
    n, b10, l10 = listener_node('lis_past10')
    n2, b30, l30 = listener_node('lis_past30', cache=Duration(seconds=30))
    print('default cache_time: %s s' % (b10.get_cache_length() if hasattr(b10, 'get_cache_length') else 'n/a'))
    time.sleep(16.0)
    now = n.get_clock().now()
    for back in [5, 9.5, 12, 15, 25]:
        tq = now - Duration(seconds=back)
        for label, b in [('cache=default', b10), ('cache=30s', b30)]:
            try: b.lookup_transform('odom', 'base_link', tq); print('RESULT past now()-%ss %s: ok' % (back, label))
            except Exception as e: print('RESULT past now()-%ss %s: %s: %s' % (back, label, type(e).__name__, e))

mode = sys.argv[1]
if mode == 'bcast': bcast(float(sys.argv[2]))
elif mode == 'rate': rate_test(int(sys.argv[2]))
elif mode == 'startup': startup()
elif mode == 'nospin': nospin()
elif mode == 'callback': callback(sys.argv[2])
elif mode == 'past': past()
for ex, th in EXECS: ex.shutdown(); th.join(timeout=2)
if rclpy.ok(): rclpy.shutdown()
PY

start_b() { python3 /tmp/tfx.py bcast $1 & BP=$!; sleep 2; }
# bcast is stopped with SIGINT so rclpy exits cleanly
stop_b() { kill -INT $BP; wait $BP 2>/dev/null; }

echo "=== startup, no broadcaster running"
timeout 30 python3 /tmp/tfx.py startup 2>&1
echo "=== startup, broadcaster at 50 Hz already running (5 fresh listener processes)"
start_b 50; for i in 1 2 3 4 5; do echo "--- listener start $i"; timeout 30 python3 /tmp/tfx.py startup 2>&1; done; stop_b
for R in 10 50 100; do
  echo "=== rate $R Hz"
  start_b $R; timeout 300 python3 /tmp/tfx.py rate $R 2>&1; stop_b
done
echo "=== no spin, 50 Hz"
start_b 50; timeout 30 python3 /tmp/tfx.py nospin 2>&1; stop_b
echo "=== lookup in a timer callback, 50 Hz"
start_b 50
for H in single multi own_thread; do timeout 30 python3 /tmp/tfx.py callback $H 2>&1; done
stop_b
echo "=== past / cache_time, 50 Hz"
start_b 50; timeout 60 python3 /tmp/tfx.py past 2>&1; stop_b
echo "=== done"
