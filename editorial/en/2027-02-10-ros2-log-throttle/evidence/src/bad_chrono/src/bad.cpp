#include <chrono>
#include "rclcpp/rclcpp.hpp"
using namespace std::chrono_literals;
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("b");
  RCLCPP_INFO_THROTTLE(n->get_logger(), *n->get_clock(), 1s, "x");
  return 0;
}
