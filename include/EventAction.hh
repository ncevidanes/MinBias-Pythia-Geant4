#ifndef PYTHIAGEANT_EVENTACTION_HH
#define PYTHIAGEANT_EVENTACTION_HH

#include "Configuration.hh"

#include "G4UserEventAction.hh"

class G4Event;

namespace pg {

class EventAction final : public G4UserEventAction {
 public:
  explicit EventAction(Configuration configuration);

  void EndOfEventAction(const G4Event* event) override;

 private:
  Configuration configuration_;
};

}  // namespace pg

#endif

