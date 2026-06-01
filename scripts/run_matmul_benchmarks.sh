#!/usr/bin/env bash
set -euo pipefail

SIZES="${SIZES:-512 1024 2048}"
THREADS="${THREADS:-1 2 4 8 16}"
TRIALS="${TRIALS:-10}"
TUNE_SAMPLE_SIZE="${TUNE_SAMPLE_SIZE:-512}"
TUNE_TRIALS="${TUNE_TRIALS:-3}"
EFFICIENCY_TOLERANCE="${EFFICIENCY_TOLERANCE:-0.25}"
OUT="${OUT:-results/openmp_scaling.csv}"

max_threads=1
for threads in ${THREADS}; do
    if [ "${threads}" -gt "${max_threads}" ]; then
        max_threads="${threads}"
    fi
done

mkdir -p "$(dirname "${OUT}")"
make

echo "mode,N,threads,trial,time_sec,correct,goal,speedup,efficiency" > "${OUT}"

run_matmul() {
    ./autotuner "$@" --csv
}

append_row() {
    local mode="$1"
    local n="$2"
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

    echo "${mode},${n},${threads},${trial},${time_sec},${correct},${goal},${speedup},${efficiency}" >> "${OUT}"
}

for n in ${SIZES}; do
    declare -A dynamic_threads_by_goal=()

    for goal in performance efficiency; do
        tuning_line="$(run_matmul dynamic "${n}" 0 --tune-goal "${goal}" --tune-sample-size "${TUNE_SAMPLE_SIZE}" --tune-trials "${TUNE_TRIALS}" --max-threads "${max_threads}" --efficiency-tolerance "${EFFICIENCY_TOLERANCE}")"
        dynamic_threads_by_goal["${goal}"]="$(echo "${tuning_line}" | awk -F, '{ print $3 }')"
    done

    for trial in $(seq 1 "${TRIALS}"); do
        serial_time=""

        for threads in ${THREADS}; do
            static_line="$(run_matmul static "${n}" "${threads}")"
            static_threads="$(echo "${static_line}" | awk -F, '{ print $3 }')"
            static_time="$(echo "${static_line}" | awk -F, '{ print $4 }')"
            static_correct="$(echo "${static_line}" | awk -F, '{ print $5 }')"

            if [[ "${threads}" == "1" ]]; then
                serial_time="${static_time}"
            fi

            if [[ -z "${serial_time}" ]]; then
                echo "Error: serial_time is not set for length ${length}. Ensure that the first run captures serial_time correctly."
                exit 1
            fi
            
            append_row "static" "${n}" "${static_threads}" "${trial}" "${static_time}" "${static_correct}" "fixed" "${serial_time}"
        done

        for goal in performance efficiency; do
            dynamic_threads="${dynamic_threads_by_goal[${goal}]}"
            dynamic_line="$(run_matmul dynamic "${n}" "${dynamic_threads}")"
            dynamic_time="$(echo "${dynamic_line}" | awk -F, '{ print $4 }')"
            dynamic_correct="$(echo "${dynamic_line}" | awk -F, '{ print $5 }')"
            append_row "dynamic" "${n}" "${dynamic_threads}" "${trial}" "${dynamic_time}" "${dynamic_correct}" "${goal}" "${serial_time}"
        done
    done
done

echo "Wrote ${OUT}"
