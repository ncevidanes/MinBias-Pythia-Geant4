#ifndef PYTHIAGEANT_DETECTORCONSTRUCTION_HH
#define PYTHIAGEANT_DETECTORCONSTRUCTION_HH

#include "Configuration.hh"
#include "Sampling.hh"

#include "G4VUserDetectorConstruction.hh"

#include <vector>

class G4LogicalVolume;
class G4VPhysicalVolume;

namespace pg {

class DetectorConstruction final : public G4VUserDetectorConstruction {
 public:
  explicit DetectorConstruction(Configuration configuration);

  G4VPhysicalVolume* Construct() override;
  void ConstructSDandField() override;

 private:
  struct SensitiveGroup {
    Sampling sampling;
    std::vector<G4LogicalVolume*> logicalVolumes;
  };

  Configuration configuration_;
  std::vector<SensitiveGroup> sensitiveGroups_;
};

}  // namespace pg

#endif

