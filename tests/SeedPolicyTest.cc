#include "SeedPolicy.hh"

#include <cstdint>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireEqual64(
    const std::uint64_t actual,
    const std::uint64_t expected,
    const std::string& message) {
  if (actual == expected) {
    return;
  }

  std::ostringstream stream;
  stream << message
         << ": expected=" << expected
         << ", obtained=" << actual;
  throw std::runtime_error(stream.str());
}

void RequireEqualInt(
    const int actual,
    const int expected,
    const std::string& message) {
  if (actual == expected) {
    return;
  }

  throw std::runtime_error(
      message +
      ": expected=" + std::to_string(expected) +
      ", obtained=" + std::to_string(actual));
}

void CheckPolicyIdentity() {
  Require(
      std::string(pg::kSeedPolicyName) ==
          "event-stable-v1",
      "Unexpected seed policy name");

  Require(
      std::string(pg::kSeedIdentityName) == "bcid",
      "Unexpected stable seed identity");

  Require(
      std::string(pg::kSeedMixerName) ==
          "splitmix64-v1",
      "Unexpected seed mixer name");

  Require(
      pg::kPythiaMaximumSeed == 900000000LL,
      "Unexpected PYTHIA maximum seed");
}

void CheckStreamIdentifiers() {
  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kPythiaInitialization),
      1ULL,
      "PYTHIA initialization stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kInteractionCount),
      2ULL,
      "Interaction-count stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kPythiaSubevent),
      3ULL,
      "PYTHIA subevent stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kVertexX),
      4ULL,
      "Vertex-X stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kVertexY),
      5ULL,
      "Vertex-Y stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kVertexZ),
      6ULL,
      "Vertex-Z stream changed");

  RequireEqual64(
      static_cast<std::uint64_t>(
          pg::SeedStream::kVertexT),
      7ULL,
      "Vertex-T stream changed");
}

void CheckSplitMix64KnownVectors() {
  struct Case {
    std::uint64_t input;
    std::uint64_t expected;
  };

  const Case cases[] = {
      {
          0x0000000000000000ULL,
          0xE220A8397B1DCDAFULL,
      },
      {
          0x0000000000000001ULL,
          0x910A2DEC89025CC1ULL,
      },
      {
          0x123456789ABCDEF0ULL,
          0x161922C645CE50E8ULL,
      },
      {
          0xFFFFFFFFFFFFFFFFULL,
          0xE4D971771B652C20ULL,
      },
  };

  for (const auto& test : cases) {
    RequireEqual64(
        pg::SplitMix64(test.input),
        test.expected,
        "SplitMix64 known vector changed");
  }
}

void CheckStableTupleKnownVectors() {
  RequireEqual64(
      pg::StableSeed64(
          512ULL,
          0ULL,
          0ULL,
          pg::SeedStream::kPythiaInitialization),
      0x5E7BFBFB1D57CB4AULL,
      "Initialization tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          0ULL,
          0ULL,
          pg::SeedStream::kPythiaInitialization),
      0x313F9DE9D174B095ULL,
      "Seed-base tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          0ULL,
          pg::SeedStream::kInteractionCount),
      0xDF397B4A4D8002FFULL,
      "Interaction-count tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          0ULL,
          pg::SeedStream::kPythiaSubevent),
      0xBD32EF3BA3EF96FFULL,
      "PYTHIA subevent-zero tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kPythiaSubevent),
      0x64BF1B275D8EF2F4ULL,
      "PYTHIA subevent-one tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kVertexX),
      0x18050414C172DD3EULL,
      "Vertex-X tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kVertexY),
      0x820282ADAE115AC2ULL,
      "Vertex-Y tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kVertexZ),
      0x310A85DE8E694A47ULL,
      "Vertex-Z tuple changed");

  RequireEqual64(
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kVertexT),
      0x9401F24A8CE586ECULL,
      "Vertex-T tuple changed");
}

void CheckPythiaMappingKnownVectors() {
  RequireEqualInt(
      pg::PythiaSeedForStableTuple(
          9512ULL,
          0ULL,
          0ULL,
          pg::SeedStream::kPythiaInitialization),
      258266518,
      "PYTHIA initialization mapping changed");

  RequireEqualInt(
      pg::PythiaSeedForStableTuple(
          9512ULL,
          42ULL,
          0ULL,
          pg::SeedStream::kInteractionCount),
      388468480,
      "Interaction-count PYTHIA mapping changed");

  RequireEqualInt(
      pg::PythiaSeedForStableTuple(
          9512ULL,
          42ULL,
          0ULL,
          pg::SeedStream::kPythiaSubevent),
      636409600,
      "Subevent-zero PYTHIA mapping changed");

  RequireEqualInt(
      pg::PythiaSeedForStableTuple(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kPythiaSubevent),
      731852789,
      "Subevent-one PYTHIA mapping changed");
}

void CheckTupleSensitivity() {
  const auto reference =
      pg::StableSeed64(
          9512ULL,
          42ULL,
          1ULL,
          pg::SeedStream::kPythiaSubevent);

  Require(
      reference ==
          pg::StableSeed64(
              9512ULL,
              42ULL,
              1ULL,
              pg::SeedStream::kPythiaSubevent),
      "Identical tuple is not deterministic");

  Require(
      reference !=
          pg::StableSeed64(
              9513ULL,
              42ULL,
              1ULL,
              pg::SeedStream::kPythiaSubevent),
      "Changing seed_base did not change seed");

  Require(
      reference !=
          pg::StableSeed64(
              9512ULL,
              43ULL,
              1ULL,
              pg::SeedStream::kPythiaSubevent),
      "Changing BCID did not change seed");

  Require(
      reference !=
          pg::StableSeed64(
              9512ULL,
              42ULL,
              2ULL,
              pg::SeedStream::kPythiaSubevent),
      "Changing subevent did not change seed");

  Require(
      reference !=
          pg::StableSeed64(
              9512ULL,
              42ULL,
              1ULL,
              pg::SeedStream::kVertexX),
      "Changing stream did not change seed");
}

void CheckOperationalCollisionDomain() {
  constexpr std::uint64_t kSeedBase = 9512ULL;
  constexpr std::uint64_t kBcids = 256ULL;
  constexpr std::uint64_t kSubevents = 16ULL;

  std::set<std::uint64_t> stableSeeds;
  std::set<int> pythiaSeeds;

  const pg::SeedStream streams[] = {
      pg::SeedStream::kPythiaInitialization,
      pg::SeedStream::kInteractionCount,
      pg::SeedStream::kPythiaSubevent,
      pg::SeedStream::kVertexX,
      pg::SeedStream::kVertexY,
      pg::SeedStream::kVertexZ,
      pg::SeedStream::kVertexT,
  };

  for (std::uint64_t bcid = 0;
       bcid < kBcids;
       ++bcid) {
    for (std::uint64_t subevent = 0;
         subevent < kSubevents;
         ++subevent) {
      for (const auto stream : streams) {
        const auto stableSeed =
            pg::StableSeed64(
                kSeedBase,
                bcid,
                subevent,
                stream);

        Require(
            stableSeeds.insert(stableSeed).second,
            "Stable 64-bit seed collision in operational domain");

        const int pythiaSeed =
            pg::PythiaSeedFromStableSeed(stableSeed);

        Require(
            pythiaSeed >= 1 &&
                pythiaSeed <=
                    pg::kPythiaMaximumSeed,
            "PYTHIA seed outside valid interval");

        Require(
            pythiaSeeds.insert(pythiaSeed).second,
            "PYTHIA mapped seed collision in operational domain");
      }
    }
  }

  constexpr std::size_t expected =
      static_cast<std::size_t>(
          kBcids * kSubevents * 7ULL);

  Require(
      stableSeeds.size() == expected,
      "Unexpected stable-seed domain size");

  Require(
      pythiaSeeds.size() == expected,
      "Unexpected mapped-PYTHIA domain size");
}


}  // namespace

int main() {
  try {
    CheckPolicyIdentity();
    CheckStreamIdentifiers();
    CheckSplitMix64KnownVectors();
    CheckStableTupleKnownVectors();
    CheckPythiaMappingKnownVectors();
    CheckTupleSensitivity();
    CheckOperationalCollisionDomain();

    std::cout
        << "Event-stable seed policy tests passed"
        << std::endl;

    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "Seed policy test failed: "
        << error.what()
        << std::endl;
    return 1;
  }
}
