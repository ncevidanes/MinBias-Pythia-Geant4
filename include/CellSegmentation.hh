#ifndef PYTHIAGEANT_CELLSEGMENTATION_HH
#define PYTHIAGEANT_CELLSEGMENTATION_HH

#include "Sampling.hh"

#include <cstdint>
#include <optional>

namespace pg {

using CellId = std::uint64_t;

constexpr int kPackedCellIdBits = 23;
constexpr CellId kMaxPackedCellId =
    (CellId{1} << kPackedCellIdBits) - CellId{1};

struct CellAddress {
  int sampling = -1;
  int side = 0;
  int etaIndex = -1;
  int phiIndex = -1;

  bool operator==(const CellAddress& other) const;
};

struct CellGeometry {
  CellAddress address;
  CellId cellId = 0;
  double etaMin = 0.0;
  double etaMax = 0.0;
  double phiMin = 0.0;
  double phiMax = 0.0;
  double etaCenter = 0.0;
  double phiCenter = 0.0;
};

std::optional<double> NormalizePhi(double phi);
std::optional<CellId> EncodeCellId(const CellAddress& address);
std::optional<CellAddress> DecodeCellId(CellId cellId);

class CellSegmentation {
 public:
  explicit CellSegmentation(Sampling sampling);

  const Sampling& Definition() const { return sampling_; }
  int NumberEtaBins() const { return numberEtaBins_; }
  int NumberPhiBins() const { return numberPhiBins_; }

  std::optional<CellGeometry> Locate(double eta, double phi) const;
  std::optional<CellGeometry> Describe(const CellAddress& address) const;

 private:
  Sampling sampling_;
  int numberEtaBins_ = 0;
  int numberPhiBins_ = 0;
};

}  // namespace pg

#endif
