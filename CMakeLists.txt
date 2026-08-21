cmake_minimum_required(VERSION 3.20)

project(PythiaGeantOneStage VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Geant4 11.2 REQUIRED)
include(${Geant4_USE_FILE})

find_program(
  PYTHIA8_CONFIG_EXECUTABLE
  NAMES pythia8-config
  DOC "Path to the pythia8-config helper"
)

if(NOT PYTHIA8_CONFIG_EXECUTABLE)
  message(FATAL_ERROR
    "pythia8-config was not found. Activate the environment containing "
    "PYTHIA 8 or add its bin directory to PATH.")
endif()

execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --cxxflags
  OUTPUT_VARIABLE PYTHIA8_CXXFLAGS_RAW
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --libs
  OUTPUT_VARIABLE PYTHIA8_LIBS_RAW
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)

execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --version
  OUTPUT_VARIABLE PG_PYTHIA_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)

find_program(ROOT_CONFIG_EXECUTABLE NAMES root-config)
if(NOT ROOT_CONFIG_EXECUTABLE)
  message(FATAL_ERROR
    "root-config was not found. Activate the environment containing ROOT "
    "or add its bin directory to PATH.")
endif()

execute_process(
  COMMAND "${ROOT_CONFIG_EXECUTABLE}" --version
  OUTPUT_VARIABLE PG_ROOT_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
  COMMAND "${ROOT_CONFIG_EXECUTABLE}" --cflags
  OUTPUT_VARIABLE ROOT_CXXFLAGS_RAW
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
  COMMAND "${ROOT_CONFIG_EXECUTABLE}" --libs
  OUTPUT_VARIABLE ROOT_LIBS_RAW
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)

set(PG_GIT_COMMIT "unknown")
set(PG_GIT_DESCRIBE "unknown")
find_package(Git QUIET)

if(Git_FOUND)
  execute_process(
    COMMAND "${GIT_EXECUTABLE}" rev-parse HEAD
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    OUTPUT_VARIABLE PG_GIT_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
    RESULT_VARIABLE PG_GIT_COMMIT_RESULT
  )

  if(NOT PG_GIT_COMMIT_RESULT EQUAL 0)
    set(PG_GIT_COMMIT "unknown")
  endif()

  execute_process(
    COMMAND "${GIT_EXECUTABLE}" describe --always --dirty --tags
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    OUTPUT_VARIABLE PG_GIT_DESCRIBE
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
    RESULT_VARIABLE PG_GIT_DESCRIBE_RESULT
  )

  if(NOT PG_GIT_DESCRIBE_RESULT EQUAL 0)
    set(PG_GIT_DESCRIBE "unknown")
  endif()
endif()

file(MAKE_DIRECTORY "${PROJECT_BINARY_DIR}/generated")
configure_file(
  cmake/BuildInfo.hh.in
  "${PROJECT_BINARY_DIR}/generated/BuildInfo.hh"
  @ONLY
)

separate_arguments(PYTHIA8_CXXFLAGS NATIVE_COMMAND "${PYTHIA8_CXXFLAGS_RAW}")
separate_arguments(PYTHIA8_LIBS NATIVE_COMMAND "${PYTHIA8_LIBS_RAW}")
separate_arguments(ROOT_CXXFLAGS NATIVE_COMMAND "${ROOT_CXXFLAGS_RAW}")
separate_arguments(ROOT_LIBS NATIVE_COMMAND "${ROOT_LIBS_RAW}")

# Preserve the project's C++17 contract even if a dependency helper
# injects its own -std= flag.
list(FILTER PYTHIA8_CXXFLAGS EXCLUDE REGEX "^-std=")
list(FILTER ROOT_CXXFLAGS EXCLUDE REGEX "^-std=")

add_executable(
  pythia_geant
  app/main.cc
  src/ActionInitialization.cc
  src/CalorimeterSD.cc
  src/CellSegmentation.cc
  src/Configuration.cc
  src/DetectorConstruction.cc
  src/EventAction.cc
  src/EventState.cc
  src/LineageInfo.cc
  src/PrimaryGeneratorAction.cc
  src/RootOutput.cc
  src/RunAction.cc
  src/Sampling.cc
  src/TrackingAction.cc
)

target_include_directories(
  pythia_geant
  PRIVATE
    "${PROJECT_SOURCE_DIR}/include"
    "${PROJECT_BINARY_DIR}/generated"
)
target_compile_options(
  pythia_geant
  PRIVATE
    ${PYTHIA8_CXXFLAGS}
    -Wall
    -Wextra
    -Wpedantic
)
target_link_libraries(
  pythia_geant
  PRIVATE
    ${Geant4_LIBRARIES}
    ${PYTHIA8_LIBS}
)

add_library(
  single_particle_analysis
  src/SingleParticleAnalysis.cc
  src/Sampling.cc
)
target_include_directories(
  single_particle_analysis
  PUBLIC
    "${PROJECT_SOURCE_DIR}/include"
)
target_compile_options(
  single_particle_analysis
  PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)

add_executable(
  single_particle_analyzer
  app/analyze_single_particle.cc
)
# ROOT 6.36.06 in the validated environment was built with C++20.
# Keep the simulator on C++17 and match ROOT only at this API boundary.
set_target_properties(
  single_particle_analyzer
  PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)
target_compile_options(
  single_particle_analyzer
  PRIVATE
    ${ROOT_CXXFLAGS}
    -Wall
    -Wextra
    -Wpedantic
)
target_link_libraries(
  single_particle_analyzer
  PRIVATE
    single_particle_analysis
    ${ROOT_LIBS}
)

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)

  add_executable(
    particle_decision_test
    tests/ParticleDecisionTest.cc
  )
  target_include_directories(
    particle_decision_test
    PRIVATE
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_compile_options(
    particle_decision_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  add_test(NAME particle_decision COMMAND particle_decision_test)

  add_executable(
    cell_segmentation_test
    tests/CellSegmentationTest.cc
    src/CellSegmentation.cc
    src/Sampling.cc
  )
  target_include_directories(
    cell_segmentation_test
    PRIVATE
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_compile_options(
    cell_segmentation_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  add_test(NAME cell_segmentation COMMAND cell_segmentation_test)

  add_executable(
    seed_policy_test
    tests/SeedPolicyTest.cc
  )
  target_include_directories(
    seed_policy_test
    PRIVATE
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_compile_options(
    seed_policy_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  add_test(NAME seed_policy COMMAND seed_policy_test)

  add_executable(
    configuration_test
    tests/ConfigurationTest.cc
    src/Configuration.cc
  )
  target_include_directories(
    configuration_test
    PRIVATE
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_compile_options(
    configuration_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  add_test(NAME configuration COMMAND configuration_test)

  add_executable(
    single_particle_kinematics_test
    tests/SingleParticleKinematicsTest.cc
  )
  target_include_directories(
    single_particle_kinematics_test
    PRIVATE
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_compile_options(
    single_particle_kinematics_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  add_test(
    NAME single_particle_kinematics
    COMMAND single_particle_kinematics_test
  )

  add_executable(
    single_particle_analysis_test
    tests/SingleParticleAnalysisTest.cc
  )
  target_compile_options(
    single_particle_analysis_test
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )
  target_link_libraries(
    single_particle_analysis_test
    PRIVATE
      single_particle_analysis
  )
  add_test(
    NAME single_particle_analysis
    COMMAND single_particle_analysis_test
  )

  add_test(
    NAME statistical_aggregator
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_statistical_aggregator.py"
  )

  add_test(
    NAME statistical_campaign_executor
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_statistical_campaign_executor.py"
  )

  add_test(
    NAME longitudinal_containment
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_longitudinal_containment.py"
  )

  add_test(
    NAME hadronic_tail_systematics
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_hadronic_tail_systematics.py"
  )

  add_test(
    NAME hadronic_tail_aggregator
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_hadronic_tail_aggregator.py"
  )

  add_test(
    NAME integrated_minbias_preflight
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_integrated_minbias_preflight.py"
  )

  add_test(
    NAME integrated_minbias_executor
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_integrated_minbias_executor.py"
  )

  add_test(
    NAME neutrino_transport_preflight
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_neutrino_transport_preflight.py"
  )

  add_test(
    NAME neutrino_transport_executor
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_neutrino_transport_executor.py"
  )

  add_test(
    NAME neutrino_transport_stage83_preflight
    COMMAND "${Python3_EXECUTABLE}" -B
      "${PROJECT_SOURCE_DIR}/tests/test_neutrino_transport_stage83_preflight.py"
  )
endif()

install(TARGETS pythia_geant RUNTIME DESTINATION bin)
