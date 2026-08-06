#include "RunAction.hh"

#include "RootOutput.hh"

#include <utility>

namespace pg {

RunAction::RunAction(Configuration configuration)
    : configuration_(std::move(configuration)) {
  RootOutput::Book();
}

void RunAction::BeginOfRunAction(const G4Run* /*run*/) {
  RootOutput::BeginRun(configuration_);
}

void RunAction::EndOfRunAction(const G4Run* /*run*/) {
  RootOutput::EndRun();
}

}  // namespace pg
