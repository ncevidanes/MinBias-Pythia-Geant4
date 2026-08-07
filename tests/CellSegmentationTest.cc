#include "CellSegmentation.hh"
#include "Sampling.hh"

#include <cmath>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>

namespace {

constexpr double kPi = 3.14159265358979323846;

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void RequireNear(const double actual, const double expected,
                 const double tolerance, const std::string& message) {
  Require(std::abs(actual - expected) <= tolerance, message);
}

std::map<int, pg::Sampling> CanonicalSamplings() {
  std::map<int, pg::Sampling> result;
  for (const auto& sampling : pg::MakeBarrelSamplings()) {
    const auto [iterator, inserted] = result.emplace(sampling.id, sampling);
    if (!inserted) {
      const pg::Sampling& first = iterator->second;
      Require(first.subdetector == sampling.subdetector,
              "Repeated sampling ID changed subdetector");
      RequireNear(first.deltaEta, sampling.deltaEta, 1.0e-15,
                  "Repeated sampling ID changed deltaEta");
      RequireNear(first.deltaPhi, sampling.deltaPhi, 1.0e-15,
                  "Repeated sampling ID changed deltaPhi");
      RequireNear(first.maxAbsEta, sampling.maxAbsEta, 1.0e-15,
                  "Repeated sampling ID changed maxAbsEta");
    }
  }
  return result;
}

void CheckBinTable(const std::map<int, pg::Sampling>& samplings) {
  const std::map<int, std::pair<int, int>> expected{
      {static_cast<int>(pg::SamplingId::PSB), {128, 64}},
      {static_cast<int>(pg::SamplingId::EMB1), {1024, 64}},
      {static_cast<int>(pg::SamplingId::EMB2), {128, 256}},
      {static_cast<int>(pg::SamplingId::EMB3), {64, 256}},
      {static_cast<int>(pg::SamplingId::TileCal1), {34, 64}},
      {static_cast<int>(pg::SamplingId::TileCal2), {34, 64}},
      {static_cast<int>(pg::SamplingId::TileCal3), {17, 64}},
      {static_cast<int>(pg::SamplingId::TileExt1), {36, 64}},
      {static_cast<int>(pg::SamplingId::TileExt2), {36, 64}},
      {static_cast<int>(pg::SamplingId::TileExt3), {18, 64}},
  };

  Require(samplings.size() == expected.size(),
          "Unexpected number of logical samplings");
  for (const auto& [id, binCounts] : expected) {
    const pg::CellSegmentation segmentation(samplings.at(id));
    Require(segmentation.NumberEtaBins() == binCounts.first,
            "Unexpected eta bin count for sampling " + std::to_string(id));
    Require(segmentation.NumberPhiBins() == binCounts.second,
            "Unexpected phi bin count for sampling " + std::to_string(id));
  }
}

void CheckEveryCellIsUnique(
    const std::map<int, pg::Sampling>& samplings) {
  std::set<pg::CellId> ids;

  for (const auto& [id, sampling] : samplings) {
    const pg::CellSegmentation segmentation(sampling);
    for (int etaIndex = 0;
         etaIndex < segmentation.NumberEtaBins(); ++etaIndex) {
      for (const int side : {-1, 1}) {
        for (int phiIndex = 0;
             phiIndex < segmentation.NumberPhiBins(); ++phiIndex) {
          const pg::CellAddress address{id, side, etaIndex, phiIndex};
          const auto cell = segmentation.Describe(address);
          if (!cell.has_value()) {
            continue;
          }

          Require(cell->etaMin < cell->etaCenter &&
                      cell->etaCenter < cell->etaMax,
                  "Eta center lies outside cell bounds");
          Require(cell->phiMin < cell->phiCenter &&
                      cell->phiCenter < cell->phiMax,
                  "Phi center lies outside cell bounds");
          Require(cell->phiCenter >= -kPi && cell->phiCenter < kPi,
                  "Phi center is outside the canonical interval");

          const auto decoded = pg::DecodeCellId(cell->cellId);
          Require(decoded.has_value() && *decoded == address,
                  "Cell ID encode/decode round trip failed");
          Require(static_cast<pg::CellId>(
                      static_cast<double>(cell->cellId)) == cell->cellId,
                  "Cell ID is not exactly representable in the ROOT column");
          const auto located = segmentation.Locate(
              cell->etaCenter, cell->phiCenter);
          Require(located.has_value() && located->address == address,
                  "Cell center did not map back to its address");
          Require(ids.insert(cell->cellId).second,
                  "Duplicate packed cell ID");
        }
      }
    }
  }

  Require(ids.size() == 134144,
          "Unexpected number of unique logical cells: " +
              std::to_string(ids.size()));
}

void CheckBoundaries(const std::map<int, pg::Sampling>& samplings) {
  const pg::CellSegmentation segmentation(
      samplings.at(static_cast<int>(pg::SamplingId::EMB2)));
  const double maxEta = segmentation.Definition().maxAbsEta;

  const auto negativeEta = segmentation.Locate(-maxEta, 0.0);
  const auto positiveEta = segmentation.Locate(maxEta, 0.0);
  Require(negativeEta.has_value() && positiveEta.has_value(),
          "Inclusive eta boundaries were rejected");
  Require(negativeEta->address.etaIndex == 0 &&
              negativeEta->address.side == -1,
          "Negative eta boundary was assigned incorrectly");
  Require(positiveEta->address.etaIndex ==
                  segmentation.NumberEtaBins() - 1 &&
              positiveEta->address.side == 1,
          "Positive eta boundary was assigned incorrectly");

  const double outside =
      std::nextafter(maxEta, std::numeric_limits<double>::infinity());
  Require(!segmentation.Locate(outside, 0.0).has_value(),
          "Eta outside the declared acceptance was accepted");

  const auto minusPi = segmentation.Locate(0.2, -kPi);
  const auto plusPi = segmentation.Locate(0.2, kPi);
  const auto threePi = segmentation.Locate(0.2, 3.0 * kPi);
  Require(minusPi.has_value() && plusPi.has_value() &&
              threePi.has_value(),
          "A finite phi boundary was rejected");
  Require(minusPi->cellId == plusPi->cellId &&
              minusPi->cellId == threePi->cellId,
          "Equivalent phi boundaries map to different cells");
  Require(minusPi->address.phiIndex == 0,
          "Canonical -pi boundary is not in the first phi bin");
}

void CheckCentralSplit(const std::map<int, pg::Sampling>& samplings) {
  const pg::CellSegmentation segmentation(
      samplings.at(static_cast<int>(pg::SamplingId::TileCal3)));
  const auto negative = segmentation.Locate(-0.05, 0.0);
  const auto positive = segmentation.Locate(0.05, 0.0);

  Require(negative.has_value() && positive.has_value(),
          "Central TileCal3 cells were not found");
  Require(negative->address.etaIndex == positive->address.etaIndex,
          "Central split changed the nominal eta index");
  Require(negative->address.side == -1 && positive->address.side == 1,
          "Central split did not preserve detector side");
  Require(negative->cellId != positive->cellId,
          "Central cells on opposite sides share an ID");
  RequireNear(negative->etaCenter, -0.05, 1.0e-12,
              "Negative central cell has the wrong center");
  RequireNear(positive->etaCenter, 0.05, 1.0e-12,
              "Positive central cell has the wrong center");
}

void CheckInvalidInputs(const std::map<int, pg::Sampling>& samplings) {
  Require(!pg::EncodeCellId({0, 0, 0, 0}).has_value(),
          "side=0 was accepted");
  Require(!pg::EncodeCellId({10, 1, 0, 0}).has_value(),
          "Unknown sampling was accepted");
  Require(!pg::EncodeCellId({0, 1, 1024, 0}).has_value(),
          "Oversized eta index was accepted");
  Require(!pg::EncodeCellId({0, 1, 0, 256}).has_value(),
          "Oversized phi index was accepted");
  Require(!pg::DecodeCellId(pg::kMaxPackedCellId + 1).has_value(),
          "Cell ID with reserved high bits was accepted");

  pg::Sampling invalid =
      samplings.at(static_cast<int>(pg::SamplingId::EMB1));
  invalid.deltaEta = 0.00325;
  bool threw = false;
  try {
    const pg::CellSegmentation segmentation(invalid);
    (void)segmentation;
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  Require(threw, "Non-divisible EMB1 granularity was accepted");
}

}  // namespace

int main() {
  try {
    const auto all = pg::MakeBarrelSamplings();
    Require(all.size() == 13,
            "Expected seven central and six extended placements");

    const auto samplings = CanonicalSamplings();
    CheckBinTable(samplings);
    CheckEveryCellIsUnique(samplings);
    CheckBoundaries(samplings);
    CheckCentralSplit(samplings);
    CheckInvalidInputs(samplings);

    std::cout << "Cell segmentation tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Cell segmentation test failed: " << error.what()
              << std::endl;
    return 1;
  }
}
