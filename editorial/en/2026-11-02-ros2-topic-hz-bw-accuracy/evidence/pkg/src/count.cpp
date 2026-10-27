// counts messages on /joint_states for argv[1] seconds after a 2 s warm-up, prints rate
#include <chrono>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  double secs = std::stod(argv[1]);
  auto node = std::make_shared<rclcpp::Node>("hz_count");
  long n = 0; size_t bytes = 0; bool on = false;
  auto sub = node->create_subscription<sensor_msgs::msg::JointState>("/joint_states", rclcpp::QoS(1000),
    [&](std::shared_ptr<rclcpp::SerializedMessage> m) { if (on) { n++; bytes += m->size(); } });
  auto t0 = std::chrono::steady_clock::now();
  while (rclcpp::ok() && std::chrono::steady_clock::now() - t0 < std::chrono::seconds(2)) rclcpp::spin_some(node);
  on = true; auto t1 = std::chrono::steady_clock::now();
  while (rclcpp::ok() && std::chrono::steady_clock::now() - t1 < std::chrono::duration<double>(secs)) rclcpp::spin_some(node);
  double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();
  printf("count: %ld msgs in %.2f s = %.1f Hz, %.0f B/msg serialized, %.1f KB/s\n", n, el, n / el, n ? (double)bytes / n : 0.0, bytes / el / 1024);
  rclcpp::shutdown();
}
