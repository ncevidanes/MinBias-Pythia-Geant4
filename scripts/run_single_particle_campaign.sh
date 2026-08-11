#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="${project_dir}/config/single_particle.conf"
output_dir="${project_dir}/outputs/cycle6-stage63d"
build_jobs="${BUILD_JOBS:-2}"
dry_run=false

usage() {
  cat <<'EOF'
Uso:
  ./scripts/run_single_particle_campaign.sh [opções]

Opções:
  --dry-run             valida build, testes e as nove configurações;
                        não executa o transporte nem cria ROOTs
  --output-dir CAMINHO  diretório da campanha
                        (padrão: outputs/cycle6-stage63d)
  --build-jobs N        paralelismo da compilação (padrão: BUILD_JOBS ou 2)
  -h, --help            mostra esta ajuda

A matriz científica é fixa: elétron, fóton e píon positivo em 1, 10 e
100 GeV, com 100 eventos, uma thread, eta = phi = 0 e sementes registradas.
EOF
}

fail() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

require_positive_integer() {
  local name="$1"
  local value="$2"
  [[ "$value" =~ ^[1-9][0-9]*$ ]] ||
    fail "${name} deve ser um inteiro positivo; recebido: ${value}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || fail "--output-dir exige um caminho"
      output_dir="$2"
      shift 2
      ;;
    --build-jobs)
      [[ $# -ge 2 ]] || fail "--build-jobs exige um valor"
      build_jobs="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "opção desconhecida: $1"
      ;;
  esac
done

require_positive_integer "--build-jobs" "$build_jobs"

if [[ "$output_dir" != /* ]]; then
  output_dir="${project_dir}/${output_dir}"
fi

for command_name in \
  cmake cmp ctest cut git grep mktemp mv python3 sha256sum tee; do
  command -v "$command_name" >/dev/null 2>&1 ||
    fail "comando obrigatório não encontrado: ${command_name}"
done

[[ -s "$config_file" ]] || fail "configuração ausente: ${config_file}"
[[ -x "${project_dir}/run.sh" ]] || fail "run.sh não é executável"

cd "$project_dir"

if [[ "$dry_run" == false ]]; then
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    fail "a campanha deve ser executada dentro do repositório Git"
  git diff --quiet ||
    fail "há alterações rastreadas não preparadas; faça commit antes da campanha"
  git diff --cached --quiet ||
    fail "há alterações preparadas; faça commit antes da campanha"
fi

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "$build_jobs"
ctest --test-dir build --output-on-failure

[[ -x build/single_particle_analyzer ]] ||
  fail "build/single_particle_analyzer não foi produzido"

campaign=(
  "electron|11|1|631001"
  "electron|11|10|631002"
  "electron|11|100|631003"
  "photon|22|1|632001"
  "photon|22|10|632002"
  "photon|22|100|632003"
  "pion_plus|211|1|633001"
  "pion_plus|211|10|633002"
  "pion_plus|211|100|633003"
)

temporary_dir="$(mktemp -d /tmp/minbias-stage63d.XXXXXX)"
cleanup() {
  case "$temporary_dir" in
    /tmp/minbias-stage63d.*)
      rm -rf -- "$temporary_dir"
      ;;
  esac
}
trap cleanup EXIT

run_arguments() {
  local pdg="$1"
  local energy="$2"
  local seed="$3"
  local root_file="$4"

  printf '%s\0' \
    --events 100 \
    --threads 1 \
    --seed "$seed" \
    --particle-pdg "$pdg" \
    --particle-kinetic-energy-gev "$energy" \
    --particle-eta 0 \
    --particle-phi 0 \
    --output "$root_file"
}

if [[ "$dry_run" == true ]]; then
  for entry in "${campaign[@]}"; do
    IFS='|' read -r particle pdg energy seed <<<"$entry"
    run_name="${particle}_${energy}gev"
    root_file="${output_dir}/${run_name}.root"
    log_file="${temporary_dir}/${run_name}.log"
    mapfile -d '' -t arguments < <(
      run_arguments "$pdg" "$energy" "$seed" "$root_file"
    )

    BUILD_JOBS="$build_jobs" ./run.sh "$config_file" \
      "${arguments[@]}" --dry-run >"$log_file" 2>&1

    grep -Fqx 'generator_mode = single_particle' "$log_file"
    grep -Fqx 'events = 100' "$log_file"
    grep -Fqx 'threads = 1' "$log_file"
    grep -Fqx "seed_base = ${seed}" "$log_file"
    grep -Fqx 'physics_list = FTFP_BERT_ATL' "$log_file"
    grep -Eq '^production_cut_mm = 1([.]0*)?$' "$log_file"
    grep -Fqx "single_particle_pdg = ${pdg}" "$log_file"
    grep -Fqx \
      "single_particle_kinetic_energy_gev = ${energy}" "$log_file"
    grep -Fqx 'single_particle_eta = 0' "$log_file"
    grep -Fqx 'single_particle_phi = 0' "$log_file"

    printf 'PREFLIGHT_CASE=PASS run=%s pdg=%s energy_gev=%s seed=%s\n' \
      "$run_name" "$pdg" "$energy" "$seed"
  done

  printf 'CAMPAIGN_PREFLIGHT=PASS cases=%d events_per_case=100\n' \
    "${#campaign[@]}"
  exit 0
fi

mkdir -p "$output_dir"

campaign_summary="${output_dir}/campaign_summary.csv"
campaign_manifest="${output_dir}/campaign_manifest.tsv"
campaign_validation="${output_dir}/campaign_validation.txt"

for final_file in \
  "$campaign_summary" "$campaign_manifest" "$campaign_validation"; do
  [[ ! -e "$final_file" ]] ||
    fail "a saída já existe; preserve-a e escolha --output-dir: ${final_file}"
done

for entry in "${campaign[@]}"; do
  IFS='|' read -r particle pdg energy seed <<<"$entry"
  run_name="${particle}_${energy}gev"
  for suffix in \
    root root.manifest.txt summary.csv samplings.csv simulation.log analysis.log; do
    candidate="${output_dir}/${run_name}.${suffix}"
    [[ ! -e "$candidate" ]] ||
      fail "a saída já existe; preserve-a e escolha --output-dir: ${candidate}"
  done
done

git_commit="$(git rev-parse HEAD)"
manifest_tmp="${temporary_dir}/campaign_manifest.tsv"
summary_tmp="${temporary_dir}/campaign_summary.csv"
validation_tmp="${temporary_dir}/campaign_validation.txt"

printf '%s\n' \
  $'run\tparticle\tpdg\tkinetic_energy_gev\tevents\tseed\troot_sha256\tgit_commit' \
  >"$manifest_tmp"

summary_files=()

for entry in "${campaign[@]}"; do
  IFS='|' read -r particle pdg energy seed <<<"$entry"
  run_name="${particle}_${energy}gev"
  root_file="${output_dir}/${run_name}.root"
  summary_file="${output_dir}/${run_name}.summary.csv"
  sampling_file="${output_dir}/${run_name}.samplings.csv"
  simulation_log="${output_dir}/${run_name}.simulation.log"
  analysis_log="${output_dir}/${run_name}.analysis.log"
  repeated_summary="${temporary_dir}/${run_name}.summary.csv"
  repeated_sampling="${temporary_dir}/${run_name}.samplings.csv"
  repeated_log="${temporary_dir}/${run_name}.analysis.log"
  mapfile -d '' -t arguments < <(
    run_arguments "$pdg" "$energy" "$seed" "$root_file"
  )

  printf 'CAMPAIGN_CASE=START run=%s\n' "$run_name"
  BUILD_JOBS="$build_jobs" ./run.sh "$config_file" \
    "${arguments[@]}" 2>&1 | tee "$simulation_log"

  [[ -s "$root_file" ]] || fail "ROOT ausente ou vazio: ${root_file}"
  [[ -s "${root_file}.manifest.txt" ]] ||
    fail "manifesto ausente ou vazio: ${root_file}.manifest.txt"

  root_hash_before="$(sha256sum "$root_file" | cut -d' ' -f1)"

  build/single_particle_analyzer \
    --input "$root_file" \
    --summary-csv "$summary_file" \
    --sampling-csv "$sampling_file" \
    2>&1 | tee "$analysis_log"
  grep -Fqx 'ANALYSIS_RESULT=PASS' "$analysis_log"

  build/single_particle_analyzer \
    --input "$root_file" \
    --summary-csv "$repeated_summary" \
    --sampling-csv "$repeated_sampling" \
    >"$repeated_log" 2>&1
  grep -Fqx 'ANALYSIS_RESULT=PASS' "$repeated_log"

  cmp -s "$summary_file" "$repeated_summary" ||
    fail "resumo não determinístico: ${run_name}"
  cmp -s "$sampling_file" "$repeated_sampling" ||
    fail "CSV por sampling não determinístico: ${run_name}"

  root_hash_after="$(sha256sum "$root_file" | cut -d' ' -f1)"
  [[ "$root_hash_after" == "$root_hash_before" ]] ||
    fail "o analisador modificou o ROOT: ${run_name}"

  python3 - "$summary_file" "$sampling_file" \
    "$pdg" "$energy" <<'PY'
import csv
import math
import sys

summary_path, sampling_path, expected_pdg, expected_energy = sys.argv[1:]

with open(summary_path, newline="", encoding="utf-8") as stream:
    summary_rows = list(csv.DictReader(stream))
if len(summary_rows) != 1:
    raise SystemExit(f"expected one summary row in {summary_path}")
row = summary_rows[0]

if row["generator_mode"] != "single_particle":
    raise SystemExit("unexpected generator_mode")
if int(row["single_particle_pdg"]) != int(expected_pdg):
    raise SystemExit("unexpected particle PDG")
if not math.isclose(
    float(row["single_particle_kinetic_energy_gev"]),
    float(expected_energy),
    rel_tol=0.0,
    abs_tol=1.0e-12,
):
    raise SystemExit("unexpected kinetic energy")
if float(row["single_particle_eta"]) != 0.0:
    raise SystemExit("unexpected eta")
if float(row["single_particle_phi"]) != 0.0:
    raise SystemExit("unexpected phi")
if int(row["event_count"]) != 100:
    raise SystemExit("unexpected event_count")
if int(row["hit_count"]) <= 0:
    raise SystemExit("hit_count must be positive")

numeric_summary = (
    "mean_energy_mev",
    "sample_stddev_energy_mev",
    "mean_response",
    "relative_resolution",
    "sampling_centroid",
    "sampling_width",
    "eta_width",
    "phi_width",
)
for field in numeric_summary:
    value = float(row[field])
    if not math.isfinite(value):
        raise SystemExit(f"non-finite summary field: {field}")
if float(row["mean_energy_mev"]) <= 0.0:
    raise SystemExit("mean_energy_mev must be positive")
if float(row["mean_response"]) <= 0.0:
    raise SystemExit("mean_response must be positive")
if float(row["sample_stddev_energy_mev"]) < 0.0:
    raise SystemExit("sample stddev must be non-negative")
if float(row["relative_resolution"]) < 0.0:
    raise SystemExit("relative resolution must be non-negative")

with open(sampling_path, newline="", encoding="utf-8") as stream:
    sampling_rows = list(csv.DictReader(stream))
expected_names = (
    "PSB", "EMB1", "EMB2", "EMB3", "TileCal1",
    "TileCal2", "TileCal3", "TileExt1", "TileExt2", "TileExt3",
)
if len(sampling_rows) != len(expected_names):
    raise SystemExit("expected exactly ten sampling rows")
for index, (sampling, name) in enumerate(zip(sampling_rows, expected_names)):
    if int(sampling["sampling"]) != index or sampling["name"] != name:
        raise SystemExit(f"unexpected sampling row at index {index}")
    for field in (
        "mean_energy_mev",
        "sample_stddev_energy_mev",
        "total_energy_fraction",
        "eta_width",
        "phi_width",
    ):
        if not math.isfinite(float(sampling[field])):
            raise SystemExit(f"non-finite sampling field: {field}")
PY

  printf '%s\t%s\t%s\t%s\t100\t%s\t%s\t%s\n' \
    "$run_name" "$particle" "$pdg" "$energy" "$seed" \
    "$root_hash_before" "$git_commit" >>"$manifest_tmp"
  summary_files+=("$summary_file")
  printf 'CAMPAIGN_CASE=PASS run=%s root_sha256=%s\n' \
    "$run_name" "$root_hash_before"
done

python3 - "$summary_tmp" "$validation_tmp" \
  "${summary_files[@]}" <<'PY'
import csv
import math
import sys

summary_output = sys.argv[1]
validation_output = sys.argv[2]
input_paths = sys.argv[3:]

rows = []
fieldnames = None
for path in input_paths:
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        current_rows = list(reader)
        if len(current_rows) != 1:
            raise SystemExit(f"expected one row in {path}")
        if fieldnames is None:
            fieldnames = reader.fieldnames
        elif reader.fieldnames != fieldnames:
            raise SystemExit(f"inconsistent CSV header in {path}")
        rows.extend(current_rows)

if len(rows) != 9 or fieldnames is None:
    raise SystemExit("campaign must contain exactly nine summaries")

with open(summary_output, "w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

groups = {}
for row in rows:
    pdg = int(row["single_particle_pdg"])
    energy = float(row["single_particle_kinetic_energy_gev"])
    deposit = float(row["mean_energy_mev"])
    if not math.isfinite(deposit) or deposit <= 0.0:
        raise SystemExit("campaign contains an invalid mean deposit")
    groups.setdefault(pdg, []).append((energy, deposit))

for pdg in (11, 22, 211):
    points = sorted(groups.get(pdg, ()))
    if [energy for energy, _ in points] != [1.0, 10.0, 100.0]:
        raise SystemExit(f"incomplete energy matrix for PDG {pdg}")
    deposits = [deposit for _, deposit in points]
    if not deposits[0] < deposits[1] < deposits[2]:
        raise SystemExit(f"mean deposit is not increasing for PDG {pdg}")

with open(validation_output, "w", encoding="utf-8", newline="\n") as stream:
    stream.write("CAMPAIGN_RESULT=PASS\n")
    stream.write("cases=9\n")
    stream.write("events_per_case=100\n")
    stream.write("sampling_rows_per_case=10\n")
    stream.write("repeat_analysis=byte_identical\n")
    stream.write("root_hash=unchanged\n")
    stream.write("mean_deposit_monotonic_by_particle=true\n")
PY

mv -- "$manifest_tmp" "$campaign_manifest"
mv -- "$summary_tmp" "$campaign_summary"
mv -- "$validation_tmp" "$campaign_validation"

printf 'CAMPAIGN_RESULT=PASS cases=9 events_per_case=100\n'
printf 'CAMPAIGN_OUTPUT_DIR=%s\n' "$output_dir"
