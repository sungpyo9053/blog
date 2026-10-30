#!/bin/bash
# Reproduces colcon "Duplicate package names not supported:" and the underlay override warning.
# On the Docker host:   bash repro.sh host <distro>   (runs "main" inside ros:<distro>-ros-base)
# Inside a container:   bash repro.sh main
# Packages are minimal ament_cmake packages (project(<name> NONE) + ament_package(), no sources).
if [ "$1" = host ]; then
  D=$2; I=ros:$D-ros-base; H=$(cd "$(dirname "$0")" && pwd)
  docker run --rm --name dup-$D --pids-limit 40 --cpus 1.5 --ulimit core=0 \
    -e MAKEFLAGS=-j1 -v $H/repro.sh:/repro.sh:ro $I bash /repro.sh main
  exit 0
fi
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
C="colcon"
OC=/usr/lib/python3/dist-packages/colcon_override_check/package_selection/override_check.py
mkpkg() {  # mkpkg <dir> <name> [exec_depend]
  mkdir -p $1; local dep=""; [ -n "$3" ] && dep="<exec_depend>$3</exec_depend>"
  cat > $1/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$2</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>$dep
<export><build_type>ament_cmake</build_type></export></package>
X
  printf 'cmake_minimum_required(VERSION 3.8)\nproject(%s NONE)\nfind_package(ament_cmake REQUIRED)\nament_package()\n' $2 > $1/CMakeLists.txt
}
fresh() {  # fresh ws: src/pkg_a, src/pkg_b
  cd /; rm -rf /ws; mkdir -p /ws/src; cd /ws
  mkpkg src/pkg_a pkg_a; mkpkg src/pkg_b pkg_b
}
run() {  # run <label> <cmd...> ; prints output (trimmed) + exit code + what got installed
  echo "--- $1"; shift; echo "\$ $*"
  "$@" > /tmp/o.log 2>&1; local rc=$?
  grep -vE '^\s*$' /tmp/o.log | head -40
  echo "exit=$rc"
  echo "installed: $(ls install 2>/dev/null | grep -vE '\.(sh|bash|zsh|ps1|py|dsv)$|COLCON_IGNORE|_local_setup' | tr '\n' ' ')"
}
dupws() { fresh; cp -r src/pkg_a src/pkg_a_old; }

echo "=== distro=$ROS_DISTRO nproc=$(nproc)"
cmake --version | head -1
dpkg-query -W -f='${Package} ${Version}\n' python3-colcon-core python3-colcon-cmake python3-colcon-ros \
  python3-colcon-override-check python3-colcon-package-selection python3-colcon-recursive-crawl \
  python3-colcon-installed-package-information 2>&1
echo "std_msgs in underlay: $(ros2 pkg prefix std_msgs 2>&1)"

echo; echo "##### T1 copied folder src/pkg_a_old with the same <name> (pkg_a)"
dupws
run "colcon build" $C build
run "colcon build --packages-select pkg_b" $C build --packages-select pkg_b
run "colcon build --packages-ignore pkg_a" $C build --packages-ignore pkg_a
run "colcon build --continue-on-error" $C build --continue-on-error
run "colcon test" $C test
run "colcon list" $C list
run "colcon list --paths-only" $C list --paths-only
run "colcon list --names-only" $C list --names-only
run "colcon info pkg_a" $C info pkg_a
echo "--- three copies"
cp -r src/pkg_a src/pkg_a_backup
run "colcon build (pkg_a, pkg_a_old, pkg_a_backup)" $C build
echo "--- rename <name> in the copy to pkg_a_old"
dupws; sed -i 's#<name>pkg_a</name>#<name>pkg_a_old</name>#' src/pkg_a_old/package.xml
run "colcon build after renaming <name> only (CMake project() still pkg_a)" $C build
dupws; sed -i 's#<name>pkg_a</name>#<name>pkg_a_old</name>#' src/pkg_a_old/package.xml; sed -i 's/project(pkg_a /project(pkg_a_old /' src/pkg_a_old/CMakeLists.txt
run "colcon build after renaming <name> and project()" $C build

echo; echo "##### T2 nested / misplaced copies"
fresh; mkdir -p src/some_repo; cp -r src/pkg_a src/some_repo/pkg_a
run "nested git-clone style src/some_repo/pkg_a + src/pkg_a" $C build
fresh; cp -r src/pkg_a ./pkg_a
run "copy at workspace root /ws/pkg_a + /ws/src/pkg_a, build from /ws" $C build
run "same, build with --base-paths src" $C build --base-paths src
fresh; mkdir -p /ws/src/.hidden_backup; cp -r src/pkg_a src/.hidden_backup/pkg_a
run "copy in a hidden dir src/.hidden_backup/pkg_a" $C build
fresh; mkdir -p src/some_repo/.git; cp -r src/pkg_a src/some_repo/pkg_a
run "nested clone with .git dir src/some_repo/.git + src/some_repo/pkg_a" $C build
echo "--- ran colcon build inside src/ by mistake, then from /ws"
fresh; cd src; run "colcon build inside /ws/src" $C build; cd /ws
echo "COLCON_IGNORE files created inside src: $(find src -maxdepth 2 -name COLCON_IGNORE | tr '\n' ' ')"
echo "package.xml files under src/build src/install: $(find src/build src/install -name package.xml | tr '\n' ' ')"
run "colcon build from /ws with src/build src/install src/log present" $C build
rm -f src/build/COLCON_IGNORE src/install/COLCON_IGNORE src/log/COLCON_IGNORE
run "same after deleting their COLCON_IGNORE files" $C build
echo "--- old install/ copied into src (cp -r install src/old_install)"
fresh; $C build >/dev/null 2>&1; cp -r install src/old_install
run "colcon build with src/old_install (has COLCON_IGNORE)" $C build
rm -f src/old_install/COLCON_IGNORE
run "same after rm src/old_install/COLCON_IGNORE" $C build

echo; echo "##### T3 ignore marker files in the copy src/pkg_a_old"
for f in COLCON_IGNORE AMENT_IGNORE CATKIN_IGNORE colcon_ignore .colcon_ignore IGNORE; do
  dupws; touch src/pkg_a_old/$f
  run "marker src/pkg_a_old/$f" $C build
done
dupws; echo "pkg_a" > src/pkg_a_old/COLCON_IGNORE
run "COLCON_IGNORE with content (not empty)" $C build
echo "--- marker in a parent folder"
for f in COLCON_IGNORE AMENT_IGNORE CATKIN_IGNORE; do
  fresh; mkdir -p src/backup; cp -r src/pkg_a src/backup/pkg_a; touch src/backup/$f
  run "src/backup/$f with src/backup/pkg_a inside" $C build
done
echo "--- marker in the ORIGINAL instead: which copy gets built?"
dupws; sed -i 's/ament_package()/message(STATUS "BUILDING_FROM_OLD_COPY")\nament_package()/' src/pkg_a_old/CMakeLists.txt; touch src/pkg_a/COLCON_IGNORE
run "COLCON_IGNORE in src/pkg_a, copy src/pkg_a_old prints marker" $C build --event-handlers console_direct+
echo "marker lines: $(grep -c BUILDING_FROM_OLD_COPY /tmp/o.log)"

echo; echo "##### T4 --base-paths / --paths / --packages-skip to pick one copy"
dupws
run "--base-paths src/pkg_a src/pkg_b" $C build --base-paths src/pkg_a src/pkg_b
dupws
run "--paths src/pkg_a src/pkg_b" $C build --paths src/pkg_a src/pkg_b
dupws
run "--paths 'src/pkg_*' (glob passed to colcon)" $C build --paths 'src/pkg_*'
dupws
run "--packages-skip pkg_a" $C build --packages-skip pkg_a
dupws
run "--packages-select pkg_a" $C build --packages-select pkg_a
dupws
run "colcon list --base-paths src/pkg_a src/pkg_b" $C list --base-paths src/pkg_a src/pkg_b
run "colcon list --paths src/pkg_a_old" $C list --paths src/pkg_a_old
run "colcon build --paths src/pkg_a src/pkg_b, then plain colcon build" $C build --paths src/pkg_a src/pkg_b
run "plain colcon build afterwards" $C build

t5() {  # overlay/underlay tests
fresh; mkpkg src/std_msgs std_msgs
run "colcon build (overlay std_msgs)" $C build
run "colcon build --packages-select std_msgs" $C build --packages-select std_msgs
run "colcon build --allow-overriding std_msgs" $C build --allow-overriding std_msgs
run "colcon build --allow-overriding (no name)" $C build --allow-overriding
run "colcon build --allow-overriding pkg_a (wrong name)" $C build --allow-overriding pkg_a
run "colcon list (overlay std_msgs)" $C list
echo "--- source the overlay's own install, then build again (same terminal)"
fresh; $C build >/dev/null 2>&1
run "build after sourcing own install/setup.bash" bash -c "source install/setup.bash; colcon build"
echo "--- second overlay /ws_b built on top of /ws (pkg_a in both)"
rm -rf /ws_b; mkdir -p /ws_b/src; cd /ws_b; mkpkg src/pkg_a pkg_a
run "ws_b build with /ws sourced (pkg_a also in /ws/install)" bash -c "source /ws/install/setup.bash; colcon build"
run "ws_b build with /ws sourced + --allow-overriding pkg_a" bash -c "source /ws/install/setup.bash; colcon build --allow-overriding pkg_a"
run "ros2 pkg prefix pkg_a after sourcing /ws then /ws_b" bash -c "source /ws/install/setup.bash; source install/setup.bash; ros2 pkg prefix pkg_a"
echo "--- same two cases with --merge-install workspaces"
fresh; $C build --merge-install >/dev/null 2>&1
run "build --merge-install after sourcing own merged install/setup.bash" bash -c "source install/setup.bash; colcon build --merge-install"
rm -rf /ws_b; mkdir -p /ws_b/src; cd /ws_b; mkpkg src/pkg_a pkg_a
run "ws_b build with merged /ws sourced (pkg_a also in /ws/install)" bash -c "source /ws/install/setup.bash; colcon build"
run "ws_b same + --allow-overriding pkg_a" bash -c "source /ws/install/setup.bash; colcon build --allow-overriding pkg_a"
echo "--- underlay /ws where pkg_c exec_depends on pkg_a (pkg_a no longer a leaf), overlay /ws_b overrides pkg_a"
fresh; mkpkg src/pkg_c pkg_c pkg_a; $C build >/dev/null 2>&1; ls install
rm -rf /ws_b; mkdir -p /ws_b/src; cd /ws_b; mkpkg src/pkg_a pkg_a
run "ws_b build, /ws sourced, pkg_c in /ws depends on pkg_a" bash -c "source /ws/install/setup.bash; colcon build"
run "ws_b same + --allow-overriding pkg_a" bash -c "source /ws/install/setup.bash; colcon build --allow-overriding pkg_a"
[ -f $OC ] && { echo "--- override_check.py source: leaf-package filter"; grep -n -B1 -A3 "leaf packages" $OC; }
cd /
}
echo; echo "##### T5 overlay package with the same name as an underlay package (std_msgs in /opt/ros), image as shipped"
echo "colcon extensions with override in name: $(colcon extensions 2>/dev/null | grep -i override | tr '\n' ' ')"
t5
echo; echo "##### T6 same tests after apt-get install python3-colcon-override-check"
apt-get update -qq >/dev/null 2>&1
echo "apt-cache depends python3-colcon-common-extensions:"; apt-cache depends python3-colcon-common-extensions 2>&1 | grep -i -E "depends|override" | head -30
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-colcon-override-check >/tmp/apt.log 2>&1; echo "apt install exit=$?"; tail -2 /tmp/apt.log
dpkg-query -W -f='${Package} ${Version}\n' python3-colcon-override-check python3-colcon-installed-package-information 2>&1
echo "colcon extensions with override in name: $(colcon extensions 2>/dev/null | grep -i override | tr '\n' ' ')"
t5
cd /
echo "=== done"
