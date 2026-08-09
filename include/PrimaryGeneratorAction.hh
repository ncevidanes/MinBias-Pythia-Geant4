#ifndef PYTHIAGEANT_PRIMARYGENERATORACTION_HH
#define PYTHIAGEANT_PRIMARYGENERATORACTION_HH

#include "Configuration.hh"
#include "ParticleDecision.hh"

#include "G4VUserPrimaryGeneratorAction.hh"
#include "Pythia8/Pythia.h"

#include <memory>
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
  void AuditPythiaParticle(int eventId, int bcid, int subevent, int index,
                           ParticleRejectionCode rejectionCode);
  void GeneratePythiaPrimaries(G4Event* event);
  void GenerateSingleParticle(G4Event* event);

  Configuration configuration_;
  std::unique_ptr<Pythia8::Pythia> pythia_;
  std::mt19937_64 random_;
};

}  // namespace pg

#endif

