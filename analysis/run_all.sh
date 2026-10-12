#!/usr/bin/env bash
# Regenerate every table and figure of the revised manuscript from the public dataset.
set -euo pipefail
DATA=$(cd "${1:?data dir}" && pwd)
mkdir -p "${2:?output dir}" "${3:?figure dir}"
OUT=$(cd "$2" && pwd); FIG=$(cd "$3" && pwd)
cd "$(dirname "$0")"
python3 -I modes2.py "$DATA"                       | tee "$OUT/modes.txt"
python3 -I verify2.py "$DATA"                      | tee "$OUT/controlled_fits.txt"
python3 -I verify3.py "$DATA"                      | tee "$OUT/telemetry_counts.txt"
python3 -I verify4.py "$DATA"                      | tee "$OUT/telemetry_reports.txt"
python3 -I heterogeneity.py "$DATA" "$OUT"         > "$OUT/heterogeneity.txt"
python3 -I fig_hazard.py "$OUT" "$FIG"
python3 -I envelope_controlled.py "$DATA" "$OUT" "$FIG" > "$OUT/envelope.txt"
python3 -I queue_replay.py "$DATA" "$OUT" 300      > "$OUT/replay.txt"
python3 -I fig_replay.py "$OUT" "$FIG"
python3 -I extra_round3.py "$DATA" "$OUT"         > "$OUT/round3.txt"
python3 -I utilisation.py "$DATA" "$OUT"          > "$OUT/utilisation.txt"
python3 -I round4_stats.py "$DATA" "$OUT" 2000 2000 > "$OUT/round4_stats.txt"
python3 -I quiet_benchmark.py "$DATA" "$OUT" 300   > "$OUT/quiet_benchmark.txt"
python3 -I round7.py "$DATA" "$OUT"               > "$OUT/round7.txt"
python3 -I frozen_rule.py "$DATA" "$OUT"          > "$OUT/frozen_rule.txt"     # must reproduce the pre-registered frozen_rule.json (hash printed)
if [ -d "$DATA/measurements/signing/rp2040/validation" ]; then                 # validation blocks (v1.1.0)
  python3 -I validation_blocks.py "$DATA" "$OUT" "$OUT/frozen_rule.json" > "$OUT/validation_blocks.txt"
fi
if [ -f "$DATA/measurements/telemetry/esp32_reports_fresh.csv" ]; then   # fresh-input ESP32 set (v1.1.0)
  python3 -I fresh_esp32.py "$DATA" "$OUT"         > "$OUT/fresh_esp32.txt"
fi
python3 -I hint_path.py "$DATA" "$OUT"            > "$OUT/hint_path.txt"      # hint path from accepted candidates, stage envelope, hint counts
if [ -f "$DATA/raw/rp2040-campaign-randomness.tar.gz" ] && [ -f "$DATA/raw/rp2040-validation-session.tar.gz" ]; then   # randomness streams (v1.1.0)
  RND=$(mktemp -d)
  tar -xzf "$DATA/raw/rp2040-campaign-randomness.tar.gz" -C "$RND"
  tar -xzf "$DATA/raw/rp2040-validation-session.tar.gz" -C "$RND" --wildcards 'results/validation_*/randomness/*'
  python3 -I randomness_check.py "$OUT/randomness_check.csv" "$RND"/results/campaign_*/randomness "$RND"/results/validation_*/randomness > "$OUT/randomness_check.txt"
  rm -rf "$RND"
fi
python3 -I fig_telemetry.py "$DATA" "$FIG"
python3 -I make_figs2.py "$DATA" "$FIG"
echo "done: results in $OUT, figures in $FIG"
