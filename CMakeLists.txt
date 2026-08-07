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

separate_arguments(PYTHIA8_CXXFLAGS NATIVE_COMMAND "${PYTHIA8_CXXFLAGS_RAW}")
separate_arguments(PYTHIA8_LIBS NATIVE_COMMAND "${PYTHIA8_LIBS_RAW}")

# Preserve the project's C++17 contract even if an older pythia8-config
# injects its own -std= flag.
list(FILTER PYTHIA8_CXXFLAGS EXCLUDE REGEX "^-std=")

add_executable(
  pythia_geant
  app/main.cc
  src/ActionInitialization.cc
  src/CalorimeterSD.cc
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

target_include_directories(pythia_geant PRIVATE "${PROJECT_SOURCE_DIR}/include")
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

include(CTest)
if(BUILD_TESTING)
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
endif()

install(TARGETS pythia_geant RUNTIME DESTINATION bin)
