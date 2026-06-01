#!/usr/bin/env bash
set -euo pipefail

LENGTH="${LENGTH:-6}"
CHARSET="${CHARSET:-abcdefghjklmnopqrstuvwxyz}"
TARGET="${TARGET:-pokemo}"
THREADS="${THREADS:-1 2 4 8 16}"
MAX_THREADS="${MAX_THREADS:-16}"
TRIALS="${TRIALS:-5}"
TUNE_SAMPLE_SIZE="${TUNE_SAMPLE_SIZE:-5}"
TUNE_TRIALS="${TUNE_TRIALS:-3}"
EFFICIENCY_TOLERANCE="${EFFICIENCY_TOLERANCE:-0.25}"
OUT="${OUT:-results/password_crack.csv}"

mkdir -p "$(dirname "${OUT}")"
make

echo "mode,length,threads,trial,time_sec,correct,goal,speedup,efficiency" > "${OUT}"

run_case() {
    ./autotuner "$@" --workload password --charset "${CHARSET}" --password-target "${TARGET}" --csv
}

append_row() {
    local mode="$1"
    local length="$2"
    local threads="$3"
    local trial="$4"
    local time_sec="$5"
    local correct="$6"
    local goal="$7"
    local serial_time="$8"

    local speedup
    local efficiency

    speedup="$(awk -v s="${serial_time}" -v p="${time_sec}" 'BEGIN { if (p > 0) printf "%.6f", s / p; else printf "0.000000" }')"
    efficiency="$(awk -v sp="${speedup}" -v th="${threads}" 'BEGIN { if (th > 0) printf "%.6f", sp / th; else printf "0.000000" }')"

    echo "${mode},${length},${threads},${trial},${time_sec},${correct},${goal},${speedup},${efficiency}" >> "${OUT}"
}

for length in ${LENGTH}; do
    declare -A dynamic_threads_by_goal=()

    # --- Pre-tune for both goals ---
    for goal in performance efficiency; do
        tuning_line="$(run_case dynamic "${length}" 0 --tune-goal "${goal}" --tune-sample-size "${TUNE_SAMPLE_SIZE}" --tune-trials "${TUNE_TRIALS}" --max-threads "${MAX_THREADS}" --efficiency-tolerance "${EFFICIENCY_TOLERANCE}")"
        dynamic_threads_by_goal["${goal}"]="$(echo "${tuning_line}" | awk -F, '{ print $3 }')"
    done

    for trial in $(seq 1 "${TRIALS}"); do
        # --- Serial baseline ---
        serial_line="$(run_case sequential "${length}" 1)"
        serial_time="$(echo "${serial_line}" | awk -F, '{ print $4 }')"
        serial_correct="$(echo "${serial_line}" | awk -F, '{ print $5 }')"

        append_row "sequential" "${length}" 1 "${trial}" "${serial_time}" "${serial_correct}" "baseline" "${serial_time}"

        # --- Static runs ---
        for threads in ${THREADS}; do
            static_line="$(run_case static "${length}" "${threads}")"
            static_threads="$(echo "${static_line}" | awk -F, '{ print $3 }')"
            static_time="$(echo "${static_line}" | awk -F, '{ print $4 }')"
            static_correct="$(echo "${static_line}" | awk -F, '{ print $5 }')"

            append_row "static" "${length}" "${static_threads}" "${trial}" "${static_time}" "${static_correct}" "fixed" "${serial_time}"
        done

        # --- Dynamic runs (apply tuned thread counts) ---
        for goal in performance efficiency; do
            dynamic_threads="${dynamic_threads_by_goal[${goal}]}"

            dynamic_line="$(run_case optimized "${length}" "${dynamic_threads}")"
            dynamic_time="$(echo "${dynamic_line}" | awk -F, '{ print $4 }')"
            dynamic_correct="$(echo "${dynamic_line}" | awk -F, '{ print $5 }')"

            append_row "dynamic" "${length}" "${dynamic_threads}" "${trial}" "${dynamic_time}" "${dynamic_correct}" "${goal}" "${serial_time}"
        done
    done
done

echo "Wrote ${OUT}"