// Stress: one thread waits for not-yet-available transforms, another publishes them.
// Prints iterations reached; reports DEADLOCK if progress stops for 3 s, OK after 20 s.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <thread>
#include <unistd.h>
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/create_timer_ros.h"
#include "geometry_msgs/msg/transform_stamped.hpp"
using namespace std::chrono_literals;
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("race");
  auto clock = std::make_shared<rclcpp::Clock>(RCL_SYSTEM_TIME);
  tf2_ros::Buffer buffer(clock);
  buffer.setCreateTimerInterface(std::make_shared<tf2_ros::CreateTimerROS>(
    node->get_node_base_interface(), node->get_node_timers_interface()));
  rclcpp::executors::SingleThreadedExecutor exec; exec.add_node(node);
  std::thread spin([&] { exec.spin(); });
  std::atomic<long> waits{0}, sets{0}, callbacks{0};
  std::atomic<bool> stop{false};
  std::thread waiter([&] {
    for (long i = 1; !stop; ++i) {
      buffer.waitForTransform("map", "base", tf2::TimePoint(std::chrono::milliseconds(i)), 50ms,
        [&](const tf2_ros::TransformStampedFuture &) { ++callbacks; });
      ++waits;
    }
  });
  std::thread setter([&] {
    for (long i = 1; !stop; ++i) {
      geometry_msgs::msg::TransformStamped t;
      t.header.frame_id = "map"; t.child_frame_id = "base";
      t.header.stamp = rclcpp::Time(0, i * 1000000); t.transform.rotation.w = 1.0;
      buffer.setTransform(t, "race");
      ++sets;
    }
  });
  auto start = std::chrono::steady_clock::now();
  long last = -1; auto still = start;
  while (true) {
    std::this_thread::sleep_for(100ms);
    long now_total = waits + sets;
    auto t = std::chrono::steady_clock::now();
    if (now_total != last) { last = now_total; still = t; }
    double el = std::chrono::duration<double>(t - start).count();
    if (t - still > 3s) {
      std::printf("DEADLOCK at %.1f s waits=%ld sets=%ld callbacks=%ld\n", el - 3.0, (long)waits, (long)sets, (long)callbacks);
      std::fflush(stdout); _exit(0);
    }
    if (el > 20.0) {
      std::printf("OK 20.0 s waits=%ld sets=%ld callbacks=%ld\n", (long)waits, (long)sets, (long)callbacks);
      std::fflush(stdout); _exit(0);
    }
  }
}
