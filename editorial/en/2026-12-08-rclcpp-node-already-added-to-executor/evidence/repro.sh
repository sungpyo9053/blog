#!/bin/bash
# rclcpp "Node '/x' has already been added to an executor" and
# "spin_*() called while already spinning": causes and fixes, measured.
#
# Host (runner):    bash repro.sh host <distro>    -> runs one distro in container pk2-p9-<distro>
# Inside container: bash /work/repro.sh inner      (called by host mode)

MODE=${1:-}

if [ "$MODE" = host ]; then
  D=$2
  ulimit -c 0
  docker pull -q ros:$D-ros-base >/dev/null
  docker run --name pk2-p9-$D --ulimit core=0 --cpus 1.5 --pids-limit 512 -v "$(dirname "$(readlink -f "$0")")":/work \
    ros:$D-ros-base bash /work/repro.sh inner
  exit $?
fi

[ "$MODE" = inner ] || { echo "usage: repro.sh host <distro> | inner"; exit 2; }

ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "compiler: $(g++ --version | head -1)"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"

mkdir -p /ws/src/exq/src && cd /ws/src/exq
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>exq</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_srvs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(exq)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_srvs REQUIRED)
add_executable(cases src/cases.cpp)
target_link_libraries(cases rclcpp::rclcpp ${std_srvs_TARGETS})
add_executable(uncaught src/uncaught.cpp)
target_link_libraries(uncaught rclcpp::rclcpp)
install(TARGETS cases uncaught DESTINATION lib/${PROJECT_NAME})
ament_package()
X

# The plain mistake, no try/catch: shows what the user actually sees.
cat > src/uncaught.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("my_node");
  rclcpp::executors::SingleThreadedExecutor exec;
  exec.add_node(node);
  rclcpp::spin(node);   // second executor for the same node
  rclcpp::shutdown();
}
X

cat > src/cases.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <rclcpp/version.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
using namespace std::chrono_literals;
using Trigger = std_srvs::srv::Trigger;
using Clock = std::chrono::steady_clock;
#if RCLCPP_VERSION_MAJOR >= 17
#define SRV_QOS rclcpp::ServicesQoS()
#else
#define SRV_QOS rmw_qos_profile_services_default
#endif

static double ms(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}

// Service server in its own node and executor thread, same process.
struct Server {
  rclcpp::Node::SharedPtr node;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> ex;
  rclcpp::Service<Trigger>::SharedPtr srv;
  std::thread th;
  Server() {
    node = std::make_shared<rclcpp::Node>("srv_node");
    srv = node->create_service<Trigger>("trig",
      [](const std::shared_ptr<Trigger::Request>, std::shared_ptr<Trigger::Response> r) {
        r->success = true; r->message = "ok"; });
    ex = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    ex->add_node(node);
    th = std::thread([this] { ex->spin(); });
  }
  ~Server() { ex->cancel(); if (th.joinable()) th.join(); }
};

static void report(const std::string & name, std::vector<double> & v, int want) {
  std::sort(v.begin(), v.end());
  std::cout << "RESULT " << name << " ok=" << v.size() << "/" << want;
  if (!v.empty()) std::cout << " median_ms=" << v[v.size() / 2] << " max_ms=" << v.back();
  std::cout << std::endl;
}

static const int N = 20;

int run(const std::string & c) {
  auto node = std::make_shared<rclcpp::Node>("my_node");

  if (c == "double_spin") {             // add_node, then rclcpp::spin(node)
    rclcpp::executors::SingleThreadedExecutor ex;
    ex.add_node(node);
    rclcpp::spin(node);
  } else if (c == "two_executors") {    // same node into two executors
    rclcpp::executors::SingleThreadedExecutor a, b;
    a.add_node(node);
    b.add_node(node);
  } else if (c == "add_twice_same") {   // same executor twice
    rclcpp::executors::SingleThreadedExecutor a;
    a.add_node(node);
    a.add_node(node);
  } else if (c == "cbgroup_two_executors") {
    auto g = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive, false);
    rclcpp::executors::SingleThreadedExecutor a, b;
    a.add_callback_group(g, node->get_node_base_interface());
    b.add_callback_group(g, node->get_node_base_interface());
  } else if (c == "cbgroup_auto_then_node") {  // group auto-added with node, then added to 2nd executor
    auto g = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive, true);
    rclcpp::executors::SingleThreadedExecutor a, b;
    a.add_node(node);
    b.add_callback_group(g, node->get_node_base_interface());
  } else if (c == "remove_then_spin") {  // control: remove_node frees the node
    rclcpp::executors::SingleThreadedExecutor a;
    a.add_node(node);
    a.remove_node(node);
    rclcpp::spin_some(node);
    std::cout << "RESULT remove_then_spin ok" << std::endl;
  } else if (c == "spin_some_in_cb") {   // rclcpp::spin_some(node) inside a timer of a spinning node
    auto t = node->create_wall_timer(100ms, [node] { rclcpp::spin_some(node); });
    rclcpp::spin(node);
  } else if (c == "exec_spin_some_in_cb" || c == "exec_spin_once_in_cb" || c == "exec_spin_all_in_cb") {
    rclcpp::executors::SingleThreadedExecutor ex;
    auto t = node->create_wall_timer(100ms, [&ex, c] {
      if (c == "exec_spin_some_in_cb") ex.spin_some();
      else if (c == "exec_spin_once_in_cb") ex.spin_once(0ms);
      else ex.spin_all(10ms);
    });
    ex.add_node(node);
    ex.spin();
  } else if (c == "sufc_in_cb" || c == "exec_sufc_in_cb" || c == "mte_sufc_in_cb") {
    Server s;
    auto cli = node->create_client<Trigger>("trig");
    cli->wait_for_service(5s);
    std::shared_ptr<rclcpp::Executor> ex;
    if (c == "mte_sufc_in_cb") ex = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();
    else ex = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    auto t = node->create_wall_timer(100ms, [node, cli, ex, c] {
      auto f = cli->async_send_request(std::make_shared<Trigger::Request>());
      if (c == "sufc_in_cb") rclcpp::spin_until_future_complete(node, f, 2s);
      else ex->spin_until_future_complete(f, 2s);
    });
    if (c == "sufc_in_cb") rclcpp::spin(node); else { ex->add_node(node); ex->spin(); }
  } else if (c == "mte_sufc_in_cb_caught") {  // same as mte_sufc_in_cb, exception caught in the callback
    Server s;
    auto cli = node->create_client<Trigger>("trig");
    cli->wait_for_service(5s);
    auto ex = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();
    auto t = node->create_wall_timer(100ms, [cli, ex] {
      auto f = cli->async_send_request(std::make_shared<Trigger::Request>());
      try { ex->spin_until_future_complete(f, 2s); }
      catch (const std::exception & e) { std::cout << "CAUGHT_IN_CALLBACK what(): " << e.what() << std::endl; }
      ex->cancel();
    });
    ex->add_node(node);
    ex->spin();
  } else if (c == "param_client_in_cb") {   // SyncParametersClient(node) used inside a callback
    Server s;
    auto t = node->create_wall_timer(100ms, [node] {
      auto pc = std::make_shared<rclcpp::SyncParametersClient>(node, "srv_node");
      pc->wait_for_service(5s);
      auto v = pc->get_parameters({"use_sim_time"});
      std::cout << "got " << v.size() << std::endl;
    });
    rclcpp::spin(node);
  } else if (c == "param_client_outside") {  // control: same client before spinning
    Server s;
    auto pc = std::make_shared<rclcpp::SyncParametersClient>(node, "srv_node");
    pc->wait_for_service(5s);
    auto v = pc->get_parameters({"use_sim_time"});
    std::cout << "RESULT param_client_outside got=" << v.size()
              << " use_sim_time=" << (v.size() ? v[0].value_to_string() : "?") << std::endl;
  } else if (c == "sufc_main") {   // control: the normal way, no spin before
    Server s;
    auto cli = node->create_client<Trigger>("trig");
    cli->wait_for_service(5s);
    std::vector<double> lat;
    for (int i = 0; i < N; ++i) {
      auto t0 = Clock::now();
      auto f = cli->async_send_request(std::make_shared<Trigger::Request>());
      if (rclcpp::spin_until_future_complete(node, f, 2s) == rclcpp::FutureReturnCode::SUCCESS)
        lat.push_back(ms(t0, Clock::now()));
    }
    report("sufc_main", lat, N);
  } else if (c == "fix_async_callback") {   // fix 1: async_send_request with a response callback
    Server s;
    auto cli = node->create_client<Trigger>("trig");
    cli->wait_for_service(5s);
    std::vector<double> lat; int sent = 0;
    auto t = node->create_wall_timer(100ms, [&] {
      if (sent >= N) return;
      ++sent;
      auto t0 = Clock::now();
      cli->async_send_request(std::make_shared<Trigger::Request>(),
        [&lat, t0](rclcpp::Client<Trigger>::SharedFuture) { lat.push_back(ms(t0, Clock::now())); });
    });
    auto end = Clock::now() + 10s;
    rclcpp::executors::SingleThreadedExecutor ex; ex.add_node(node);
    while ((int)lat.size() < N && Clock::now() < end) ex.spin_once(100ms);
    report("fix_async_callback", lat, N);
  } else if (c == "fix_mte_group" || c == "neg_mte_same_group" || c == "neg_ste_group") {
    // fix 2: client in its own callback group + MultiThreadedExecutor, block with wait_for
    Server s;
    auto timer_g = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto cli_g = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto cli = (c == "neg_mte_same_group")
      ? node->create_client<Trigger>("trig", SRV_QOS, timer_g)
      : node->create_client<Trigger>("trig", SRV_QOS, cli_g);
    cli->wait_for_service(5s);
    std::vector<double> lat; std::atomic<int> done{0}, timeouts{0};
    auto t = node->create_wall_timer(100ms, [&] {
      if (done + timeouts >= N) return;
      auto t0 = Clock::now();
      auto f = cli->async_send_request(std::make_shared<Trigger::Request>());
      if (f.wait_for(1s) == std::future_status::ready) { lat.push_back(ms(t0, Clock::now())); ++done; }
      else { ++timeouts; cli->remove_pending_request(f.request_id); }
    }, timer_g);
    std::shared_ptr<rclcpp::Executor> ex;
    if (c == "neg_ste_group") ex = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    else ex = std::make_shared<rclcpp::executors::MultiThreadedExecutor>(rclcpp::ExecutorOptions(), 2);
    ex->add_node(node);
    std::thread th([&] { ex->spin(); });
    auto end = Clock::now() + 30s;
    while (done + timeouts < N && Clock::now() < end) std::this_thread::sleep_for(50ms);
    ex->cancel(); th.join();
    report(c, lat, N);
    std::cout << "TIMEOUTS " << c << " " << timeouts.load() << std::endl;
  } else if (c == "fix_side_node") {   // fix 3: separate client node with its own executor
    Server s;
    auto side = std::make_shared<rclcpp::Node>("my_node_client");
    auto side_ex = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    side_ex->add_node(side);
    auto cli = side->create_client<Trigger>("trig");
    cli->wait_for_service(5s);
    std::vector<double> lat; int sent = 0;
    auto t = node->create_wall_timer(100ms, [&] {
      if (sent >= N) return;
      ++sent;
      auto t0 = Clock::now();
      auto f = cli->async_send_request(std::make_shared<Trigger::Request>());
      if (side_ex->spin_until_future_complete(f, 2s) == rclcpp::FutureReturnCode::SUCCESS)
        lat.push_back(ms(t0, Clock::now()));
    });
    rclcpp::executors::SingleThreadedExecutor ex; ex.add_node(node);
    auto end = Clock::now() + 10s;
    while (sent < N && Clock::now() < end) ex.spin_once(100ms);
    report("fix_side_node", lat, N);
  } else {
    std::cout << "unknown case " << c << std::endl; return 2;
  }
  return 0;
}

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string c = argc > 1 ? argv[1] : "";
  int rc = 0;
  auto t0 = Clock::now();
  try {
    rc = run(c);
  } catch (const std::exception & e) {
    std::cout << "EXCEPTION " << c << " after_ms=" << ms(t0, Clock::now())
              << " what(): " << e.what() << std::endl;
    rc = 1;
  }
  rclcpp::shutdown();
  return rc;
}
X

cd /ws
echo "=== build"
export MAKEFLAGS=-j1
( time colcon build --event-handlers console_direct+ --parallel-workers 1 ) 2>&1 \
  | grep -E "warning|error|deprecat|Finished|Summary|real" | head -40
source /ws/install/setup.bash

echo "=== uncaught (plain mistake, no try/catch)"
timeout 20 ros2 run exq uncaught 2>&1 | tail -5; echo "exit=${PIPESTATUS[0]}"

for c in double_spin two_executors add_twice_same cbgroup_two_executors cbgroup_auto_then_node \
         remove_then_spin spin_some_in_cb exec_spin_some_in_cb exec_spin_once_in_cb exec_spin_all_in_cb \
         sufc_in_cb exec_sufc_in_cb mte_sufc_in_cb mte_sufc_in_cb_caught param_client_in_cb param_client_outside \
         sufc_main fix_async_callback fix_mte_group neg_mte_same_group neg_ste_group fix_side_node; do
  echo "=== case $c"
  timeout 60 ros2 run exq cases $c 2>&1 | grep -v "^\s*$" | tail -8
  echo "exit=${PIPESTATUS[0]}"
done
echo "=== repeat mte_sufc_in_cb x10 (how the abort is reported)"
for i in $(seq 1 10); do
  timeout 30 ros2 run exq cases mte_sufc_in_cb 2>&1 | grep -E "terminate called|what\(\)" | tr '\n' ' '; echo
done | sort | uniq -c
echo "=== done"
