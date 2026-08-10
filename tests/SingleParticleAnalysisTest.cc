/*
 * MinBias-Pythia-Geant4
 * Copyright (C) 2026 Nelson Cevidanes Nascimento de Assis
 * SPDX-License-Identifier: GPL-3.0-only
 */

#include "SingleParticleAnalysis.hh"

#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double kPi = 3.14159265358979323846;

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireNear(const double actual, const double expected,
                 const double tolerance,
                 const std::string& message) {
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

std::vector<pg::SingleParticleEventRecord> ValidEvents() {
  return {
      {10, 2.0},
      {11, 4.0},
  };
}

std::vector<pg::SingleParticleHitRecord> ValidHits() {
  return {
      {10, 0, 0.0, kPi - 0.1, 1.0},
      {10, 1, 2.0, -kPi + 0.1, 1.0},
      {11, 0, 0.0, kPi - 0.1, 2.0},
      {11, 1, 2.0, -kPi + 0.1, 2.0},
  };
}

void CheckNominalAnalysis() {
  const auto result =
      pg::AnalyzeSingleParticleRecords(
          0.006, ValidEvents(), ValidHits());

  Require(result.eventCount == 2,
          "Incorrect event count");
  Require(result.hitCount == 4,
          "Incorrect hit count");
  RequireNear(result.meanEnergyMeV, 3.0, 1.0e-12,
              "Incorrect mean energy");
  RequireNear(result.sampleStddevEnergyMeV, std::sqrt(2.0),
              1.0e-12, "Incorrect sample standard deviation");
  RequireNear(result.meanResponse, 0.5, 1.0e-12,
              "Incorrect response");
  RequireNear(result.relativeResolution, std::sqrt(2.0) / 3.0,
              1.0e-12, "Incorrect relative resolution");
  RequireNear(result.samplingCentroid, 0.5, 1.0e-12,
              "Incorrect sampling centroid");
  RequireNear(result.samplingWidth, 0.5, 1.0e-12,
              "Incorrect sampling width");
  RequireNear(result.etaWidth, 1.0, 1.0e-12,
              "Incorrect eta width");
  RequireNear(result.phiWidth, 0.1, 1.0e-12,
              "Phi wrapping was not applied");

  Require(result.samplings.size() == 10,
          "Incorrect number of sampling summaries");
  Require(result.samplings[0].name == "PSB",
          "Incorrect first sampling name");
  Require(result.samplings[9].name == "TileExt3",
          "Incorrect last sampling name");

  for (const std::size_t index : {0U, 1U}) {
    const auto& sampling = result.samplings[index];
    RequireNear(sampling.meanEnergyMeV, 1.5, 1.0e-12,
                "Incorrect sampling mean");
    RequireNear(sampling.sampleStddevEnergyMeV,
                std::sqrt(0.5), 1.0e-12,
                "Incorrect sampling standard deviation");
    RequireNear(sampling.totalEnergyFraction, 0.5, 1.0e-12,
                "Incorrect sampling energy fraction");
  }

  for (std::size_t index = 2;
       index < result.samplings.size(); ++index) {
    RequireNear(result.samplings[index].meanEnergyMeV,
                0.0, 1.0e-12,
                "Empty sampling has non-zero energy");
  }
}

void CheckPhiNormalization() {
  RequireNear(
      pg::NormalizePhiDifference(2.0 * kPi + 0.25),
      0.25, 1.0e-12,
      "Positive phi wrapping failed");
  RequireNear(
      pg::NormalizePhiDifference(-2.0 * kPi - 0.25),
      -0.25, 1.0e-12,
      "Negative phi wrapping failed");
  RequireNear(
      pg::NormalizePhiDifference(kPi),
      -kPi, 1.0e-12,
      "Pi boundary is not canonical");
}

void CheckInvalidInputs() {
  const auto events = ValidEvents();
  const auto hits = ValidHits();

  RequireInvalid(
      [&] {
        (void)pg::AnalyzeSingleParticleRecords(
            0.0, events, hits);
      },
      "Zero kinetic energy was accepted");

  RequireInvalid(
      [&] {
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, {}, {});
      },
      "Empty event collection was accepted");

  RequireInvalid(
      [&] {
        auto invalid = events;
        invalid[1].event = invalid[0].event;
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, invalid, hits);
      },
      "Duplicate event identifier was accepted");

  RequireInvalid(
      [&] {
        auto invalid = hits;
        invalid[0].sampling = 10;
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, events, invalid);
      },
      "Invalid sampling was accepted");

  RequireInvalid(
      [&] {
        auto invalid = hits;
        invalid[0].event = 999;
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, events, invalid);
      },
      "Unknown event reference was accepted");

  RequireInvalid(
      [&] {
        auto invalid = hits;
        invalid[0].energyMeV = -1.0;
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, events, invalid);
      },
      "Negative hit energy was accepted");

  RequireInvalid(
      [&] {
        auto invalid = hits;
        invalid[0].etaCenter =
            std::numeric_limits<double>::quiet_NaN();
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, events, invalid);
      },
      "Non-finite hit coordinate was accepted");

  RequireInvalid(
      [&] {
        auto invalid = events;
        invalid[0].totalEnergyMeV += 0.01;
        (void)pg::AnalyzeSingleParticleRecords(
            1.0, invalid, hits);
      },
      "Inconsistent event and hit energies were accepted");
}

}  // namespace

int main() {
  try {
    CheckNominalAnalysis();
    CheckPhiNormalization();
    CheckInvalidInputs();

    std::cout
        << "Single-particle analysis tests passed"
        << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "Single-particle analysis test failed: "
        << error.what() << std::endl;
    return 1;
  }
}
