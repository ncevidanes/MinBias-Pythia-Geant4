#ifndef PYTHIAGEANT_SINGLEPARTICLEKINEMATICS_HH
#define PYTHIAGEANT_SINGLEPARTICLEKINEMATICS_HH

#include <cmath>
#include <stdexcept>

namespace pg {

struct SingleParticleKinematics {
  double pxGeV = 0.0;
  double pyGeV = 0.0;
  double pzGeV = 0.0;
  double totalEnergyGeV = 0.0;
};

inline SingleParticleKinematics MakeSingleParticleKinematics(
    const double kineticEnergyGeV, const double massGeV, const double eta,
    const double phi) {
  if (!std::isfinite(kineticEnergyGeV) || kineticEnergyGeV <= 0.0) {
    throw std::invalid_argument(
        "single_particle_kinetic_energy_gev must be finite and positive");
  }
  if (!std::isfinite(massGeV) || massGeV < 0.0) {
    throw std::invalid_argument(
        "single-particle mass must be finite and non-negative");
  }
  if (!std::isfinite(eta)) {
    throw std::invalid_argument("single_particle_eta must be finite");
  }
  if (!std::isfinite(phi)) {
    throw std::invalid_argument("single_particle_phi must be finite");
  }

  const double totalEnergyGeV = kineticEnergyGeV + massGeV;
  const double momentumSecondFactorGeV =
      kineticEnergyGeV + 2.0 * massGeV;
  if (!std::isfinite(totalEnergyGeV) ||
      !std::isfinite(momentumSecondFactorGeV)) {
    throw std::overflow_error(
        "single-particle energy lies outside the supported range");
  }

  const double momentumGeV =
      std::sqrt(kineticEnergyGeV) *
      std::sqrt(momentumSecondFactorGeV);
  const double coshEta = std::cosh(eta);
  if (!std::isfinite(momentumGeV) || !std::isfinite(coshEta)) {
    throw std::overflow_error(
        "single-particle momentum lies outside the supported range");
  }

  const double transverseMomentumGeV = momentumGeV / coshEta;
  const SingleParticleKinematics result{
      transverseMomentumGeV * std::cos(phi),
      transverseMomentumGeV * std::sin(phi),
      momentumGeV * std::tanh(eta),
      totalEnergyGeV,
  };

  if (!std::isfinite(result.pxGeV) || !std::isfinite(result.pyGeV) ||
      !std::isfinite(result.pzGeV)) {
    throw std::overflow_error(
        "single-particle momentum components are not finite");
  }
  return result;
}

}  // namespace pg

#endif
