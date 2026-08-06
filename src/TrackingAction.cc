#include "TrackingAction.hh"

#include "LineageInfo.hh"

#include "G4DynamicParticle.hh"
#include "G4PrimaryParticle.hh"
#include "G4Track.hh"
#include "G4TrackingManager.hh"

namespace pg {

void TrackingAction::PreUserTrackingAction(const G4Track* track) {
  if (track->GetUserInformation() != nullptr || track->GetParentID() != 0) {
    return;
  }

  const auto* primaryParticle =
      track->GetDynamicParticle()->GetPrimaryParticle();
  if (primaryParticle == nullptr) {
    return;
  }

  const auto* primaryInfo = dynamic_cast<const PrimaryLineageInfo*>(
      primaryParticle->GetUserInformation());
  if (primaryInfo != nullptr) {
    fpTrackingManager->SetUserTrackInformation(
        new TrackLineageInfo(*primaryInfo));
  }
}

void TrackingAction::PostUserTrackingAction(const G4Track* track) {
  const auto* parentInfo =
      dynamic_cast<const TrackLineageInfo*>(track->GetUserInformation());
  if (parentInfo == nullptr) {
    return;
  }

  const auto* secondaries = fpTrackingManager->GimmeSecondaries();
  if (secondaries == nullptr) {
    return;
  }

  for (auto* secondary : *secondaries) {
    if (secondary->GetUserInformation() == nullptr) {
      secondary->SetUserInformation(new TrackLineageInfo(*parentInfo));
    }
  }
}

}  // namespace pg
