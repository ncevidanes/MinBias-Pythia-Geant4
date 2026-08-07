#include "ParticleDecision.hh"

#include <iostream>
#include <limits>

namespace {

int failures = 0;

void Expect(const char* name, pg::ParticleDecisionInput input,
            const pg::ParticleRejectionCode expected) {
  const auto actual = pg::ClassifyParticle(input);
  if (actual != expected) {
    std::cerr << name << ": esperado " << static_cast<int>(expected)
              << ", obtido " << static_cast<int>(actual) << '\n';
    ++failures;
  }
}

pg::ParticleDecisionInput ValidParticle() {
  pg::ParticleDecisionInput input;
  input.isFinal = true;
  input.isVisible = true;
  input.hasGeantDefinition = true;
  input.maxAbsEta = 1.8;
  input.pdg = 211;
  return input;
}

}  // namespace

int main() {
  auto input = ValidParticle();
  Expect("accepted", input, pg::ParticleRejectionCode::kAccepted);

  input = ValidParticle();
  input.isFinal = false;
  Expect("not_final", input, pg::ParticleRejectionCode::kNotFinal);

  input = ValidParticle();
  input.pdg = 12;
  input.isVisible = false;
  Expect("neutrino_disabled", input,
         pg::ParticleRejectionCode::kNeutrinoDisabled);

  input.transportNeutrinos = true;
  Expect("neutrino_enabled", input, pg::ParticleRejectionCode::kAccepted);

  input = ValidParticle();
  input.isVisible = false;
  Expect("invisible_non_neutrino", input,
         pg::ParticleRejectionCode::kInvisibleNonNeutrino);

  input = ValidParticle();
  input.eta = 1.800001;
  Expect("outside_eta", input,
         pg::ParticleRejectionCode::kOutsideEtaAcceptance);

  input.eta = 1.8;
  Expect("eta_boundary_inclusive", input,
         pg::ParticleRejectionCode::kAccepted);

  input.eta = std::numeric_limits<double>::quiet_NaN();
  Expect("non_finite_eta", input,
         pg::ParticleRejectionCode::kOutsideEtaAcceptance);

  input = ValidParticle();
  input.hasGeantDefinition = false;
  Expect("unknown_pdg", input, pg::ParticleRejectionCode::kUnknownPdg);

  if (failures != 0) {
    return 1;
  }
  std::cout << "ParticleDecisionTest: OK\n";
  return 0;
}
