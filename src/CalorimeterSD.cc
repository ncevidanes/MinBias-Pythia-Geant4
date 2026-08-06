#include "CalorimeterSD.hh"

#include "EventState.hh"
#include "LineageInfo.hh"

#include "G4ParticleDefinition.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Track.hh"

#include <algorithm>
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
    : G4VSensitiveDetector(name), sampling_(std::move(sampling)) {}

G4bool CalorimeterSD::ProcessHits(G4Step* step,
                                  G4TouchableHistory* /*history*/) {
  const double energyMeV = step->GetTotalEnergyDeposit() / MeV;
  if (energyMeV <= 0.0) {
    return false;
  }

  const auto* preStep = step->GetPreStepPoint();
  const G4ThreeVector& position = preStep->GetPosition();
  const double eta = Pseudorapidity(position);
  if (std::abs(eta) >= sampling_.maxAbsEta) {
    return false;
  }

  constexpr double pi = 3.14159265358979323846;
  const int numberEtaBins =
      static_cast<int>(std::ceil(2.0 * sampling_.maxAbsEta /
                                 sampling_.deltaEta));
  const int numberPhiBins =
      static_cast<int>(std::lround(2.0 * pi / sampling_.deltaPhi));

  int etaIndex = static_cast<int>(
      std::floor((eta + sampling_.maxAbsEta) / sampling_.deltaEta));
  double phi = std::atan2(position.y(), position.x());
  int phiIndex =
      static_cast<int>(std::floor((phi + pi) / sampling_.deltaPhi));

  etaIndex = std::clamp(etaIndex, 0, numberEtaBins - 1);
  phiIndex = std::clamp(phiIndex, 0, numberPhiBins - 1);

  const double etaCenter =
      -sampling_.maxAbsEta + (etaIndex + 0.5) * sampling_.deltaEta;
  const double phiCenter = -pi + (phiIndex + 0.5) * sampling_.deltaPhi;
  const int side =
      sampling_.zCenterMm < 0.0 ? -1 : (sampling_.zCenterMm > 0.0 ? 1 : 0);

  const auto* track = step->GetTrack();
  const auto* lineage =
      dynamic_cast<const TrackLineageInfo*>(track->GetUserInformation());
  const int subevent = lineage ? lineage->Subevent() : -1;
  const int pdg = track->GetParticleDefinition()->GetPDGEncoding();

  const CellKey key{subevent, sampling_.id, side, etaIndex, phiIndex};
  const double cellId =
      sampling_.id * 100000000.0 + (side + 1) * 10000000.0 +
      etaIndex * 1000.0 + phiIndex;

  EventState::Instance().RecordDeposit(
      key, static_cast<int>(sampling_.subdetector), cellId, etaCenter,
      phiCenter, energyMeV, preStep->GetGlobalTime() / ns, pdg,
      track->GetTrackID(), track->GetParentID());

  return true;
}

}  // namespace pg
