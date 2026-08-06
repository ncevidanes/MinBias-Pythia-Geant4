#ifndef PYTHIAGEANT_RUNACTION_HH
#define PYTHIAGEANT_RUNACTION_HH

#include "Configuration.hh"

#include "G4UserRunAction.hh"

class G4Run;

namespace pg {

class RunAction final : public G4UserRunAction {
 public:
  explicit RunAction(Configuration configuration);

  void BeginOfRunAction(const G4Run* run) override;
  void EndOfRunAction(const G4Run* run) override;

 private:
  Configuration configuration_;
};

}  // namespace pg

#endif

