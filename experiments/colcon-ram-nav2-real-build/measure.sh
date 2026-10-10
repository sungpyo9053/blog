#!/usr/bin/env bash
# Peak RAM of a real colcon build (Nav2, Jazzy) under fixed container memory caps.
# Complements ../colcon-build-executor-sequential-memory-budget (synthetic, mechanism only)
# with real-package numbers. Run on a throwaway 4 vCPU / 16 GB host. Swap is disabled per run
# (--memory-swap == --memory) so "fits" means fits in RAM.
# Output: results.tsv (label, mem_limit, workers, makeflags, exit, oom_kills, peak_bytes, wall_s)
#         env.txt (image digest, nav2 commit, host cpu/mem)
set -uo pipefail
cd "$(dirname "$0")"

docker pull -q ros:jazzy
docker build -q -t colcon-ram-nav2 - <<'EOF'
FROM ros:jazzy
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /ws
RUN git clone --depth 1 -b jazzy https://github.com/ros-navigation/navigation2.git src/navigation2 \
 && git -C src/navigation2 rev-parse HEAD > /ws/nav2_commit.txt
RUN apt-get update && rosdep update --rosdistro jazzy \
 && rosdep install -y --from-paths src --ignore-src --rosdistro jazzy \
 && rm -rf /var/lib/apt/lists/*
EOF
{ docker image inspect ros:jazzy --format '{{index .RepoDigests 0}}'
  docker run --rm colcon-ram-nav2 cat /ws/nav2_commit.txt
  nproc; free -b | awk '/Mem:/{print $2}'; uname -r; } > env.txt

printf 'label\tmem_limit\tworkers\tmakeflags\texit\toom_kills\tpeak_bytes\twall_s\n' > results.tsv

run() {  # label mem workers makeflags
  local label=$1 mem=$2 workers=$3 mk=$4 start
  start=$(date +%s)
  docker run --rm -m "$mem" --memory-swap "$mem" --cpus 4 \
    -e MK="$mk" -e WORKERS="$workers" colcon-ram-nav2 bash -c '
      source /opt/ros/jazzy/setup.bash
      args=(); [ "$WORKERS" != default ] && args=(--parallel-workers "$WORKERS")
      [ -n "$MK" ] && export MAKEFLAGS="$MK"
      colcon build --event-handlers console_direct- "${args[@]}" > /tmp/build.log 2>&1; rc=$?
      grep -m3 -iE "killed signal|out of memory|cannot allocate" /tmp/build.log >&2
      tail -5 /tmp/build.log >&2
      oom=$(awk "/^oom_kill /{print \$2}" /sys/fs/cgroup/memory.events)
      echo "RESULT $rc $oom $(cat /sys/fs/cgroup/memory.peak)"
    ' 2> "log-$label.txt" | grep '^RESULT' | {
      read -r _ rc oom peak
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$label" "$mem" "$workers" "${mk:-default}" \
        "$rc" "$oom" "$peak" "$(( $(date +%s) - start ))" >> results.tsv
    }
}

# Default colcon behaviour (workers = nproc, make -j nproc) is what readers actually run.
run default-16g 16g default ""
run default-8g  8g  default ""
run default-4g  4g  default ""
# The usual advice for low-RAM machines.
run seq-16g     16g 1       "-j1"
run seq-4g      4g  1       "-j1"
echo done > DONE
