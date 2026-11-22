#include "rclcpp/rclcpp.hpp"
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("b");
  RCLCPP_INFO_THROTTLE(n->get_logger(), *n->get_clock(), rclcpp::Duration::from_seconds(1.0), "x");
  return 0;
}
