#!/bin/bash
# Run inside ros:<distro>-ros-base as root, e.g.
#   docker run --rm --network none -v $PWD:/e ros:humble-ros-base bash /e/repro.sh
# Compiles one small rclcpp node per timer-creation variant and records whether it
# builds and the first error lines, then runs a few timers to count callbacks.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=61
echo "=== distro=$ROS_DISTRO date=$(date -u +%FT%TZ)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
g++ --version | head -1; cmake --version | head -1; python3 --version
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"

W=/w; mkdir -p $W/src; cd $W

# case name | 1 = add "using namespace std::chrono_literals;" | statement in the constructor
cat > cases.txt <<'C'
c01_lambda_ok|1|t_ = create_wall_timer(500ms, [this]() { cb(); });
c02_bind_ok|1|t_ = create_wall_timer(500ms, std::bind(&N::cb, this));
c03_no_chrono_literals|0|t_ = create_wall_timer(500ms, [this]() { cb(); });
c04_double_period|1|t_ = create_wall_timer(0.5, [this]() { cb(); });
c05_int_period|1|t_ = create_wall_timer(500, [this]() { cb(); });
c06_rclcpp_duration_period|1|t_ = create_wall_timer(rclcpp::Duration(1, 0), [this]() { cb(); });
c07_duration_to_chrono|1|t_ = create_wall_timer(rclcpp::Duration(1, 0).to_chrono<std::chrono::nanoseconds>(), [this]() { cb(); });
c08_fractional_seconds_literal|1|t_ = create_wall_timer(0.5s, [this]() { cb(); });
c09_member_pointer_no_bind|1|t_ = create_wall_timer(500ms, &N::cb);
c10_bind_without_this|1|t_ = create_wall_timer(500ms, std::bind(&N::cb));
c11_lambda_no_this_capture|1|t_ = create_wall_timer(500ms, []() { cb(); });
c12_cb_int_bind_no_arg|1|t_ = create_wall_timer(500ms, std::bind(&N::cb_int, this));
c13_cb_int_bind_value|1|t_ = create_wall_timer(500ms, std::bind(&N::cb_int, this, 5));
c14_cb_int_placeholder_1|1|t_ = create_wall_timer(500ms, std::bind(&N::cb_int, this, std::placeholders::_1));
c15_cb_timerbase_ref|1|t_ = create_wall_timer(500ms, std::bind(&N::cb_timer, this, std::placeholders::_1));
c16_cb_timer_shared_ptr|1|t_ = create_wall_timer(500ms, [this](rclcpp::TimerBase::SharedPtr) { cb(); });
c17_std_function_int_create_timer|1|std::function<void(int)> f = std::bind(&N::cb_int, this, std::placeholders::_1); t_ = rclcpp::create_timer(this, get_clock(), rclcpp::Duration(1, 0), f);
c18_create_timer_free_ok|1|t_ = rclcpp::create_timer(this, get_clock(), rclcpp::Duration(1, 0), [this]() { cb(); });
c19_create_timer_free_chrono|1|t_ = rclcpp::create_timer(this, get_clock(), 500ms, [this]() { cb(); });
c20_node_create_timer_member|1|t_ = this->create_timer(500ms, [this]() { cb(); });
c21_std_function_void_ok|1|std::function<void()> f = std::bind(&N::cb, this); t_ = create_wall_timer(500ms, f);
c22_lambda_calls_cb_int_5|1|t_ = create_wall_timer(500ms, [this]() { cb_int(5); });
c23_std_function_wraps_bind_value|1|std::function<void()> f = std::bind(&N::cb_int, this, 5); t_ = create_wall_timer(500ms, f);
C

{
echo 'cmake_minimum_required(VERSION 3.8)'
echo 'project(timer_cases CXX)'
echo 'set(CMAKE_CXX_STANDARD 17)'
echo 'find_package(rclcpp REQUIRED)'
} > src/CMakeLists.txt
while IFS='|' read -r name lit stmt; do
  {
    echo '#include <chrono>'
    echo '#include <functional>'
    echo '#include <memory>'
    echo '#include "rclcpp/rclcpp.hpp"'
    [ "$lit" = 1 ] && echo 'using namespace std::chrono_literals;'
    echo 'class N : public rclcpp::Node {'
    echo 'public:'
    echo '  N() : Node("n") {'
    echo "    $stmt"
    echo '  }'
    echo '  void cb() {}'
    echo '  void cb_int(int) {}'
    echo '  void cb_timer(rclcpp::TimerBase &) {}'
    echo '  rclcpp::TimerBase::SharedPtr t_;'
    echo '};'
    echo 'int main(int argc, char ** argv) { rclcpp::init(argc, argv); auto n = std::make_shared<N>(); rclcpp::shutdown(); return 0; }'
  } > src/$name.cpp
  echo "add_executable($name $name.cpp)" >> src/CMakeLists.txt
  echo "target_link_libraries($name rclcpp::rclcpp)" >> src/CMakeLists.txt
done < cases.txt

# runtime check program
cat > src/rt.cpp <<'R'
#include <chrono>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>
#include <typeinfo>
#include "rclcpp/rclcpp.hpp"
using namespace std::chrono_literals;
int ticks = 0;
void spin_for(rclcpp::Node::SharedPtr n, std::chrono::milliseconds d) {
  auto end = std::chrono::steady_clock::now() + d;
  while (std::chrono::steady_clock::now() < end) { rclcpp::spin_some(n); std::this_thread::sleep_for(1ms); }
}
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string mode = argv[1];
  rclcpp::NodeOptions opts;
  if (mode == "sim_time_no_clock" || mode == "sim_time_wall_timer") opts.parameter_overrides({{"use_sim_time", true}});
  auto n = std::make_shared<rclcpp::Node>("rt", opts);
  rclcpp::TimerBase::SharedPtr keep;
  try {
    if (mode == "member_100ms") {
      keep = n->create_wall_timer(100ms, []() { ticks++; });
    } else if (mode == "local_discarded_100ms") {
      auto local = n->create_wall_timer(100ms, []() { ticks++; });  // goes out of scope here
    } else if (mode == "negative_period") {
      keep = n->create_wall_timer(-100ms, []() { ticks++; });
    } else if (mode == "zero_period_spin_200ms") {
      keep = n->create_wall_timer(0ms, []() { ticks++; });
    } else if (mode == "cancel_after_3") {
      keep = n->create_wall_timer(100ms, [](rclcpp::TimerBase & t) { if (++ticks == 3) t.cancel(); });
    } else if (mode == "sim_time_no_clock") {
      keep = rclcpp::create_timer(n, n->get_clock(), rclcpp::Duration(0, 100000000), []() { ticks++; });
    } else if (mode == "sim_time_wall_timer") {
      keep = n->create_wall_timer(100ms, []() { ticks++; });
    }
  } catch (const std::exception & e) {
    std::printf("mode=%s exception=%s what=%s\n", mode.c_str(), typeid(e).name(), e.what());
    rclcpp::shutdown(); return 3;
  }
  spin_for(n, mode == "zero_period_spin_200ms" ? 200ms : 1050ms);
  std::printf("mode=%s ticks=%d clock_type=%d\n", mode.c_str(), ticks, (int)n->get_clock()->get_clock_type());
  rclcpp::shutdown();
  return 0;
}
R
echo "add_executable(rt rt.cpp)" >> src/CMakeLists.txt
echo "target_link_libraries(rt rclcpp::rclcpp)" >> src/CMakeLists.txt

cmake -S src -B build > cmake.log 2>&1 || { echo "cmake configure failed"; cat cmake.log; exit 1; }
mkdir -p /e/raw_$ROS_DISTRO
for name in $(cut -d'|' -f1 cases.txt) rt; do
  t0=$(date +%s.%N)
  timeout 300 nice -n 10 cmake --build build --target $name -- -j1 > /e/raw_$ROS_DISTRO/$name.log 2>&1; rc=$?
  t1=$(date +%s.%N)
  echo
  echo "### CASE $name"
  if [ "$name" != rt ]; then
    echo "stmt: $(grep "^$name|" cases.txt | cut -d'|' -f3)"
    echo "chrono_literals: $(grep "^$name|" cases.txt | cut -d'|' -f2)"
  fi
  echo "build_exit=$rc seconds=$(python3 -c "print(round($t1-$t0,1))") log_lines=$(wc -l < /e/raw_$ROS_DISTRO/$name.log) error_lines=$(grep -c 'error:' /e/raw_$ROS_DISTRO/$name.log)"
  # first error lines, plus the "required from here" line in our file
  grep -E 'error:|static assertion|required from here' /e/raw_$ROS_DISTRO/$name.log | sed 's#/opt/ros/[a-z]*/include/#<ros>/include/#g; s#/w/src/##g' | cut -c1-400 | head -8
done

echo; echo "=== runtime (rclcpp)"
for m in member_100ms local_discarded_100ms negative_period zero_period_spin_200ms cancel_after_3 sim_time_no_clock sim_time_wall_timer; do
  timeout 20 ./build/rt $m 2>&1 | grep -v '^\s*$' | cut -c1-300; echo "exit=${PIPESTATUS[0]}"
done

echo; echo "=== runtime (rclpy)"
cat > /w/py_rt.py <<'P'
import sys, time, traceback
import rclpy
from rclpy.node import Node
mode = sys.argv[1]
rclpy.init()
n = Node('py_rt')
ticks = [0]
keep = None
def inc():
    ticks[0] += 1
def spin_for(sec):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=0.01)
try:
    if mode == 'member_100ms':
        keep = n.create_timer(0.1, inc)
    elif mode == 'local_discarded_100ms':
        def make():
            t = n.create_timer(0.1, inc)
        make()
    elif mode == 'int_period_1':
        keep = n.create_timer(1, inc)
    elif mode == 'ms_as_period_100':
        keep = n.create_timer(100, inc)
    elif mode == 'callback_with_arg':
        def cb(event):
            ticks[0] += 1
        keep = n.create_timer(0.1, cb)
    elif mode == 'negative_period':
        keep = n.create_timer(-0.1, inc)
    spin_for(1.05)
    print(f'mode={mode} ticks={ticks[0]} timers_held_by_node={len(list(n.timers))}')
except Exception as e:
    print(f'mode={mode} exception={type(e).__name__}: {e}')
    traceback.print_exc(limit=1)
P
for m in member_100ms local_discarded_100ms int_period_1 ms_as_period_100 callback_with_arg negative_period; do
  timeout 20 python3 /w/py_rt.py $m 2>&1 | grep -v '^\s*$' | cut -c1-300 | head -8; echo "exit=${PIPESTATUS[0]}"
done
echo "=== done $(date -u +%FT%TZ)"
