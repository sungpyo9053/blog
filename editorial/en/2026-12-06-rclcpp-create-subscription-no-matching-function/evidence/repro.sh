#!/bin/bash
# Run inside ros:<distro>-ros-base. Compiles one small rclcpp node per variant and records
# whether create_subscription / create_publisher compiles, how long it took, and the error text.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-std-msgs 2>/dev/null
g++ --version | head -1; cmake --version | head -1
W=/w; mkdir -p $W/src $W/build; cd $W

# name|constructor body|member declarations
cat > /w/variants.txt <<'X'
ok_bind_sharedptr|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
ok_lambda_constref|sub_ = create_subscription<String>("chatter", 10, [this](const String & msg) { cb(msg); });|void cb(const String & msg) { (void)msg; }
c_no_qos|sub_ = create_subscription<String>("chatter", std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
fix_no_qos_depth|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
c_no_placeholder|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this));|void cb(const String::SharedPtr msg) { (void)msg; }
c_no_template_arg|sub_ = create_subscription("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
c_wrong_msg_type|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const std_msgs::msg::Int32::SharedPtr msg) { (void)msg; }
c_extra_arg_unbound|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String & msg, int src) { (void)msg; (void)src; }
fix_extra_arg_bind|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1, 1));|void cb(const String & msg, int src) { (void)msg; (void)src; }
fix_extra_arg_lambda|sub_ = create_subscription<String>("chatter", 10, [this](const String & msg) { cb(msg, 1); });|void cb(const String & msg, int src) { (void)msg; (void)src; }
c_rmw_qos_profile|sub_ = create_subscription<String>("chatter", rmw_qos_profile_sensor_data, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
fix_rmw_qos_sensordataqos|sub_ = create_subscription<String>("chatter", rclcpp::SensorDataQoS(), std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
fix_rmw_qos_wrapped|sub_ = create_subscription<String>("chatter", rclcpp::QoS(rclcpp::QoSInitialization::from_rmw(rmw_qos_profile_sensor_data), rmw_qos_profile_sensor_data), std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; }
c_overloaded_cb|sub_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; } void cb(const std_msgs::msg::Int32::SharedPtr msg) { (void)msg; }
fix_overloaded_lambda|sub_ = create_subscription<String>("chatter", 10, [this](const String::SharedPtr msg) { cb(msg); });|void cb(const String::SharedPtr msg) { (void)msg; } void cb(const std_msgs::msg::Int32::SharedPtr msg) { (void)msg; }
c_generic_lambda|sub_ = create_subscription<String>("chatter", 10, [](auto msg) { (void)msg; });|
c_member_type_mismatch|sub_int_ = create_subscription<String>("chatter", 10, std::bind(&N::cb, this, _1));|void cb(const String::SharedPtr msg) { (void)msg; } rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr sub_int_;
c_pub_no_qos|pub_ = create_publisher<String>("chatter");|
fix_pub_depth|pub_ = create_publisher<String>("chatter", 10);|
sig_constref|sub_ = create_subscription<String>("chatter", 10, [](const String & m) { (void)m; });|
sig_value|sub_ = create_subscription<String>("chatter", 10, [](String m) { (void)m; });|
sig_ref|sub_ = create_subscription<String>("chatter", 10, [](String & m) { (void)m; });|
sig_sharedptr|sub_ = create_subscription<String>("chatter", 10, [](String::SharedPtr m) { (void)m; });|
sig_const_sharedptr|sub_ = create_subscription<String>("chatter", 10, [](const String::SharedPtr m) { (void)m; });|
sig_const_sharedptr_ref|sub_ = create_subscription<String>("chatter", 10, [](const String::SharedPtr & m) { (void)m; });|
sig_sharedptr_ref|sub_ = create_subscription<String>("chatter", 10, [](String::SharedPtr & m) { (void)m; });|
sig_constsharedptr|sub_ = create_subscription<String>("chatter", 10, [](String::ConstSharedPtr m) { (void)m; });|
sig_const_constsharedptr_ref|sub_ = create_subscription<String>("chatter", 10, [](const String::ConstSharedPtr & m) { (void)m; });|
sig_uniqueptr|sub_ = create_subscription<String>("chatter", 10, [](String::UniquePtr m) { (void)m; });|
sig_constref_msginfo|sub_ = create_subscription<String>("chatter", 10, [](const String & m, const rclcpp::MessageInfo & i) { (void)m; (void)i; });|
sig_sharedptr_msginfo|sub_ = create_subscription<String>("chatter", 10, [](String::SharedPtr m, const rclcpp::MessageInfo & i) { (void)m; (void)i; });|
sig_serialized_sharedptr|sub_ = create_subscription<String>("chatter", 10, [](std::shared_ptr<rclcpp::SerializedMessage> m) { (void)m; });|
sig_serialized_constref|sub_ = create_subscription<String>("chatter", 10, [](const rclcpp::SerializedMessage & m) { (void)m; });|
sig_raw_pointer|sub_ = create_subscription<String>("chatter", 10, [](const String * m) { (void)m; });|
X

{
echo 'cmake_minimum_required(VERSION 3.8)'
echo 'project(subvariants CXX)'
echo 'set(CMAKE_CXX_STANDARD 17)'
echo 'find_package(rclcpp REQUIRED)'
echo 'find_package(std_msgs REQUIRED)'
} > src/CMakeLists.txt
while IFS='|' read -r name ctor members; do
cat > src/$name.cpp <<C
#include <functional>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_msgs/msg/int32.hpp"
using std::placeholders::_1;
using String = std_msgs::msg::String;
class N : public rclcpp::Node
{
public:
  N() : Node("n")
  {
    $ctor
  }
  $members
  rclcpp::Subscription<String>::SharedPtr sub_;
  rclcpp::Publisher<String>::SharedPtr pub_;
};
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto n = std::make_shared<N>();
  rclcpp::shutdown();
  return 0;
}
C
echo "add_executable($name $name.cpp)" >> src/CMakeLists.txt
echo "target_link_libraries($name rclcpp::rclcpp \${std_msgs_TARGETS})" >> src/CMakeLists.txt
done < /w/variants.txt

# runtime check: one callback, extra argument passed via lambda, two topics
cat > src/rt_extra_arg.cpp <<'C'
#include <chrono>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
using String = std_msgs::msg::String;
class Listener : public rclcpp::Node
{
public:
  Listener() : Node("listener")
  {
    s1_ = create_subscription<String>("chatter_1", 10, [this](const String & m) { cb(m, 1); });
    s2_ = create_subscription<String>("chatter_2", 10, [this](const String & m) { cb(m, 2); });
  }
  void cb(const String & m, int src) { RCLCPP_INFO(get_logger(), "RT heard '%s' from %d", m.data.c_str(), src); }
  rclcpp::Subscription<String>::SharedPtr s1_, s2_;
};
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto n = std::make_shared<Listener>();
  rclcpp::executors::SingleThreadedExecutor ex; ex.add_node(n);
  ex.spin_until_future_complete(std::promise<void>().get_future(), std::chrono::seconds(12));
  rclcpp::shutdown();
  return 0;
}
C
echo "add_executable(rt_extra_arg rt_extra_arg.cpp)" >> src/CMakeLists.txt
echo "target_link_libraries(rt_extra_arg rclcpp::rclcpp \${std_msgs_TARGETS})" >> src/CMakeLists.txt

cd build && cmake ../src -DCMAKE_BUILD_TYPE=Release > /tmp/cmake.log 2>&1 || { cat /tmp/cmake.log; exit 1; }
mkdir -p /w/logs
while IFS='|' read -r name ctor members; do
  t0=$(date +%s.%N)
  make $name > /w/logs/$name.log 2>&1; rc=$?
  t1=$(date +%s.%N)
  L=/w/logs/$name.log
  printf '### %s rc=%s secs=%.1f lines=%s bytes=%s errors=%s warnings=%s\n' "$name" "$rc" "$(awk "BEGIN{print $t1 - $t0}")" \
    "$(wc -l < $L)" "$(wc -c < $L)" "$(grep -c 'error:' $L)" "$(grep -c 'warning:' $L)"
  if [ $rc -ne 0 ]; then
    grep -m3 'error:' $L | sed 's#^/w/src/##' | cut -c1-400
    grep -E 'static assertion failed|static_assert' $L | sort -u | head -3 | cut -c1-400
    grep -E 'candidate expects|no known conversion|could not convert|no match for' $L | sort -u | head -4 | cut -c1-400
  else
    grep 'warning:' $L | sort -u | head -3 | cut -c1-400
  fi
done < /w/variants.txt

echo "=== runtime check"
make rt_extra_arg > /w/logs/rt.log 2>&1 || { tail -20 /w/logs/rt.log; }
./rt_extra_arg & P=$!
sleep 3
timeout 20 ros2 topic pub --once -w 1 /chatter_1 std_msgs/msg/String "{data: one}" > /dev/null 2>&1
timeout 20 ros2 topic pub --once -w 1 /chatter_2 std_msgs/msg/String "{data: two}" > /dev/null 2>&1
wait $P; echo "rt exit=$?"
echo "=== done $ROS_DISTRO"
