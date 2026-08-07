#include "CellSegmentation.hh"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

namespace pg {
namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;
constexpr int kPhiBits = 8;
constexpr int kEtaBits = 10;
constexpr int kSideBits = 1;
constexpr int kSamplingBits = 4;
constexpr int kEtaShift = kPhiBits;
constexpr int kSideShift = kEtaShift + kEtaBits;
constexpr int kSamplingShift = kSideShift + kSideBits;
constexpr CellId kPhiMask = (CellId{1} << kPhiBits) - CellId{1};
constexpr CellId kEtaMask = (CellId{1} << kEtaBits) - CellId{1};
constexpr CellId kSamplingMask =
    (CellId{1} << kSamplingBits) - CellId{1};
constexpr int kLargestSamplingId =
    static_cast<int>(SamplingId::TileExt3);

static_assert(kSamplingShift + kSamplingBits == kPackedCellIdBits,
              "The packed cell ID layout must use exactly 23 bits.");

int ExactBinCount(const double span, const double width,
                  const std::string& coordinate) {
  if (!std::isfinite(span) || !std::isfinite(width) || span <= 0.0 ||
      width <= 0.0) {
    throw std::invalid_argument("Invalid " + coordinate +
                                " segmentation interval");
  }

  const double ratio = span / width;
  const double rounded = std::round(ratio);
  const double tolerance =
      1.0e-10 * std::max(1.0, std::abs(ratio));
  if (std::abs(ratio - rounded) > tolerance || rounded < 1.0 ||
      rounded > static_cast<double>(std::numeric_limits<int>::max())) {
    throw std::invalid_argument(
        coordinate + " range is not exactly divisible by its granularity");
  }

  return static_cast<int>(rounded);
}

bool IsValidPackedAddress(const CellAddress& address) {
  return address.sampling >= 0 &&
         address.sampling <= kLargestSamplingId &&
         (address.side == -1 || address.side == 1) &&
         address.etaIndex >= 0 &&
         static_cast<CellId>(address.etaIndex) <= kEtaMask &&
         address.phiIndex >= 0 &&
         static_cast<CellId>(address.phiIndex) <= kPhiMask;
}

}  // namespace

bool CellAddress::operator==(const CellAddress& other) const {
  return sampling == other.sampling && side == other.side &&
         etaIndex == other.etaIndex && phiIndex == other.phiIndex;
}

std::optional<double> NormalizePhi(const double phi) {
  if (!std::isfinite(phi)) {
    return std::nullopt;
  }

  double normalized = std::fmod(phi + kPi, kTwoPi);
  if (normalized < 0.0) {
    normalized += kTwoPi;
  }
  normalized -= kPi;

  // Canonical half-open interval: +pi and -pi identify the same direction.
  if (normalized >= kPi) {
    normalized = -kPi;
  }
  return normalized;
}

std::optional<CellId> EncodeCellId(const CellAddress& address) {
  if (!IsValidPackedAddress(address)) {
    return std::nullopt;
  }

  const CellId sideCode = address.side > 0 ? CellId{1} : CellId{0};
  const CellId cellId =
      (static_cast<CellId>(address.sampling) << kSamplingShift) |
      (sideCode << kSideShift) |
      (static_cast<CellId>(address.etaIndex) << kEtaShift) |
      static_cast<CellId>(address.phiIndex);
  return cellId;
}

std::optional<CellAddress> DecodeCellId(const CellId cellId) {
  if (cellId > kMaxPackedCellId) {
    return std::nullopt;
  }

  CellAddress address;
  address.phiIndex = static_cast<int>(cellId & kPhiMask);
  address.etaIndex =
      static_cast<int>((cellId >> kEtaShift) & kEtaMask);
  address.side = ((cellId >> kSideShift) & CellId{1}) == CellId{0}
                     ? -1
                     : 1;
  address.sampling = static_cast<int>(
      (cellId >> kSamplingShift) & kSamplingMask);

  if (!IsValidPackedAddress(address)) {
    return std::nullopt;
  }
  return address;
}

CellSegmentation::CellSegmentation(Sampling sampling)
    : sampling_(std::move(sampling)) {
  if (sampling_.id < 0 || sampling_.id > kLargestSamplingId) {
    throw std::invalid_argument("Sampling ID cannot be packed in cell_id");
  }
  if (!std::isfinite(sampling_.maxAbsEta) ||
      sampling_.maxAbsEta <= 0.0) {
    throw std::invalid_argument("Sampling maxAbsEta must be finite and positive");
  }

  numberEtaBins_ = ExactBinCount(
      2.0 * sampling_.maxAbsEta, sampling_.deltaEta, "eta");
  numberPhiBins_ =
      ExactBinCount(kTwoPi, sampling_.deltaPhi, "phi");

  if (numberEtaBins_ - 1 > static_cast<int>(kEtaMask) ||
      numberPhiBins_ - 1 > static_cast<int>(kPhiMask)) {
    throw std::invalid_argument(
        "Sampling granularity exceeds the packed cell_id field width");
  }
}

std::optional<CellGeometry> CellSegmentation::Locate(
    const double eta, const double phi) const {
  if (!std::isfinite(eta) || eta < -sampling_.maxAbsEta ||
      eta > sampling_.maxAbsEta) {
    return std::nullopt;
  }

  const auto normalizedPhi = NormalizePhi(phi);
  if (!normalizedPhi.has_value()) {
    return std::nullopt;
  }

  int etaIndex = 0;
  if (eta == sampling_.maxAbsEta) {
    etaIndex = numberEtaBins_ - 1;
  } else if (eta == 0.0) {
    etaIndex = numberEtaBins_ / 2;
  } else {
    etaIndex = static_cast<int>(std::floor(
        (eta + sampling_.maxAbsEta) / sampling_.deltaEta));
  }
  const int phiIndex = static_cast<int>(
      std::floor((*normalizedPhi + kPi) / sampling_.deltaPhi));

  if (etaIndex < 0 || etaIndex >= numberEtaBins_ || phiIndex < 0 ||
      phiIndex >= numberPhiBins_) {
    return std::nullopt;
  }

  const CellAddress address{
      sampling_.id,
      eta < 0.0 ? -1 : 1,
      etaIndex,
      phiIndex,
  };
  return Describe(address);
}

std::optional<CellGeometry> CellSegmentation::Describe(
    const CellAddress& address) const {
  if (address.sampling != sampling_.id ||
      (address.side != -1 && address.side != 1) ||
      address.etaIndex < 0 || address.etaIndex >= numberEtaBins_ ||
      address.phiIndex < 0 || address.phiIndex >= numberPhiBins_) {
    return std::nullopt;
  }

  const int middle = numberEtaBins_ / 2;
  if (numberEtaBins_ % 2 == 0) {
    const int expectedSide = address.etaIndex < middle ? -1 : 1;
    if (address.side != expectedSide) {
      return std::nullopt;
    }
  } else if ((address.etaIndex < middle && address.side != -1) ||
             (address.etaIndex > middle && address.side != 1)) {
    return std::nullopt;
  }

  double etaMin = -sampling_.maxAbsEta +
                  address.etaIndex * sampling_.deltaEta;
  double etaMax = etaMin + sampling_.deltaEta;
  if (address.side < 0) {
    etaMax = std::min(etaMax, 0.0);
  } else {
    etaMin = std::max(etaMin, 0.0);
  }
  if (numberEtaBins_ % 2 == 0) {
    if (address.etaIndex == middle - 1) {
      etaMax = 0.0;
    } else if (address.etaIndex == middle) {
      etaMin = 0.0;
    }
  }
  if (!(etaMin < etaMax)) {
    return std::nullopt;
  }

  const double phiMin = -kPi + address.phiIndex * sampling_.deltaPhi;
  const double phiMax = phiMin + sampling_.deltaPhi;
  const auto cellId = EncodeCellId(address);
  if (!cellId.has_value()) {
    return std::nullopt;
  }

  return CellGeometry{
      address,
      *cellId,
      etaMin,
      etaMax,
      phiMin,
      phiMax,
      0.5 * (etaMin + etaMax),
      0.5 * (phiMin + phiMax),
  };
}

}  // namespace pg
