# MinBias-Pythia-Geant4
# Lightweight continuous-integration test project.
#
# SPDX-License-Identifier: GPL-3.0-only

cmake_minimum_required(VERSION 3.20)

project(
  MinBiasLightweightCI
  LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)

find_package(
  Python3 3.10 REQUIRED
  COMPONENTS Interpreter
)

get_filename_component(
  REPOSITORY_ROOT
  "${CMAKE_CURRENT_LIST_DIR}/../.."
  ABSOLUTE
)

function(add_lightweight_cpp_test test_name)

  add_executable(
    "${test_name}"
    ${ARGN}
  )

  target_include_directories(
    "${test_name}"
    PRIVATE
      "${REPOSITORY_ROOT}/include"
  )

  target_compile_options(
    "${test_name}"
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )

  add_test(
    NAME "${test_name}"
    COMMAND "${test_name}"
  )

  set_tests_properties(
    "${test_name}"
    PROPERTIES
      WORKING_DIRECTORY "${REPOSITORY_ROOT}"
  )

endfunction()

add_lightweight_cpp_test(
  particle_decision
  "${REPOSITORY_ROOT}/tests/ParticleDecisionTest.cc"
)

add_lightweight_cpp_test(
  cell_segmentation
  "${REPOSITORY_ROOT}/tests/CellSegmentationTest.cc"
  "${REPOSITORY_ROOT}/src/CellSegmentation.cc"
  "${REPOSITORY_ROOT}/src/Sampling.cc"
)

add_lightweight_cpp_test(
  seed_policy
  "${REPOSITORY_ROOT}/tests/SeedPolicyTest.cc"
)

add_lightweight_cpp_test(
  stable_random
  "${REPOSITORY_ROOT}/tests/StableRandomTest.cc"
)

add_lightweight_cpp_test(
  configuration
  "${REPOSITORY_ROOT}/tests/ConfigurationTest.cc"
  "${REPOSITORY_ROOT}/src/Configuration.cc"
)

add_lightweight_cpp_test(
  single_particle_kinematics
  "${REPOSITORY_ROOT}/tests/SingleParticleKinematicsTest.cc"
)

add_lightweight_cpp_test(
  single_particle_analysis
  "${REPOSITORY_ROOT}/tests/SingleParticleAnalysisTest.cc"
  "${REPOSITORY_ROOT}/src/SingleParticleAnalysis.cc"
  "${REPOSITORY_ROOT}/src/Sampling.cc"
)

set(
  LIGHTWEIGHT_PYTHON_TESTS
  test_hadronic_tail_aggregator.py
  test_hadronic_tail_systematics.py
  test_integrated_minbias_executor.py
  test_integrated_minbias_preflight.py
  test_longitudinal_containment.py
  test_neutrino_transport_executor.py
  test_neutrino_transport_preflight.py
  test_neutrino_transport_stage83_executor.py
  test_neutrino_transport_stage83_preflight.py
  test_performance_reproducibility_executor.py
  test_performance_reproducibility_preflight.py
  test_statistical_aggregator.py
  test_statistical_campaign_executor.py
)

foreach(test_file IN LISTS LIGHTWEIGHT_PYTHON_TESTS)

  get_filename_component(
    test_name
    "${test_file}"
    NAME_WE
  )

  add_test(
    NAME "${test_name}"
    COMMAND
      "${Python3_EXECUTABLE}"
      -B
      "${REPOSITORY_ROOT}/tests/${test_file}"
  )

  set_tests_properties(
    "${test_name}"
    PROPERTIES
      WORKING_DIRECTORY "${REPOSITORY_ROOT}"
      ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1"
  )

endforeach()
