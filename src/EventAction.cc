#include "EventAction.hh"

#include "EventState.hh"
#include "RootOutput.hh"

#include "G4Event.hh"
#include "G4ios.hh"

#include <utility>

namespace pg {

EventAction::EventAction(Configuration configuration)
    : configuration_(std::move(configuration)) {}

void EventAction::EndOfEventAction(const G4Event* event) {
  RootOutput::WriteEventAndHits(configuration_);

  if (event->GetEventID() % configuration_.printEvery == 0) {
    const EventState& state = EventState::Instance();
    G4cout << "[BC " << state.bcid << "] interações "
           << state.generatedInteractions << '/'
           << state.requestedInteractions << ", primárias transportadas "
           << state.transportedParticles << ", células/subeventos "
           << state.deposits.size() << G4endl;
  }
}

}  // namespace pg
