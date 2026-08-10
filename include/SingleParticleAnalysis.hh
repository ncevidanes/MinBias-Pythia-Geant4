/*
 * MinBias-Pythia-Geant4
 * Copyright (C) 2026 Nelson Cevidanes Nascimento de Assis
 * SPDX-License-Identifier: GPL-3.0-only
 */

#ifndef PYTHIAGEANT_SINGLE_PARTICLE_ANALYSIS_HH
#define PYTHIAGEANT_SINGLE_PARTICLE_ANALYSIS_HH

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace pg {

inline constexpr std::size_t kSingleParticleSamplingCount = 10;

struct SingleParticleEventRecord {
  int event;
  double totalEnergyMeV;
};

struct SingleParticleHitRecord {
  int event;
  int sampling;
  double etaCenter;
  double phiCenter;
  double energyMeV;
};

struct SamplingAnalysisSummary {
  int sampling = 0;
  std::string name;
  double meanEnergyMeV = 0.0;
  double sampleStddevEnergyMeV = 0.0;
  double totalEnergyFraction = 0.0;
  double etaWidth = 0.0;
  double phiWidth = 0.0;
};

struct SingleParticleAnalysisSummary {
  std::size_t eventCount = 0;
  std::size_t hitCount = 0;
  double meanEnergyMeV = 0.0;
  double sampleStddevEnergyMeV = 0.0;
  double meanResponse = 0.0;
  double relativeResolution = 0.0;
  double samplingCentroid = 0.0;
  double samplingWidth = 0.0;
  double etaWidth = 0.0;
  double phiWidth = 0.0;
  std::array<SamplingAnalysisSummary,
             kSingleParticleSamplingCount> samplings{};
};

double NormalizePhiDifference(double angle);

SingleParticleAnalysisSummary AnalyzeSingleParticleRecords(
    double kineticEnergyGeV,
    const std::vector<SingleParticleEventRecord>& events,
    const std::vector<SingleParticleHitRecord>& hits,
    double absoluteEnergyToleranceMeV = 1.0e-9,
    double relativeEnergyTolerance = 1.0e-9);

}  // namespace pg

#endif
