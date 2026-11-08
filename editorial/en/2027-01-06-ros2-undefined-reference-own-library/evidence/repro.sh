#!/bin/bash
# Reproduces "undefined reference to", CMake target errors and a runtime
# "symbol lookup error ... undefined symbol" with a small library in ROS 2
# ament_cmake workspaces, then the fixes.
# Run inside ros:<distro>-ros-base, e.g.:
#   docker run --rm --network none -e ROS_DOMAIN_ID=88 -v $PWD:/w ros:humble-ros-base bash /w/repro.sh
# (no set -u: the ROS setup scripts read unset variables)
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export MAKEFLAGS=-j2
R=/work/$$; mkdir -p $R
echo "distro=$ROS_DISTRO cmake=$(cmake --version | head -1) gcc=$(g++ -dumpfullversion) colcon-core=$(python3 -c 'import colcon_core;print(colcon_core.__version__)')"

pkgxml() { # name deps...
  local n=$1; shift; local d=""
  for x in "$@"; do d="$d  <depend>$x</depend>
"; done
  cat <<X
<?xml version="1.0"?>
<package format="3"><name>$n</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
$d  <export><build_type>ament_cmake</build_type></export></package>
X
}

lib_sources() { # dir
  mkdir -p $1/include/mylib $1/src
  printf '#pragma once\nnamespace mylib { int add(int a, int b); }\n' > $1/include/mylib/mylib.hpp
  printf '#include "mylib/mylib.hpp"\nnamespace mylib { int add(int a, int b) { return a + b; } }\n' > $1/src/mylib.cpp
}

app_sources() { # dir
  mkdir -p $1/src
  printf '#include <cstdio>\n#include "mylib/mylib.hpp"\nint main() { std::printf("add(2,3)=%%d\\n", mylib::add(2, 3)); return 0; }\n' > $1/src/app.cpp
}

build() { # case ws [colcon args]
  local c=$1 ws=$2; shift 2
  echo
  echo "### CASE $c ${*:-}"
  cd $ws
  local t0=$(date +%s.%N)
  timeout 300 colcon build --event-handlers console_direct+ "$@" > $ws/build.log 2>&1
  local rc=$?
  local t1=$(date +%s.%N)
  echo "colcon exit=$rc seconds=$(python3 -c "print(round($t1-$t0,1))")"
  grep -E "undefined reference|error:|CMake Error|cannot find|ld returned|was not found|links to|^    [a-z_]+::[a-z_]+|but the target|Unknown CMake|Summary:|Failed|failed|No such file" $ws/build.log \
    | grep -v "^-- " | sed "s#$ws#<ws>#g" | awk '!seen[$0]++' | head -14
}

runapp() { # ws pkg
  ( source $1/install/setup.bash
    timeout 20 ros2 run $2 app > $1/run.log 2>&1; echo "run exit=$?" >> $1/run.log
    sed "s#$1#<ws>#g" $1/run.log )
}

# ---------------- single package: library and executable together ----------------
solo() { # case cmake_body
  local c=$1 ws=$R/$1 p=$R/$1/src/solo
  mkdir -p $p
  lib_sources $p; app_sources $p; pkgxml solo > $p/package.xml
  printf 'cmake_minimum_required(VERSION 3.8)\nproject(solo C CXX)\nfind_package(ament_cmake REQUIRED)\n%s\ninstall(TARGETS app DESTINATION lib/${PROJECT_NAME})\ninstall(TARGETS mylib LIBRARY DESTINATION lib)\nament_package()\n' "$2" > $p/CMakeLists.txt
}
LIBT='add_library(mylib SHARED src/mylib.cpp)
target_include_directories(mylib PUBLIC include)
add_executable(app src/app.cpp)'

solo S0_linked "$LIBT
target_link_libraries(app mylib)"
build S0_linked $R/S0_linked && runapp $R/S0_linked solo

solo S1_no_target_link_libraries "$LIBT
target_include_directories(app PRIVATE include)"
build S1_no_target_link_libraries $R/S1_no_target_link_libraries

solo S2_source_not_in_add_library 'add_library(mylib SHARED src/other.cpp)
target_include_directories(mylib PUBLIC include)
add_executable(app src/app.cpp)
target_link_libraries(app mylib)'
echo '// mylib.cpp was left out of add_library' > $R/S2_source_not_in_add_library/src/solo/src/other.cpp
build S2_source_not_in_add_library $R/S2_source_not_in_add_library

# C function called from C++ without extern "C"
cfun() { # case header_text
  solo $1 'add_library(mylib SHARED src/cfun.c)
target_include_directories(mylib PUBLIC include)
add_executable(app src/app.cpp)
target_link_libraries(app mylib)'
  local p=$R/$1/src/solo
  printf '%s\n' "$2" > $p/include/mylib/cfun.h
  printf '#include "mylib/cfun.h"\nint c_add(int a, int b) { return a + b; }\n' > $p/src/cfun.c
  printf '#include <cstdio>\n#include "mylib/cfun.h"\nint main() { std::printf("c_add(2,3)=%%d\\n", c_add(2, 3)); return 0; }\n' > $p/src/app.cpp
}
cfun S3_c_function_no_extern_c '#pragma once
int c_add(int a, int b);'
build S3_c_function_no_extern_c $R/S3_c_function_no_extern_c
cfun S3_fix_extern_c '#pragma once
#ifdef __cplusplus
extern "C" {
#endif
int c_add(int a, int b);
#ifdef __cplusplus
}
#endif'
build S3_fix_extern_c $R/S3_fix_extern_c && runapp $R/S3_fix_extern_c solo

# template defined in the .cpp file
tmpl() { # case extra_cpp_line
  solo $1 "$LIBT
target_link_libraries(app mylib)"
  local p=$R/$1/src/solo
  printf '#pragma once\nnamespace mylib { int add(int a, int b); template <typename T> T twice(T x); }\n' > $p/include/mylib/mylib.hpp
  printf '#include "mylib/mylib.hpp"\nnamespace mylib { int add(int a, int b) { return a + b; }\ntemplate <typename T> T twice(T x) { return x + x; }\n%s }\n' "$2" > $p/src/mylib.cpp
  printf '#include <cstdio>\n#include "mylib/mylib.hpp"\nint main() { std::printf("twice(4)=%%d\\n", mylib::twice(4)); return 0; }\n' > $p/src/app.cpp
}
tmpl S4_template_in_cpp ''
build S4_template_in_cpp $R/S4_template_in_cpp
tmpl S4_fix_explicit_instantiation 'template int twice<int>(int);'
build S4_fix_explicit_instantiation $R/S4_fix_explicit_instantiation && runapp $R/S4_fix_explicit_instantiation solo

# ---------------- two packages: mylib (library) and app (executable) ----------------
cross() { # case lib_export_lines app_link_lines [lib_extra]
  local c=$1 ws=$R/$1
  mkdir -p $ws/src/mylib $ws/src/app
  lib_sources $ws/src/mylib; app_sources $ws/src/app
  pkgxml mylib ${4:+rcutils} > $ws/src/mylib/package.xml
  pkgxml app mylib > $ws/src/app/package.xml
  cat > $ws/src/mylib/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(mylib)
find_package(ament_cmake REQUIRED)
add_library(mylib SHARED src/mylib.cpp)
target_include_directories(mylib PUBLIC \$<BUILD_INTERFACE:\${CMAKE_CURRENT_SOURCE_DIR}/include> \$<INSTALL_INTERFACE:include>)
${4:-}
install(DIRECTORY include/ DESTINATION include)
install(TARGETS mylib EXPORT export_mylib LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin INCLUDES DESTINATION include)
$2
ament_package()
X
  cat > $ws/src/app/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(app)
find_package(ament_cmake REQUIRED)
find_package(mylib REQUIRED)
add_executable(app src/app.cpp)
$3
install(TARGETS app DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
}
ATD='ament_target_dependencies(app mylib)'
VARS='target_include_directories(app PRIVATE ${mylib_INCLUDE_DIRS})
target_link_libraries(app ${mylib_LIBRARIES})'
TGT='target_link_libraries(app mylib::mylib)'
EXP_INC='ament_export_include_directories(include)'
EXP_OLD='ament_export_include_directories(include)
ament_export_libraries(mylib)'
EXP_TGT='ament_export_targets(export_mylib HAS_LIBRARY_TARGET)'

cross X1_no_exports_plain_name '' 'target_link_libraries(app mylib)'
build X1_no_exports_plain_name $R/X1_no_exports_plain_name
cross X2_no_exports_ament_target_dependencies '' "$ATD"
build X2_no_exports_ament_target_dependencies $R/X2_no_exports_ament_target_dependencies
cross X3_include_only_ament_target_dependencies "$EXP_INC" "$ATD"
build X3_include_only_ament_target_dependencies $R/X3_include_only_ament_target_dependencies
cross X3_include_only_variables "$EXP_INC" "$VARS"
build X3_include_only_variables $R/X3_include_only_variables
cross X4_fix_export_libraries_ament_target_dependencies "$EXP_OLD" "$ATD"
build X4_fix_export_libraries_ament_target_dependencies $R/X4_fix_export_libraries_ament_target_dependencies && runapp $R/X4_fix_export_libraries_ament_target_dependencies app
cross X4_fix_export_libraries_variables "$EXP_OLD" "$VARS"
build X4_fix_export_libraries_variables $R/X4_fix_export_libraries_variables && runapp $R/X4_fix_export_libraries_variables app
cross X5_namespaced_target_not_exported "$EXP_OLD" "$TGT"
build X5_namespaced_target_not_exported $R/X5_namespaced_target_not_exported
cross X6_fix_export_targets "$EXP_TGT" "$TGT"
build X6_fix_export_targets $R/X6_fix_export_targets && runapp $R/X6_fix_export_targets app
cross X6_export_targets_ament_target_dependencies "$EXP_TGT" "$ATD"
build X6_export_targets_ament_target_dependencies $R/X6_export_targets_ament_target_dependencies && runapp $R/X6_export_targets_ament_target_dependencies app
cross X7_export_targets_without_HAS_LIBRARY_TARGET 'ament_export_targets(export_mylib)' "$TGT"
build X7_export_targets_without_HAS_LIBRARY_TARGET $R/X7_export_targets_without_HAS_LIBRARY_TARGET && runapp $R/X7_export_targets_without_HAS_LIBRARY_TARGET app
echo "LD_LIBRARY_PATH has mylib/lib after sourcing X6: $(source $R/X6_fix_export_targets/install/setup.bash; echo $LD_LIBRARY_PATH | tr ':' '\n' | grep -c 'mylib/lib')"
echo "LD_LIBRARY_PATH has mylib/lib after sourcing X7: $(source $R/X7_export_targets_without_HAS_LIBRARY_TARGET/install/setup.bash; echo $LD_LIBRARY_PATH | tr ':' '\n' | grep -c 'mylib/lib')"
echo "RUNPATH of X7 app: $(readelf -d $R/X7_export_targets_without_HAS_LIBRARY_TARGET/install/app/lib/app/app | grep -cE 'RPATH|RUNPATH') entries"

# library links a dependency publicly but does not export it
DEP='find_package(rcutils REQUIRED)
target_link_libraries(mylib PUBLIC rcutils::rcutils)'
cross X8_dependency_not_exported "$EXP_TGT" "$TGT" "$DEP"
build X8_dependency_not_exported $R/X8_dependency_not_exported
cross X8_fix_export_dependencies "$EXP_TGT
ament_export_dependencies(rcutils)" "$TGT" "$DEP"
build X8_fix_export_dependencies $R/X8_fix_export_dependencies && runapp $R/X8_fix_export_dependencies app

# ---------------- stale executable after the library's signature changed ----------------
W=$R/X9_stale
cross X9_stale "$EXP_TGT" "$TGT"
build X9_initial_build $W && runapp $W app
echo "exported symbol before: $(nm -D --defined-only $W/install/mylib/lib/libmylib.so | grep add | c++filt | awk '{print $3,$4,$5}')"
sed -i 's/int add(int a, int b)/long add(long a, long b)/' $W/src/mylib/include/mylib/mylib.hpp $W/src/mylib/src/mylib.cpp
grep -h add $W/src/mylib/include/mylib/mylib.hpp
build X9_rebuild_library_only $W --packages-select mylib
echo "exported symbol after: $(nm -D --defined-only $W/install/mylib/lib/libmylib.so | grep add | c++filt | awk '{print $3,$4,$5}')"
runapp $W app
build X9_rebuild_packages_above $W --packages-above mylib
runapp $W app
echo "app include flags: $(grep CXX_INCLUDES $W/build/app/CMakeFiles/app.dir/flags.make | sed "s#$W#<ws>#g")"
echo "app.cpp.o depends on mylib.hpp (lines in compiler_depend/depend files): $(cat $W/build/app/CMakeFiles/app.dir/compiler_depend.make $W/build/app/CMakeFiles/app.dir/depend.make 2>/dev/null | grep -c mylib.hpp)"
echo "app.cpp.o references: $(nm -C $W/build/app/CMakeFiles/app.dir/src/app.cpp.o | grep add)"
echo "installed header: $(grep -h add $W/install/mylib/include/mylib/mylib.hpp)"
echo "mtime installed header vs app.cpp.o: $(stat -c %Y $W/install/mylib/include/mylib/mylib.hpp) $(stat -c %Y $W/build/app/CMakeFiles/app.dir/src/app.cpp.o)"
build X9_packages_above_second_try $W --packages-above mylib
runapp $W app
build X9_rebuild_app_cmake_clean_first $W --packages-select app --cmake-clean-first
runapp $W app
# same change again, this time fixed with one command
sed -i 's/long add(long a, long b)/int add(int a, int b)/' $W/src/mylib/include/mylib/mylib.hpp $W/src/mylib/src/mylib.cpp
build X9_revert_then_packages_up_to_app_clean_first $W --packages-up-to app --cmake-clean-first
runapp $W app
# ---------------- repeat: is --packages-above enough right after the edit? ----------------
echo
echo "### CASE X10_repeat (initial build, edit, --packages-select mylib, --packages-above mylib)"
for wait in 0 2; do
  for i in 1 2 3 4 5; do
    c=X10_w${wait}_$i; W=$R/$c
    cross $c "$EXP_TGT" "$TGT"
    ( cd $W; colcon build > b0.log 2>&1 )
    sleep $wait
    sed -i 's/int add(int a, int b)/long add(long a, long b)/' $W/src/mylib/include/mylib/mylib.hpp $W/src/mylib/src/mylib.cpp
    ( cd $W; colcon build --packages-select mylib > b1.log 2>&1 )
    r1=$(runapp $W app | tail -1)
    ( cd $W; colcon build --packages-above mylib > b2.log 2>&1; echo $? > b2.rc )
    r2=$(runapp $W app | tail -1)
    echo "sleep_before_edit=${wait}s try=$i after_select_mylib:[$r1] packages_above_colcon_exit=$(cat $W/b2.rc) after_packages_above:[$r2] undefined_reference_lines=$(grep -c 'undefined reference' $W/b2.log)"
  done
done
echo
echo "### DONE"
