#ifndef PYTHIAGEANT_CALORIMETERSD_HH
#define PYTHIAGEANT_CALORIMETERSD_HH

#include "CellSegmentation.hh"

#include "G4VSensitiveDetector.hh"

class G4Step;
class G4TouchableHistory;

namespace pg {

class CalorimeterSD final : public G4VSensitiveDetector {
 public:
  CalorimeterSD(const G4String& name, Sampling sampling);

  G4bool ProcessHits(G4Step* step, G4TouchableHistory* history) override;

 private:
  CellSegmentation segmentation_;
};

}  // namespace pg

#endif

