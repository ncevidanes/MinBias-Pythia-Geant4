#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only

set -euo pipefail

PROJECT_ROOT="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

BASELINE_FILE="${PROJECT_ROOT}/ci/coverage-baseline.env"
REQUIREMENTS_FILE="${PROJECT_ROOT}/ci/coverage-requirements.txt"

BUILD_DIR="${PROJECT_ROOT}/build-coverage"
REPORT_DIR="${PROJECT_ROOT}/build-coverage-report"
TOOL_DIR="${PROJECT_ROOT}/build-coverage-tools"

JOBS="${COVERAGE_JOBS:-2}"
ENFORCE_BASELINE="${COVERAGE_ENFORCE_BASELINE:-0}"


die() {
  echo "COVERAGE_ERROR=$*" >&2
  exit 1
}


require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    die "required command not found: $1"
}


numeric_field() {
  local report="$1"
  local row="$2"
  local column="$3"

  awk \
    -v row="$row" \
    -v column="$column" \
    '$1 == row { print $column }' \
    "$report"
}


require_integer() {
  local name="$1"
  local value="$2"

  [[ "$value" =~ ^[0-9]+$ ]] ||
    die "$name is not an integer: $value"
}


assert_equal() {
  local name="$1"
  local actual="$2"
  local expected="$3"

  if [[ "$actual" != "$expected" ]]; then
    echo "${name}_EXPECTED=$expected" >&2
    echo "${name}_ACTUAL=$actual" >&2
    die "${name} mismatch"
  fi

  echo "${name}_GATE=PASS"
}


safe_reset_directory() {
  local directory="$1"

  case "$directory" in
    "$PROJECT_ROOT"/build-coverage|\
    "$PROJECT_ROOT"/build-coverage-report|\
    "$PROJECT_ROOT"/build-coverage-tools)
      ;;
    *)
      die "refusing to remove unexpected directory: $directory"
      ;;
  esac

  rm -rf -- "$directory"
}


for command in \
  cmake \
  ctest \
  python3 \
  gcc \
  g++ \
  gcov \
  awk \
  grep \
  find
do
  require_command "$command"
done


[[ "$ENFORCE_BASELINE" == "0" || "$ENFORCE_BASELINE" == "1" ]] ||
  die "COVERAGE_ENFORCE_BASELINE must be 0 or 1"

[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] ||
  die "COVERAGE_JOBS must be a positive integer"

[[ -f "$BASELINE_FILE" ]] ||
  die "coverage baseline file not found: $BASELINE_FILE"

[[ -f "$REQUIREMENTS_FILE" ]] ||
  die "coverage requirements file not found: $REQUIREMENTS_FILE"


# shellcheck disable=SC1090
source "$BASELINE_FILE"


echo "======================================================"
echo " PROJECT COVERAGE — CANONICAL FULL RUN"
echo "======================================================"

echo "PROJECT_ROOT=$PROJECT_ROOT"
echo "COVERAGE_BASELINE_ID=$COVERAGE_BASELINE_ID"
echo "COVERAGE_ENFORCE_BASELINE=$ENFORCE_BASELINE"
echo "COVERAGE_JOBS=$JOBS"


GCC_VERSION="$(gcc -dumpfullversion)"
GCOV_VERSION="$(
  gcov --version |
    awk 'NR == 1 { print $NF }'
)"

GCC_MAJOR="${GCC_VERSION%%.*}"
GCOV_MAJOR="${GCOV_VERSION%%.*}"

echo "GCC_VERSION=$GCC_VERSION"
echo "GCOV_VERSION=$GCOV_VERSION"

assert_equal \
  COVERAGE_GCC_MAJOR \
  "$GCC_MAJOR" \
  "$COVERAGE_EXPECTED_GCC_MAJOR"

assert_equal \
  COVERAGE_GCOV_MAJOR \
  "$GCOV_MAJOR" \
  "$COVERAGE_EXPECTED_GCOV_MAJOR"


echo
echo "=== Coverage tool environment ==="

safe_reset_directory "$TOOL_DIR"

python3 -m venv "$TOOL_DIR"

"$TOOL_DIR/bin/python" \
  -m pip \
  install \
  --disable-pip-version-check \
  --no-cache-dir \
  --quiet \
  -r "$REQUIREMENTS_FILE"

GCOVR="$TOOL_DIR/bin/gcovr"

[[ -x "$GCOVR" ]] ||
  die "gcovr installation failed"

GCOVR_VERSION="$(
  "$GCOVR" --version |
    awk 'NR == 1 { print $2 }'
)"

echo "GCOVR_VERSION=$GCOVR_VERSION"

assert_equal \
  COVERAGE_GCOVR_VERSION \
  "$GCOVR_VERSION" \
  "$COVERAGE_EXPECTED_GCOVR_VERSION"


echo
echo "=== Fresh isolated coverage build ==="

safe_reset_directory "$BUILD_DIR"
safe_reset_directory "$REPORT_DIR"

mkdir -p "$REPORT_DIR"

cmake \
  -S "$PROJECT_ROOT" \
  -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DBUILD_TESTING=ON \
  -DCMAKE_CXX_FLAGS="-O0 -g --coverage -fno-inline" \
  -DCMAKE_EXE_LINKER_FLAGS="--coverage"

echo "COVERAGE_CONFIGURE_GATE=PASS"

cmake \
  --build "$BUILD_DIR" \
  --parallel "$JOBS"

echo "COVERAGE_BUILD_GATE=PASS"


echo
echo "=== Canonical CTest suite ==="

CTEST_COUNT="$(
  ctest \
    --test-dir "$BUILD_DIR" \
    -N \
    2>/dev/null |
    grep -Ec 'Test[[:space:]]*#[0-9]+:' || true
)"

echo "CTEST_DISCOVERED_COUNT=$CTEST_COUNT"

assert_equal \
  COVERAGE_CTEST_COUNT \
  "$CTEST_COUNT" \
  "$COVERAGE_EXPECTED_CTEST_COUNT"

ctest \
  --test-dir "$BUILD_DIR" \
  --output-on-failure \
  -j1

echo "COVERAGE_CTEST_GATE=PASS"


echo
echo "=== Coverage artifacts ==="

GCNO_COUNT="$(
  find "$BUILD_DIR" \
    -type f \
    -name '*.gcno' |
    wc -l
)"

GCDA_COUNT="$(
  find "$BUILD_DIR" \
    -type f \
    -name '*.gcda' |
    wc -l
)"

echo "GCNO_COUNT=$GCNO_COUNT"
echo "GCDA_COUNT=$GCDA_COUNT"

[[ "$GCNO_COUNT" -gt 0 ]] ||
  die "no .gcno files were generated"

[[ "$GCDA_COUNT" -gt 0 ]] ||
  die "no .gcda files were generated"

echo "COVERAGE_ARTIFACT_GATE=PASS"


echo
echo "=== Line report ==="

"$GCOVR" \
  --root "$PROJECT_ROOT" \
  --object-directory "$BUILD_DIR" \
  --gcov-executable "$(command -v gcov)" \
  --filter "$PROJECT_ROOT/src/" \
  --filter "$PROJECT_ROOT/app/" \
  --exclude "$PROJECT_ROOT/tests/" \
  --txt "$REPORT_DIR/lines.txt"

cat "$REPORT_DIR/lines.txt"


echo
echo "=== Branch report ==="

"$GCOVR" \
  --root "$PROJECT_ROOT" \
  --object-directory "$BUILD_DIR" \
  --gcov-executable "$(command -v gcov)" \
  --filter "$PROJECT_ROOT/src/" \
  --filter "$PROJECT_ROOT/app/" \
  --exclude "$PROJECT_ROOT/tests/" \
  --txt-metric branch \
  --txt "$REPORT_DIR/branches.txt"

cat "$REPORT_DIR/branches.txt"


echo
echo "=== Structured metrics ==="

GLOBAL_LINES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    TOTAL \
    2
)"

GLOBAL_LINES_EXEC="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    TOTAL \
    3
)"

GLOBAL_BRANCHES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    TOTAL \
    2
)"

GLOBAL_BRANCHES_TAKEN="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    TOTAL \
    3
)"

EVENTSTATE_LINES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    src/EventState.cc \
    2
)"

EVENTSTATE_LINES_EXEC="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    src/EventState.cc \
    3
)"

EVENTSTATE_BRANCHES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    src/EventState.cc \
    2
)"

EVENTSTATE_BRANCHES_TAKEN="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    src/EventState.cc \
    3
)"

LINEAGE_LINES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    src/LineageInfo.cc \
    2
)"

LINEAGE_LINES_EXEC="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    src/LineageInfo.cc \
    3
)"

LINEAGE_BRANCHES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    src/LineageInfo.cc \
    2
)"

ANALYZER_LINES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    app/analyze_single_particle.cc \
    2
)"

ANALYZER_LINES_EXEC="$(
  numeric_field \
    "$REPORT_DIR/lines.txt" \
    app/analyze_single_particle.cc \
    3
)"

ANALYZER_BRANCHES_TOTAL="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    app/analyze_single_particle.cc \
    2
)"

ANALYZER_BRANCHES_TAKEN="$(
  numeric_field \
    "$REPORT_DIR/branches.txt" \
    app/analyze_single_particle.cc \
    3
)"


for pair in \
  "GLOBAL_LINES_TOTAL:$GLOBAL_LINES_TOTAL" \
  "GLOBAL_LINES_EXEC:$GLOBAL_LINES_EXEC" \
  "GLOBAL_BRANCHES_TOTAL:$GLOBAL_BRANCHES_TOTAL" \
  "GLOBAL_BRANCHES_TAKEN:$GLOBAL_BRANCHES_TAKEN" \
  "EVENTSTATE_LINES_TOTAL:$EVENTSTATE_LINES_TOTAL" \
  "EVENTSTATE_LINES_EXEC:$EVENTSTATE_LINES_EXEC" \
  "EVENTSTATE_BRANCHES_TOTAL:$EVENTSTATE_BRANCHES_TOTAL" \
  "EVENTSTATE_BRANCHES_TAKEN:$EVENTSTATE_BRANCHES_TAKEN" \
  "LINEAGE_LINES_TOTAL:$LINEAGE_LINES_TOTAL" \
  "LINEAGE_LINES_EXEC:$LINEAGE_LINES_EXEC" \
  "LINEAGE_BRANCHES_TOTAL:$LINEAGE_BRANCHES_TOTAL" \
  "ANALYZER_LINES_TOTAL:$ANALYZER_LINES_TOTAL" \
  "ANALYZER_LINES_EXEC:$ANALYZER_LINES_EXEC" \
  "ANALYZER_BRANCHES_TOTAL:$ANALYZER_BRANCHES_TOTAL" \
  "ANALYZER_BRANCHES_TAKEN:$ANALYZER_BRANCHES_TAKEN"
do
  name="${pair%%:*}"
  value="${pair#*:}"

  require_integer "$name" "$value"
done


echo "GLOBAL_LINES=$GLOBAL_LINES_EXEC/$GLOBAL_LINES_TOTAL"
echo "GLOBAL_BRANCHES=$GLOBAL_BRANCHES_TAKEN/$GLOBAL_BRANCHES_TOTAL"

echo "EVENTSTATE_LINES=$EVENTSTATE_LINES_EXEC/$EVENTSTATE_LINES_TOTAL"
echo "EVENTSTATE_BRANCHES=$EVENTSTATE_BRANCHES_TAKEN/$EVENTSTATE_BRANCHES_TOTAL"

echo "LINEAGEINFO_LINES=$LINEAGE_LINES_EXEC/$LINEAGE_LINES_TOTAL"
echo "LINEAGEINFO_BRANCH_COUNT=$LINEAGE_BRANCHES_TOTAL"

echo "ANALYZER_LINES=$ANALYZER_LINES_EXEC/$ANALYZER_LINES_TOTAL"
echo "ANALYZER_BRANCHES=$ANALYZER_BRANCHES_TAKEN/$ANALYZER_BRANCHES_TOTAL"


awk \
  -v exec="$GLOBAL_LINES_EXEC" \
  -v total="$GLOBAL_LINES_TOTAL" \
  'BEGIN {
    printf "GLOBAL_EXACT_LINE_COVERAGE=%.2f%%\n",
           100.0 * exec / total
  }'

awk \
  -v taken="$GLOBAL_BRANCHES_TAKEN" \
  -v total="$GLOBAL_BRANCHES_TOTAL" \
  'BEGIN {
    printf "GLOBAL_EXACT_BRANCH_COVERAGE=%.2f%%\n",
           100.0 * taken / total
  }'


echo
echo "=== Optional exact baseline gate ==="

if [[ "$ENFORCE_BASELINE" == "1" ]]; then

  assert_equal \
    BASELINE_GLOBAL_LINES_TOTAL \
    "$GLOBAL_LINES_TOTAL" \
    "$COVERAGE_BASELINE_GLOBAL_LINES_TOTAL"

  assert_equal \
    BASELINE_GLOBAL_LINES_EXEC \
    "$GLOBAL_LINES_EXEC" \
    "$COVERAGE_BASELINE_GLOBAL_LINES_EXEC"

  assert_equal \
    BASELINE_GLOBAL_BRANCHES_TOTAL \
    "$GLOBAL_BRANCHES_TOTAL" \
    "$COVERAGE_BASELINE_GLOBAL_BRANCHES_TOTAL"

  assert_equal \
    BASELINE_GLOBAL_BRANCHES_TAKEN \
    "$GLOBAL_BRANCHES_TAKEN" \
    "$COVERAGE_BASELINE_GLOBAL_BRANCHES_TAKEN"

  assert_equal \
    BASELINE_EVENTSTATE_LINES_TOTAL \
    "$EVENTSTATE_LINES_TOTAL" \
    "$COVERAGE_BASELINE_EVENTSTATE_LINES_TOTAL"

  assert_equal \
    BASELINE_EVENTSTATE_LINES_EXEC \
    "$EVENTSTATE_LINES_EXEC" \
    "$COVERAGE_BASELINE_EVENTSTATE_LINES_EXEC"

  assert_equal \
    BASELINE_EVENTSTATE_BRANCHES_TOTAL \
    "$EVENTSTATE_BRANCHES_TOTAL" \
    "$COVERAGE_BASELINE_EVENTSTATE_BRANCHES_TOTAL"

  assert_equal \
    BASELINE_EVENTSTATE_BRANCHES_TAKEN \
    "$EVENTSTATE_BRANCHES_TAKEN" \
    "$COVERAGE_BASELINE_EVENTSTATE_BRANCHES_TAKEN"

  assert_equal \
    BASELINE_LINEAGEINFO_LINES_TOTAL \
    "$LINEAGE_LINES_TOTAL" \
    "$COVERAGE_BASELINE_LINEAGEINFO_LINES_TOTAL"

  assert_equal \
    BASELINE_LINEAGEINFO_LINES_EXEC \
    "$LINEAGE_LINES_EXEC" \
    "$COVERAGE_BASELINE_LINEAGEINFO_LINES_EXEC"

  assert_equal \
    BASELINE_LINEAGEINFO_BRANCHES_TOTAL \
    "$LINEAGE_BRANCHES_TOTAL" \
    "$COVERAGE_BASELINE_LINEAGEINFO_BRANCHES_TOTAL"

  assert_equal \
    BASELINE_ANALYZER_LINES_TOTAL \
    "$ANALYZER_LINES_TOTAL" \
    "$COVERAGE_BASELINE_ANALYZER_LINES_TOTAL"

  assert_equal \
    BASELINE_ANALYZER_LINES_EXEC \
    "$ANALYZER_LINES_EXEC" \
    "$COVERAGE_BASELINE_ANALYZER_LINES_EXEC"

  assert_equal \
    BASELINE_ANALYZER_BRANCHES_TOTAL \
    "$ANALYZER_BRANCHES_TOTAL" \
    "$COVERAGE_BASELINE_ANALYZER_BRANCHES_TOTAL"

  assert_equal \
    BASELINE_ANALYZER_BRANCHES_TAKEN \
    "$ANALYZER_BRANCHES_TAKEN" \
    "$COVERAGE_BASELINE_ANALYZER_BRANCHES_TAKEN"

  echo "COVERAGE_BASELINE_GATE=PASS"

else

  echo "COVERAGE_BASELINE_GATE=NOT_REQUESTED"

fi


echo
echo "======================================================"
echo " COVERAGE RUN COMPLETE"
echo "======================================================"

echo "COVERAGE_REPORT_DIR=$REPORT_DIR"
echo "COVERAGE_LINE_REPORT=$REPORT_DIR/lines.txt"
echo "COVERAGE_BRANCH_REPORT=$REPORT_DIR/branches.txt"
