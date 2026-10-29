# Three files, run on a 2-vCPU Ubuntu runner (Docker). Copy each section to its own file in one directory, then: ./repro.sh
# Phases ran in this order: humble bridge+lo (with earlier caps: A_default 40, Fast DDS 45, no extra/comm), then humble extra, humble comm,
# jazzy and lyrical with all phases (bridge extra comm lo), then followup on all three. Every run is in out_<distro>.txt with a '######## phase' header.
# ===================== repro.sh =====================
#!/bin/bash
# Host-side driver (Lightsail runner). Distros run one after another.
set -u
W=/tmp/en-cyc; cd $W
for d in ${DISTROS:-humble jazzy lyrical}; do
  echo "##### $d  $(date -u +%FT%TZ)  load: $(uptime)"
  img=ros:$d-ros-base
  docker pull -q $img
  docker rm -f cyc-$d >/dev/null 2>&1
  docker run -d --name cyc-$d --memory 2500m --ulimit core=0 $img sleep infinity
  docker exec cyc-$d bash -c "apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$d-rmw-cyclonedds-cpp ros-$d-demo-nodes-cpp iproute2 procps >/dev/null 2>&1; echo apt rc=\$?"
  docker cp cyc_test.sh cyc-$d:/cyc_test.sh; docker cp many_nodes.py cyc-$d:/many_nodes.py
  {
    echo "image: $img $(docker image inspect $img --format '{{index .RepoDigests 0}}')"
    docker exec cyc-$d bash -c "dpkg-query -W -f='\${Package} \${Version}\n' 'ros-$d-rmw-cyclonedds-cpp' 'ros-$d-cyclonedds' 'ros-$d-rmw-fastrtps-cpp' 'ros-$d-fastrtps' 'ros-$d-fastdds' 'ros-$d-rmw-implementation' 2>/dev/null; . /etc/os-release; echo \$PRETTY_NAME"
  } > digests_$d.txt 2>&1
  for ph in ${PHASES:-bridge extra comm lo}; do
    [ $ph = lo ] && docker network disconnect bridge cyc-$d
    echo "######## phase $ph  $(date -u +%FT%TZ)  load: $(cat /proc/loadavg)" >> out_$d.txt
    docker exec cyc-$d bash /cyc_test.sh $ph >> out_$d.txt 2>&1
  done
  echo "##### docker images DURING ($d)" >> cleanup_during.txt; docker images >> cleanup_during.txt
  docker rm -f cyc-$d
  echo "##### $d done $(date -u +%FT%TZ) load: $(uptime)"
done

# ===================== cyc_test.sh (runs inside the container) =====================
#!/bin/bash
# Runs INSIDE a ros:<distro>-ros-base container (cyc-<distro>).
# Usage: cyc_test.sh bridge|lo
# Counts how many single-node processes start on one host before
# "Failed to find a free participant index" appears, under several configs.
source /opt/ros/$ROS_DISTRO/setup.bash
PHASE=$1
TALKER=/opt/ros/$ROS_DISTRO/lib/demo_nodes_cpp/talker
LISTENER=/opt/ros/$ROS_DISTRO/lib/demo_nodes_cpp/listener
L=/tmp/logs; mkdir -p $L
CYC=rmw_cyclonedds_cpp

reset_env() {
  unset CYCLONEDDS_URI ROS_LOCALHOST_ONLY ROS_AUTOMATIC_DISCOVERY_RANGE ROS_DOMAIN_ID
  export RMW_IMPLEMENTATION=$CYC
}
lh_env() {  # localhost-only discovery, per distro
  if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1
  else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
}
killall_nodes() {
  pkill -f "$TALKER" ; pkill -f "$LISTENER"; pkill -f many_nodes.py; pkill -f component_container
  ros2 daemon stop >/dev/null 2>&1; sleep 2
  pkill -9 -f /opt/ros 2>/dev/null; sleep 1
}
ports() {  # Cyclone auto index => unicast discovery port 7400+250*domain+10+2*idx
  echo "  UDP sockets bound to 7400-7999: $(ss -ulnH | awk '{print $4}' | grep -cE ':7[4-9][0-9][0-9]$')"
  echo "  distinct ports 7410..7408+2k (even, domain 0 index slots): $(ss -ulnH | awk '{print $4}' | sed 's/.*://' | awk '$1>=7410 && $1<7650 && $1%2==0' | sort -u | wc -l)"
}
comm_check() {  # does a fresh listener hear the talkers?
  timeout 8 $LISTENER --ros-args -r __node:=probe_listener > $L/listener_$1.txt 2>&1
  echo "  listener (8 s): $(grep -c 'I heard' $L/listener_$1.txt) 'I heard' lines; first lines:"; head -3 $L/listener_$1.txt | sed 's/^/    /'
}
wait_load() {  # shared 2-vCPU runner: never pile on while the host is busy
  while [ "$(cut -d. -f1 /proc/loadavg)" -ge ${1:-3} ]; do sleep 5; done
}
# count LABEL MAX [EXTRA_AFTER_FAIL]
count() {
  local label=$1 max=$2 extra=${3:-3} first_fail=0 alive=0 after=0
  echo "=== $label  (RMW=$RMW_IMPLEMENTATION LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-} RANGE=${ROS_AUTOMATIC_DISCOVERY_RANGE:-} DOMAIN=${ROS_DOMAIN_ID:-0} URI=${CYCLONEDDS_URI:-})"
  wait_load 3
  for i in $(seq 1 $max); do
    wait_load 6
    $TALKER --ros-args -r __node:=${label}_t$i > $L/${label}_$i.txt 2>&1 &
    local p=$!; sleep 1
    if kill -0 $p 2>/dev/null; then alive=$((alive+1)); else
      if [ $first_fail = 0 ]; then first_fail=$i; echo "  process #$i exited; its full output:"; sed 's/^/    | /' $L/${label}_$i.txt
      else echo "  process #$i exited too: $(grep -m1 -E 'Failed|failed' $L/${label}_$i.txt)"; fi
    fi
    if [ $first_fail != 0 ]; then after=$((after+1)); [ $after -gt $extra ] && break; fi
  done
  echo "  RESULT $label: started=$i alive=$alive first_failure=#$first_fail"
  echo "  talker RSS total: $(ps -o rss= -C talker | awk '{s+=$1} END {printf "%d MB", s/1024}')"
}

if [ "$PHASE" = bridge ]; then
  echo "### interfaces"; ip -br link; ip -br addr
  reset_env
  count A_default 36; ports; comm_check A; killall_nodes

  reset_env; lh_env
  count B_localhost 45; ports
  echo "  ros2 node list --no-daemon while at the limit:"; ros2 node list --no-daemon 2>&1 | tail -6 | sed 's/^/    /'
  comm_check B; killall_nodes

  if [ "$ROS_DISTRO" != humble ]; then
    reset_env; export ROS_LOCALHOST_ONLY=1
    count B2_ROS_LOCALHOST_ONLY_1 45; killall_nodes
  fi

  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>auto</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count C_auto_no_max 45; killall_nodes

  reset_env; lh_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
  count D_localhost_max20 30; ports; killall_nodes

  reset_env; lh_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count E_localhost_none 40; ports; comm_check E; killall_nodes

  reset_env; lh_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" multicast="true"/></Interfaces></General><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count E2_localhost_none_lo_multicast 40; comm_check E2; killall_nodes

  echo "=== F_domain_split: fill domain 0 (localhost) then start talkers on domain 1"
  reset_env; lh_env
  count F0_domain0 45 1
  export ROS_DOMAIN_ID=1
  count F1_domain1 10 1; ports; killall_nodes

  echo "=== G_daemon: ros2 daemon running before counting (localhost)"
  reset_env; lh_env
  ros2 daemon start 2>&1 | sed 's/^/  /'; sleep 2
  count G_with_daemon 45; ports
  echo "  ros2 node list (daemon) at the limit:"; ros2 node list 2>&1 | tail -4 | sed 's/^/    /'
  killall_nodes

  echo "=== H_many_nodes_one_process: rclpy, 40 nodes in one context (localhost)"
  reset_env; lh_env
  python3 /many_nodes.py 40 > $L/H.txt 2>&1 &
  sleep 8; sed 's/^/  /' $L/H.txt | tail -3; ports
  count H_after_40node_proc 45; killall_nodes

  echo "=== I_component_container: 1 container, 20 Talker components via ros2 component load (localhost)"
  reset_env; lh_env
  /opt/ros/$ROS_DISTRO/lib/rclcpp_components/component_container > $L/I.txt 2>&1 &
  sleep 3
  okl=0; for k in $(seq 1 20); do
    ros2 component load /ComponentManager demo_nodes_cpp demo_nodes_cpp::Talker -n comp_t$k > $L/I_load_$k.txt 2>&1 && okl=$((okl+1)) || { echo "  load $k failed:"; tail -3 $L/I_load_$k.txt | sed 's/^/    /'; }
  done
  echo "  loads ok: $okl/20"; ports
  echo "  container node count via ros2 node list --no-daemon: $(ros2 node list --no-daemon 2>/dev/null | grep -c comp_t)"
  count I_after_container 45; killall_nodes

  reset_env; export RMW_IMPLEMENTATION=rmw_fastrtps_cpp; lh_env
  count B_fastdds_localhost 36; comm_check B_fastdds; killall_nodes
fi

if [ "$PHASE" = lo ]; then
  echo "### interfaces (bridge disconnected)"; ip -br link; ip -br addr
  reset_env
  count J_lo_only_default 45; ports
  echo "  ros2 topic list --no-daemon at the limit:"; ros2 topic list --no-daemon 2>&1 | tail -6 | sed 's/^/    /'
  python3 -c "import rclpy; rclpy.init(); n=rclpy.create_node('py_probe'); print('py node ok')" 2>&1 | tail -6 | sed 's/^/  rclpy at limit: /'
  killall_nodes
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count K_lo_only_none 40; comm_check K; killall_nodes
  reset_env; export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  count L_lo_only_fastdds 36; comm_check L; killall_nodes
fi
if [ "$PHASE" = extra ]; then
  echo "=== X0: effective ParticipantIndex reported by Cyclone config trace (lo only, URI says none)"
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery><Tracing><Category>config</Category><OutputFile>/tmp/logs/x0_trace.log</OutputFile></Tracing></Domain></CycloneDDS>'
  timeout 4 $TALKER --ros-args -r __node:=x0 > $L/x0.txt 2>&1
  grep -iE 'ParticipantIndex|AllowMulticast|multicast' /tmp/logs/x0_trace.log | head -8 | sed 's/^/  trace: /'
  echo "  same, with ROS localhost setting on:"
  lh_env; timeout 4 $TALKER --ros-args -r __node:=x0b > $L/x0b.txt 2>&1; head -3 $L/x0b.txt | sed 's/^/    /'
  grep -iE 'ParticipantIndex|AllowMulticast' /tmp/logs/x0_trace.log | tail -4 | sed 's/^/  trace: /'
  # localhost without ROS_LOCALHOST_ONLY / RANGE: put lo into CYCLONEDDS_URI yourself
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count X1_uri_lo_none 30; comm_check X1; killall_nodes
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" multicast="true"/></Interfaces></General><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count X2_uri_lo_multicast_none 30; comm_check X2; ports; killall_nodes
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
  count X3_uri_lo_auto_max20 24; comm_check X3; killall_nodes
fi
if [ "$PHASE" = comm ]; then
  # below the limit: do nodes on loopback actually talk under each config?
  for cfg in localhost_env lo_auto_max20 localhost_env_max20; do
    reset_env
    case $cfg in
      localhost_env) lh_env ;;
      lo_auto_max20) export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>' ;;
      localhost_env_max20) lh_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>' ;;
    esac
    count Y_$cfg 5; comm_check Y_$cfg; killall_nodes
  done
fi
if [ "$PHASE" = followup ]; then
  # X1 again past the 32 limit, and E (localhost + none) below any limit
  reset_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count Z1_uri_lo_none 36; ports; head -2 $L/Z1_uri_lo_none_1.txt | sed 's/^/  first talker: /'; killall_nodes
  reset_env; lh_env; export CYCLONEDDS_URI='<CycloneDDS><Domain><Discovery><ParticipantIndex>none</ParticipantIndex></Discovery></Domain></CycloneDDS>'
  count Z2_localhost_none_small 5; sleep 3; comm_check Z2; killall_nodes
  echo "=== Z3: does ros2 component load leave a daemon behind? (localhost)"
  reset_env; lh_env
  /opt/ros/$ROS_DISTRO/lib/rclcpp_components/component_container > $L/Z3.txt 2>&1 &
  sleep 3; echo "  before load: $(ros2 daemon status --help >/dev/null 2>&1; pgrep -fc _ros2_daemon) daemon process(es)"; ports
  ros2 component load /ComponentManager demo_nodes_cpp demo_nodes_cpp::Talker -n z3_t1 2>&1 | tail -1 | sed 's/^/  /'
  echo "  after load: $(pgrep -fc _ros2_daemon) daemon process(es)"; ports
  killall_nodes
fi
echo "### done $PHASE"

# ===================== many_nodes.py =====================
# One process, one rclpy context, N nodes spun by one executor.
import sys, rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
n = int(sys.argv[1])
rclpy.init()
ex = SingleThreadedExecutor()
nodes = []
for i in range(n):
    node = rclpy.create_node(f'many_{i}')
    node.create_publisher(String, 'chatter_many', 10)
    nodes.append(node); ex.add_node(node)
print(f'created {len(nodes)} nodes in one process', flush=True)
ex.spin()
