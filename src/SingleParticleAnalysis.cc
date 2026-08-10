/*
 * MinBias-Pythia-Geant4
 * Copyright (C) 2026 Nelson Cevidanes Nascimento de Assis
 * SPDX-License-Identifier: GPL-3.0-only
 */

#include "SingleParticleAnalysis.hh"

#include "Sampling.hh"

#include <algorithm>
#include <array>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace pg {
namespace {

constexpr double kPi = 3.14159265358979323846;

struct LinearMoments {
  double weight = 0.0;
  double weightedValue = 0.0;
  double weightedSquare = 0.0;

  void Add(const double value, const double newWeight) {
    weight += newWeight;
    weightedValue += newWeight * value;
    weightedSquare += newWeight * value * value;
  }

  double Mean() const {
    return weight > 0.0 ? weightedValue / weight : 0.0;
  }

  double Width() const {
    if (weight <= 0.0) {
      return 0.0;
    }
    const double mean = Mean();
    const double variance =
        std::max(0.0, weightedSquare / weight - mean * mean);
    return std::sqrt(variance);
  }
};

struct PhiMoments {
  double weight = 0.0;
  double weightedSin = 0.0;
  double weightedCos = 0.0;
  double weightedDistanceSquare = 0.0;

  void Add(const double phi, const double newWeight) {
    weight += newWeight;
    weightedSin += newWeight * std::sin(phi);
    weightedCos += newWeight * std::cos(phi);
  }

  double Center() const {
    if (weight <= 0.0) {
      return 0.0;
    }
    return std::atan2(weightedSin, weightedCos);
  }

  void AddDistance(const double phi, const double newWeight) {
    const double difference =
        NormalizePhiDifference(phi - Center());
    weightedDistanceSquare +=
        newWeight * difference * difference;
  }

  double Width() const {
    return weight > 0.0
               ? std::sqrt(weightedDistanceSquare / weight)
               : 0.0;
  }
};

std::pair<double, double> SampleStatistics(
    const std::vector<double>& values) {
  const double sum =
      std::accumulate(values.begin(), values.end(), 0.0);
  const double mean = sum / static_cast<double>(values.size());

  if (values.size() < 2) {
    return {mean, 0.0};
  }

  double squaredDifferences = 0.0;
  for (const double value : values) {
    const double difference = value - mean;
    squaredDifferences += difference * difference;
  }

  return {
      mean,
      std::sqrt(
          squaredDifferences /
          static_cast<double>(values.size() - 1)),
  };
}

bool NearlyEqual(const double first, const double second,
                 const double absoluteTolerance,
                 const double relativeTolerance) {
  const double scale =
      std::max(std::abs(first), std::abs(second));
  return std::abs(first - second) <=
         absoluteTolerance + relativeTolerance * scale;
}

void RequireFiniteNonnegative(const double value,
                              const std::string& description) {
  if (!std::isfinite(value) || value < 0.0) {
    throw std::invalid_argument(
        description + " must be finite and non-negative");
  }
}

}  // namespace

double NormalizePhiDifference(const double angle) {
  if (!std::isfinite(angle)) {
    throw std::invalid_argument(
        "Phi difference must be finite");
  }

  constexpr double twoPi = 2.0 * kPi;
  double normalized = std::fmod(angle + kPi, twoPi);
  if (normalized < 0.0) {
    normalized += twoPi;
  }
  return normalized - kPi;
}

SingleParticleAnalysisSummary AnalyzeSingleParticleRecords(
    const double kineticEnergyGeV,
    const std::vector<SingleParticleEventRecord>& events,
    const std::vector<SingleParticleHitRecord>& hits,
    const double absoluteEnergyToleranceMeV,
    const double relativeEnergyTolerance) {
  if (!std::isfinite(kineticEnergyGeV) ||
      kineticEnergyGeV <= 0.0) {
    throw std::invalid_argument(
        "Kinetic energy must be finite and positive");
  }

  const double incidentEnergyMeV = 1000.0 * kineticEnergyGeV;
  if (!std::isfinite(incidentEnergyMeV)) {
    throw std::invalid_argument(
        "Kinetic energy is outside the supported range");
  }

  RequireFiniteNonnegative(
      absoluteEnergyToleranceMeV,
      "Absolute energy tolerance");
  RequireFiniteNonnegative(
      relativeEnergyTolerance,
      "Relative energy tolerance");

  if (events.empty()) {
    throw std::invalid_argument(
        "At least one event is required");
  }

  std::unordered_map<int, std::size_t> eventIndices;
  std::vector<double> eventEnergies;
  eventEnergies.reserve(events.size());

  for (std::size_t index = 0; index < events.size(); ++index) {
    const auto& event = events[index];
    if (event.event < 0) {
      throw std::invalid_argument(
          "Event identifier must be non-negative");
    }
    RequireFiniteNonnegative(
        event.totalEnergyMeV, "Event energy");

    if (!eventIndices.emplace(event.event, index).second) {
      throw std::invalid_argument(
          "Duplicate event identifier: " +
          std::to_string(event.event));
    }
    eventEnergies.push_back(event.totalEnergyMeV);
  }

  std::vector<double> hitEnergyByEvent(events.size(), 0.0);
  std::array<std::vector<double>,
             kSingleParticleSamplingCount> energyBySampling;
  for (auto& values : energyBySampling) {
    values.assign(events.size(), 0.0);
  }

  LinearMoments samplingMoments;
  LinearMoments etaMoments;
  PhiMoments phiMoments;
  std::array<LinearMoments,
             kSingleParticleSamplingCount> samplingEtaMoments;
  std::array<PhiMoments,
             kSingleParticleSamplingCount> samplingPhiMoments;

  for (const auto& hit : hits) {
    const auto eventIterator = eventIndices.find(hit.event);
    if (eventIterator == eventIndices.end()) {
      throw std::invalid_argument(
          "Hit references unknown event: " +
          std::to_string(hit.event));
    }

    if (hit.sampling < 0 ||
        hit.sampling >=
            static_cast<int>(kSingleParticleSamplingCount)) {
      throw std::invalid_argument(
          "Hit contains invalid sampling: " +
          std::to_string(hit.sampling));
    }

    if (!std::isfinite(hit.etaCenter) ||
        !std::isfinite(hit.phiCenter)) {
      throw std::invalid_argument(
          "Hit coordinates must be finite");
    }
    RequireFiniteNonnegative(hit.energyMeV, "Hit energy");

    const std::size_t eventIndex = eventIterator->second;
    const std::size_t samplingIndex =
        static_cast<std::size_t>(hit.sampling);

    hitEnergyByEvent[eventIndex] += hit.energyMeV;
    energyBySampling[samplingIndex][eventIndex] +=
        hit.energyMeV;

    samplingMoments.Add(
        static_cast<double>(hit.sampling), hit.energyMeV);
    etaMoments.Add(hit.etaCenter, hit.energyMeV);
    phiMoments.Add(hit.phiCenter, hit.energyMeV);
    samplingEtaMoments[samplingIndex].Add(
        hit.etaCenter, hit.energyMeV);
    samplingPhiMoments[samplingIndex].Add(
        hit.phiCenter, hit.energyMeV);
  }

  for (std::size_t index = 0; index < events.size(); ++index) {
    if (!NearlyEqual(
            eventEnergies[index],
            hitEnergyByEvent[index],
            absoluteEnergyToleranceMeV,
            relativeEnergyTolerance)) {
      throw std::invalid_argument(
          "Hit energy sum differs from event total for event " +
          std::to_string(events[index].event));
    }
  }

  for (const auto& hit : hits) {
    const std::size_t samplingIndex =
        static_cast<std::size_t>(hit.sampling);
    phiMoments.AddDistance(hit.phiCenter, hit.energyMeV);
    samplingPhiMoments[samplingIndex].AddDistance(
        hit.phiCenter, hit.energyMeV);
  }

  const auto [meanEnergy, sampleStddev] =
      SampleStatistics(eventEnergies);
  const double totalEnergy =
      std::accumulate(
          eventEnergies.begin(), eventEnergies.end(), 0.0);

  SingleParticleAnalysisSummary result;
  result.eventCount = events.size();
  result.hitCount = hits.size();
  result.meanEnergyMeV = meanEnergy;
  result.sampleStddevEnergyMeV = sampleStddev;
  result.meanResponse = meanEnergy / incidentEnergyMeV;
  result.relativeResolution =
      meanEnergy > 0.0 ? sampleStddev / meanEnergy : 0.0;
  result.samplingCentroid = samplingMoments.Mean();
  result.samplingWidth = samplingMoments.Width();
  result.etaWidth = etaMoments.Width();
  result.phiWidth = phiMoments.Width();

  for (std::size_t index = 0;
       index < kSingleParticleSamplingCount; ++index) {
    const auto [samplingMean, samplingStddev] =
        SampleStatistics(energyBySampling[index]);
    const double samplingTotal =
        std::accumulate(
            energyBySampling[index].begin(),
            energyBySampling[index].end(), 0.0);

    auto& summary = result.samplings[index];
    summary.sampling = static_cast<int>(index);
    summary.name = SamplingName(static_cast<int>(index));
    summary.meanEnergyMeV = samplingMean;
    summary.sampleStddevEnergyMeV = samplingStddev;
    summary.totalEnergyFraction =
        totalEnergy > 0.0 ? samplingTotal / totalEnergy : 0.0;
    summary.etaWidth = samplingEtaMoments[index].Width();
    summary.phiWidth = samplingPhiMoments[index].Width();
  }

  return result;
}

}  // namespace pg
