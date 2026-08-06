#ifndef PYTHIAGEANT_TRACKINGACTION_HH
#define PYTHIAGEANT_TRACKINGACTION_HH

#include "G4UserTrackingAction.hh"

namespace pg {

class TrackingAction final : public G4UserTrackingAction {
 public:
  void PreUserTrackingAction(const G4Track* track) override;
  void PostUserTrackingAction(const G4Track* track) override;
};

}  // namespace pg

#endif

