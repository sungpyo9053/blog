#!/usr/bin/env bash
# Which local LLM sizes run under a fixed RAM cap? Ollama (CPU only) in a container with
# memory cap and swap disabled (--memory-swap == --memory), same method as ../colcon-ram-*.
# Run on a throwaway 4 vCPU / 16 GB host. Peak = container cgroup memory.peak (includes mmap'd weights).
# Output: results.tsv (model, mem_limit, try, ok, error, peak_bytes, oom_kills, load_s, eval_count, tok_per_s)
#         env.txt (image digest, model digests, host cpu/mem)
set -uo pipefail
cd "$(dirname "$0")"
MODELS="${MODELS:-qwen2.5:3b qwen2.5:7b qwen2.5:14b}"
CAPS="${CAPS:-4g 8g 16g}"
PROMPT="Explain in about 100 words why a robot arm needs inverse kinematics."

docker pull -q ollama/ollama:latest
docker volume create ollama-models >/dev/null
docker run -d --name pull -v ollama-models:/root/.ollama ollama/ollama:latest >/dev/null; sleep 5
for m in $MODELS; do docker exec pull ollama pull "$m" >/dev/null 2>&1; done
{ docker image inspect ollama/ollama:latest --format '{{index .RepoDigests 0}}'
  docker exec pull ollama --version
  docker exec pull ollama list
  nproc; free -b | awk '/Mem:/{print $2}'; uname -r; } > env.txt
docker rm -f pull >/dev/null

printf 'model\tmem_limit\ttry\tok\terror\tpeak_bytes\toom_kills\tload_s\teval_count\ttok_per_s\n' > results.tsv
for cap in $CAPS; do for m in $MODELS; do
  docker run -d --name llm -m "$cap" --memory-swap "$cap" --cpus 4 -p 127.0.0.1:11434:11434 -v ollama-models:/root/.ollama ollama/ollama:latest >/dev/null
  for i in $(seq 30); do curl -sf localhost:11434/api/version >/dev/null && break; sleep 1; done
  for try in 1 2 3; do
    body=$(python3 -c 'import json,sys;print(json.dumps({"model":sys.argv[1],"prompt":sys.argv[2],"stream":False,"options":{"num_predict":128,"temperature":0,"seed":0}}))' "$m" "$PROMPT")
    resp=$(curl -s -m 900 localhost:11434/api/generate -d "$body" || true)
    [ -z "$resp" ] && resp='{"error":"no response (server died?)"}'
    peak=$(docker exec llm cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo NA)
    oom=$(docker exec llm awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events 2>/dev/null || echo NA)
    [ "$peak" = NA ] && { oom=$(docker inspect llm --format '{{.State.OOMKilled}}'); }
    python3 - "$m" "$cap" "$try" "$peak" "$oom" "$resp" >> results.tsv <<'PY'
import json,sys
m,cap,t,peak,oom,resp=sys.argv[1:]
try: r=json.loads(resp)
except Exception: r={"error":resp[:200]}
err=(r.get("error") or "").replace("\t"," ").replace("\n"," ")[:200]
ok=0 if err else 1
ld=r.get("load_duration",0)/1e9; ec=r.get("eval_count",0); ed=r.get("eval_duration",0)
tps=round(ec/(ed/1e9),2) if ed else 0
print("\t".join(map(str,[m,cap,t,ok,err or "-",peak,oom,round(ld,2),ec,tps])))
PY
  done
  docker logs llm > "log-${m//[:.]/_}-$cap.txt" 2>&1
  docker rm -f llm >/dev/null
done; done
echo done > DONE
