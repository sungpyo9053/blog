// Compiles only where rclcpp has pre/post set-parameter callbacks.
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("postcheck");
  auto pre = n->add_pre_set_parameters_callback([](std::vector<rclcpp::Parameter> &) {});
  auto post = n->add_post_set_parameters_callback([](const std::vector<rclcpp::Parameter> &) {});
  rclcpp::shutdown();
  return 0;
}
