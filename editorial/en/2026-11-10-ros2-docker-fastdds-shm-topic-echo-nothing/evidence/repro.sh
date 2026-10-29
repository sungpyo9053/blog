#!/bin/bash
# Usage: bash repro.sh <distro>   (humble | jazzy | lyrical)
# Runs on a Docker host. Two containers from ros:<distro>-ros-base:
#   shm-sub: ros2 topic echo /shm_test (started first, 20 s window, SIGINT at the end)
#   shm-pub: pub.py, waits 2 s, then publishes 100 std_msgs/String "msg N" at 10 Hz
# At t=9 s, ros2 node list / ros2 topic list run inside shm-sub.
# All runs use ROS_DOMAIN_ID=77.
# bash repro.sh <distro> extra   runs only the g_/h_ cases (added after the first Humble pass).
# bash repro.sh <distro> cyc     runs only the Cyclone DDS cases.
# Order: Humble ran a-f first, then "extra" (g, h). Jazzy ran the full script (Cyclone build failed, then "cyc"). Lyrical ran the full script.
set -u
D=$1; IMG=ros:$D-ros-base; W=/tmp/en-shm/$D
mkdir -p $W/devshm; cd $W
cat > pub.py <<'X'
import time, rclpy
from std_msgs.msg import String
rclpy.init()
n = rclpy.create_node('shm_pub')
p = n.create_publisher(String, '/shm_test', 10)
time.sleep(2.0)
sent = 0
for i in range(1, 101):
    m = String(); m.data = 'msg %d' % i
    p.publish(m); sent += 1
    time.sleep(0.1)
print('PUB sent=%d matched_subs=%d' % (sent, p.get_subscription_count()), flush=True)
time.sleep(1.0)
n.destroy_node(); rclpy.shutdown()
X
cat > udp.xml <<'X'
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>udp_only</transport_id>
      <type>UDPv4</type>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="udp_only_participant" is_default_profile="true">
    <rtps>
      <userTransports>
        <transport_id>udp_only</transport_id>
      </userTransports>
      <useBuiltinTransports>false</useBuiltinTransports>
    </rtps>
  </participant>
</profiles>
X
printf 'FROM %s\nRUN apt-get update -qq && apt-get install -y -qq ros-%s-rmw-cyclonedds-cpp >/dev/null && rm -rf /var/lib/apt/lists/*\n' $IMG $D > Dockerfile.cyc

echo "=== distro=$D image=$IMG"
docker pull -q $IMG
docker image inspect -f '{{index .RepoDigests 0}} {{.Created}}' $IMG
docker run --rm $IMG bash -c "source /opt/ros/$D/setup.bash; dpkg-query -W -f='\${Package} \${Version}\n' 'ros-$D-fastrtps' 'ros-$D-fastdds' 'ros-$D-rmw-fastrtps-cpp' 'ros-$D-rmw-implementation' 'ros-$D-ros2cli' 2>/dev/null; echo ROS_DISTRO=\$ROS_DISTRO; echo RMW_IMPLEMENTATION_env=\${RMW_IMPLEMENTATION:-unset}; python3 -c 'import rclpy; rclpy.init(); from rclpy.utilities import get_rmw_implementation_identifier as g; print(\"rmw_default=\"+g())'"

SRC="source /opt/ros/$D/setup.bash"
run_case() {  # name subflags pubflags [image]
  local name=$1 sf=$2 pf=$3 img=${4:-$IMG}
  echo; echo "=== case $name"
  echo "sub flags: $sf"; echo "pub flags: $pf"
  ls /dev/shm > $W/hostshm_before_$name.txt
  local t0=$(date +%s.%N)
  docker run -d --rm --name shm-sub $sf -e ROS_DOMAIN_ID=77 -v $W:/w $img bash -c "$SRC; timeout -k 5 -s INT 20 ros2 topic echo /shm_test std_msgs/msg/String > /w/sub_$name.txt 2>&1" >/dev/null
  sleep 3
  docker run -d --rm --name shm-pub $pf -e ROS_DOMAIN_ID=77 -v $W:/w $img bash -c "$SRC; timeout -k 5 -s INT 25 python3 /w/pub.py > /w/pub_$name.txt 2>&1" >/dev/null
  sleep 6
  timeout 30 docker exec shm-sub bash -c "$SRC; echo '--- ros2 node list'; ros2 node list; echo '--- ros2 topic list'; ros2 topic list" > $W/list_$name.txt 2>&1
  timeout 40 docker wait shm-pub >/dev/null 2>&1; timeout 40 docker wait shm-sub >/dev/null 2>&1
  docker kill shm-pub shm-sub >/dev/null 2>&1 && echo "NOTE: had to docker kill leftover container(s)"
  sleep 1
  echo "elapsed_s=$(echo "$(date +%s.%N) - $t0" | bc)"
  cat $W/list_$name.txt
  echo "--- pub output"; cat $W/pub_$name.txt
  echo "--- sub: received $(grep -c '^data:' $W/sub_$name.txt) of 100"
  echo "first: $(grep '^data:' $W/sub_$name.txt | head -1)  last: $(grep '^data:' $W/sub_$name.txt | tail -1)"
  echo "--- sub non-data lines (uniq -c)"; grep -v -e '^data:' -e '^---$' $W/sub_$name.txt | sort | uniq -c
  ls /dev/shm > $W/hostshm_after_$name.txt
  echo "--- new files in host /dev/shm:"; comm -13 $W/hostshm_before_$name.txt $W/hostshm_after_$name.txt
}

EXTRA() {
  U="--user 1000:1000 -e HOME=/tmp -e ROS_LOG_DIR=/tmp"
  run_case g_mixed_sub_ipchost_only "--net=host --ipc=host" "--net=host"
  run_case h_ipchost_root_sub_uid1000_pub "--net=host --ipc=host" "--net=host --ipc=host $U"
  echo "--- leftover Fast DDS files in host /dev/shm after h_:"; ls -l /dev/shm | grep -i -E "fastrtps|fast_datasharing|fastdds" || echo none
}
CYC() {
echo; echo "=== building shm-cyc:$D"
if docker build -q -t shm-cyc:$D - < Dockerfile.cyc ; then
  docker run --rm shm-cyc:$D bash -c "dpkg-query -W -f='\${Package} \${Version}\n' ros-$D-rmw-cyclonedds-cpp ros-$D-cyclonedds"
  C="-e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
  echo "--- cyclone interface choice (Tracing config, --net=host)"
  docker run --rm --net=host $C -e ROS_DOMAIN_ID=77 -v $W:/w -e CYCLONEDDS_URI='<Tracing><Verbosity>config</Verbosity><OutputFile>stderr</OutputFile></Tracing>' shm-cyc:$D bash -c "$SRC; timeout -k 5 -s INT 4 ros2 topic list --no-daemon" 2>&1 | grep -i -E 'interface|multicast' | head -8
  run_case f_cyclonedds "--net=host $C" "--net=host $C" shm-cyc:$D
  run_case f_cyclonedds_bridge "$C" "$C" shm-cyc:$D
  cat > $W/cyc_lo.xml <<'X'
<CycloneDDS><Domain Id="any">
  <General><Interfaces><NetworkInterface name="lo"/></Interfaces><AllowMulticast>false</AllowMulticast></General>
  <Discovery><Peers><Peer address="127.0.0.1"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>50</MaxAutoParticipantIndex></Discovery>
</Domain></CycloneDDS>
X
  LO=file:///w/cyc_lo.xml
  run_case f_cyclonedds_lo_unicast "--net=host $C -e CYCLONEDDS_URI=$LO" "--net=host $C -e CYCLONEDDS_URI=$LO" shm-cyc:$D
else
  echo "cyclonedds build FAILED"
fi
}
if [ "${2:-}" = cyc ]; then CYC; echo "=== done $D cyc"; exit 0; fi
if [ "${2:-}" = extra ]; then EXTRA; echo "=== done $D extra"; exit 0; fi
run_case a_bridge "" ""
run_case b_nethost_1 "--net=host" "--net=host"
run_case b_nethost_2 "--net=host" "--net=host"
run_case b_nethost_3 "--net=host" "--net=host"
run_case c_nethost_ipchost "--net=host --ipc=host" "--net=host --ipc=host"
run_case d_nethost_devshm_vol "--net=host -v $W/devshm:/dev/shm" "--net=host -v $W/devshm:/dev/shm"
run_case e1_env_udpv4_both "--net=host -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4" "--net=host -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4"
run_case e1_env_udpv4_sub_only "--net=host -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4" "--net=host"
run_case e1_env_udpv4_pub_only "--net=host" "--net=host -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4"
run_case e2_xml_FASTRTPS_var "--net=host -e FASTRTPS_DEFAULT_PROFILES_FILE=/w/udp.xml" "--net=host -e FASTRTPS_DEFAULT_PROFILES_FILE=/w/udp.xml"
run_case e3_xml_FASTDDS_var "--net=host -e FASTDDS_DEFAULT_PROFILES_FILE=/w/udp.xml" "--net=host -e FASTDDS_DEFAULT_PROFILES_FILE=/w/udp.xml"
EXTRA
CYC
echo "=== done $D"
# One-off run after the Jazzy pass (output at the end of out_jazzy.txt):
# docker run --rm --net=host -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e ROS_DOMAIN_ID=77 \
#   -e CYCLONEDDS_URI="<Tracing><Verbosity>fine</Verbosity><OutputFile>stderr</OutputFile></Tracing>" shm-cyc:jazzy \
#   bash -c "source /opt/ros/jazzy/setup.bash; timeout -k 5 -s INT 4 ros2 topic list --no-daemon" 2>&1 | grep -i -E "selected|interfaces:|ens5|udp/"
