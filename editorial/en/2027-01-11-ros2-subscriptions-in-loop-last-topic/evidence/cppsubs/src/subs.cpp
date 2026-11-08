// Usage: subs <not_stored|stored_loop|reset>
#include <chrono>
#include <cstdio>
#include <map>
#include <string>
#include <vector>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
using String = std_msgs::msg::String;
using namespace std::chrono;

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string variant = argc > 1 ? argv[1] : "stored_loop";
  auto sub_node = std::make_shared<rclcpp::Node>("cpp_sub");
  auto pub_node = std::make_shared<rclcpp::Node>("cpp_pub");
  std::vector<std::string> topics = {"/robot1/pose", "/robot2/pose", "/robot3/pose"};
  int right = 0, wrong = 0, after_reset = 0;
  bool reset_done = false;
  std::vector<rclcpp::Subscription<String>::SharedPtr> subs;
  for (const auto & topic : topics) {
    auto cb = [&, topic](const String & msg) {
      if (reset_done) after_reset++;
      if (msg.data == topic) right++; else wrong++;
    };
    if (variant == "not_stored") {
      sub_node->create_subscription<String>(topic, 10, cb);  // return value dropped
    } else {
      subs.push_back(sub_node->create_subscription<String>(topic, 10, cb));
    }
  }
  std::map<std::string, rclcpp::Publisher<String>::SharedPtr> pubs;
  for (const auto & t : topics) pubs[t] = pub_node->create_publisher<String>(t, 10);
  rclcpp::executors::SingleThreadedExecutor ex;
  ex.add_node(sub_node); ex.add_node(pub_node);
  auto t0 = steady_clock::now();
  while (steady_clock::now() - t0 < 2s && pubs["/robot1/pose"]->get_subscription_count() == 0)
    ex.spin_some(10ms);
  std::printf("variant %s matched_count_after_wait %zu graph_count %zu\n", variant.c_str(),
    pubs["/robot1/pose"]->get_subscription_count(), pub_node->count_subscribers("/robot1/pose"));
  auto publish_for = [&](milliseconds d) {
    auto end = steady_clock::now() + d;
    while (steady_clock::now() < end) {
      for (auto & kv : pubs) { String m; m.data = kv.first; kv.second->publish(m); }
      auto e2 = steady_clock::now() + 50ms;
      while (steady_clock::now() < e2) ex.spin_some(5ms);
    }
  };
  publish_for(1000ms);
  std::printf("received %d label_matches_source %d label_wrong %d\n", right + wrong, right, wrong);
  if (variant == "reset") {
    for (auto & s : subs) s.reset();
    reset_done = true;
    auto tr = steady_clock::now();
    double drop = -1;
    while (steady_clock::now() - tr < 5s) {
      if (drop < 0 && pubs["/robot1/pose"]->get_subscription_count() == 0)
        drop = duration<double>(steady_clock::now() - tr).count();
      publish_for(20ms);
    }
    std::printf("after reset(): msgs_after_reset %d publisher_matched_zero_after_s %.4f graph_count_after_5s %zu\n",
      after_reset, drop, pub_node->count_subscribers("/robot1/pose"));
  }
  rclcpp::shutdown();
  return 0;
}
