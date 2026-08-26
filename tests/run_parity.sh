#!/bin/bash
# Byte-level parity check: original R engines vs the Python port.
# Requires: Rscript (tidyverse, readxl), python3 (openpyxl), and the two
# course data directories (defaults point at the repo's Ellis copies).
set -euo pipefail
cd "$(dirname "$0")"

INTRO_DATA="${1:-../courses/university-of-iowa/intro-to-rmi/ellis/data}"
LH_DATA="${2:-../courses/university-of-iowa/life-health/ellis/data}"

rm -rf out_r out_py
Rscript parity_test.R out_r reference "$INTRO_DATA" "$LH_DATA"
python3 parity_test.py out_py "$INTRO_DATA" "$LH_DATA"

# The intro engine embeds the output path after \end{document} (mirroring the
# R source's stray `file = file` inside c(...)); normalize it before diffing.
fail=0
for f in out_r/*.tex; do
  name="$(basename "$f")"
  if ! diff <(sed "s| out_r/| OUT/|" "out_r/$name") \
            <(sed "s| out_py/| OUT/|" "out_py/$name") > "/tmp/parity_diff_$name.txt" 2>&1; then
    echo "MISMATCH: $name (see /tmp/parity_diff_$name.txt)"
    fail=1
  else
    echo "match:    $name"
  fi
done
exit $fail
