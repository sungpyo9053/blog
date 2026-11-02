#!/bin/bash
# std::bad_weak_ptr from shared_from_this() in ROS 2 nodes: causes and fixes.
# Run on the runner, one distro at a time:
#   docker run --rm --name pck-<distro> --ulimit core=0 --pids-limit 256 --cpus 1.5 \
#     -v $PWD:/e ros:<distro>-ros-base bash /e/repro.sh > out_<distro>.txt 2>&1
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO date=$(date -u +%FT%TZ)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-tf2-ros ros-$ROS_DISTRO-rclcpp-lifecycle \
  ros-$ROS_DISTRO-rclcpp-components 2>/dev/null
g++ --version | head -1; nproc; echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export ROS_DOMAIN_ID=$(( 40 + RANDOM % 50 ))

echo; echo "##### install image_transport (apt, inside this container only)"
T0=$(date +%s)
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends ros-$ROS_DISTRO-image-transport ) > /tmp/apt.log 2>&1
echo "apt exit=$? seconds=$(( $(date +%s) - T0 ))"; tail -3 /tmp/apt.log
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-image-transport 2>/dev/null

W=/tmp/ws; mkdir -p $W/src/bwp/src $W/src/bwp_it/src
cat > $W/src/bwp/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>bwp</name><version>0.0.1</version><description>bad_weak_ptr repro</description>
  <maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><depend>rclcpp_lifecycle</depend><depend>rclcpp_components</depend>
  <depend>std_msgs</depend><depend>tf2_ros</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
cat > $W/src/bwp/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(bwp)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
add_executable(bwp_node src/bwp_node.cpp)
target_link_libraries(bwp_node rclcpp::rclcpp rclcpp_lifecycle::rclcpp_lifecycle ${std_msgs_TARGETS} tf2_ros::tf2_ros)
add_library(bwp_components SHARED src/components.cpp)
target_link_libraries(bwp_components rclcpp::rclcpp rclcpp_components::component ${std_msgs_TARGETS})
rclcpp_components_register_nodes(bwp_components "bwp::BadComponent" "bwp::TimerComponent")
install(TARGETS bwp_components ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
install(TARGETS bwp_node DESTINATION lib/${PROJECT_NAME})
ament_package()
EOF
cat > $W/src/bwp/src/common.hpp <<'EOF'
#pragma once
#include <chrono>
#include <cstdio>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
// Stands in for any class whose constructor wants rclcpp::Node::SharedPtr
// (image_transport::ImageTransport, older tf2/MoveIt/nav helpers, your own).
struct NeedsNode {
  explicit NeedsNode(rclcpp::Node::SharedPtr n) : node(n) {
    pub = n->create_publisher<std_msgs::msg::String>("helper_out", 10);
  }
  rclcpp::Node::SharedPtr node;  // holds a strong reference
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub;
};
struct NeedsNodeWeak {
  explicit NeedsNodeWeak(rclcpp::Node::SharedPtr n) : node(n) {
    pub = n->create_publisher<std_msgs::msg::String>("helper_out", 10);
  }
  rclcpp::Node::WeakPtr node;    // holds a weak reference
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub;
};
EOF
cat > $W/src/bwp/src/bwp_node.cpp <<'EOF'
#include <algorithm>
#include <string>
#include <vector>
#include "common.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#if __has_include("tf2_ros/transform_broadcaster.hpp")
#include "tf2_ros/transform_broadcaster.hpp"
#include "tf2_ros/transform_listener.hpp"
#include "tf2_ros/buffer.hpp"
#else
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#endif
using namespace std::chrono_literals;
using Clock = std::chrono::steady_clock;
static double us(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::micro>(b - a).count();
}

class CtorBody : public rclcpp::Node {
public:
  CtorBody() : Node("ctor_body") {
    RCLCPP_INFO(get_logger(), "constructor: calling shared_from_this()");
    auto self = shared_from_this();
    RCLCPP_INFO(get_logger(), "constructor: after shared_from_this() (not expected)");
  }
};
class CtorInitList : public rclcpp::Node {
public:
  CtorInitList() : Node("ctor_initlist"), helper_(shared_from_this()) {}
  NeedsNode helper_;
};
class CtorTf : public rclcpp::Node {
public:
  CtorTf() : Node("ctor_tf") {
    br_ = std::make_shared<tf2_ros::TransformBroadcaster>(shared_from_this());
  }
  std::shared_ptr<tf2_ros::TransformBroadcaster> br_;
};
class Plain : public rclcpp::Node {
public:
  explicit Plain(const std::string & n) : Node(n) {}
};
class WeakInCtor : public rclcpp::Node {
public:
  WeakInCtor() : Node("weak_in_ctor") {
    auto w = weak_from_this();
    std::printf("RESULT weak_in_ctor: weak_from_this().expired()=%d lock()==nullptr=%d\n",
      (int)w.expired(), (int)(w.lock() == nullptr));
  }
};
class DtorSft : public rclcpp::Node {
public:
  DtorSft() : Node("dtor_sft") {}
  ~DtorSft() override {
    try { auto s = shared_from_this(); std::printf("RESULT dtor: shared_from_this() returned\n"); }
    catch (const std::bad_weak_ptr & e) { std::printf("RESULT dtor: caught std::bad_weak_ptr what()=%s\n", e.what()); }
    std::fflush(stdout);
  }
};
class WrapThis : public rclcpp::Node {
public:
  WrapThis() : Node("wrap_this") { self_ = rclcpp::Node::SharedPtr(this); }
  rclcpp::Node::SharedPtr self_;
};
class NoopDeleter : public rclcpp::Node {
public:
  NoopDeleter() : Node("noop_deleter") {
    // the helper keeps the non-owning shared_ptr, as image_transport::ImageTransport would
    helper_ = std::make_shared<NeedsNode>(rclcpp::Node::SharedPtr(this, [](rclcpp::Node *) {}));
  }
  ~NoopDeleter() override { std::printf("RESULT noop_deleter: destructor ran\n"); std::fflush(stdout); }
  std::shared_ptr<NeedsNode> helper_;
};
class FixInit : public rclcpp::Node {
public:
  explicit FixInit(const std::string & which) : Node("fix_init"), which_(which) {}
  ~FixInit() override { std::printf("  destructor ran (%s)\n", which_.c_str()); std::fflush(stdout); }
  void init() {
    if (which_ == "helper") helper_ = std::make_shared<NeedsNode>(shared_from_this());
    if (which_ == "helper_weak") helper_weak_ = std::make_shared<NeedsNodeWeak>(shared_from_this());
    if (which_ == "tf_broadcaster") br_ = std::make_shared<tf2_ros::TransformBroadcaster>(shared_from_this());
    if (which_ == "tf_listener") {
      buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
      tl_ = std::make_shared<tf2_ros::TransformListener>(*buffer_, shared_from_this());
    }
  }
  std::string which_;
  std::shared_ptr<NeedsNode> helper_;
  std::shared_ptr<NeedsNodeWeak> helper_weak_;
  std::shared_ptr<tf2_ros::TransformBroadcaster> br_;
  std::shared_ptr<tf2_ros::Buffer> buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tl_;
};
class FixTimer : public rclcpp::Node {
public:
  FixTimer() : Node("fix_timer") {
    init_timer_ = create_wall_timer(0ms, [this]() {
      init_timer_->cancel();
      t_cb = Clock::now();
      helper_ = std::make_shared<NeedsNodeWeak>(shared_from_this());
      calls++;
    });
    t_ctor_end = Clock::now();
  }
  rclcpp::TimerBase::SharedPtr init_timer_;
  std::shared_ptr<NeedsNodeWeak> helper_;
  Clock::time_point t_ctor_end, t_cb;
  int calls = 0;
};
class FixRaw : public rclcpp::Node {
public:
  FixRaw() : Node("fix_raw") {
    br_ = std::make_shared<tf2_ros::TransformBroadcaster>(this);
    buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
    tl_ = std::make_shared<tf2_ros::TransformListener>(*buffer_, this);
    std::printf("RESULT fix_raw: TransformBroadcaster(this) and TransformListener(buffer, this) constructed in the constructor\n");
  }
  ~FixRaw() override { std::printf("  destructor ran (fix_raw)\n"); std::fflush(stdout); }
  std::shared_ptr<tf2_ros::TransformBroadcaster> br_;
  std::shared_ptr<tf2_ros::Buffer> buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tl_;
};
class LcCtor : public rclcpp_lifecycle::LifecycleNode {
public:
  LcCtor() : LifecycleNode("lc_ctor") { auto self = shared_from_this(); }
};
class LcConfigure : public rclcpp_lifecycle::LifecycleNode {
public:
  LcConfigure() : LifecycleNode("lc_configure") {}
  using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;
  CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
    br_ = std::make_shared<tf2_ros::TransformBroadcaster>(shared_from_this());
    std::printf("RESULT lc_configure: shared_from_this() worked in on_configure\n");
    return CallbackReturn::SUCCESS;
  }
  std::shared_ptr<tf2_ros::TransformBroadcaster> br_;
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string mode = argc > 1 ? argv[1] : "";
  std::printf("mode=%s __cplusplus=%ld\n", mode.c_str(), (long)__cplusplus); std::fflush(stdout);
  if (mode == "ctor_body") auto n = std::make_shared<CtorBody>();
  else if (mode == "ctor_initlist") auto n = std::make_shared<CtorInitList>();
  else if (mode == "ctor_tf") auto n = std::make_shared<CtorTf>();
  else if (mode == "lc_ctor") auto n = std::make_shared<LcCtor>();
  else if (mode == "stack") { Plain n("stack_node"); auto s = n.shared_from_this(); }
  else if (mode == "unique") { auto u = std::make_unique<Plain>("unique_node"); auto s = u->shared_from_this(); }
  else if (mode == "catch") {
    try { auto n = std::make_shared<CtorBody>(); }
    catch (const std::bad_weak_ptr & e) { std::printf("RESULT catch: std::bad_weak_ptr caught, what()=%s\n", e.what()); }
  }
  else if (mode == "unique_then_shared") {
    auto u = std::make_unique<Plain>("unique_node");
    rclcpp::Node::SharedPtr s = std::move(u);
    auto s2 = s->shared_from_this();
    std::printf("RESULT unique_then_shared: shared_from_this() ok, use_count=%ld\n", s.use_count());
  }
  else if (mode == "weak_in_ctor") auto n = std::make_shared<WeakInCtor>();
  else if (mode == "dtor") { auto n = std::make_shared<DtorSft>(); n.reset(); }
  else if (mode == "wrap_this") {
    { auto n = std::make_shared<WrapThis>(); std::printf("RESULT wrap_this: constructed, use_count=%ld\n", n.use_count()); std::fflush(stdout); }
    std::printf("RESULT wrap_this: owner released, process still running\n");
  }
  else if (mode == "noop_deleter") {
    auto owner = std::make_shared<NoopDeleter>();
    auto sfp = owner->shared_from_this();
    bool same = !owner.owner_before(sfp) && !sfp.owner_before(owner);
    std::printf("RESULT noop_deleter: owner.use_count=%ld shared_from_this().use_count=%ld same_control_block=%d\n",
      owner.use_count(), sfp.use_count(), (int)same);
    std::weak_ptr<NoopDeleter> w = owner;
    owner.reset();
    std::printf("RESULT noop_deleter: after owner.reset() with the shared_from_this() copy still held: object destroyed=%d, that copy reports use_count=%ld (not dereferenced)\n",
      (int)w.expired(), sfp.use_count());
  }
  else if (mode == "fix_init") {
    for (const char * which : {"helper", "helper_weak", "tf_broadcaster", "tf_listener"}) {
      auto t0 = Clock::now();
      auto n = std::make_shared<FixInit>(which);
      n->init();
      auto t1 = Clock::now();
      long uc = n.use_count();
      std::weak_ptr<FixInit> w = n;
      n.reset();
      std::printf("RESULT fix_init %s: init ok, construct+init %.0f us, use_count after init=%ld, destroyed after reset=%d\n",
        which, us(t0, t1), uc, (int)w.expired());
      std::fflush(stdout);
    }
  }
  else if (mode == "fix_timer") {
    std::vector<double> a, b; int bad = 0;
    for (int i = 0; i < 20; i++) {
      auto n = std::make_shared<FixTimer>();
      bool before = n->helper_ != nullptr;
      rclcpp::executors::SingleThreadedExecutor ex;
      ex.add_node(n);
      auto ts = Clock::now();
      auto deadline = ts + 2s;
      while (n->calls == 0 && Clock::now() < deadline) ex.spin_once(100ms);
      for (int k = 0; k < 5; k++) ex.spin_once(10ms);
      if (before || n->calls != 1) bad++;
      a.push_back(us(n->t_ctor_end, n->t_cb)); b.push_back(us(ts, n->t_cb));
      if (i == 0) std::printf("RESULT fix_timer: helper set before spin=%d, timer callback count=%d\n", (int)before, n->calls);
    }
    std::sort(a.begin(), a.end()); std::sort(b.begin(), b.end());
    std::printf("RESULT fix_timer 20 runs: ctor end -> init callback us min=%.0f median=%.0f max=%.0f; spin start -> callback us min=%.0f median=%.0f max=%.0f; runs not exactly once=%d\n",
      a.front(), a[10], a.back(), b.front(), b[10], b.back(), bad);
  }
  else if (mode == "fix_raw") {
    auto n = std::make_shared<FixRaw>();
    std::weak_ptr<FixRaw> w = n; long uc = n.use_count(); n.reset();
    std::printf("RESULT fix_raw: use_count=%ld destroyed after reset=%d\n", uc, (int)w.expired());
  }
  else if (mode == "lc_configure") {
    auto n = std::make_shared<LcConfigure>();
    auto st = n->configure();
    std::printf("RESULT lc_configure: state after configure()=%s\n", st.label().c_str());
  }
  else std::printf("unknown mode\n");
  std::fflush(stdout);
  rclcpp::shutdown();
  return 0;
}
EOF
cat > $W/src/bwp/src/components.cpp <<'EOF'
#include "common.hpp"
#include "rclcpp_components/register_node_macro.hpp"
using namespace std::chrono_literals;
namespace bwp {
class BadComponent : public rclcpp::Node {
public:
  explicit BadComponent(const rclcpp::NodeOptions & o) : Node("bad_component", o) {
    helper_ = std::make_shared<NeedsNodeWeak>(shared_from_this());
  }
  std::shared_ptr<NeedsNodeWeak> helper_;
};
class TimerComponent : public rclcpp::Node {
public:
  explicit TimerComponent(const rclcpp::NodeOptions & o) : Node("timer_component", o) {
    t_ = create_wall_timer(0ms, [this]() {
      t_->cancel();
      helper_ = std::make_shared<NeedsNodeWeak>(shared_from_this());
      RCLCPP_INFO(get_logger(), "init done in one-shot timer, shared_from_this() ok");
    });
  }
  rclcpp::TimerBase::SharedPtr t_;
  std::shared_ptr<NeedsNodeWeak> helper_;
};
}  // namespace bwp
RCLCPP_COMPONENTS_REGISTER_NODE(bwp::BadComponent)
RCLCPP_COMPONENTS_REGISTER_NODE(bwp::TimerComponent)
EOF
# image_transport cases live in their own package so a compile error there can't hide the rest
cat > $W/src/bwp_it/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>bwp_it</name><version>0.0.1</version><description>image_transport cases</description>
  <maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><depend>image_transport</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
cat > $W/src/bwp_it/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(bwp_it)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(image_transport REQUIRED)
foreach(t it_ctor it_init it_raw)
  add_executable(${t} src/${t}.cpp)
  target_link_libraries(${t} rclcpp::rclcpp image_transport::image_transport)
  install(TARGETS ${t} DESTINATION lib/${PROJECT_NAME})
endforeach()
ament_package()
EOF
cat > $W/src/bwp_it/src/it_ctor.cpp <<'EOF'
#include "rclcpp/rclcpp.hpp"
#include "image_transport/image_transport.hpp"
class ItCtor : public rclcpp::Node {
public:
  ItCtor() : Node("it_ctor") {
    image_transport::ImageTransport it(shared_from_this());
    pub_ = it.advertise("camera/image", 1);
  }
  image_transport::Publisher pub_;
};
int main(int argc, char ** argv) { rclcpp::init(argc, argv); auto n = std::make_shared<ItCtor>(); rclcpp::shutdown(); }
EOF
cat > $W/src/bwp_it/src/it_init.cpp <<'EOF'
#include <cstdio>
#include "rclcpp/rclcpp.hpp"
#include "image_transport/image_transport.hpp"
class ItInit : public rclcpp::Node {
public:
  ItInit() : Node("it_init") {}
  ~ItInit() override { std::printf("  destructor ran (it_init)\n"); std::fflush(stdout); }
  void init() {
    it_ = std::make_shared<image_transport::ImageTransport>(shared_from_this());
    pub_ = it_->advertise("camera/image", 1);
  }
  std::shared_ptr<image_transport::ImageTransport> it_;
  image_transport::Publisher pub_;
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<ItInit>(); n->init();
  std::printf("RESULT it_init: ImageTransport(shared_from_this()) after make_shared ok, topic=%s\n", n->pub_.getTopic().c_str());
  std::weak_ptr<ItInit> w = n; long uc = n.use_count(); n.reset();
  std::printf("RESULT it_init: use_count=%ld destroyed after reset=%d (ImageTransport kept as member)\n", uc, (int)w.expired());
  rclcpp::shutdown();
}
EOF
cat > $W/src/bwp_it/src/it_raw.cpp <<'EOF'
#include <cstdio>
#include "rclcpp/rclcpp.hpp"
#include "image_transport/image_transport.hpp"
class ItRaw : public rclcpp::Node {
public:
  ItRaw() : Node("it_raw") {
    pub_ = image_transport::create_publisher(this, "camera/image");
  }
  ~ItRaw() override { std::printf("  destructor ran (it_raw)\n"); std::fflush(stdout); }
  image_transport::Publisher pub_;
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<ItRaw>();
  std::printf("RESULT it_raw: image_transport::create_publisher(this, ...) in constructor ok, topic=%s\n", n->pub_.getTopic().c_str());
  std::weak_ptr<ItRaw> w = n; long uc = n.use_count(); n.reset();
  std::printf("RESULT it_raw: use_count=%ld destroyed after reset=%d\n", uc, (int)w.expired());
  rclcpp::shutdown();
}
EOF

# node-interfaces API (deprecation message on Lyrical points here); own package, may not compile everywhere
mkdir -p $W/src/bwp_it_ifaces/src
sed -e 's/bwp_it</bwp_it_ifaces</' -e 's/image_transport cases/image_transport node-interfaces API/' $W/src/bwp_it/package.xml > $W/src/bwp_it_ifaces/package.xml
cat > $W/src/bwp_it_ifaces/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(bwp_it_ifaces)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(image_transport REQUIRED)
add_executable(it_ifaces src/it_ifaces.cpp)
target_link_libraries(it_ifaces rclcpp::rclcpp image_transport::image_transport)
install(TARGETS it_ifaces DESTINATION lib/${PROJECT_NAME})
ament_package()
EOF
cat > $W/src/bwp_it_ifaces/src/it_ifaces.cpp <<'EOF'
#include <cstdio>
#include "rclcpp/rclcpp.hpp"
#include "image_transport/image_transport.hpp"
class ItIfaces : public rclcpp::Node {
public:
  ItIfaces() : Node("it_ifaces") {
    pub_ = image_transport::create_publisher(*this, "camera/image", rclcpp::QoS(1));
    it_ = std::make_shared<image_transport::ImageTransport>(*this);
    pub2_ = it_->advertise("camera/image2", 1);
  }
  ~ItIfaces() override { std::printf("  destructor ran (it_ifaces)\n"); std::fflush(stdout); }
  image_transport::Publisher pub_, pub2_;
  std::shared_ptr<image_transport::ImageTransport> it_;
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<ItIfaces>();
  std::printf("RESULT it_ifaces: create_publisher(*this, ...) and ImageTransport(*this) in constructor ok, topics=%s %s\n",
    n->pub_.getTopic().c_str(), n->pub2_.getTopic().c_str());
  std::weak_ptr<ItIfaces> w = n; long uc = n.use_count(); n.reset();
  std::printf("RESULT it_ifaces: use_count=%ld destroyed after reset=%d\n", uc, (int)w.expired());
  rclcpp::shutdown();
}
EOF

echo; echo "##### build (one worker, make -j1)"
cd $W
T0=$(date +%s)
MAKEFLAGS=-j1 colcon build --parallel-workers 1 --continue-on-error --event-handlers console_direct+ 2>&1 \
  | grep -iE "warning|error|deprecat|Finished|Failed|Summary|packages? (finished|failed)" | grep -v "^--" | head -80
echo "build seconds=$(( $(date +%s) - T0 ))"
source $W/install/setup.bash

run() { echo; echo "--- $*"; timeout -s KILL 30 "$@" 2>&1; echo "exit=$?"; }
B=$W/install/bwp/lib/bwp/bwp_node
I=$W/install/bwp_it/lib/bwp_it
echo; echo "##### 1: causes (uncaught)"
for m in ctor_body ctor_initlist ctor_tf lc_ctor stack unique; do run $B $m; done
echo "(same case through ros2 run)"; run ros2 run bwp bwp_node ctor_body
[ -x $W/install/bwp_it/lib/bwp_it/it_ctor ] && run $I/it_ctor || echo "it_ctor: not built"
echo; echo "##### 2: what the exception is, weak_from_this, destructor, unique_ptr then shared_ptr"
for m in catch weak_in_ctor dtor unique_then_shared; do run $B $m; done
echo; echo "##### 3: wrong fixes"
for i in 1 2 3; do run $B wrap_this; done
run $B noop_deleter
echo; echo "##### 4: fixes"
for m in fix_init fix_timer fix_raw lc_configure; do run $B $m; done
[ -x $W/install/bwp_it/lib/bwp_it/it_init ] && run $I/it_init || echo "it_init: not built"
[ -x $W/install/bwp_it/lib/bwp_it/it_raw ] && run $I/it_raw || echo "it_raw: not built"
[ -x $W/install/bwp_it_ifaces/lib/bwp_it_ifaces/it_ifaces ] && run $W/install/bwp_it_ifaces/lib/bwp_it_ifaces/it_ifaces || echo "it_ifaces: not built"
echo; echo "##### 5: components in component_container"
ros2 run rclcpp_components component_container > /tmp/container.log 2>&1 &
CPID=$!
# wait until discovery sees the container (a load before that prints "Unable to find container node")
for i in $(seq 1 20); do timeout 10 ros2 component list 2>/dev/null | grep -q ComponentManager && break; sleep 1; done
echo "container visible after ${i} list attempts"
# Jazzy sometimes answered "Unable to find container node" right after list saw it; retry up to 3 times
for i in 1 2 3; do
  run timeout 20 ros2 component load /ComponentManager bwp bwp::BadComponent
  grep -q "Component constructor threw" /tmp/container.log && { echo "bad component load reached the container on attempt $i"; break; }
  sleep 2
done
sleep 1
kill -0 $CPID 2>/dev/null && echo "container alive after failed load=1" || echo "container alive after failed load=0"
for i in 1 2 3; do
  run timeout 20 ros2 component load /ComponentManager bwp bwp::TimerComponent
  timeout 10 ros2 component list 2>&1 | grep -q timer_component && { echo "timer_component loaded on attempt $i"; break; }
done
run timeout 20 ros2 component list
# SIGINT is ignored by background jobs in a non-interactive shell, so use SIGTERM
kill -TERM $CPID; ( sleep 10; kill -KILL $CPID 2>/dev/null ) & wait $CPID; echo "container exit=$?"; pkill -KILL -f component_container 2>/dev/null
echo "--- container log"; cat /tmp/container.log
echo "=== done"
