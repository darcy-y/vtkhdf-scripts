#!/usr/bin/env bash
# @ Author      :  darcy-y
# @ Time        :  2026-04-07 15:50:00
# @ Description :  convert all vtu files in input/case_* dir to output/case_*.vtkhdf (specify input and output dir as args)

set -euo pipefail

BASE_INPUT_DIR="${1:-input}"
BASE_OUTPUT_DIR="${2:-output}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CONVERTER="$REPO_ROOT/converters/vtu_series_to_vtkhdf.py"
ADD_JSON="$REPO_ROOT/tools/add_json_to_hdf.py"

DT="${DT:-0.1}"
T0="${T0:-0.1}"
TIME_MODE="${TIME_MODE:-index}"

mkdir -p "$BASE_OUTPUT_DIR"

for case_dir in "$BASE_INPUT_DIR"/case_*; do
    [ -d "$case_dir" ] || continue

    case_name="$(basename "$case_dir")"
    dump_pattern="$case_dir/dump/particle/dump_*.vtu"
    output_file="$BASE_OUTPUT_DIR/${case_name}.vtkhdf"

    # ignore dir without vtu files
    shopt -s nullglob
    files=( $dump_pattern )
    shopt -u nullglob

    if [ ${#files[@]} -eq 0 ]; then
        echo "[SKIP] No VTU files found for $case_name"
        continue
    fi

    echo "[RUN ] $case_name -> $output_file"

    # do convertion
    python3 "$CONVERTER" \
        --input "$dump_pattern" \
        --output "$output_file" \
        --dt "$DT" \
        --t0 "$T0" \
        --time-mode "$TIME_MODE"

    # add json to vtkhdf
    python3 "$ADD_JSON" --vtkhdf-path "$output_file" --json-path "$case_dir/${case_name}.json"

    echo "[DONE] $case_name"
done
