#include "SeedPolicy.hh"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void Require(
    const bool condition,
    const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireEqual(
    const int actual,
    const int expected,
    const std::string& message) {
  if (actual != expected) {
    throw std::runtime_error(
        message +
        ": expected=" +
        std::to_string(expected) +
        ", obtained=" +
        std::to_string(actual));
  }
}

void RequireEqual64(
    const std::uint64_t actual,
    const std::uint64_t expected,
    const std::string& message) {
  if (actual != expected) {
    throw std::runtime_error(message);
  }
}

}  // namespace

int main() {
  try {
    Require(
        pg::kGeant4TransportMaximumSeed ==
            2147483646LL,
        "Unexpected Geant4 transport seed maximum");

    Require(
        std::string(
            pg::kGeant4TransportSeedPolicyName)
            == "event-stable-v1",
        "Unexpected transport seed policy");

    Require(
        std::string(
            pg::kGeant4TransportSeedIdentityName)
            == "bcid",
        "Unexpected transport seed identity");

    Require(
        std::string(
            pg::kGeant4TransportSeedMixerName)
            == "splitmix64-v1",
        "Unexpected transport seed mixer");

    Require(
        std::string(
            pg::kGeant4TransportSeedStreamName)
            == "transport-event",
        "Unexpected transport stream name");

    Require(
        std::string(
            pg::kGeant4TransportReseedScopeName)
            == "event-before-tracking",
        "Unexpected transport reseed scope");

    RequireEqual64(
        static_cast<std::uint64_t>(
            pg::SeedStream::
                kGeant4TransportEvent),
        8ULL,
        "Transport stream identifier changed");

    RequireEqual(
        pg::TransportSeedForStableTuple(
            9512ULL,
            42ULL),
        1667806656,
        "Transport known vector BCID 42 changed");

    RequireEqual(
        pg::TransportSeedForStableTuple(
            9512ULL,
            11000ULL),
        749816736,
        "Transport known vector BCID 11000 changed");

    RequireEqual(
        pg::TransportSeedForStableTuple(
            9512ULL,
            11001ULL),
        298535423,
        "Transport known vector BCID 11001 changed");

    RequireEqual(
        pg::TransportSeedForStableTuple(
            9512ULL,
            11002ULL),
        342911087,
        "Transport known vector BCID 11002 changed");

    RequireEqual(
        pg::TransportSeedForStableTuple(
            9512ULL,
            11003ULL),
        1676149082,
        "Transport known vector BCID 11003 changed");

    const int reference =
        pg::TransportSeedForStableTuple(
            9512ULL,
            11000ULL);

    Require(
        reference ==
            pg::TransportSeedForStableTuple(
                9512ULL,
                11000ULL),
        "Transport seed is not deterministic");

    Require(
        reference !=
            pg::TransportSeedForStableTuple(
                9513ULL,
                11000ULL),
        "Transport seed ignores seed_base");

    Require(
        reference !=
            pg::TransportSeedForStableTuple(
                9512ULL,
                11001ULL),
        "Transport seed ignores BCID");

    for (std::uint64_t bcid = 0;
         bcid < 100000ULL;
         ++bcid) {

      const int seed =
          pg::TransportSeedForStableTuple(
              9512ULL,
              bcid);

      Require(
          seed >= 1,
          "Transport seed is not positive");

      Require(
          seed <=
              pg::kGeant4TransportMaximumSeed,
          "Transport seed exceeds maximum");
    }

    const auto pythiaStable =
        pg::StableSeed64(
            9512ULL,
            42ULL,
            0ULL,
            pg::SeedStream::kPythiaSubevent);

    const auto transportStable =
        pg::StableSeed64(
            9512ULL,
            42ULL,
            0ULL,
            pg::SeedStream::
                kGeant4TransportEvent);

    Require(
        pythiaStable != transportStable,
        "Transport stream is not domain separated");

    std::cout
        << "Event-stable Geant4 transport seed policy tests passed"
        << std::endl;

    return 0;

  } catch (const std::exception& error) {

    std::cerr
        << "Transport seed policy test failed: "
        << error.what()
        << std::endl;

    return 1;
  }
}
