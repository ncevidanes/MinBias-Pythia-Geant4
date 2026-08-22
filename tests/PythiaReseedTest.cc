#include "SeedPolicy.hh"

#include "Pythia8/Pythia.h"

#include <cstdint>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct ParticleSnapshot {
  int id = 0;
  int status = 0;
  int mother1 = 0;
  int mother2 = 0;
  int daughter1 = 0;
  int daughter2 = 0;
  int isFinal = 0;
  int isVisible = 0;

  double px = 0.0;
  double py = 0.0;
  double pz = 0.0;
  double e = 0.0;
  double m = 0.0;
  double xProd = 0.0;
  double yProd = 0.0;
  double zProd = 0.0;
  double tProd = 0.0;

  bool operator==(const ParticleSnapshot& other) const {
    return
        id == other.id &&
        status == other.status &&
        mother1 == other.mother1 &&
        mother2 == other.mother2 &&
        daughter1 == other.daughter1 &&
        daughter2 == other.daughter2 &&
        isFinal == other.isFinal &&
        isVisible == other.isVisible &&
        px == other.px &&
        py == other.py &&
        pz == other.pz &&
        e == other.e &&
        m == other.m &&
        xProd == other.xProd &&
        yProd == other.yProd &&
        zProd == other.zProd &&
        tProd == other.tProd;
  }
};

using EventSnapshot = std::vector<ParticleSnapshot>;

void Require(
    const bool condition,
    const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

EventSnapshot SnapshotEvent(
    const Pythia8::Event& event) {
  EventSnapshot snapshot;
  snapshot.reserve(
      static_cast<std::size_t>(event.size()));

  for (int index = 0; index < event.size(); ++index) {
    const auto& particle = event[index];

    snapshot.push_back(ParticleSnapshot{
        particle.id(),
        particle.status(),
        particle.mother1(),
        particle.mother2(),
        particle.daughter1(),
        particle.daughter2(),
        particle.isFinal() ? 1 : 0,
        particle.isVisible() ? 1 : 0,
        particle.px(),
        particle.py(),
        particle.pz(),
        particle.e(),
        particle.m(),
        particle.xProd(),
        particle.yProd(),
        particle.zProd(),
        particle.tProd(),
    });
  }

  return snapshot;
}

void RequireEqual(
    const EventSnapshot& first,
    const EventSnapshot& second,
    const std::string& message) {
  if (first.size() != second.size()) {
    throw std::runtime_error(
        message +
        ": different event sizes (" +
        std::to_string(first.size()) +
        " vs " +
        std::to_string(second.size()) +
        ")");
  }

  for (std::size_t index = 0;
       index < first.size();
       ++index) {
    if (!(first[index] == second[index])) {
      throw std::runtime_error(
          message +
          ": first difference at particle " +
          std::to_string(index));
    }
  }
}

bool EventsDiffer(
    const EventSnapshot& first,
    const EventSnapshot& second) {
  if (first.size() != second.size()) {
    return true;
  }

  for (std::size_t index = 0;
       index < first.size();
       ++index) {
    if (!(first[index] == second[index])) {
      return true;
    }
  }

  return false;
}

std::unique_ptr<Pythia8::Pythia> MakePythia(
    const std::string& configurationPath,
    const std::uint64_t seedBase) {
  auto pythia =
      std::make_unique<Pythia8::Pythia>();

  Require(
      pythia->readFile(configurationPath),
      "Failed to read PYTHIA configuration");

  /*
   * Keep the unit test quiet without changing the physics
   * configuration.
   */
  Require(
      pythia->readString(
          "Init:showChangedSettings = off"),
      "Failed to disable changed-settings printout");

  Require(
      pythia->readString(
          "Init:showChangedParticleData = off"),
      "Failed to disable particle-data printout");

  Require(
      pythia->readString(
          "Next:numberShowInfo = 0"),
      "Failed to disable event-info printout");

  Require(
      pythia->readString(
          "Next:numberShowProcess = 0"),
      "Failed to disable process printout");

  Require(
      pythia->readString(
          "Next:numberShowEvent = 0"),
      "Failed to disable event printout");

  const int initializationSeed =
      pg::PythiaSeedForStableTuple(
          seedBase,
          0ULL,
          0ULL,
          pg::SeedStream::kPythiaInitialization);

  Require(
      pythia->readString("Random:setSeed = on"),
      "Failed to enable PYTHIA explicit seed");

  Require(
      pythia->readString(
          "Random:seed = " +
          std::to_string(initializationSeed)),
      "Failed to set PYTHIA initialization seed");

  Require(
      pythia->init(),
      "PYTHIA initialization failed");

  return pythia;
}

EventSnapshot GenerateStableEvent(
    Pythia8::Pythia& pythia,
    const std::uint64_t seedBase,
    const std::uint64_t bcid,
    const std::uint64_t subevent) {
  const int seed =
      pg::PythiaSeedForStableTuple(
          seedBase,
          bcid,
          subevent,
          pg::SeedStream::kPythiaSubevent);

  Require(
      seed >= 1 &&
          seed <= pg::kPythiaMaximumSeed,
      "Derived PYTHIA seed is outside valid interval");

  /*
   * Rndm::init() is the Cycle 10 event-stable boundary:
   * no previous worker history is allowed to choose the
   * random sequence for this subevent.
   */
  pythia.rndm.init(seed);

  Require(
      pythia.next(),
      "PYTHIA event generation failed");

  return SnapshotEvent(pythia.event);
}

void CheckIndependentInstances(
    const std::string& configurationPath) {
  constexpr std::uint64_t kSeedBase = 9512ULL;
  constexpr std::uint64_t kBcid = 42ULL;

  auto first =
      MakePythia(configurationPath, kSeedBase);

  auto second =
      MakePythia(configurationPath, kSeedBase);

  const auto firstEvent =
      GenerateStableEvent(
          *first,
          kSeedBase,
          kBcid,
          0ULL);

  const auto secondEvent =
      GenerateStableEvent(
          *second,
          kSeedBase,
          kBcid,
          0ULL);

  RequireEqual(
      firstEvent,
      secondEvent,
      "Independent PYTHIA instances diverged");
}

void CheckHistoryIndependence(
    const std::string& configurationPath) {
  constexpr std::uint64_t kSeedBase = 9512ULL;
  constexpr std::uint64_t kTargetBcid = 42ULL;

  auto reference =
      MakePythia(configurationPath, kSeedBase);

  const auto referenceEvent =
      GenerateStableEvent(
          *reference,
          kSeedBase,
          kTargetBcid,
          0ULL);

  auto withHistory =
      MakePythia(configurationPath, kSeedBase);

  for (std::uint64_t bcid = 100ULL;
       bcid < 108ULL;
       ++bcid) {
    (void)GenerateStableEvent(
        *withHistory,
        kSeedBase,
        bcid,
        bcid % 3ULL);
  }

  const auto afterHistory =
      GenerateStableEvent(
          *withHistory,
          kSeedBase,
          kTargetBcid,
          0ULL);

  RequireEqual(
      referenceEvent,
      afterHistory,
      "PYTHIA event depended on previous worker history");
}

void CheckSameInstanceReseed(
    const std::string& configurationPath) {
  constexpr std::uint64_t kSeedBase = 9512ULL;
  constexpr std::uint64_t kTargetBcid = 77ULL;

  auto pythia =
      MakePythia(configurationPath, kSeedBase);

  const auto first =
      GenerateStableEvent(
          *pythia,
          kSeedBase,
          kTargetBcid,
          1ULL);

  (void)GenerateStableEvent(
      *pythia,
      kSeedBase,
      800ULL,
      0ULL);

  (void)GenerateStableEvent(
      *pythia,
      kSeedBase,
      801ULL,
      2ULL);

  const auto second =
      GenerateStableEvent(
          *pythia,
          kSeedBase,
          kTargetBcid,
          1ULL);

  RequireEqual(
      first,
      second,
      "Reinitializing the same PYTHIA RNG did not reproduce the event");
}

void CheckSeedSensitivity(
    const std::string& configurationPath) {
  constexpr std::uint64_t kSeedBase = 9512ULL;

  auto first =
      MakePythia(configurationPath, kSeedBase);

  auto second =
      MakePythia(configurationPath, kSeedBase);

  auto third =
      MakePythia(configurationPath, kSeedBase + 1ULL);

  const auto reference =
      GenerateStableEvent(
          *first,
          kSeedBase,
          42ULL,
          0ULL);

  const auto differentBcid =
      GenerateStableEvent(
          *second,
          kSeedBase,
          43ULL,
          0ULL);

  const auto differentSeedBase =
      GenerateStableEvent(
          *third,
          kSeedBase + 1ULL,
          42ULL,
          0ULL);

  Require(
      EventsDiffer(reference, differentBcid),
      "Changing BCID did not change PYTHIA event");

  Require(
      EventsDiffer(reference, differentSeedBase),
      "Changing seed_base did not change PYTHIA event");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 2) {
      throw std::runtime_error(
          "Usage: pythia_reseed_test PYTHIA_CONFIG");
    }

    const std::string configurationPath = argv[1];

    CheckIndependentInstances(configurationPath);
    CheckHistoryIndependence(configurationPath);
    CheckSameInstanceReseed(configurationPath);
    CheckSeedSensitivity(configurationPath);

    std::cout
        << "PYTHIA event-stable reseed tests passed"
        << std::endl;

    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "PYTHIA event-stable reseed test failed: "
        << error.what()
        << std::endl;

    return 1;
  }
}
