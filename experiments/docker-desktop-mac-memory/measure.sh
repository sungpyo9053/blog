#!/bin/bash
# Docker Desktop (macOS) host memory: how much the Mac pays per container, and whether it comes back.
# Leaves non-test containers alone. Test containers are prefixed ddm-.
set -u
OUT=${OUT:-results}; REPEATS=${REPEATS:-3}; HOG_MB=${HOG_MB:-1500}
mkdir -p "$OUT"; TSV="$OUT/results.tsv"
[ -f "$TSV" ] || printf 'run\tstep\tts\thost_docker_rss_mib\tvm_used_mib\tvm_total_mib\tmac_free_pct\tcontainers_mib\n' > "$TSV"
host_rss() { ps -axo rss,comm | grep -E 'Docker.app|Virtualization.VirtualMachine' | grep -v grep | awk '{s+=$1} END {printf "%.0f", s/1024}'; }
vm_mem() { docker run --rm --name ddm-probe redis:7-alpine free -m | awk '/Mem:/ {print $3"\t"$2}'; }
mac_free() { memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}'; }
ctr_mem() { ids=$(docker ps -q --filter name=ddm-); [ -n "$ids" ] && docker stats --no-stream --format '{{.Name}}={{.MemUsage}}' $ids | tr '\n' ' '; }
rec() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$(date +%H:%M:%S)" "$(host_rss)" "$(vm_mem)" "$(mac_free)" "$(ctr_mem)" >> "$TSV"; }
cleanup() { docker rm -f $(docker ps -aq --filter name=ddm-) >/dev/null 2>&1; }
trap cleanup EXIT
{ date; sw_vers; sysctl -n hw.model hw.memsize hw.ncpu; defaults read /Applications/Docker.app/Contents/Info.plist CFBundleShortVersionString;
  docker info --format 'engine={{.ServerVersion}} vm_mem={{.MemTotal}} vm_cpus={{.NCPU}} kernel={{.KernelVersion}}';
  echo "other containers running (names withheld): $(docker ps -q | wc -l | tr -d ' ')"; docker image inspect --format '{{.RepoTags}} {{.Id}}' postgres:16 redis:7-alpine node:22-alpine; } > "$OUT/env.txt" 2>&1
for r in $(seq 1 "$REPEATS"); do
  cleanup; sleep 60; rec "$r" 0-baseline
  docker run -d --name ddm-pg -e POSTGRES_PASSWORD=x postgres:16 >/dev/null
  docker run -d --name ddm-redis redis:7-alpine >/dev/null
  docker run -d --name ddm-node node:22-alpine node -e 'require("http").createServer((q,s)=>s.end("ok")).listen(3000)' >/dev/null
  sleep 60; rec "$r" 1-pg-redis-node
  docker run -d --name ddm-hog redis:7-alpine sh -c "head -c ${HOG_MB}m /dev/zero | tail; sleep 3600" >/dev/null
  sleep 40; rec "$r" 2-hog-${HOG_MB}m
  docker rm -f ddm-hog >/dev/null; sleep 60; rec "$r" 3-hog-removed-60s
  sleep 120; rec "$r" 4-hog-removed-180s
  cleanup; sleep 120; rec "$r" 5-all-removed-120s
done
date > "$OUT/DONE"
