#!/bin/bash
# Run inside ros:<distro>-ros-base (docker run --ulimit core=0).
# Why a message_filters TimeSynchronizer / ApproximateTimeSynchronizer callback never fires.
# A Python publisher sends geometry_msgs/PointStamped on /a and /b (10 Hz, 5 s => 50 each);
# Python and C++ subscribers count raw messages per input and synchronized callbacks.
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=46 MAKEFLAGS=-j2
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-message-filters ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
python3 - <<'X'
import inspect, message_filters as mf
print('message_filters.py', mf.__file__)
for c in ('Subscriber', 'TimeSynchronizer', 'ApproximateTimeSynchronizer'):
    print('SIG', c, inspect.signature(getattr(mf, c).__init__))
X
W=/ws; mkdir -p $W/src; cd $W/src

# ---------- Python publisher ----------
cat > /pub.py <<'X'
import sys, time, rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
a = dict(x.split('=') for x in sys.argv[1:])
off = float(a.get('offset_ms', 0)); qos = a.get('qos', 'reliable')
rate_a = float(a.get('rate_a', 10)); rate_b = float(a.get('rate_b', 10))
zero_b = a.get('zero_b', '0') == '1'; sep = a.get('separate', '0') == '1'
typ = a.get('type', 'point'); dur = float(a.get('dur', 5))
rclpy.init(); n = Node('pub')
q = qos_profile_sensor_data if qos == 'best_effort' else QoSProfile(depth=10)
M = String if typ == 'string' else PointStamped
pa = n.create_publisher(M, 'a', q); pb = n.create_publisher(M, 'b', q)
def mk(stamp):
    m = M()
    if typ == 'string': m.data = 'x'
    elif stamp is not None: m.header.stamp = stamp.to_msg(); m.header.frame_id = 'f'
    return m
def both():
    t = n.get_clock().now()
    pa.publish(mk(t))
    tb = n.get_clock().now() if sep else t
    pb.publish(mk(None if zero_b else tb + Duration(nanoseconds=int(off * 1e6))))
def only_a(): pa.publish(mk(n.get_clock().now()))
def only_b():
    t = n.get_clock().now()
    pb.publish(mk(None if zero_b else t + Duration(nanoseconds=int(off * 1e6))))
if rate_a == rate_b: n.create_timer(1.0 / rate_a, both)
else: n.create_timer(1.0 / rate_a, only_a); n.create_timer(1.0 / rate_b, only_b)
end = time.time() + dur
while time.time() < end: rclpy.spin_once(n, timeout_sec=0.05)
n.destroy_node(); rclpy.shutdown()
X

# ---------- Python subscriber ----------
cat > /sub.py <<'X'
import sys, time, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
import message_filters as mf
a = dict(x.split('=') for x in sys.argv[1:])
kind = a.get('kind', 'exact'); slop = float(a.get('slop', 0.1)); qn = int(a.get('queue', 10))
qos = a.get('qos', 'default'); hl = a.get('headerless', '0') == '1'
store = a.get('store', '1') == '1'; typ = a.get('type', 'point'); dur = float(a.get('dur', 7))
rclpy.init(); n = Node('sync_py')
M = String if typ == 'string' else PointStamped
kw = {'qos_profile': qos_profile_sensor_data} if qos == 'sensor' else {}
sa = mf.Subscriber(n, M, 'a', **kw); sb = mf.Subscriber(n, M, 'b', **kw)
c = {'a': 0, 'b': 0, 'sync': 0, 'first': None}; t0 = time.time()
sa.registerCallback(lambda m: c.__setitem__('a', c['a'] + 1))
sb.registerCallback(lambda m: c.__setitem__('b', c['b'] + 1))
def cb(ma, mb):
    c['sync'] += 1
    if c['first'] is None: c['first'] = round(time.time() - t0, 2)
if kind == 'exact': s = mf.TimeSynchronizer([sa, sb], qn)
else: s = mf.ApproximateTimeSynchronizer([sa, sb], qn, slop, allow_headerless=hl)
s.registerCallback(cb)
if not store: del s
try:
    end = time.time() + dur
    while time.time() < end: rclpy.spin_once(n, timeout_sec=0.05)
except Exception as e:
    print('EXCEPTION', type(e).__name__, e)
print(f"RESULT py a={c['a']} b={c['b']} sync={c['sync']} first_sync_s={c['first']}")
X

# ---------- C++ subscriber + compile probes ----------
mkpkg() {  # name src
  mkdir -p $W/src/$1/src
  cat > $W/src/$1/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$1</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>message_filters</depend><depend>geometry_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > $W/src/$1/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($1)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(message_filters REQUIRED)
find_package(geometry_msgs REQUIRED)
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp::rclcpp message_filters::message_filters \${geometry_msgs_TARGETS})
install(TARGETS node DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
  cat > $W/src/$1/src/node.cpp
}
mkpkg sync_cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
#include <message_filters/time_synchronizer.hpp>
#include <message_filters/synchronizer.hpp>
#include <message_filters/sync_policies/approximate_time.hpp>
#if __has_include(<message_filters/subscriber.h>)
#define OLD_QOS 1
#define MAKE_TS(a, b, q) std::make_shared<message_filters::TimeSynchronizer<P, P>>(a, b, q)
#else
#define MAKE_TS(a, b, q) std::make_shared<message_filters::TimeSynchronizer<P, P>>(q, a, b)
#endif
using P = geometry_msgs::msg::PointStamped;
using Approx = message_filters::sync_policies::ApproximateTime<P, P>;
struct SyncNode : rclcpp::Node {
  message_filters::Subscriber<P> sa, sb;
  std::shared_ptr<message_filters::TimeSynchronizer<P, P>> exact;
  std::shared_ptr<message_filters::Synchronizer<Approx>> approx;
  int na = 0, nb = 0, ns = 0; double first = -1; rclcpp::Time t0;
  void on_sync(const P::ConstSharedPtr &, const P::ConstSharedPtr &) {
    ns++; if (first < 0) {first = (now() - t0).seconds();} }
  SyncNode(const std::string & kind, const std::string & qos, const std::string & scope, int q)
  : Node("sync_cpp") {
    t0 = now();
#ifdef OLD_QOS
    auto prof = (qos == "sensor") ? rmw_qos_profile_sensor_data : rmw_qos_profile_default;
#else
    rclcpp::QoS prof = (qos == "sensor") ? rclcpp::QoS(rclcpp::SensorDataQoS()) : rclcpp::QoS(10);
#endif
    std::function<void(const P::ConstSharedPtr &)> fa = [this](const P::ConstSharedPtr &) {na++;};
    std::function<void(const P::ConstSharedPtr &)> fb = [this](const P::ConstSharedPtr &) {nb++;};
    if (scope == "localsubs") {
      message_filters::Subscriber<P> la, lb;
      la.subscribe(this, "a", prof); lb.subscribe(this, "b", prof);
      exact = MAKE_TS(la, lb, q);
      exact->registerCallback(&SyncNode::on_sync, this);
      RCLCPP_INFO(get_logger(), "subscribers were locals in the constructor");
      return;
    }
    sa.subscribe(this, "a", prof); sb.subscribe(this, "b", prof);
    sa.registerCallback(fa); sb.registerCallback(fb);
    if (scope == "localsync") {
#ifdef OLD_QOS
      message_filters::TimeSynchronizer<P, P> local(sa, sb, q);
#else
      message_filters::TimeSynchronizer<P, P> local(q, sa, sb);
#endif
      local.registerCallback(&SyncNode::on_sync, this);
      RCLCPP_INFO(get_logger(), "synchronizer was a local in the constructor");
      return;
    }
    if (kind == "exact") {
      exact = MAKE_TS(sa, sb, q);
      exact->registerCallback(&SyncNode::on_sync, this);
    } else {
      approx = std::make_shared<message_filters::Synchronizer<Approx>>(Approx(q), sa, sb);
      approx->registerCallback(&SyncNode::on_sync, this);
    }
  }
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string kind = argc > 1 ? argv[1] : "exact", qos = argc > 2 ? argv[2] : "default";
  std::string scope = argc > 3 ? argv[3] : "member"; int q = argc > 4 ? atoi(argv[4]) : 10;
  auto n = std::make_shared<SyncNode>(kind, qos, scope, q);
  auto end = std::chrono::steady_clock::now() + std::chrono::seconds(7);
  rclcpp::executors::SingleThreadedExecutor ex; ex.add_node(n);
  while (std::chrono::steady_clock::now() < end) ex.spin_some(std::chrono::milliseconds(50));
  printf("RESULT cpp a=%d b=%d sync=%d first_sync_s=%.2f\n", n->na, n->nb, n->ns, n->first);
  rclcpp::shutdown();
}
X
mkpkg probe_h_include <<'X'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.h>
#include <message_filters/time_synchronizer.h>
int main() { return 0; }
X
mkpkg probe_rmw_qos <<'X'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
int main(int c, char ** v) { rclcpp::init(c, v); auto n = std::make_shared<rclcpp::Node>("p");
  message_filters::Subscriber<geometry_msgs::msg::PointStamped> s;
  s.subscribe(n.get(), "a", rmw_qos_profile_sensor_data); return 0; }
X
mkpkg probe_rclcpp_qos <<'X'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
int main(int c, char ** v) { rclcpp::init(c, v); auto n = std::make_shared<rclcpp::Node>("p");
  message_filters::Subscriber<geometry_msgs::msg::PointStamped> s;
  s.subscribe(n.get(), "a", rclcpp::SensorDataQoS()); return 0; }
X
mkpkg probe_no_qos <<'X'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
int main(int c, char ** v) { rclcpp::init(c, v); auto n = std::make_shared<rclcpp::Node>("p");
  message_filters::Subscriber<geometry_msgs::msg::PointStamped> s;
  s.subscribe(n.get(), "a"); return 0; }
X
mkpkg probe_lambda_cb <<'X2'
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
#include <message_filters/time_synchronizer.hpp>
using P = geometry_msgs::msg::PointStamped;
int main(int c, char ** v) { rclcpp::init(c, v); auto n = std::make_shared<rclcpp::Node>("p");
  message_filters::Subscriber<P> a, b;
#if __has_include(<message_filters/subscriber.h>)
  message_filters::TimeSynchronizer<P, P> s(a, b, 10);
#else
  message_filters::TimeSynchronizer<P, P> s(10, a, b);
#endif
  s.registerCallback([](const P::ConstSharedPtr &, const P::ConstSharedPtr &) {});
  return 0; }
X2
for o in last first; do
  if [ $o = last ]; then args="a, b, 10"; else args="10, a, b"; fi
  mkpkg probe_ts_queue_$o <<X2
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <message_filters/subscriber.hpp>
#include <message_filters/time_synchronizer.hpp>
using P = geometry_msgs::msg::PointStamped;
int main() { message_filters::Subscriber<P> a, b;
  message_filters::TimeSynchronizer<P, P> s($args); return 0; }
X2
done
cd $W
for p in probe_h_include probe_ts_queue_last probe_ts_queue_first probe_lambda_cb probe_rmw_qos probe_rclcpp_qos probe_no_qos sync_cpp; do
  colcon build --packages-select $p --parallel-workers 1 --event-handlers console_direct- >/tmp/b_$p.log 2>&1
  rc=$?; echo "=== BUILD $p rc=$rc"
  grep -E "error:|warning:|deprecated" /tmp/b_$p.log | sed -E 's#/opt/ros/[a-z]+/#/opt/ros/$D/#' | sort -u | head -6
done
source $W/install/setup.bash
[ -n "$BUILD_ONLY" ] && exit 0

# ---------- runs ----------
run() {  # label | sub command | pub args
  local label="$1" sub="$2" pub="$3"
  echo "=== CASE $label | sub: $sub | pub: $pub"
  timeout 20 $sub > /tmp/sub.log 2>&1 & local sp=$!
  sleep 1; timeout 15 python3 /pub.py $pub > /tmp/pub.log 2>&1
  wait $sp; echo "exit=$?"
  grep -E 'EXCEPTION|WARN|ERROR|Error|INFO|terminate|what\(\)|Segmentation|Aborted' /tmp/sub.log | sed -E 's/\[[0-9]+\.[0-9]+\]/[t]/' | sort | uniq -c | head -6
  echo "warn_lines=$(grep -c WARN /tmp/sub.log)"; grep RESULT /tmp/sub.log
  grep -E 'Error|Traceback' /tmp/pub.log | head -3
}
PY="python3 /sub.py"; CPP="ros2 run sync_cpp node"
run P1_exact_same_stamp       "$PY kind=exact"                        ""
run P2_exact_offset_1ms       "$PY kind=exact"                        "offset_ms=1"
run P3_exact_two_now_calls    "$PY kind=exact"                        "separate=1"
run P4_approx_slop0.1_off1ms  "$PY kind=approx slop=0.1"              "offset_ms=1"
run P5_approx_slop0.1_off50   "$PY kind=approx slop=0.1"              "offset_ms=50"
run P6_approx_slop0.01_off50  "$PY kind=approx slop=0.01"             "offset_ms=50"
run P7_approx_two_now_calls   "$PY kind=approx slop=0.01"             "separate=1"
run P8_besteffort_pub_default "$PY kind=exact"                        "qos=best_effort"
run P9_besteffort_pub_sensor  "$PY kind=exact qos=sensor"             "qos=best_effort"
run P10_reliable_pub_sensor   "$PY kind=exact qos=sensor"             ""
run P11_approx_b_stamp_zero   "$PY kind=approx slop=0.1"              "zero_b=1"
run P12_approx_lag500_q1      "$PY kind=approx slop=0.1 queue=1"      "offset_ms=-500"
run P13_approx_lag500_q3      "$PY kind=approx slop=0.1 queue=3"      "offset_ms=-500"
run P14_approx_lag500_q10     "$PY kind=approx slop=0.1 queue=10"     "offset_ms=-500"
run P15_approx_rates_10_1     "$PY kind=approx slop=0.1"              "rate_a=10 rate_b=1"
run P16_exact_rates_10_1      "$PY kind=exact"                        "rate_a=10 rate_b=1"
run P17_headerless_default    "$PY kind=approx slop=0.1 type=string"  "type=string"
run P18_headerless_allowed    "$PY kind=approx slop=0.1 type=string headerless=1" "type=string"
run P19_sync_not_stored       "$PY kind=exact store=0"                ""
run C1_exact_same_stamp       "$CPP exact default member"             ""
run C2_exact_offset_1ms       "$CPP exact default member"             "offset_ms=1"
run C3_approx_off50           "$CPP approx default member"            "offset_ms=50"
run C4_approx_off900          "$CPP approx default member"            "offset_ms=900"
run C5_approx_b_stamp_zero    "$CPP approx default member"            "zero_b=1"
run C6_besteffort_pub_default "$CPP exact default member"             "qos=best_effort"
run C7_besteffort_pub_sensor  "$CPP exact sensor member"              "qos=best_effort"
run C8_sync_local             "$CPP exact default localsync"          ""
run C9_subscribers_local      "$CPP exact default localsubs"          ""
run C10_approx_lag500_q1      "$CPP approx default member 1"          "offset_ms=-500"
run C11_approx_lag500_q10     "$CPP approx default member 10"         "offset_ms=-500"
echo "=== done $ROS_DISTRO"
