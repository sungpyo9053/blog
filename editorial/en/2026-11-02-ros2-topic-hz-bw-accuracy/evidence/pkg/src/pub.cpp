// publishes JointState with 2 joints at argv[1] Hz on /joint_states
#include <chrono>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  double hz = std::stod(argv[1]);
  auto node = std::make_shared<rclcpp::Node>("hz_pub");
  auto pub = node->create_publisher<sensor_msgs::msg::JointState>("/joint_states", 10);
  sensor_msgs::msg::JointState m; m.name = {"j1", "j2"}; m.position = {0, 0}; m.velocity = {0, 0}; m.effort = {0, 0};
  auto period = std::chrono::nanoseconds(static_cast<int64_t>(1e9 / hz));
  auto t = node->create_wall_timer(period, [&]() { m.header.stamp = node->now(); pub->publish(m); });
  rclcpp::spin(node); rclcpp::shutdown();
}
