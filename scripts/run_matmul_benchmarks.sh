#!/usr/bin/env bash
set -euo pipefail

SIZES="${SIZES:-1024}"
THREADS="${THREADS:-1 2 4 8 16}"
TRIALS="${TRIALS:-3}"
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

echo "mode,N,threads,trial,time_sec,correct,goal" > "${OUT}"

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

    echo "${mode},${n},${threads},${trial},${time_sec},${correct},${goal}" >> "${OUT}"
}

for n in ${SIZES}; do
    declare -A dynamic_threads_by_goal=()

    for goal in performance efficiency; do
        tuning_line="$(run_matmul dynamic "${n}" 0 --tune-goal "${goal}" --tune-sample-size "${TUNE_SAMPLE_SIZE}" --tune-trials "${TUNE_TRIALS}" --max-threads "${max_threads}" --efficiency-tolerance "${EFFICIENCY_TOLERANCE}")"
        dynamic_threads_by_goal["${goal}"]="$(echo "${tuning_line}" | awk -F, '{ print $3 }')"
    done

    for trial in $(seq 1 "${TRIALS}"); do
        for threads in ${THREADS}; do
            static_line="$(run_matmul static "${n}" "${threads}")"
            static_threads="$(echo "${static_line}" | awk -F, '{ print $3 }')"
            static_time="$(echo "${static_line}" | awk -F, '{ print $4 }')"
            static_correct="$(echo "${static_line}" | awk -F, '{ print $5 }')"

            append_row "static" "${n}" "${static_threads}" "${trial}" "${static_time}" "${static_correct}" "fixed"
        done

        for goal in performance efficiency; do
            dynamic_threads="${dynamic_threads_by_goal[${goal}]}"
            dynamic_line="$(run_matmul dynamic "${n}" "${dynamic_threads}")"
            dynamic_time="$(echo "${dynamic_line}" | awk -F, '{ print $4 }')"
            dynamic_correct="$(echo "${dynamic_line}" | awk -F, '{ print $5 }')"
            append_row "dynamic" "${n}" "${dynamic_threads}" "${trial}" "${dynamic_time}" "${dynamic_correct}" "${goal}"
        done
    done
done

echo "Wrote ${OUT}"
