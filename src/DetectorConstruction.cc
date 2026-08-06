#include "DetectorConstruction.hh"

#include "CalorimeterSD.hh"

#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Tubs.hh"
#include "G4VisAttributes.hh"

#include <string>
#include <utility>

namespace pg {

DetectorConstruction::DetectorConstruction(Configuration configuration)
    : configuration_(std::move(configuration)) {}

G4VPhysicalVolume* DetectorConstruction::Construct() {
  sensitiveGroups_.clear();

  auto* nist = G4NistManager::Instance();
  auto* vacuum = nist->FindOrBuildMaterial("G4_Galactic");

  auto* worldSolid =
      new G4Tubs("WorldSolid", 0.0, 6.0 * m, 10.0 * m, 0.0, 360.0 * deg);
  auto* worldLogical =
      new G4LogicalVolume(worldSolid, vacuum, "WorldLogical");
  worldLogical->SetVisAttributes(G4VisAttributes::GetInvisible());

  auto* worldPhysical =
      new G4PVPlacement(nullptr, {}, worldLogical, "WorldPhysical", nullptr,
                        false, 0, configuration_.checkOverlaps);

  for (const Sampling& sampling : MakeBarrelSamplings()) {
    SensitiveGroup group{sampling, {}};
    auto* absorber =
        nist->FindOrBuildMaterial(sampling.absorberMaterial, true);
    auto* active = nist->FindOrBuildMaterial(sampling.activeMaterial, true);

    for (int layer = 0; layer < sampling.layers; ++layer) {
      const double layerInner =
          sampling.rMinMm + layer * sampling.LayerThicknessMm();
      const double absorberOuter =
          layerInner + sampling.absorberThicknessMm;
      const double activeOuter = absorberOuter + sampling.activeThicknessMm;
      const std::string suffix =
          sampling.name + "_L" + std::to_string(layer);

      if (sampling.absorberThicknessMm > 0.0) {
        auto* absorberSolid =
            new G4Tubs(suffix + "_AbsorberSolid", layerInner * mm,
                       absorberOuter * mm, sampling.zHalfLengthMm * mm, 0.0,
                       360.0 * deg);
        auto* absorberLogical = new G4LogicalVolume(
            absorberSolid, absorber, suffix + "_AbsorberLogical");
        new G4PVPlacement(
            nullptr, G4ThreeVector(0.0, 0.0, sampling.zCenterMm * mm),
            absorberLogical, suffix + "_AbsorberPhysical", worldLogical,
            false, layer, configuration_.checkOverlaps);
      }

      auto* activeSolid =
          new G4Tubs(suffix + "_ActiveSolid", absorberOuter * mm,
                     activeOuter * mm, sampling.zHalfLengthMm * mm, 0.0,
                     360.0 * deg);
      auto* activeLogical =
          new G4LogicalVolume(activeSolid, active, suffix + "_ActiveLogical");
      new G4PVPlacement(
          nullptr, G4ThreeVector(0.0, 0.0, sampling.zCenterMm * mm),
          activeLogical, suffix + "_ActivePhysical", worldLogical, false,
          layer, configuration_.checkOverlaps);

      group.logicalVolumes.push_back(activeLogical);
    }

    sensitiveGroups_.push_back(std::move(group));
  }

  return worldPhysical;
}

void DetectorConstruction::ConstructSDandField() {
  auto* manager = G4SDManager::GetSDMpointer();

  for (const SensitiveGroup& group : sensitiveGroups_) {
    const std::string detectorName = "SD_" + group.sampling.name;
    auto* sensitiveDetector =
        new CalorimeterSD(detectorName, group.sampling);
    manager->AddNewDetector(sensitiveDetector);
    for (auto* logicalVolume : group.logicalVolumes) {
      SetSensitiveDetector(logicalVolume, sensitiveDetector);
    }
  }
}

}  // namespace pg
