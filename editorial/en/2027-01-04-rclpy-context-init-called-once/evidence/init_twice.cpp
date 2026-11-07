// rclcpp init-twice experiments: ./init_twice <case>
#include <chrono>
#include <cstdio>
#include <functional>
#include <typeinfo>
#include <memory>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

static void report(const char * label, const std::function<void()> & fn)
{
  try {
    fn();
    std::printf("%s: OK\n", label);
  } catch (const std::exception & e) {
    std::printf("%s: THREW %s: %s\n", label, typeid(e).name(), e.what());
  }
}

static void use_node(const char * name)
{
  auto n = std::make_shared<rclcpp::Node>(name);
  auto p = n->create_publisher<std_msgs::msg::String>("chatter", 10);
  std_msgs::msg::String m; m.data = "x"; p->publish(m);
}

int main(int argc, char ** argv)
{
  std::string c = argc > 1 ? argv[1] : "";
  if (c == "twice") {
    rclcpp::init(argc, argv);
    report("second rclcpp::init", [&] {rclcpp::init(argc, argv);});
    std::printf("rclcpp::ok() after failed init: %d\n", rclcpp::ok());
    report("use default context after failed init", [] {use_node("after_fail");});
    rclcpp::shutdown();
  } else if (c == "reinit") {
    rclcpp::init(argc, argv); rclcpp::shutdown();
    std::printf("rclcpp::ok() after shutdown: %d\n", rclcpp::ok());
    report("init after shutdown", [&] {rclcpp::init(argc, argv);});
    report("node after re-init", [] {use_node("re");});
    rclcpp::shutdown();
  } else if (c == "guard") {
    rclcpp::init(argc, argv);
    report("guarded with rclcpp::ok()", [&] {if (!rclcpp::ok()) {rclcpp::init(argc, argv); std::printf("  (init called)\n");} else {std::printf("  (skipped, already ok)\n");}});
    rclcpp::shutdown();
    report("guarded with rclcpp::ok() after shutdown", [&] {if (!rclcpp::ok()) {rclcpp::init(argc, argv); std::printf("  (init called)\n");} else {std::printf("  (skipped, already ok)\n");}});
    rclcpp::shutdown();
  } else if (c == "fixture") {
    // gtest-style: SetUp() inits, TearDown() maybe shuts down, 3 tests
    for (int teardown = 0; teardown < 2; ++teardown) {
      int ok = 0, bad = 0; std::string msg;
      for (int t = 0; t < 3; ++t) {
        try {
          rclcpp::init(argc, argv);
          use_node("fx");
          if (teardown) {rclcpp::shutdown();}
          ++ok;
        } catch (const std::exception & e) {++bad; msg = e.what();}
      }
      std::printf("fixture %s: passed=%d threw=%d %s\n",
        teardown ? "with TearDown shutdown" : "no TearDown shutdown", ok, bad, msg.c_str());
      if (rclcpp::ok()) {rclcpp::shutdown();}
    }
  } else if (c == "context") {
    rclcpp::init(argc, argv);
    auto ctx = std::make_shared<rclcpp::Context>();
    report("ctx->init while default is up", [&] {ctx->init(argc, argv);});
    report("node on ctx", [&] {
        rclcpp::NodeOptions o; o.context(ctx);
        auto n = std::make_shared<rclcpp::Node>("on_ctx", o);
      });
    report("second ctx->init", [&] {ctx->init(argc, argv);});
    ctx->shutdown("done"); rclcpp::shutdown();
  } else if (c == "timing") {
    const int N = 50;
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < N; ++i) {rclcpp::init(argc, argv); rclcpp::shutdown();}
    auto t1 = std::chrono::steady_clock::now();
    for (int i = 0; i < N; ++i) {rclcpp::init(argc, argv); use_node("t"); rclcpp::shutdown();}
    auto t2 = std::chrono::steady_clock::now();
    std::printf("init+shutdown x%d: %.2f ms each\n", N,
      std::chrono::duration<double, std::milli>(t1 - t0).count() / N);
    std::printf("init+node+publish+shutdown x%d: %.2f ms each\n", N,
      std::chrono::duration<double, std::milli>(t2 - t1).count() / N);
  } else if (c == "uncaught") {
    rclcpp::init(argc, argv);
    rclcpp::init(argc, argv);
  }
  return 0;
}
