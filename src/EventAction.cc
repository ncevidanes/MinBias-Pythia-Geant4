#include "EventAction.hh"

#include "EventState.hh"
#include "RootOutput.hh"
#include "SeedPolicy.hh"

#include "G4Event.hh"
#include "G4Exception.hh"
#include "G4ios.hh"
#include "Randomize.hh"

#include <cstdint>
#include <utility>

namespace pg {

EventAction::EventAction(Configuration configuration)
    : configuration_(std::move(configuration)) {}

void EventAction::BeginOfEventAction(const G4Event* event) {
  EventState& state = EventState::Instance();

  const int eventId = event->GetEventID();
  const int bcid = configuration_.firstBcid + eventId;

  if (state.eventId != eventId || state.bcid != bcid) {
    G4ExceptionDescription message;

    message
        << "EventState/global-BCID mismatch before transport: "
        << "event=" << eventId
        << ", expected_bcid=" << bcid
        << ", state_event=" << state.eventId
        << ", state_bcid=" << state.bcid;

    G4Exception(
        "EventAction::BeginOfEventAction",
        "TransportSeedIdentity",
        FatalException,
        message);

    return;
  }

  const int transportSeed =
      TransportSeedForStableTuple(
          static_cast<std::uint64_t>(
              configuration_.seedBase),
          static_cast<std::uint64_t>(bcid));

  G4Random::setTheSeed(
      static_cast<long>(transportSeed));

  state.geant4TransportSeed = transportSeed;
}

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
