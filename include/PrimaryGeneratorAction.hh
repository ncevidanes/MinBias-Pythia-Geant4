#ifndef PYTHIAGEANT_PRIMARYGENERATORACTION_HH
#define PYTHIAGEANT_PRIMARYGENERATORACTION_HH

#include "Configuration.hh"

#include "G4VUserPrimaryGeneratorAction.hh"
#include "Pythia8/Pythia.h"

#include <random>

class G4Event;

namespace pg {

class PrimaryGeneratorAction final
    : public G4VUserPrimaryGeneratorAction {
 public:
  explicit PrimaryGeneratorAction(Configuration configuration);

  void GeneratePrimaries(G4Event* event) override;

 private:
  int DrawInteractionCount();
  double DrawGaussian(double sigma);
  void AuditPythiaEvent(int eventId, int bcid, int subevent);
  bool IsNeutrino(int pdg) const;

  Configuration configuration_;
  Pythia8::Pythia pythia_;
  std::mt19937_64 random_;
};

}  // namespace pg

#endif

