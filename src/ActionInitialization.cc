#include "ActionInitialization.hh"

#include "EventAction.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "TrackingAction.hh"

#include <utility>

namespace pg {

ActionInitialization::ActionInitialization(Configuration configuration)
    : configuration_(std::move(configuration)) {}

void ActionInitialization::BuildForMaster() const {
  SetUserAction(new RunAction(configuration_));
}

void ActionInitialization::Build() const {
  SetUserAction(new RunAction(configuration_));
  SetUserAction(new PrimaryGeneratorAction(configuration_));
  SetUserAction(new EventAction(configuration_));
  SetUserAction(new TrackingAction());
}

}  // namespace pg
