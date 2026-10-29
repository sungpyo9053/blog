#!/bin/bash
# Runs INSIDE ros:<distro>-ros-base as root. Usage (host):
#   docker run --rm --name rdp-$D -v $PWD/repro.sh:/repro.sh:ro ros:$D-ros-base bash /repro.sh > out_$D.txt 2>&1
run() { echo; echo "\$ $*"; "$@" 2>&1; echo "[exit=$?]"; }
sec() { echo; echo "=================== $* ==================="; }

mkpkg() { # mkpkg <dir> <name> <dep...>
  mkdir -p "$1/$2"
  { echo '<?xml version="1.0"?>'
    echo '<package format="3"><name>'"$2"'</name><version>0.0.1</version>'
    echo '<description>t</description><maintainer email="dev@example.com">t</maintainer><license>MIT</license>'
    echo '<buildtool_depend>ament_cmake</buildtool_depend>'
    shift 2; for d in "$@"; do echo "<depend>$d</depend>"; done
    echo '<export><build_type>ament_cmake</build_type></export></package>'; } > "$1/$2/package.xml"
}

sec "versions"
run date -u
run grep PRETTY_NAME /etc/os-release
echo "ROS_DISTRO=$ROS_DISTRO"
run rosdep --version
run dpkg-query -W python3-rosdep python3-rosdep-modules python3-rosdistro-modules python3-pip
run python3 --version
run ls -la /root/.ros/rosdep/sources.cache
run ls /etc/ros/rosdep/sources.list.d

# workspaces
mkpkg /ws/c/src pkg_b
mkpkg /ws/c/src pkg_a pkg_b rclpy python3-numpy
mkpkg /ws/b/src pkg_bt turtlesim
mkpkg /ws/d/src pkg_typo python-numpy
mkpkg /ws/d2/src pkg_fake not_a_real_key_xyz
mkpkg /ws/e/src pkg_pip python3-anytree-pip
mkpkg /ws/h/src pkg_custom my_custom_tool
mkpkg /ws/g/src pkg_typo python-numpy
mkpkg /ws/g/src pkg_a2 rclpy python3-numpy tree

sec "(a) cache empty: move ~/.ros/rosdep away"
mv /root/.ros/rosdep /root/.ros/rosdep.image
run rosdep install --from-paths /ws/c/src --ignore-src -r -y -s
run rosdep resolve python3-numpy
sec "(a) rosdep update"
run bash -c 'time rosdep update'
run ls -la /root/.ros/rosdep/sources.cache

sec "(a2) apt lists empty (no apt-get update) - real install of tree"
run ls /var/lib/apt/lists
run rosdep install --from-paths /ws/g/src --ignore-src -y --skip-keys python-numpy
run apt-get update -qq

sec "(b) ROS_DISTRO unset, no --rosdistro (pkg_bt depends on turtlesim, not in ros-base)"
run env -u ROS_DISTRO rosdep install --from-paths /ws/b/src --ignore-src -r -y -s
run env -u ROS_DISTRO rosdep install --from-paths /ws/b/src --ignore-src -y -s
run env -u ROS_DISTRO rosdep resolve turtlesim
run env -u ROS_DISTRO rosdep resolve python3-numpy
sec "(b) ROS_DISTRO unset, --rosdistro $ROS_DISTRO"
run env -u ROS_DISTRO rosdep install --from-paths /ws/b/src --ignore-src -r -y -s --rosdistro "$ROS_DISTRO"
sec "(b) ROS_DISTRO set (default env)"
run rosdep install --from-paths /ws/b/src --ignore-src -r -y -s
sec "(b2) wrong distro: --rosdistro other"
for o in humble jazzy lyrical; do [ "$o" = "$ROS_DISTRO" ] || run rosdep resolve rclpy --rosdistro "$o"; done

sec "(c) in-workspace dependency pkg_b, without --ignore-src"
run rosdep install --from-paths /ws/c/src -r -y -s
run rosdep install --from-paths /ws/c/src -y -s
sec "(c) with --ignore-src"
run rosdep install --from-paths /ws/c/src --ignore-src -r -y -s
run rosdep install --from-paths /ws/c/src --ignore-src -y

sec "(d) misspelled key python-numpy"
run rosdep install --from-paths /ws/d/src --ignore-src -r -y
run rosdep resolve python-numpy
run rosdep resolve python3-numpy
run rosdep where-defined python3-numpy
sec "(d) nonexistent key"
run rosdep install --from-paths /ws/d2/src --ignore-src -r -y
sec "(d) fix: python-numpy -> python3-numpy"
sed -i 's/python-numpy/python3-numpy/' /ws/d/src/pkg_typo/package.xml
run rosdep install --from-paths /ws/d/src --ignore-src -r -y

sec "(e) pip-only key python3-anytree-pip"
run rosdep resolve python3-anytree-pip
run which pip3
run rosdep install --from-paths /ws/e/src --ignore-src -r -y
run python3 -c 'import anytree; print("anytree", anytree.__version__)'
sec "(e) retry with PIP_BREAK_SYSTEM_PACKAGES=1"
run env PIP_BREAK_SYSTEM_PACKAGES=1 rosdep install --from-paths /ws/e/src --ignore-src -r -y
run python3 -c 'import anytree; print("anytree", anytree.__version__)'

sec "(e) install python3-pip, retry"
run bash -c 'apt-get install -y -qq python3-pip >/dev/null 2>&1; dpkg-query -W python3-pip'
run rosdep install --from-paths /ws/e/src --ignore-src -r -y
run python3 -c 'import anytree; print("anytree", anytree.__version__)'
run env PIP_BREAK_SYSTEM_PACKAGES=1 rosdep install --from-paths /ws/e/src --ignore-src -r -y
run python3 -c 'import anytree; print("anytree", anytree.__version__)'

sec "(f) rosdep init (image already initialized), then twice from clean"
run rosdep init
rm /etc/ros/rosdep/sources.list.d/20-default.list
run rosdep init
run rosdep init

sec "(g) -r vs no -r with one bad key + good keys (simulate)"
run rosdep install --from-paths /ws/g/src --ignore-src -y -s
run rosdep install --from-paths /ws/g/src --ignore-src -r -y -s
sec "(g) diagnostics"
run rosdep check --from-paths /ws/g/src --ignore-src
run rosdep check --from-paths /ws/c/src --ignore-src
run rosdep keys --from-paths /ws/g/src --ignore-src
run rosdep keys --from-paths /ws/c/src
run rosdep keys --from-paths /ws/c/src --ignore-src
run rosdep resolve rclpy
run rosdep resolve tree

sec "(h) custom source for my_custom_tool"
run rosdep install --from-paths /ws/h/src --ignore-src -r -y
cat > /ws/custom.yaml <<'Y'
my_custom_tool:
  ubuntu: [tree]
Y
echo "yaml file:///ws/custom.yaml" > /etc/ros/rosdep/sources.list.d/10-local.list
run cat /etc/ros/rosdep/sources.list.d/10-local.list
echo "--- before rosdep update:"
run rosdep resolve my_custom_tool
run rosdep update
echo "--- after rosdep update:"
run rosdep resolve my_custom_tool
run rosdep where-defined my_custom_tool
run rosdep install --from-paths /ws/h/src --ignore-src -r -y
run rosdep check --from-paths /ws/h/src --ignore-src
echo; echo DONE
