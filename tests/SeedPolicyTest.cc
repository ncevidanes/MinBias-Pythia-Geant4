#include "SeedPolicy.hh"

#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireEqual(const int actual, const int expected,
                  const std::string& message) {
  Require(actual == expected,
          message + ": expected " + std::to_string(expected) +
              ", obtained " + std::to_string(actual));
}

void CheckConstants() {
  Require(pg::kPythiaWorkerSeedStride == 104729LL,
          "Unexpected PYTHIA worker seed stride");
  Require(pg::kPythiaMaximumSeed == 900000000LL,
          "Unexpected PYTHIA maximum seed");
}

void CheckNormalization() {
  struct Case {
    long long input;
    int expected;
  };

  const std::vector<Case> cases{
      {1LL, 1},
      {512LL, 512},
      {pg::kPythiaMaximumSeed,
       static_cast<int>(pg::kPythiaMaximumSeed)},
      {pg::kPythiaMaximumSeed + 1LL, 1},
      {2LL * pg::kPythiaMaximumSeed,
       static_cast<int>(pg::kPythiaMaximumSeed)},
      {0LL, static_cast<int>(pg::kPythiaMaximumSeed)},
      {-1LL, static_cast<int>(pg::kPythiaMaximumSeed - 1LL)},
      {-pg::kPythiaMaximumSeed,
       static_cast<int>(pg::kPythiaMaximumSeed)},
      {1LL - pg::kPythiaMaximumSeed, 1},
      {std::numeric_limits<long long>::min() + 1LL, 845224193},
      {std::numeric_limits<long long>::max(), 54775807},
  };

  for (const auto& test : cases) {
    RequireEqual(pg::NormalizePythiaSeed(test.input), test.expected,
                 "Incorrect normalization for input " +
                     std::to_string(test.input));
  }
}

void CheckWorkerMapping() {
  RequireEqual(pg::PythiaSeedForWorker(512, -1), 512,
               "Negative thread ID did not map to worker zero");
  RequireEqual(
      pg::PythiaSeedForWorker(
          512, std::numeric_limits<int>::min()),
      512, "Minimum thread ID did not map to worker zero");
  RequireEqual(pg::PythiaSeedForWorker(512, 0), 512,
               "Worker zero changed the base seed");
  RequireEqual(pg::PythiaSeedForWorker(512, 1), 105241,
               "Worker one received an unexpected seed");
  RequireEqual(pg::PythiaSeedForWorker(512, 2), 209970,
               "Worker two received an unexpected seed");

  RequireEqual(
      pg::PythiaSeedForWorker(
          static_cast<int>(pg::kPythiaMaximumSeed), 1),
      104729, "Worker seed wrap-around is incorrect");
  RequireEqual(pg::PythiaSeedForWorker(899950000, 1), 54729,
               "Worker seed wrap-around lost its offset");
}

void CheckWorkerSequence() {
  constexpr int kSeedBase = 512;
  constexpr int kWorkersToCheck = 4096;
  std::set<int> seeds;

  for (int threadId = 0; threadId < kWorkersToCheck; ++threadId) {
    const int actual = pg::PythiaSeedForWorker(kSeedBase, threadId);
    const int expected = pg::NormalizePythiaSeed(
        static_cast<long long>(kSeedBase) +
        pg::kPythiaWorkerSeedStride * threadId);

    RequireEqual(actual, expected,
                 "Worker mapping changed at thread " +
                     std::to_string(threadId));
    Require(actual >= 1 && actual <= pg::kPythiaMaximumSeed,
            "Worker seed lies outside the PYTHIA interval");
    Require(seeds.insert(actual).second,
            "Worker seed collision at thread " +
                std::to_string(threadId));
  }

  Require(static_cast<int>(seeds.size()) == kWorkersToCheck,
          "Unexpected number of unique worker seeds");
}

}  // namespace

int main() {
  try {
    CheckConstants();
    CheckNormalization();
    CheckWorkerMapping();
    CheckWorkerSequence();
    std::cout << "Seed policy tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Seed policy test failed: " << error.what()
              << std::endl;
    return 1;
  }
}
