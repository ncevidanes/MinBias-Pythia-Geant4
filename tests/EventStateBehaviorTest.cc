#include "EventState.hh"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireNear(const double actual, const double expected,
                 const double tolerance, const std::string& message) {
  Require(std::abs(actual - expected) <= tolerance, message);
}

void RequireCountersReset(const pg::EventState& state) {
  Require(state.requestedInteractions == 0,
          "requestedInteractions was not reset");
  Require(state.generatedInteractions == 0,
          "generatedInteractions was not reset");
  Require(state.generationFailures == 0, "generationFailures was not reset");
  Require(state.generatorParticles == 0, "generatorParticles was not reset");
  Require(state.transportedParticles == 0,
          "transportedParticles was not reset");
  Require(state.unknownPdgParticles == 0, "unknownPdgParticles was not reset");
  Require(state.rejectedNotFinal == 0, "rejectedNotFinal was not reset");
  Require(state.rejectedNeutrinoDisabled == 0,
          "rejectedNeutrinoDisabled was not reset");
  Require(state.rejectedInvisibleNonNeutrino == 0,
          "rejectedInvisibleNonNeutrino was not reset");
  Require(state.rejectedOutsideEtaAcceptance == 0,
          "rejectedOutsideEtaAcceptance was not reset");
  Require(state.unlineagedSteps == 0, "unlineagedSteps was not reset");
  Require(state.segmentationFailures == 0,
          "segmentationFailures was not reset");
  Require(state.geant4TransportSeed == 0,
          "geant4TransportSeed was not reset");
}

void CheckCellKeyOrdering() {
  const pg::CellKey baseline{1, 2, -1, 3, 4};

  Require(baseline < pg::CellKey{2, 2, -1, 3, 4},
          "CellKey subevent ordering failed");
  Require(baseline < pg::CellKey{1, 3, -1, 3, 4},
          "CellKey sampling ordering failed");
  Require(baseline < pg::CellKey{1, 2, 1, 3, 4},
          "CellKey side ordering failed");
  Require(baseline < pg::CellKey{1, 2, -1, 4, 4},
          "CellKey eta-index ordering failed");
  Require(baseline < pg::CellKey{1, 2, -1, 3, 5},
          "CellKey phi-index ordering failed");

  Require(!(baseline < baseline), "CellKey ordering is not irreflexive");
  Require(!(pg::CellKey{2, 2, -1, 3, 4} < baseline),
          "CellKey reverse ordering failed");
}

void CheckReset(pg::EventState& state) {
  state.eventId = 999;
  state.bcid = 998;
  state.requestedInteractions = 1;
  state.generatedInteractions = 2;
  state.generationFailures = 3;
  state.generatorParticles = 4;
  state.transportedParticles = 5;
  state.unknownPdgParticles = 6;
  state.rejectedNotFinal = 7;
  state.rejectedNeutrinoDisabled = 8;
  state.rejectedInvisibleNonNeutrino = 9;
  state.rejectedOutsideEtaAcceptance = 10;
  state.unlineagedSteps = 11;
  state.segmentationFailures = 12;
  state.geant4TransportSeed = 13;

  state.deposits.emplace(pg::CellKey{0, 0, 1, 0, 0}, pg::CellDeposit{});

  state.Reset(42, 12042);

  Require(state.eventId == 42, "eventId was not assigned during reset");
  Require(state.bcid == 12042, "bcid was not assigned during reset");
  RequireCountersReset(state);
  Require(state.deposits.empty(), "deposits were not cleared during reset");
}

void CheckGeneratorDecisions(pg::EventState& state) {
  state.Reset(1, 1001);

  state.RecordGeneratorDecision(pg::ParticleRejectionCode::kAccepted);

  Require(state.rejectedNotFinal == 0 &&
              state.rejectedNeutrinoDisabled == 0 &&
              state.rejectedInvisibleNonNeutrino == 0 &&
              state.rejectedOutsideEtaAcceptance == 0 &&
              state.unknownPdgParticles == 0,
          "Accepted generator decision changed rejection counters");

  state.RecordGeneratorDecision(pg::ParticleRejectionCode::kNotFinal);
  state.RecordGeneratorDecision(
      pg::ParticleRejectionCode::kNeutrinoDisabled);
  state.RecordGeneratorDecision(
      pg::ParticleRejectionCode::kInvisibleNonNeutrino);
  state.RecordGeneratorDecision(
      pg::ParticleRejectionCode::kOutsideEtaAcceptance);
  state.RecordGeneratorDecision(pg::ParticleRejectionCode::kUnknownPdg);

  Require(state.rejectedNotFinal == 1,
          "kNotFinal did not increment its counter");
  Require(state.rejectedNeutrinoDisabled == 1,
          "kNeutrinoDisabled did not increment its counter");
  Require(state.rejectedInvisibleNonNeutrino == 1,
          "kInvisibleNonNeutrino did not increment its counter");
  Require(state.rejectedOutsideEtaAcceptance == 1,
          "kOutsideEtaAcceptance did not increment its counter");
  Require(state.unknownPdgParticles == 1,
          "kUnknownPdg did not increment its counter");
}

void CheckDeposits(pg::EventState& state) {
  state.Reset(2, 1002);

  const pg::CellKey key{3, 4, -1, 5, 6};

  state.RecordDeposit(key, 7, 12345, 0.25, -1.25, 0.0, 9.0, 11, 10, 1);
  state.RecordDeposit(key, 7, 12345, 0.25, -1.25, -1.0, 9.0, 11, 10, 1);

  Require(state.deposits.empty(),
          "Non-positive energy created a calorimeter deposit");

  state.RecordDeposit(key, 7, 12345, 0.25, -1.25, 4.0, 10.0, 11, 10, 1);

  Require(state.deposits.size() == 1,
          "First positive deposit did not create exactly one cell");

  const pg::CellDeposit& first = state.deposits.at(key);

  Require(first.subdetector == 7, "Initial subdetector was not recorded");
  Require(first.cellId == 12345, "Initial cellId was not recorded");
  RequireNear(first.etaCenter, 0.25, 1.0e-12,
              "Initial eta center was not recorded");
  RequireNear(first.phiCenter, -1.25, 1.0e-12,
              "Initial phi center was not recorded");
  RequireNear(first.energyMeV, 4.0, 1.0e-12,
              "Initial deposited energy is incorrect");
  RequireNear(first.energyTimeMeVNs, 40.0, 1.0e-12,
              "Initial energy-time moment is incorrect");
  RequireNear(first.firstTimeNs, 10.0, 1.0e-12,
              "Initial first time is incorrect");
  RequireNear(first.largestStepMeV, 4.0, 1.0e-12,
              "Initial largest step is incorrect");
  Require(first.leadingPdg == 11, "Initial leading PDG is incorrect");
  Require(first.leadingTrackId == 10,
          "Initial leading track ID is incorrect");
  Require(first.leadingParentId == 1,
          "Initial leading parent ID is incorrect");
  Require(first.steps == 1, "Initial step count is incorrect");

  state.RecordDeposit(key, 99, 99999, 9.0, 8.0, 2.0, 5.0, 13, 20, 2);

  const pg::CellDeposit& second = state.deposits.at(key);

  Require(second.subdetector == 7,
          "Existing deposit unexpectedly changed subdetector");
  Require(second.cellId == 12345,
          "Existing deposit unexpectedly changed cellId");
  RequireNear(second.etaCenter, 0.25, 1.0e-12,
              "Existing deposit unexpectedly changed eta center");
  RequireNear(second.phiCenter, -1.25, 1.0e-12,
              "Existing deposit unexpectedly changed phi center");
  RequireNear(second.energyMeV, 6.0, 1.0e-12,
              "Accumulated deposited energy is incorrect");
  RequireNear(second.energyTimeMeVNs, 50.0, 1.0e-12,
              "Accumulated energy-time moment is incorrect");
  RequireNear(second.firstTimeNs, 5.0, 1.0e-12,
              "Earliest deposit time was not retained");
  RequireNear(second.largestStepMeV, 4.0, 1.0e-12,
              "Smaller step replaced the leading step");
  Require(second.leadingPdg == 11,
          "Smaller step replaced the leading PDG");
  Require(second.leadingTrackId == 10,
          "Smaller step replaced the leading track ID");
  Require(second.leadingParentId == 1,
          "Smaller step replaced the leading parent ID");
  Require(second.steps == 2, "Second step was not counted");

  state.RecordDeposit(key, 7, 12345, 0.25, -1.25, 6.0, 8.0, 22, 30, 3);

  const pg::CellDeposit& third = state.deposits.at(key);

  RequireNear(third.energyMeV, 12.0, 1.0e-12,
              "Third deposit energy was not accumulated");
  RequireNear(third.energyTimeMeVNs, 98.0, 1.0e-12,
              "Third deposit energy-time moment is incorrect");
  RequireNear(third.firstTimeNs, 5.0, 1.0e-12,
              "Later deposit changed the earliest time");
  RequireNear(third.largestStepMeV, 6.0, 1.0e-12,
              "Largest step was not updated");
  Require(third.leadingPdg == 22,
          "Largest step did not update leading PDG");
  Require(third.leadingTrackId == 30,
          "Largest step did not update leading track ID");
  Require(third.leadingParentId == 3,
          "Largest step did not update leading parent ID");
  Require(third.steps == 3, "Third step was not counted");

  const pg::CellKey otherKey{3, 4, 1, 5, 6};

  state.RecordDeposit(otherKey, 8, 54321, -0.25, 1.25, 1.0, 2.0, -11, 40,
                      4);

  Require(state.deposits.size() == 2,
          "Independent CellKey values did not produce independent deposits");
}

}  // namespace

int main() {
  try {
    pg::EventState& state = pg::EventState::Instance();

    Require(&state == &pg::EventState::Instance(),
            "EventState singleton identity changed");

    CheckCellKeyOrdering();
    CheckReset(state);
    CheckGeneratorDecisions(state);
    CheckDeposits(state);

    state.Reset(-1, -1);

    std::cout << "EventState behavior tests passed" << std::endl;
    return 0;

  } catch (const std::exception& error) {
    std::cerr << "EventState behavior test failed: " << error.what()
              << std::endl;
    return 1;
  }
}
