#include "Sampling.hh"

#include <cmath>

namespace pg {

std::vector<Sampling> MakeBarrelSamplings() {
  constexpr double pi = 3.14159265358979323846;

  std::vector<Sampling> samplings;

  const Sampling psb{
      static_cast<int>(SamplingId::PSB),
      "PSB",
      Subdetector::LAr,
      "G4_Galactic",
      "G4_lAr",
      1,
      0.01,
      11.0,
      1460.0,
      3400.0,
      0.0,
      0.025,
      pi / 32.0,
      1.6,
  };
  samplings.push_back(psb);

  const Sampling emb1{
      static_cast<int>(SamplingId::EMB1),
      "EMB1",
      Subdetector::LAr,
      "G4_Pb",
      "G4_lAr",
      16,
      1.51,
      4.49,
      1500.0,
      3400.0,
      0.0,
      0.003125,
      pi / 32.0,
      1.6,
  };
  samplings.push_back(emb1);

  const Sampling emb2{
      static_cast<int>(SamplingId::EMB2),
      "EMB2",
      Subdetector::LAr,
      "G4_Pb",
      "G4_lAr",
      55,
      1.7,
      4.3,
      emb1.RMaxMm(),
      3400.0,
      0.0,
      0.025,
      pi / 128.0,
      1.6,
  };
  samplings.push_back(emb2);

  const Sampling emb3{
      static_cast<int>(SamplingId::EMB3),
      "EMB3",
      Subdetector::LAr,
      "G4_Pb",
      "G4_lAr",
      9,
      1.7,
      4.3,
      emb2.RMaxMm(),
      3400.0,
      0.0,
      0.05,
      pi / 128.0,
      1.6,
  };
  samplings.push_back(emb3);

  const double tileRMin = 2283.0;
  const double tileHalfZ = 3024.0;
  const Sampling tile1{
      static_cast<int>(SamplingId::TileCal1),
      "TileCal1",
      Subdetector::Tile,
      "G4_Fe",
      "G4_PLASTIC_SC_VINYLTOLUENE",
      4,
      60.0,
      40.0,
      tileRMin,
      tileHalfZ,
      0.0,
      0.1,
      pi / 32.0,
      1.7,
  };
  samplings.push_back(tile1);

  const Sampling tile2{
      static_cast<int>(SamplingId::TileCal2),
      "TileCal2",
      Subdetector::Tile,
      "G4_Fe",
      "G4_PLASTIC_SC_VINYLTOLUENE",
      11,
      62.0,
      38.0,
      tile1.RMaxMm(),
      tileHalfZ,
      0.0,
      0.1,
      pi / 32.0,
      1.7,
  };
  samplings.push_back(tile2);

  const Sampling tile3{
      static_cast<int>(SamplingId::TileCal3),
      "TileCal3",
      Subdetector::Tile,
      "G4_Fe",
      "G4_PLASTIC_SC_VINYLTOLUENE",
      5,
      62.0,
      38.0,
      tile2.RMaxMm(),
      tileHalfZ,
      0.0,
      0.2,
      pi / 32.0,
      1.7,
  };
  samplings.push_back(tile3);

  const double extendedHalfZ = 1415.0;
  const double extendedCenter = 3704.0 + extendedHalfZ;
  for (const double sign : {-1.0, 1.0}) {
    const std::string side = sign < 0.0 ? "B" : "A";
    const Sampling ext1{
        static_cast<int>(SamplingId::TileExt1),
        "TileExt1_" + side,
        Subdetector::Tile,
        "G4_Fe",
        "G4_PLASTIC_SC_VINYLTOLUENE",
        4,
        60.0,
        40.0,
        tileRMin,
        extendedHalfZ,
        sign * extendedCenter,
        0.1,
        pi / 32.0,
        1.8,
    };
    samplings.push_back(ext1);

    const Sampling ext2{
        static_cast<int>(SamplingId::TileExt2),
        "TileExt2_" + side,
        Subdetector::Tile,
        "G4_Fe",
        "G4_PLASTIC_SC_VINYLTOLUENE",
        11,
        62.0,
        38.0,
        ext1.RMaxMm(),
        extendedHalfZ,
        sign * extendedCenter,
        0.1,
        pi / 32.0,
        1.8,
    };
    samplings.push_back(ext2);

    const Sampling ext3{
        static_cast<int>(SamplingId::TileExt3),
        "TileExt3_" + side,
        Subdetector::Tile,
        "G4_Fe",
        "G4_PLASTIC_SC_VINYLTOLUENE",
        5,
        62.0,
        38.0,
        ext2.RMaxMm(),
        extendedHalfZ,
        sign * extendedCenter,
        0.2,
        pi / 32.0,
        1.8,
    };
    samplings.push_back(ext3);
  }

  return samplings;
}

std::string SamplingName(const int id) {
  switch (static_cast<SamplingId>(id)) {
    case SamplingId::PSB:
      return "PSB";
    case SamplingId::EMB1:
      return "EMB1";
    case SamplingId::EMB2:
      return "EMB2";
    case SamplingId::EMB3:
      return "EMB3";
    case SamplingId::TileCal1:
      return "TileCal1";
    case SamplingId::TileCal2:
      return "TileCal2";
    case SamplingId::TileCal3:
      return "TileCal3";
    case SamplingId::TileExt1:
      return "TileExt1";
    case SamplingId::TileExt2:
      return "TileExt2";
    case SamplingId::TileExt3:
      return "TileExt3";
  }
  return "Unknown";
}

}  // namespace pg

