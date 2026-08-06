#ifndef PYTHIAGEANT_SAMPLING_HH
#define PYTHIAGEANT_SAMPLING_HH

#include <string>
#include <vector>

namespace pg {

enum class Subdetector : int {
  LAr = 0,
  Tile = 1,
};

enum class SamplingId : int {
  PSB = 0,
  EMB1 = 1,
  EMB2 = 2,
  EMB3 = 3,
  TileCal1 = 4,
  TileCal2 = 5,
  TileCal3 = 6,
  TileExt1 = 7,
  TileExt2 = 8,
  TileExt3 = 9,
};

struct Sampling {
  int id;
  std::string name;
  Subdetector subdetector;
  std::string absorberMaterial;
  std::string activeMaterial;
  int layers;
  double absorberThicknessMm;
  double activeThicknessMm;
  double rMinMm;
  double zHalfLengthMm;
  double zCenterMm;
  double deltaEta;
  double deltaPhi;
  double maxAbsEta;

  double LayerThicknessMm() const {
    return absorberThicknessMm + activeThicknessMm;
  }

  double RMaxMm() const {
    return rMinMm + layers * LayerThicknessMm();
  }
};

std::vector<Sampling> MakeBarrelSamplings();
std::string SamplingName(int id);

}  // namespace pg

#endif

