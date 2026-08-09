#ifndef PYTHIAGEANT_CONFIGURATION_HH
#define PYTHIAGEANT_CONFIGURATION_HH

#include <filesystem>
#include <iosfwd>
#include <string>

namespace pg {

struct Configuration {
  std::filesystem::path sourceFile;
  std::filesystem::path pythiaConfig;
  std::filesystem::path outputFile;

  std::string generatorMode = "pythia";

  int events = 3;
  int firstBcid = 0;
  int threads = 1;
  int seedBase = 512;
  int fixedInteractions = 1;
  int printEvery = 1;
  int singleParticlePdg = 11;

  double meanInteractions = 1.0;
  double productionCutMm = 1.0;
  double beamSigmaXmm = 0.0;
  double beamSigmaYmm = 0.0;
  double beamSigmaZmm = 0.0;
  double beamSigmaTns = 0.0;
  double maxAbsEta = 1.8;
  double singleParticleKineticEnergyGeV = 10.0;
  double singleParticleEta = 0.0;
  double singleParticlePhi = 0.0;

  std::string interactionMode = "poisson";
  std::string physicsList = "FTFP_BERT_ATL";

  bool transportNeutrinos = false;
  bool generatorAudit = false;
  bool checkOverlaps = false;

  static Configuration Load(const std::filesystem::path& filename);

  void Validate() const;
  void Print(std::ostream& output) const;
  std::string NormalizedText() const;
  void WriteManifest() const;
};

}  // namespace pg

#endif
