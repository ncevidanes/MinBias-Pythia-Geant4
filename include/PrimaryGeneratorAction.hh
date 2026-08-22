#ifndef PYTHIAGEANT_PRIMARYGENERATORACTION_HH
#define PYTHIAGEANT_PRIMARYGENERATORACTION_HH

#include "Configuration.hh"
#include "ParticleDecision.hh"
#include "SeedPolicy.hh"

#include "G4VUserPrimaryGeneratorAction.hh"
#include "Pythia8/Pythia.h"

#include <memory>

class G4Event;

namespace pg {

class PrimaryGeneratorAction final
    : public G4VUserPrimaryGeneratorAction {
 public:
  explicit PrimaryGeneratorAction(Configuration configuration);

  void GeneratePrimaries(G4Event* event) override;

 private:
  int DrawInteractionCount(int bcid) const;
  double DrawGaussian(int bcid, int subevent,
                      SeedStream stream,
                      double sigma) const;
  void AuditPythiaParticle(int eventId, int bcid, int subevent, int index,
                           ParticleRejectionCode rejectionCode);
  void GeneratePythiaPrimaries(G4Event* event);
  void GenerateSingleParticle(G4Event* event);

  Configuration configuration_;
  std::unique_ptr<Pythia8::Pythia> pythia_;
};

}  // namespace pg

#endif

