#include "CalorimeterSD.hh"

#include "EventState.hh"
#include "LineageInfo.hh"

#include "G4ParticleDefinition.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"

#include <cmath>
#include <utility>

namespace pg {
namespace {

double Pseudorapidity(const G4ThreeVector& position) {
  const double transverse =
      std::hypot(position.x(), position.y());
  const double theta = std::atan2(transverse, position.z());
  if (theta <= 0.0) {
    return 1.0e9;
  }
  if (theta >= 3.14159265358979323846) {
    return -1.0e9;
  }
  return -std::log(std::tan(0.5 * theta));
}

}  // namespace

CalorimeterSD::CalorimeterSD(const G4String& name, Sampling sampling)
    : G4VSensitiveDetector(name), segmentation_(std::move(sampling)) {}

G4bool CalorimeterSD::ProcessHits(G4Step* step,
                                  G4TouchableHistory* /*history*/) {
  const double energyMeV = step->GetTotalEnergyDeposit() / MeV;
  if (energyMeV <= 0.0) {
    return false;
  }

  const auto* preStep = step->GetPreStepPoint();
  const G4ThreeVector& position = preStep->GetPosition();
  const double eta = Pseudorapidity(position);
  const Sampling& sampling = segmentation_.Definition();
  if (std::abs(eta) > sampling.maxAbsEta) {
    return false;
  }

  const double phi = std::atan2(position.y(), position.x());
  const auto cell = segmentation_.Locate(eta, phi);
  if (!cell.has_value()) {
    ++EventState::Instance().segmentationFailures;
    return false;
  }

  const auto* track = step->GetTrack();
  const auto* lineage =
      dynamic_cast<const TrackLineageInfo*>(track->GetUserInformation());
  const int subevent = lineage ? lineage->Subevent() : -1;
  const int pdg = track->GetParticleDefinition()->GetPDGEncoding();

  EventState& state = EventState::Instance();
  if (lineage == nullptr) {
    ++state.unlineagedSteps;
  }

  const CellKey key{subevent,
                    cell->address.sampling,
                    cell->address.side,
                    cell->address.etaIndex,
                    cell->address.phiIndex};

  state.RecordDeposit(
      key, static_cast<int>(sampling.subdetector), cell->cellId,
      cell->etaCenter, cell->phiCenter, energyMeV,
      preStep->GetGlobalTime() / ns, pdg,
      track->GetTrackID(), track->GetParentID());

  return true;
}

}  // namespace pg
