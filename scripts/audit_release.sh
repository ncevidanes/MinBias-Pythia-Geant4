#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: comando obrigatório não encontrado: $1" >&2
    exit 2
  fi
}

for command in git python3 cmake ctest c++ pythia8-config root root-config tar cmp; do
  require_command "${command}"
done

if ! git -C "${project_dir}" diff --quiet ||
   ! git -C "${project_dir}" diff --cached --quiet; then
  echo "Erro: a auditoria A4 exige uma árvore rastreada limpa." >&2
  echo "Faça o commit candidato antes de executá-la." >&2
  exit 2
fi

commit="$(git -C "${project_dir}" rev-parse HEAD)"
describe="$(git -C "${project_dir}" describe --always --dirty --tags)"
if [[ "${describe}" == *dirty* ]]; then
  echo "Erro: git describe indica árvore suja: ${describe}" >&2
  exit 2
fi
if git -C "${project_dir}" show-ref --verify --quiet \
    refs/remotes/origin/master; then
  remote_commit="$(git -C "${project_dir}" rev-parse origin/master)"
  if [[ "${commit}" != "${remote_commit}" ]]; then
    echo "Erro: HEAD (${commit}) diverge de origin/master (${remote_commit})." >&2
    echo "Atualize ou publique a candidata antes da auditoria A4." >&2
    exit 2
  fi
fi

mkdir -p "${project_dir}/outputs"
evidence_dir="$(mktemp -d "${project_dir}/outputs/a4-audit.XXXXXX")"
build_dir="$(mktemp -d "${project_dir}/build-a4.XXXXXX")"
audit_log="${evidence_dir}/a4-audit.log"

run_audit() {
  echo "=== IDENTIDADE DA CANDIDATA ==="
  echo "commit=${commit}"
  echo "describe=${describe}"
  echo "build_dir=${build_dir}"
  echo "evidence_dir=${evidence_dir}"
  git -C "${project_dir}" status --short --untracked-files=no

  echo "=== FERRAMENTAS ==="
  cmake --version | sed -n '1p'
  c++ --version | sed -n '1p'
  pythia8-config --version
  root-config --version

  echo "=== CONFIGURAÇÕES VERSIONADAS ==="
  while IFS= read -r config; do
    python3 "${project_dir}/scripts/validate_project.py" \
      "${project_dir}/${config}"
  done < <(git -C "${project_dir}" ls-files 'config/*.conf')
  python3 -m py_compile "${project_dir}/scripts/validate_project.py"
  bash -n "${project_dir}/run.sh"
  bash -n "${project_dir}/scripts/audit_release.sh"

  echo "=== BUILD LIMPO ==="
  cmake -S "${project_dir}" -B "${build_dir}" -DCMAKE_BUILD_TYPE=Release
  cmake --build "${build_dir}" --parallel "${BUILD_JOBS:-2}"

  echo "=== TESTES DE REGRESSÃO ==="
  ctest --test-dir "${build_dir}" -N
  ctest --test-dir "${build_dir}" --output-on-failure

  executable="${build_dir}/pythia_geant"
  echo "=== CLI E DRY RUN ==="
  "${executable}" --help
  "${executable}" --config "${project_dir}/config/smoke.conf" --dry-run
  "${executable}" --config "${project_dir}/config/production.conf" \
    --events 10 --mu 10 --dry-run

  working_root="${evidence_dir}/reproducibility.root"
  first_root="${evidence_dir}/reproducibility-a.root"
  second_root="${evidence_dir}/reproducibility-b.root"
  first_manifest="${evidence_dir}/reproducibility-a.manifest.txt"
  second_manifest="${evidence_dir}/reproducibility-b.manifest.txt"

  echo "=== SMOKE A ==="
  "${executable}" --config "${project_dir}/config/smoke.conf" \
    --output "${working_root}"
  mv "${working_root}" "${first_root}"
  mv "${working_root}.manifest.txt" "${first_manifest}"

  echo "=== SMOKE B ==="
  "${executable}" --config "${project_dir}/config/smoke.conf" \
    --output "${working_root}"
  mv "${working_root}" "${second_root}"
  mv "${working_root}.manifest.txt" "${second_manifest}"

  echo "=== AUDITORIA ROOT A ==="
  root -l -b -q \
    "${project_dir}/scripts/audit_root.C(\"${first_root}\",\"${commit}\")" \
    | tee "${evidence_dir}/root-audit-a.log"
  grep -q 'AUDIT_RESULT=PASS' "${evidence_dir}/root-audit-a.log"

  echo "=== AUDITORIA ROOT B ==="
  root -l -b -q \
    "${project_dir}/scripts/audit_root.C(\"${second_root}\",\"${commit}\")" \
    | tee "${evidence_dir}/root-audit-b.log"
  grep -q 'AUDIT_RESULT=PASS' "${evidence_dir}/root-audit-b.log"

  echo "=== REPRODUTIBILIDADE ==="
  cmp "${first_manifest}" "${second_manifest}"
  root -l -b -q \
    "${project_dir}/scripts/compare_root.C(\"${first_root}\",\"${second_root}\")" \
    | tee "${evidence_dir}/root-compare.log"
  grep -q 'COMPARE_RESULT=PASS' "${evidence_dir}/root-compare.log"

  echo "=== HIGIENE DO ARQUIVO-FONTE ==="
  archive_list="${evidence_dir}/archive-files.txt"
  git -C "${project_dir}" archive --format=tar HEAD | tar -tf - | tee "${archive_list}"
  if grep -Eq '(^|/)(build[^/]*|outputs)(/|$)|\.root$|\.manifest\.txt$|\.zip$' \
      "${archive_list}"; then
    echo "Erro: o arquivo-fonte contém artefatos gerados ou ZIP aninhado." >&2
    exit 1
  fi

  echo "A4_RESULT=PASS commit=${commit}"
}

run_audit 2>&1 | tee "${audit_log}"

echo
echo "Auditoria A4 aprovada. Evidências: ${evidence_dir}"
