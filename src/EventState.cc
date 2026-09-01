#include "EventState.hh"

#include <algorithm>
#include <tuple>

namespace pg {

bool CellKey::operator<(const CellKey& other) const {
  return std::tie(subevent, sampling, side, etaIndex, phiIndex) <
         std::tie(other.subevent, other.sampling, other.side, other.etaIndex,
                  other.phiIndex);
}

EventState& EventState::Instance() {
  thread_local EventState instance;
  return instance;
}

void EventState::Reset(const int eventIdValue, const int bcidValue) {
  eventId = eventIdValue;
  bcid = bcidValue;
  requestedInteractions = 0;
  generatedInteractions = 0;
  generationFailures = 0;
  generatorParticles = 0;
  transportedParticles = 0;
  unknownPdgParticles = 0;
  rejectedNotFinal = 0;
  rejectedNeutrinoDisabled = 0;
  rejectedInvisibleNonNeutrino = 0;
  rejectedOutsideEtaAcceptance = 0;
  unlineagedSteps = 0;
  segmentationFailures = 0;
  geant4TransportSeed = 0;
  deposits.clear();
}

void EventState::RecordGeneratorDecision(
    const ParticleRejectionCode rejectionCode) {
  switch (rejectionCode) {
    case ParticleRejectionCode::kAccepted:
      break;
    case ParticleRejectionCode::kNotFinal:
      ++rejectedNotFinal;
      break;
    case ParticleRejectionCode::kNeutrinoDisabled:
      ++rejectedNeutrinoDisabled;
      break;
    case ParticleRejectionCode::kInvisibleNonNeutrino:
      ++rejectedInvisibleNonNeutrino;
      break;
    case ParticleRejectionCode::kOutsideEtaAcceptance:
      ++rejectedOutsideEtaAcceptance;
      break;
    case ParticleRejectionCode::kUnknownPdg:
      ++unknownPdgParticles;
      break;
  }
}

void EventState::RecordDeposit(const CellKey& key, const int subdetector,
                               const CellId cellId, const double etaCenter,
                               const double phiCenter, const double energyMeV,
                               const double timeNs, const int pdg,
                               const int trackId, const int parentId) {
  if (energyMeV <= 0.0) {
    return;
  }

  auto [iterator, inserted] = deposits.try_emplace(key);
  CellDeposit& deposit = iterator->second;
  if (inserted) {
    deposit.subdetector = subdetector;
    deposit.cellId = cellId;
    deposit.etaCenter = etaCenter;
    deposit.phiCenter = phiCenter;
    deposit.firstTimeNs = timeNs;
  } else {
    deposit.firstTimeNs = std::min(deposit.firstTimeNs, timeNs);
  }

  deposit.energyMeV += energyMeV;
  deposit.energyTimeMeVNs += energyMeV * timeNs;
  ++deposit.steps;

  if (energyMeV > deposit.largestStepMeV) {
    deposit.largestStepMeV = energyMeV;
    deposit.leadingPdg = pdg;
    deposit.leadingTrackId = trackId;
    deposit.leadingParentId = parentId;
  }
}

}  // namespace pg

