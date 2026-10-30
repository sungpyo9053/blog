#!/bin/bash
# Usage on the runner (headless, no host X server): bash repro.sh humble|jazzy|lyrical
# Stand-in for the host X server: Xvfb running in its OWN container (rvz-x). Its socket dir is
# bind-mounted from /tmp/en-rvz/xN/x11 into client containers as /tmp/.X11-unix.
# Clients use the plain osrf/ros:<distro>-desktop image unless the case uses $TOOLS
# (= the same image + xvfb xauth x11-utils x11-xserver-utils mesa-utils, committed locally).
# rviz2/rqt are bounded with timeout 30; exit 124 = still running when timeout fired (= it started).
set -u
D=$1; IMG=osrf/ros:$D-desktop; TOOLS=rvz-tools:$D; W=/tmp/en-rvz
ulimit -c 0
LIM="--ulimit core=0 --cpus 1.5 --pids-limit 512"
gate() { while :; do l=$(cut -d' ' -f1 /proc/loadavg); awk "BEGIN{exit !($l<4)}" && break; echo "load $l, waiting"; sleep 30; done; echo "[uptime] $(uptime)"; }
mkdir -p $W
echo "=== distro=$D image=$IMG date=$(date -u +%FT%TZ)"
df -h / | tail -1
gate
docker pull -q $IMG
docker image inspect $IMG --format '{{index .RepoDigests 0}} created={{.Created}}'
echo "--- versions in plain image"
docker run --rm $LIM $IMG bash -c "dpkg-query -W -f='\${Package} \${Version}\n' 'ros-$D-rviz2' 'ros-$D-rviz-ogre-vendor' 'ros-$D-rqt-gui' 'libqt5core5a' 'libqt5core5t64' 'libqt6core6*' 'libgl1-mesa-dri' 'libglx-mesa0' 'libgl1' 'libglvnd0' 'mesa-libgallium' 'xvfb' 'mesa-utils' 2>/dev/null; echo dri: \$(ls /usr/lib/x86_64-linux-gnu/dri/ 2>/dev/null | tr '\n' ' ' | cut -c1-300); ldd /opt/ros/$D/lib/librviz_common.so 2>/dev/null | grep -Eo 'libQt[56]Core[^ ]*' | sort -u"
echo "--- build tools image"
gate
docker run --name rvz-prep $LIM $IMG bash -c "apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends xvfb xauth x11-utils x11-xserver-utils mesa-utils 2>&1 | grep -E '^(Setting up|E:)' | sed 's/ \.\.\.//' | tr '\n' ';' | cut -c1-1500; echo"
docker commit rvz-prep $TOOLS >/dev/null && docker rm rvz-prep >/dev/null
docker run --rm $TOOLS bash -c "dpkg-query -W -f='\${Package} \${Version}\n' xvfb mesa-utils libgl1-mesa-dri 2>/dev/null"

N=0
xserver() { # $@ = extra Xvfb args. Fresh dirs per server, so no host-side deletes are needed.
  docker rm -f rvz-x >/dev/null 2>&1; N=$((N+1)); XD=$W/x$N; mkdir -p $XD/x11 $XD/auth
  X="-v $XD/x11:/tmp/.X11-unix"; AW="-v $XD/auth:/auth:ro -e XAUTHORITY=/auth/wild"; AH="-v $XD/auth:/auth:ro -e XAUTHORITY=/auth/host"
  docker run -d --name rvz-x --hostname rvz-x --ipc=shareable $LIM -v $XD/x11:/tmp/.X11-unix -v $XD/auth:/auth $TOOLS bash -c "
    C=\$(mcookie); xauth -q -f /auth/host add :99 . \$C; xauth -q -f /auth/host nlist :99 | sed -e 's/^..../ffff/' | xauth -q -f /auth/wild nmerge -; chmod 644 /auth/*
    exec Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp $*" >/dev/null
  sleep 4; echo "[xserver] Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp $*  (running: $(docker inspect -f '{{.State.Running}}' rvz-x))"
  docker exec rvz-x sh -c 'xauth -f /auth/host list 2>/dev/null; xauth -f /auth/wild list 2>/dev/null' | sed 's/[0-9a-f]\{32\}/<cookie>/'
  ls -la $XD/x11 | tail -n +2
}
xs() { docker exec rvz-x sh -c "DISPLAY=:99 XAUTHORITY=/auth/wild $1" 2>&1; }

case_() { # name image cmd docker-args...
  local name=$1 im=$2 cmd=$3; shift 3
  gate; echo; echo "### CASE $name"; echo "+ docker run $* $im :: $cmd"
  docker run -d --name rvz-c $LIM "$@" $im bash -c "source /opt/ros/\$ROS_DISTRO/setup.bash; $cmd" >/dev/null || { echo "docker run failed"; return; }
  sleep 18
  echo "[t=18s] processes: $(docker exec rvz-c sh -c 'ps -eo comm | grep -E "^(rviz2|rqt|Xvfb|glxinfo)" | tr "\n" " "' 2>/dev/null)"
  docker ps -q -f name=rvz-x | grep -q . && echo "[t=18s] windows on rvz-x :99: $(xs 'xwininfo -root -tree' | grep -iE 'rviz|rqt' | sed -E 's/^ +//' | cut -c1-90 | head -3 | tr '\n' '|')"
  docker exec rvz-c sh -c 'f=$(ls /tmp/xvfb-run.*/Xauthority 2>/dev/null | head -1); [ -n "$f" ] && DISPLAY=:99 XAUTHORITY=$f xwininfo -root -tree 2>&1 | grep -iE "rviz" | head -2' 2>/dev/null | sed 's/^ */[t=18s] window in own xvfb-run :99: /'
  local code; code=$(docker wait rvz-c)
  # identical lines (ignoring [timestamps]) are printed twice, then counted
  docker logs rvz-c 2>&1 | awk '{k=$0; gsub(/\[[0-9]+\.[0-9]+\]/,"[T]",k); c[k]++; if(c[k]<=2) print} END{for(k in c) if(c[k]>2) print "    (" c[k] "x total) " substr(k,1,140)}' | cut -c1-400
  echo "container_exit=$code"; docker rm rvz-c >/dev/null
}
RV='timeout -k 5 30 rviz2; e=$?; echo "rviz2 exit=$e"; exit $e'
RQ='timeout -k 5 30 rqt; e=$?; echo "rqt exit=$e"; exit $e'

echo; echo "===== (1) no DISPLAY, no X server"
case_ 1a-rviz2-no-display $IMG "echo DISPLAY=[\${DISPLAY:-}]; $RV"
case_ 1b-rqt-no-display $IMG "$RQ"
case_ 1c-rviz2-no-display-QT_DEBUG_PLUGINS $IMG "$RV" -e QT_DEBUG_PLUGINS=1

echo; echo "===== X server with cookie auth (-auth /auth/host)"
xserver -auth /auth/host
echo; echo "===== (2) DISPLAY set, socket not mounted"
case_ 2a-display-no-socket $IMG "$RV" -e DISPLAY=:99
case_ 2b-display-wrong-number $IMG "$RV" -e DISPLAY=:0 $X $AW
echo; echo "===== (3) socket mounted, permission"
case_ 3a-socket-no-cookie $IMG "$RV" -e DISPLAY=:99 $X
case_ 3b-socket-cookie-hostname-entry $IMG "$RV" -e DISPLAY=:99 $X $AH
case_ 3c-cookie-hostname-entry-same-hostname $IMG "$RV" -e DISPLAY=:99 $X $AH --hostname rvz-x
case_ 3d-socket-cookie-wildcard $IMG "$RV" -e DISPLAY=:99 $X $AW
echo "[xhost] $(xs 'xhost +local:')"
echo "[xhost state seen by the next connection] $(xs 'xhost' | tr '\n' ' ')"
case_ 3e-socket-no-cookie-xhost-local $IMG "$RV" -e DISPLAY=:99 $X
case_ 3f-rqt-xhost-local $IMG "$RQ" -e DISPLAY=:99 $X
echo "[xhost] $(xs 'xhost -local:')"
echo "[xhost] $(xs 'xhost +si:localuser:root')"
case_ 3h-socket-no-cookie-xhost-si-localuser-root $IMG "$RV" -e DISPLAY=:99 $X
echo "[xhost] $(xs 'xhost -si:localuser:root')"
echo "[xhost] $(xs 'xhost +')"
echo "[xhost state seen by the next connection] $(xs 'xhost' | tr '\n' ' ')"
case_ 3i-socket-no-cookie-xhost-plus $IMG "$RV" -e DISPLAY=:99 $X
echo "[xhost] $(xs 'xhost -')"

echo; echo "===== (6) network / ipc flags (cookie wildcard; socket mounted unless noted)"
case_ 6a-network-none $IMG "$RV" --network none -e DISPLAY=:99 $X $AW
case_ 6b-network-host $IMG "$RV" --network host -e DISPLAY=:99 $X $AW
case_ 6c-no-socket-netns-of-xserver $IMG "$RV" --network container:rvz-x -e DISPLAY=:99 $AW
case_ 6d-ipc-of-xserver $IMG "$RV" --ipc container:rvz-x -e DISPLAY=:99 $X $AW
case_ 6e-QT_X11_NO_MITSHM $IMG "$RV" -e QT_X11_NO_MITSHM=1 -e DISPLAY=:99 $X $AW

echo; echo "===== (5) software GL"
case_ 5a-glxinfo $TOOLS "glxinfo -B 2>&1 | head -16" -e DISPLAY=:99 $X $AW
case_ 5b-glxinfo-LIBGL_ALWAYS_SOFTWARE $TOOLS "glxinfo -B 2>&1 | grep -E 'renderer|direct|version string'" -e LIBGL_ALWAYS_SOFTWARE=1 -e DISPLAY=:99 $X $AW
case_ 5c-rviz2-LIBGL_ALWAYS_SOFTWARE $IMG "$RV" -e LIBGL_ALWAYS_SOFTWARE=1 -e DISPLAY=:99 $X $AW
MESA_DRI='echo removed: $(dpkg-query -W -f="\${Package} " libgl1-mesa-dri mesa-libgallium 2>/dev/null); dpkg --purge --force-depends libgl1-mesa-dri mesa-libgallium >/dev/null 2>&1; echo dri now: $(ls /usr/lib/x86_64-linux-gnu/dri/ 2>/dev/null | wc -l) files;'
case_ 5d-rviz2-no-mesa-dri $IMG "$MESA_DRI $RV" -e DISPLAY=:99 $X $AW
case_ 5e-rviz2-no-mesa-dri-LIBGL_ALWAYS_SOFTWARE $IMG "$MESA_DRI $RV" -e LIBGL_ALWAYS_SOFTWARE=1 -e DISPLAY=:99 $X $AW
case_ 5f-rviz2-no-libglx-mesa0 $IMG 'echo removed: $(dpkg-query -W -f="\${Package} " libglx-mesa0 2>/dev/null); dpkg --purge --force-depends libglx-mesa0 >/dev/null 2>&1; '"$RV" -e DISPLAY=:99 $X $AW
case_ 5g-rqt-no-mesa-dri $IMG "$MESA_DRI $RQ" -e DISPLAY=:99 $X $AW

echo; echo "===== X server without GLX extension"
xserver -auth /auth/host -extension GLX
echo "[xdpyinfo GLX] $(xs 'xdpyinfo' | grep -c GLX)"
case_ 5h-rviz2-server-no-GLX $IMG "$RV" -e DISPLAY=:99 $X $AW
case_ 5i-rqt-server-no-GLX $IMG "$RQ" -e DISPLAY=:99 $X $AW

echo; echo "===== X server with no -auth (like a bare 'Xvfb :99')"
xserver
case_ 3g-noauth-server-no-cookie $IMG "$RV" -e DISPLAY=:99 $X

echo; echo "===== X server with cookie auth and -noreset (server keeps xhost changes after the last client disconnects)"
xserver -auth /auth/host -noreset
echo "[xhost] $(xs 'xhost +local:')"
echo "[xhost state seen by the next connection] $(xs 'xhost' | tr '\n' ' ')"
case_ 3j-noreset-no-cookie-xhost-local $IMG "$RV" -e DISPLAY=:99 $X
case_ 3k-noreset-rqt-xhost-local $IMG "$RQ" -e DISPLAY=:99 $X
echo "[xhost] $(xs 'xhost -local:')"
echo "[xhost] $(xs 'xhost +si:localuser:root')"
case_ 3l-noreset-no-cookie-xhost-si-localuser-root $IMG "$RV" -e DISPLAY=:99 $X
echo "[xhost] $(xs 'xhost -si:localuser:root')"
case_ 3m-noreset-no-cookie-after-xhost-removed $IMG "$RV" -e DISPLAY=:99 $X
docker rm -f rvz-x >/dev/null

echo "[xvfb-run defaults] $(docker run --rm $TOOLS grep -E '^(XVFBARGS|AUTHFILE|SERVERNUM)=' /usr/bin/xvfb-run | tr '\n' ' ')"
echo; echo "===== (4) no external X server: offscreen and xvfb-run"
case_ 4a-QT_QPA_PLATFORM-offscreen $IMG "$RV" -e QT_QPA_PLATFORM=offscreen
case_ 4b-rqt-offscreen $IMG "$RQ" -e QT_QPA_PLATFORM=offscreen
case_ 4c-xvfb-run-default-screen $TOOLS "timeout -k 5 30 xvfb-run -a rviz2; e=\$?; echo \"xvfb-run exit=\$e\"; exit \$e"
case_ 4d-xvfb-run-24bit $TOOLS "timeout -k 5 30 xvfb-run -a -s '-screen 0 1280x1024x24' rviz2; e=\$?; echo \"xvfb-run exit=\$e\"; exit \$e"
case_ 4e-rviz2-in-tools-image-no-display $TOOLS "$RV"
echo; echo "=== done $D $(date -u +%FT%TZ)"; docker ps -a --format '{{.Names}}' | grep rvz- || echo "no rvz- containers"
# Driver used on the runner (one distro at a time, image deleted before the next pull):
#   for D in jazzy lyrical humble; do
#     u=$(df --output=pcent / | tail -1 | tr -dc 0-9); [ "$u" -lt 75 ] || break
#     bash repro.sh $D > out_$D.txt 2>&1
#     docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'osrf/ros|rvz-' >> during.txt
#     docker rmi rvz-tools:$D osrf/ros:$D-desktop
#   done
