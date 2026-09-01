#include "EventState.hh"

#include <iostream>
#include <stdexcept>

int main() {
  try {
    pg::EventState& state =
        pg::EventState::Instance();

    state.Reset(7, 11007);

    if (state.eventId != 7) {
      throw std::runtime_error(
          "EventState event ID reset failed");
    }

    if (state.bcid != 11007) {
      throw std::runtime_error(
          "EventState BCID reset failed");
    }

    if (state.geant4TransportSeed != 0) {
      throw std::runtime_error(
          "Transport seed was not cleared");
    }

    state.geant4TransportSeed = 123456789;

    state.Reset(8, 11008);

    if (state.geant4TransportSeed != 0) {
      throw std::runtime_error(
          "Transport seed leaked across events");
    }

    std::cout
        << "EventState transport-seed reset tests passed"
        << std::endl;

    return 0;

  } catch (const std::exception& error) {
    std::cerr
        << "EventState transport-seed test failed: "
        << error.what()
        << std::endl;

    return 1;
  }
}
