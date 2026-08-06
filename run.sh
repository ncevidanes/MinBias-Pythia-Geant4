#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_file="${1:-config/smoke.conf}"

if [[ $# -gt 0 ]]; then
  shift
fi

if [[ "${config_file}" != /* ]]; then
  config_file="${project_dir}/${config_file}"
fi

if ! command -v pythia8-config >/dev/null 2>&1; then
  echo "Erro: pythia8-config não foi encontrado no PATH." >&2
  echo "Ative primeiro o ambiente que contém o PYTHIA 8." >&2
  exit 2
fi

if [[ -z "${Geant4_DIR:-}" ]] && ! command -v geant4-config >/dev/null 2>&1; then
  echo "Aviso: Geant4_DIR e geant4-config não foram encontrados." >&2
  echo "O CMake ainda tentará localizar o Geant4 via CMAKE_PREFIX_PATH." >&2
fi

python3 "${project_dir}/scripts/validate_project.py" "${config_file}"

cmake \
  -S "${project_dir}" \
  -B "${project_dir}/build" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build "${project_dir}/build" --parallel "${BUILD_JOBS:-2}"

cd "${project_dir}"
exec "${project_dir}/build/pythia_geant" --config "${config_file}" "$@"

