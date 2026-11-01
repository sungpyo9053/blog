#!/bin/bash
# Adds the "at a glance" table figure to published posts that don't have one yet (export skips hl-glance posts).
# usage: scripts/glance_new.sh ko|en [future]   — run daily after the day's publishes (WP host export/insert, runner render+upload)
set -e
L=${1:-ko}; K=~/.ssh/huntlab-lightsail.pem; WP=admin@43.203.28.225; RN=ubuntu@3.35.47.83; T=$(mktemp -d)
cd "$(dirname "$0")/.."
scp -q -i $K scripts/glance_export.php scripts/glance_insert.php $WP:/tmp/
ssh -i $K $WP "cd /var/www/html; sudo -u www-data wp eval-file /tmp/glance_export.php $L ${2:-publish}" > $T/tables.json
n=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" $T/tables.json)
[ "$n" = 0 ] && { echo "nothing new ($L)"; rm -rf $T; exit 0; }
scp -q -i $K $T/tables.json $RN:/tmp/glance_tables.json
scp -q -i $K scripts/make_glance_figures.py $RN:apps/huntlab-blog/scripts/make_glance_figures.py
ssh -i $K $RN 'cd ~/apps/huntlab-blog; PYTHONPATH=. .venv/bin/python scripts/make_glance_figures.py /tmp/glance_tables.json /tmp/glance_out --apply | tail -1; rm -rf /tmp/glance_tables.json /tmp/glance_out' > $T/media.json
scp -q -i $K $T/media.json $WP:/tmp/enfig_media.json
ssh -i $K $WP 'cd /var/www/html; out=$(sudo -u www-data wp eval-file /tmp/glance_insert.php); echo "$out"; sudo -u www-data wp cache-enabler clear --ids=$(echo "$out" | head -1) >/dev/null; rm -f /tmp/enfig_media.json'
rm -rf $T
