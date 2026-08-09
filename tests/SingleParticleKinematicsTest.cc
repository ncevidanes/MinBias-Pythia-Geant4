#include "SingleParticleKinematics.hh"

#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

constexpr double kPi = 3.14159265358979323846;

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireNear(const double actual, const double expected,
                 const double absoluteTolerance,
                 const double relativeTolerance,
                 const std::string& message) {
  const double tolerance =
      absoluteTolerance +
      relativeTolerance * std::max(std::abs(actual), std::abs(expected));
  Require(std::abs(actual - expected) <= tolerance, message);
}

void RequireInvalid(const std::function<void()>& action,
                    const std::string& message) {
  bool threw = false;
  try {
    action();
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  Require(threw, message);
}

double MomentumSquared(const pg::SingleParticleKinematics& value) {
  return value.pxGeV * value.pxGeV +
         value.pyGeV * value.pyGeV +
         value.pzGeV * value.pzGeV;
}

void CheckCentralPhoton() {
  const auto value = pg::MakeSingleParticleKinematics(
      10.0, 0.0, 0.0, 0.0);

  RequireNear(value.pxGeV, 10.0, 1.0e-14, 1.0e-14,
              "Central photon has incorrect px");
  RequireNear(value.pyGeV, 0.0, 1.0e-14, 1.0e-14,
              "Central photon has incorrect py");
  RequireNear(value.pzGeV, 0.0, 1.0e-14, 1.0e-14,
              "Central photon has incorrect pz");
  RequireNear(value.totalEnergyGeV, 10.0, 1.0e-14, 1.0e-14,
              "Photon total energy differs from its kinetic energy");
  RequireNear(value.totalEnergyGeV * value.totalEnergyGeV -
                  MomentumSquared(value),
              0.0, 1.0e-12, 1.0e-12,
              "Photon mass shell is not zero");
}

void CheckElectronMassShell() {
  constexpr double kElectronMassGeV = 0.00051099895;
  const auto value = pg::MakeSingleParticleKinematics(
      1.0, kElectronMassGeV, 1.0, 0.5 * kPi);

  RequireNear(value.totalEnergyGeV, 1.0 + kElectronMassGeV,
              1.0e-14, 1.0e-14,
              "Electron total energy is incorrect");
  RequireNear(value.totalEnergyGeV * value.totalEnergyGeV -
                  MomentumSquared(value),
              kElectronMassGeV * kElectronMassGeV,
              1.0e-12, 1.0e-10,
              "Electron is outside its relativistic mass shell");
  RequireNear(value.pxGeV, 0.0, 1.0e-14, 1.0e-14,
              "Electron phi direction has incorrect px");
  Require(value.pyGeV > 0.0 && value.pzGeV > 0.0,
          "Electron eta/phi signs are incorrect");
}

void CheckPionDirection() {
  constexpr double kPionMassGeV = 0.13957039;
  constexpr double kEta = -1.8;
  constexpr double kPhi = -0.25 * kPi;
  const auto value = pg::MakeSingleParticleKinematics(
      100.0, kPionMassGeV, kEta, kPhi);

  const double transverseMomentumGeV =
      std::hypot(value.pxGeV, value.pyGeV);
  const double reconstructedEta =
      std::asinh(value.pzGeV / transverseMomentumGeV);
  const double reconstructedPhi = std::atan2(value.pyGeV, value.pxGeV);

  RequireNear(reconstructedEta, kEta, 1.0e-13, 1.0e-13,
              "Pion pseudorapidity was not preserved");
  RequireNear(reconstructedPhi, kPhi, 1.0e-13, 1.0e-13,
              "Pion azimuth was not preserved");
  RequireNear(value.totalEnergyGeV * value.totalEnergyGeV -
                  MomentumSquared(value),
              kPionMassGeV * kPionMassGeV,
              1.0e-10, 1.0e-9,
              "Pion is outside its relativistic mass shell");
}

void CheckInvalidInputs() {
  RequireInvalid(
      [] { pg::MakeSingleParticleKinematics(0.0, 0.0, 0.0, 0.0); },
      "Zero kinetic energy was accepted");
  RequireInvalid(
      [] { pg::MakeSingleParticleKinematics(-1.0, 0.0, 0.0, 0.0); },
      "Negative kinetic energy was accepted");
  RequireInvalid(
      [] { pg::MakeSingleParticleKinematics(1.0, -1.0, 0.0, 0.0); },
      "Negative mass was accepted");
  RequireInvalid(
      [] {
        pg::MakeSingleParticleKinematics(
            1.0, 0.0, std::numeric_limits<double>::quiet_NaN(), 0.0);
      },
      "Non-finite eta was accepted");
  RequireInvalid(
      [] {
        pg::MakeSingleParticleKinematics(
            1.0, 0.0, 0.0,
            std::numeric_limits<double>::infinity());
      },
      "Non-finite phi was accepted");
}

}  // namespace

int main() {
  try {
    CheckCentralPhoton();
    CheckElectronMassShell();
    CheckPionDirection();
    CheckInvalidInputs();
    std::cout << "Single-particle kinematics tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Single-particle kinematics test failed: "
              << error.what() << std::endl;
    return 1;
  }
}
