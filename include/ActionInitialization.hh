#ifndef PYTHIAGEANT_ACTIONINITIALIZATION_HH
#define PYTHIAGEANT_ACTIONINITIALIZATION_HH

#include "Configuration.hh"

#include "G4VUserActionInitialization.hh"

namespace pg {

class ActionInitialization final : public G4VUserActionInitialization {
 public:
  explicit ActionInitialization(Configuration configuration);

  void BuildForMaster() const override;
  void Build() const override;

 private:
  Configuration configuration_;
};

}  // namespace pg

#endif

