#ifndef PYTHIAGEANT_PARTICLEDECISION_HH
#define PYTHIAGEANT_PARTICLEDECISION_HH

#include <cmath>

namespace pg {

enum class ParticleRejectionCode : int {
  kAccepted = 0,
  kNotFinal = 1,
  kNeutrinoDisabled = 2,
  kInvisibleNonNeutrino = 3,
  kOutsideEtaAcceptance = 4,
  kUnknownPdg = 5,
};

struct ParticleDecisionInput {
  bool isFinal = false;
  bool isVisible = false;
  bool transportNeutrinos = false;
  bool hasGeantDefinition = false;
  int pdg = 0;
  double eta = 0.0;
  double maxAbsEta = 0.0;
};

inline bool IsNeutrinoPdg(const int pdg) {
  const int absolute = std::abs(pdg);
  return absolute == 12 || absolute == 14 || absolute == 16 ||
         absolute == 18;
}

inline ParticleRejectionCode ClassifyParticle(
    const ParticleDecisionInput& input) {
  if (!input.isFinal) {
    return ParticleRejectionCode::kNotFinal;
  }

  const bool isNeutrino = IsNeutrinoPdg(input.pdg);
  if (isNeutrino && !input.transportNeutrinos) {
    return ParticleRejectionCode::kNeutrinoDisabled;
  }
  if (!input.isVisible && !isNeutrino) {
    return ParticleRejectionCode::kInvisibleNonNeutrino;
  }
  if (!std::isfinite(input.eta) ||
      std::abs(input.eta) > input.maxAbsEta) {
    return ParticleRejectionCode::kOutsideEtaAcceptance;
  }
  if (!input.hasGeantDefinition) {
    return ParticleRejectionCode::kUnknownPdg;
  }
  return ParticleRejectionCode::kAccepted;
}

}  // namespace pg

#endif
