#!/bin/bash
# repro.sh <humble|jazzy|lyrical> [matrix]
# "E: Unable to locate package ros-<distro>-..." measurements. Run on the runner from /tmp/en-pick46.
# Containers need the network for apt; no ROS nodes are started, DDS env is isolated anyway.
# apt-get install -s (simulate) is used so nothing heavy is installed.
set -u
DISTRO=$1
IMG=ros:${DISTRO}-ros-base
ENVS="-e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST -e DEBIAN_FRONTEND=noninteractive"
RUN="docker run --rm --ulimit core=0 --pids-limit 30 $ENVS"
ulimit -c 0
echo "### date: $(date '+%F %T %Z')  image: $IMG  $(docker image inspect -f '{{index .RepoDigests 0}}' $IMG)"

echo; echo "### T1 fresh container, no apt-get update"
$RUN --name pk36-$DISTRO-t1 $IMG bash -c '
. /etc/os-release; echo "ubuntu=$VERSION_ID codename=$VERSION_CODENAME arch=$(dpkg --print-architecture) ROS_DISTRO=$ROS_DISTRO"
echo "index files in /var/lib/apt/lists: $(ls /var/lib/apt/lists | grep -c _Packages)"
echo "sources.list.d: $(ls /etc/apt/sources.list.d/ | tr "\n" " ")"
echo "\$ apt-get install -s ros-$ROS_DISTRO-joint-state-publisher-gui"
apt-get install -s ros-$ROS_DISTRO-joint-state-publisher-gui 2>&1 | tail -3; echo "exit=${PIPESTATUS[0]}"
'

echo; echo "### T2 after apt-get update"
$RUN --name pk36-$DISTRO-t2 $IMG bash -c '
D=$ROS_DISTRO
t0=$(date +%s.%N); apt-get update > /tmp/upd.txt 2>&1; rc=$?; t1=$(date +%s.%N)
echo "apt-get update exit=$rc seconds=$(python3 -c "print(round($t1-$t0,1))")"
grep -i "ros.org\|^E:\|^W:" /tmp/upd.txt
echo "index files: $(ls /var/lib/apt/lists | grep -c _Packages)"
sim() { echo "\$ apt-get install -s $*"; apt-get install -s "$@" > /tmp/s.txt 2>&1; rc=$?; grep -E "^E:|^ |Depends|not installable|Unable|has no installation" /tmp/s.txt | head -8; echo "exit=$rc Inst_lines=$(grep -c ^Inst /tmp/s.txt)"; }
sim ros-$D-joint-state-publisher-gui
sim ros-$D-joint_state_publisher_gui
sim ros-$D-joint-state-publisher-gui ros-$D-xacro ros-$D-not-a-package
echo "\$ apt-cache search --names-only joint.state.publisher"; apt-cache search --names-only "joint.state.publisher"
echo "--- ROS distros with packages in this index (apt-cache pkgnames ros-):"
apt-cache pkgnames ros- | cut -d- -f2 | sort | uniq -c
echo "--- ros-<X>-ros-base available here?"
for X in foxy humble iron jazzy kilted lyrical rolling; do apt-cache show ros-$X-ros-base >/dev/null 2>&1 && echo "ros-$X-ros-base: available" || echo "ros-$X-ros-base: MISSING"; done
for X in humble jazzy kilted lyrical; do [ $X = $D ] || { sim ros-$X-desktop; break; }; done
echo "--- Gazebo Classic vs new Gazebo packages for $D:"
for P in gazebo-ros-pkgs gazebo-ros2-control ros-gz gz-ros2-control desktop desktop-full; do
  v=$(apt-cache policy ros-$D-$P 2>/dev/null | awk "/Candidate/{print \$2}"); echo "ros-$D-$P: ${v:-MISSING}"; done
sim ros-$D-gazebo-ros2-control
'

echo; echo "### T5 a name apt knows but cannot install (Candidate: (none))"
$RUN --name pk36-$DISTRO-t5 $IMG bash -c '
apt-get update > /dev/null 2>&1
for P in ros-$ROS_DISTRO-gazebo-ros-pkgs ros-$ROS_DISTRO-gazebo-ros; do
echo "\$ apt-get install -s $P"; apt-get install -s $P > /tmp/s.txt 2>&1; rc=$?; grep -E "^E:|not available|referred|obsoleted|only available" /tmp/s.txt; echo "exit=$rc Inst_lines=$(grep -c ^Inst /tmp/s.txt)"
echo "\$ apt-cache showpkg $P (reverse depends, first 5)"; apt-cache showpkg $P | sed -n "/Reverse Depends/,/Dependencies/p" | head -6
done
'

if [ "${2:-}" = matrix ]; then
echo; echo "### T3 packages.ros.org ros2 index: ros-<distro>- package counts per Ubuntu codename and arch"
$RUN --name pk36-$DISTRO-t3 $IMG python3 -c '
import gzip, urllib.request, collections
want = ["ros-base","desktop","joint-state-publisher-gui","gazebo-ros2-control","gazebo-ros-pkgs","ros-gz","rviz2"]
for code in ["focal","jammy","noble","resolute"]:
    for arch in ["amd64","arm64","armhf"]:
        url = f"http://packages.ros.org/ros2/ubuntu/dists/{code}/main/binary-{arch}/Packages.gz"
        try:
            data = gzip.decompress(urllib.request.urlopen(url, timeout=60).read()).decode()
        except Exception as e:
            print(f"{code:9} {arch:6} -> {type(e).__name__}: {e}"); continue
        names = {l[9:] for l in data.splitlines() if l.startswith("Package: ")}
        c = collections.Counter(n.split("-")[1] for n in names if n.startswith("ros-"))
        print(f"{code:9} {arch:6} " + " ".join(f"{k}={v}" for k, v in sorted(c.items()) if v > 20))
        for d in [k for k, v in c.items() if v > 20 and k in ("humble","jazzy","kilted","lyrical")]:
            print("    " + d + ": " + " ".join(w + ("=yes" if f"ros-{d}-{w}" in names else "=NO") for w in want))
'

echo; echo "### T4 ubuntu:22.04 without the ROS repo, then with ros2-apt-source, wrong codename, no universe"
$RUN --name pk36-$DISTRO-t4 ubuntu:22.04 bash -c '
sim() { echo "\$ apt-get install -s $*"; apt-get install -s "$@" > /tmp/s.txt 2>&1; rc=$?; grep -E "^E:|Depends|not installable|Unable|has no installation|held broken" /tmp/s.txt | head -8; echo "exit=$rc Inst_lines=$(grep -c ^Inst /tmp/s.txt)"; }
apt-get update > /dev/null 2>&1; echo "-- plain ubuntu:22.04 after apt-get update, no ROS repo:"
sim ros-humble-ros-base
apt-get install -y -q curl ca-certificates > /dev/null 2>&1; echo "curl installed exit=$?"
V=$(curl -s --max-time 30 https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" "{print \$4}")
echo "ros2-apt-source latest tag: $V"
curl -sL --max-time 60 -o /tmp/r.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${V}/ros2-apt-source_${V}.jammy_all.deb" && dpkg -i /tmp/r.deb 2>&1 | tail -1
echo "--- /etc/apt/sources.list.d/ros2.sources:"; cat /etc/apt/sources.list.d/ros2.sources
echo "-- repo added, BEFORE apt-get update:"; sim ros-humble-ros-base
apt-get update 2>&1 | grep -i "ros.org"; echo "-- repo added, AFTER apt-get update:"; sim ros-humble-ros-base
echo "-- same repo but Suites: focal (what an Ubuntu 20.04 machine gets):"
sed -i "s/^Suites: jammy/Suites: focal/" /etc/apt/sources.list.d/ros2.sources
apt-get update 2>&1 | grep -i "ros.org\|^E:\|^W:"; sim ros-humble-ros-base
echo "focal index ROS distros: $(apt-cache pkgnames ros- | cut -d- -f2 | sort | uniq -c | awk "\$1>20{printf \"%s=%s \", \$2, \$1}")"
sed -i "s/^Suites: focal/Suites: jammy/" /etc/apt/sources.list.d/ros2.sources
echo "-- jammy repo, universe removed from /etc/apt/sources.list:"
sed -i "/^deb.* universe$/d; s/ universe//" /etc/apt/sources.list; echo "active deb lines with universe: $(grep -c "^deb.*universe" /etc/apt/sources.list)"
apt-get update > /dev/null 2>&1; sim ros-humble-ros-base; sim ros-humble-desktop
'
fi
echo; echo "### done $(date '+%F %T %Z')"
