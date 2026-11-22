// rclcpp throttle/once/skipfirst cases. Loop: 100 Hz for 5 s.
#include <chrono>
#include <memory>
#include <string>
#include <thread>
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class Worker : public rclcpp::Node {
public:
  Worker(const std::string & name, bool sim)
  : Node(name, rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("use_sim_time", sim)})) {}
  // one call site shared by every instance
  void tick_throttle(int i) { RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 1000, "MARK %s i=%d", get_name(), i); }
  void tick_once(int i) { RCLCPP_INFO_ONCE(get_logger(), "MARK %s i=%d", get_name(), i); }
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string c = argv[1];
  bool sim = c.rfind("sim", 0) == 0;
  auto n = std::make_shared<Worker>("ct", sim);
  auto n2 = std::make_shared<Worker>("ct2", false);
  rclcpp::Clock steady(RCL_STEADY_TIME);
  auto lg = n->get_logger();
  auto t0 = std::chrono::steady_clock::now();
  int i = 0;
  while (std::chrono::steady_clock::now() - t0 < 5s) {
    rclcpp::spin_some(n);
    if (c == "thr1000" || c == "sim_nodeclock") {
      RCLCPP_INFO_THROTTLE(lg, *n->get_clock(), 1000, "MARK i=%d", i);
    } else if (c == "thr1") {
      RCLCPP_INFO_THROTTLE(lg, *n->get_clock(), 1, "MARK i=%d", i);
    } else if (c == "thr_dur_ns") {
      rclcpp::Duration d = rclcpp::Duration::from_seconds(1.0);
      RCLCPP_INFO_THROTTLE(lg, *n->get_clock(), d.nanoseconds() / 1000000, "MARK i=%d", i);
    } else if (c == "skipfirst_thr") {
      RCLCPP_INFO_SKIPFIRST_THROTTLE(lg, *n->get_clock(), 1000, "MARK i=%d", i);
    } else if (c == "skipfirst") {
      RCLCPP_INFO_SKIPFIRST(lg, "MARK i=%d", i);
    } else if (c == "two_instances") {
      n->tick_throttle(i);
      n2->tick_throttle(i);
    } else if (c == "two_instances_once") {
      n->tick_once(i);
      n2->tick_once(i);
    } else if (c == "sim_steady") {
      RCLCPP_INFO_THROTTLE(lg, steady, 1000, "MARK i=%d", i);
    } else {
      fprintf(stderr, "unknown case\n");
      return 2;
    }
    ++i;
    std::this_thread::sleep_for(10ms);
  }
  printf("RESULT case=%s calls=%d sim_now_ns=%ld\n", c.c_str(), i, (long)n->get_clock()->now().nanoseconds());
  fflush(stdout);
  rclcpp::shutdown();
  return 0;
}
