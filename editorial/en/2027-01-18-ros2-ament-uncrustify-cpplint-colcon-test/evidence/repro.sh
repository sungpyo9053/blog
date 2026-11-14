#!/bin/bash
# Reproduce ament_cmake C++ lint failures (uncrustify, cpplint, cppcheck, lint_cmake, xmllint)
# in colcon test on Humble, Jazzy and Lyrical.
# Host usage:   ./repro.sh host humble|jazzy|lyrical      (runs one distro in a pk40- container)
# Inner usage:  repro.sh inner <distro>                    (runs inside the container)

MODE=${1:-host}

if [ "$MODE" = host ]; then
  D=$2
  IMG=ros:$D-ros-base
  C=pk40-$D
  W=/tmp/en-pick50
  mkdir -p $W/out
  uptime
  docker rm -f $C >/dev/null 2>&1
  docker run -d --name $C --ulimit core=0 --pids-limit 200 \
    -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    -e MAKEFLAGS=-j1 -v $W:/w $IMG sleep 4000 >/dev/null
  docker exec $C bash -c "apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$D-ament-lint-auto ros-$D-ament-lint-common git >/dev/null 2>&1; echo apt_rc=\$?"
  docker network disconnect bridge $C
  echo "network after disconnect: $(docker inspect -f '{{json .NetworkSettings.Networks}}' $C)"
  if [ "${3:-}" = cross ]; then
    docker exec $C bash /w/repro.sh cross $D
    [ -z "$KEEP" ] && docker rm -f $C >/dev/null && echo "container $C removed"
    exit 0
  fi
  docker exec $C bash /w/repro.sh inner $D
  docker network connect bridge $C
  docker exec $C bash /w/repro.sh xmlnet $D
  docker network disconnect bridge $C
  [ -z "$KEEP" ] && docker rm -f $C >/dev/null && echo "container $C removed"
  exit 0
fi

if [ "$MODE" = xmlnet ]; then
  D=$2; source /opt/ros/$D/setup.bash; cd /ws/src/lintpkg
  echo "################ 9. xmllint with network reconnected ################"
  S=$(date +%s%N); ament_xmllint package.xml 2>&1 | tail -4; echo "ament_xmllint rc=${PIPESTATUS[0]} [elapsed $(( ($(date +%s%N)-S)/1000000 )) ms]"
  cd /ws; colcon test --parallel-workers 1 --packages-select lintpkg --ctest-args -R xmllint --event-handlers console_cohesion+ 2>&1 | grep -E "Test +#" | sed 's/^ *//'
  exit 0
fi
if [ "$MODE" = cross ]; then
  D=$2; source /opt/ros/$D/setup.bash
  echo "################ 10. cross-distro check on $D (run after all distros) ################"
  for o in humble jazzy lyrical; do for k in reformatted fixed; do
    [ -d /w/out/$o/$k ] || continue
    rm -rf /tmp/x && mkdir -p /tmp/x && cp -r /w/out/$o/$k/* /tmp/x/
    (cd /tmp/x && ament_uncrustify src include > /tmp/xo.txt 2>&1; echo "$o $k files checked on $D: uncrustify rc=$?"; grep -E "^[-+][^-+]|^[-+]$|files? with code style" /tmp/xo.txt | head -20)
  done; done
  exit 0
fi
# ---------------- inner ----------------
D=$2
source /opt/ros/$D/setup.bash
OUT=/w/out/$D
rm -rf $OUT /ws; mkdir -p $OUT /ws/src
cd /ws/src
banner() { echo; echo "################ $* ################"; }
t0() { S=$(date +%s%N); }
t1() { echo "[elapsed $(( ($(date +%s%N)-S)/1000000 )) ms] $*"; }
runtest() {  # build + test + result summary
  cd /ws
  t0; colcon build --parallel-workers 1 --packages-select lintpkg >/tmp/build.log 2>&1; rc=$?; t1 "colcon build rc=$rc"
  [ $rc -ne 0 ] && tail -30 /tmp/build.log
  t0; colcon test --parallel-workers 1 --packages-select lintpkg --event-handlers console_cohesion+ >/tmp/test.log 2>&1; rc=$?; t1 "colcon test rc=$rc"
  grep -E "^ *[0-9]+/[0-9]+ Test|tests passed|tests failed|The following tests FAILED|\(Failed\)|packages? had test failures|^Summary" /tmp/test.log
  colcon test-result --test-result-base build/lintpkg >/tmp/tr.log 2>&1; echo "test-result rc=$?"; tail -3 /tmp/tr.log
}

banner "versions"
echo "ROS_DISTRO=$ROS_DISTRO"
uncrustify --version 2>&1 | head -1
cppcheck --version 2>&1 | head -1
python3 -c "import ament_cpplint.cpplint as c; print('ament_cpplint cpplint module', getattr(c,'__VERSION__','?'))" 2>&1
for p in ament_lint_auto ament_cmake_uncrustify ament_cmake_cpplint ament_cmake_cppcheck ament_cmake_lint_cmake ament_cmake_xmllint uncrustify_vendor rclcpp rclpy ros2cli; do
  printf "%s " $p; grep -oPm1 '(?<=<version>)[^<]+' /opt/ros/$D/share/$p/package.xml
done
echo "RMW default: $(ros2 doctor --report 2>/dev/null | grep -m1 -i 'middleware name' || echo n/a)"
dpkg -l | grep -E "ros-$D-rmw-(fastrtps|cyclonedds|zenoh)-cpp " | awk '{print $2, $3}'

banner "1. ros2 pkg create template, unchanged"
ros2 pkg create --build-type ament_cmake --dependencies rclcpp std_msgs --node-name my_node lintpkg >/dev/null
grep -n -A12 "BUILD_TESTING" lintpkg/CMakeLists.txt
runtest
grep -E "Test +#" /tmp/test.log | sed 's/^ *//'
banner "1b. xmllint output (container has no network)"
sed -n '/Start .*xmllint/,/Test #.*xmllint/p' /tmp/test.log | grep -vE "^\s*$" | head -30
cd /ws/src/lintpkg; t0; ament_xmllint package.xml 2>&1 | tail -6; echo "ament_xmllint rc=${PIPESTATUS[0]}"; t1 "ament_xmllint offline"; cd /ws/src
head -3 /ws/src/lintpkg/package.xml

banner "2. add a typical talker node written in 4-space K&R style"
cd /ws/src/lintpkg
mkdir -p include/lintpkg
cat > include/lintpkg/talker.hpp <<'EOF'
#pragma once
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Talker : public rclcpp::Node {
public:
    Talker();
private:
    void timer_callback();
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
    size_t count_;
};
EOF
cat > src/talker.cpp <<'EOF'
#include "lintpkg/talker.hpp"
#include <chrono>
#include <string>
#include <memory>

using namespace std::chrono_literals;

Talker::Talker() : Node("talker"), count_(0) {
    publisher_ = this->create_publisher<std_msgs::msg::String>("topic", 10);
    timer_ = this->create_wall_timer(500ms, std::bind(&Talker::timer_callback, this));
}

void Talker::timer_callback() {
    auto message = std_msgs::msg::String();
    message.data = "Hello, world! " + std::to_string(count_++);
    RCLCPP_INFO(this->get_logger(), "Publishing: '%s' with a log line that runs past one hundred characters", message.data.c_str());
    if(count_ > 10){
        count_ = 0;
    }
    publisher_->publish(message);
}

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Talker>());
    rclcpp::shutdown();
    return 0;
}
EOF
python3 - <<'EOF'
p='CMakeLists.txt'; s=open(p).read()
s=s.replace('install(TARGETS my_node','add_executable(talker src/talker.cpp)\ntarget_include_directories(talker PUBLIC\n  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>\n  $<INSTALL_INTERFACE:include>)\ntarget_compile_features(talker PUBLIC cxx_std_17)\ntarget_link_libraries(talker rclcpp::rclcpp ${std_msgs_TARGETS})\n\ninstall(TARGETS my_node talker',1)
open(p,'w').write(s)
EOF
cp -r include src CMakeLists.txt $OUT/ 2>/dev/null; mkdir -p $OUT/original && cp -r include src $OUT/original/
runtest
banner "2b. uncrustify test output (from colcon test log)"
sed -n '/uncrustify/,/^ *[0-9]*\/[0-9]* Test/p' /tmp/test.log | grep -vE "^\s*$" | head -80
banner "2c. ament_uncrustify run directly"
cd /ws/src/lintpkg
t0; ament_uncrustify src include > /tmp/unc.txt 2>&1; echo "ament_uncrustify rc=$?"; t1 "ament_uncrustify"
cat /tmp/unc.txt | head -90
echo "diff lines starting with -/+ : $(grep -cE '^[-+][^-+]' /tmp/unc.txt)"
grep -iE "divergence|files? with" /tmp/unc.txt
banner "2d. cppcheck / lint_cmake / xmllint results"
cat /ws/build/lintpkg/test_results/lintpkg/cppcheck.xunit.xml 2>/dev/null | head -20
grep -hE "tests=|failures=" /ws/build/lintpkg/test_results/lintpkg/*.xml 2>/dev/null | head -20
ls /ws/build/lintpkg/test_results/lintpkg/
t0; ament_cppcheck src include 2>&1 | tail -8; t1 "ament_cppcheck"

banner "3. enable cpplint (comment out the skip line), not a git repo"
cd /ws/src/lintpkg
sed -i 's/^  set(ament_cmake_cpplint_FOUND TRUE)/  # set(ament_cmake_cpplint_FOUND TRUE)/' CMakeLists.txt
grep -n "cpplint_FOUND" CMakeLists.txt
cd /ws/src/lintpkg; ament_cpplint src include > /tmp/cpl_nogit.txt 2>&1; echo "ament_cpplint (no git) rc=$?"
cat /tmp/cpl_nogit.txt
echo "--- categories:"; grep -oE "\[[a-z_]+/[a-z_]+\]" /tmp/cpl_nogit.txt | sort | uniq -c

banner "3b. same files inside a git repo (git init at /ws)"
cd /ws && git init -q . && git config user.email a@b && git config user.name t
cd /ws/src/lintpkg; ament_cpplint src include > /tmp/cpl_git.txt 2>&1; echo "ament_cpplint (git at /ws) rc=$?"
cat /tmp/cpl_git.txt
echo "--- diff no-git vs git:"; diff /tmp/cpl_nogit.txt /tmp/cpl_git.txt
rm -rf /ws/.git

banner "3c. colcon test with cpplint enabled"
runtest

banner "4. ament_uncrustify --reformat"
cd /ws/src/lintpkg
t0; ament_uncrustify --reformat src include > /tmp/ref.txt 2>&1; echo "reformat rc=$?"; t1 "reformat"
tail -5 /tmp/ref.txt
ament_uncrustify src include > /tmp/unc2.txt 2>&1; echo "uncrustify after reformat rc=$?"; tail -3 /tmp/unc2.txt
echo "--- reformatted talker.cpp:"; cat src/talker.cpp
echo "--- reformatted talker.hpp:"; cat include/lintpkg/talker.hpp
mkdir -p $OUT/reformatted && cp -r src include $OUT/reformatted/
ament_cpplint src include > /tmp/cpl2.txt 2>&1; echo "cpplint after reformat rc=$?"
cat /tmp/cpl2.txt
echo "--- categories:"; grep -oE "\[[a-z_]+/[a-z_]+\]" /tmp/cpl2.txt | sort | uniq -c

banner "5. fix cpplint by hand (copyright, header guard, include order, functional, NOLINT/line split)"
cat > include/lintpkg/talker.hpp <<'EOF'
// Copyright 2026 Example
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef LINTPKG__TALKER_HPP_
#define LINTPKG__TALKER_HPP_

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class Talker : public rclcpp::Node
{
public:
  Talker();

private:
  void timer_callback();
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  size_t count_;
};

#endif  // LINTPKG__TALKER_HPP_
EOF
python3 - <<'EOF'
p='src/talker.cpp'; s=open(p).read()
hdr=open('include/lintpkg/talker.hpp').read().split('#ifndef')[0]
body=s.split('using namespace',1)[1]
body='using namespace'+body
inc='#include <chrono>\n#include <functional>\n#include <memory>\n#include <string>\n\n#include "lintpkg/talker.hpp"\n\n'
body=body.replace('"Publishing: \'%s\' with a log line that runs past one hundred characters", message.data.c_str());','"Publishing: \'%s\' with a log line that runs past one hundred characters",\n    message.data.c_str());')
open(p,'w').write(hdr+inc+body)
EOF
ament_uncrustify --reformat src include >/dev/null 2>&1
ament_uncrustify src include 2>&1 | tail -1
ament_cpplint src include > /tmp/cpl3.txt 2>&1; echo "cpplint after hand fixes rc=$?"; cat /tmp/cpl3.txt
echo "--- final talker.cpp:"; cat src/talker.cpp
mkdir -p $OUT/fixed && cp -r src include $OUT/fixed/
runtest
grep -E "Test +#" /tmp/test.log | sed 's/^ *//'

banner "6. cross-distro: check files reformatted by other distros with this distro's uncrustify"
for o in humble jazzy lyrical; do
  [ -d /w/out/$o/reformatted ] || { echo "$o: not available yet"; continue; }
  rm -rf /tmp/x && mkdir -p /tmp/x && cp -r /w/out/$o/reformatted/* /tmp/x/
  (cd /tmp/x && ament_uncrustify src include > /tmp/xo.txt 2>&1; echo "$o-reformatted files checked on $D: rc=$?"; grep -E "^[-+][^-+]|^[-+]$|files? with code style|No problems" /tmp/xo.txt | head -20)
  (cd /tmp/x && ament_cpplint src include 2>&1 | tail -1)
done
# original (unformatted) file on this distro, to compare divergence size across distros
rm -rf /tmp/x && mkdir -p /tmp/x && cp -r $OUT/original/* /tmp/x/
(cd /tmp/x && ament_uncrustify src include 2>&1 | grep -cE '^[-+][^-+]' | sed 's/^/original files: changed diff lines = /')

banner "7. ways to skip a linter (measured with the original unformatted files)"
cd /ws/src/lintpkg
cp -r $OUT/original/src $OUT/original/include .
cp CMakeLists.txt /tmp/CMakeLists.bak
echo "--- 7a: list(APPEND AMENT_LINT_AUTO_EXCLUDE ament_cmake_uncrustify ament_cmake_cpplint)"
sed -i 's/^  ament_lint_auto_find_test_dependencies()/  list(APPEND AMENT_LINT_AUTO_EXCLUDE ament_cmake_uncrustify ament_cmake_cpplint)\n  ament_lint_auto_find_test_dependencies()/' CMakeLists.txt
runtest
grep -E "Test +#" /tmp/test.log | sed 's/^ *//'
cd /ws/src/lintpkg; cp /tmp/CMakeLists.bak CMakeLists.txt; rm -rf /ws/build/lintpkg
echo "--- 7b: set(AMENT_LINT_AUTO_FILE_EXCLUDE src/talker.cpp include/lintpkg/talker.hpp)"
sed -i 's/^  ament_lint_auto_find_test_dependencies()/  set(AMENT_LINT_AUTO_FILE_EXCLUDE src\/talker.cpp include\/lintpkg\/talker.hpp)\n  ament_lint_auto_find_test_dependencies()/' CMakeLists.txt
grep -n "EXCLUDE\|cpplint_FOUND" CMakeLists.txt
runtest
grep -iE "exclude|Added test" /tmp/build.log | head; (cd /ws/build/lintpkg && ctest -N | tail -8)
grep -E "Test +#" /tmp/test.log | sed 's/^ *//'
cd /ws/src/lintpkg; cp /tmp/CMakeLists.bak CMakeLists.txt; rm -rf /ws/build/lintpkg
echo "--- 7c: colcon build --cmake-args -DBUILD_TESTING=OFF then colcon test"
cd /ws; rm -rf build/lintpkg install/lintpkg
colcon build --parallel-workers 1 --packages-select lintpkg --cmake-args -DBUILD_TESTING=OFF >/tmp/b.log 2>&1; echo "build rc=$?"; tail -15 /tmp/b.log
colcon test --parallel-workers 1 --packages-select lintpkg >/tmp/t.log 2>&1; echo "test rc=$?"; grep -E "tests|Summary|No tests" /tmp/t.log | head
colcon test-result --test-result-base build/lintpkg 2>&1 | tail -2
echo "--- 7d: colcon test --ctest-args -E 'uncrustify|cpplint'"
colcon build --parallel-workers 1 --packages-select lintpkg --cmake-args -DBUILD_TESTING=ON >/tmp/b.log 2>&1; echo "build rc=$?"; tail -5 /tmp/b.log
colcon test --parallel-workers 1 --packages-select lintpkg --ctest-args -E "uncrustify|cpplint" --event-handlers console_cohesion+ >/tmp/t.log 2>&1; echo "test rc=$?"
grep -E "Test +#|tests passed|tests failed" /tmp/t.log | sed 's/^ *//'
echo "--- 7e: // NOLINT and *INDENT-OFF* markers"
cat > /tmp/n.cpp <<'EOF'
// Copyright 2026 Example
const char * a = "this line is longer than one hundred characters ......................................";  // NOLINT
const char * b = "this line is longer than one hundred characters ......................................";
/* *INDENT-OFF* */
int g() { return 2; }
/* *INDENT-ON* */
int h() { return 3; }
EOF
mkdir -p /tmp/nn && cp /tmp/n.cpp /tmp/nn/n.cpp && cd /tmp/nn
ament_cpplint n.cpp 2>&1 | grep -E "^/|Total"
ament_uncrustify n.cpp 2>&1 | grep -E "^[-+]|divergence|No problems" | head -20

banner "8. per-test timings (fixed files, cpplint on)"
cd /ws/src/lintpkg && cp -r $OUT/fixed/src $OUT/fixed/include . && cd /ws
colcon build --parallel-workers 1 --packages-select lintpkg >/tmp/b.log 2>&1; echo "build rc=$?"
colcon test --parallel-workers 1 --packages-select lintpkg --event-handlers console_cohesion+ >/tmp/t.log 2>&1
grep -E "Test +#" /tmp/t.log | sed 's/^ *//'
banner "done $D"
exit 0
