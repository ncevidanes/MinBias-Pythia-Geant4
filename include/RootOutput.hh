#ifndef PYTHIAGEANT_ROOTOUTPUT_HH
#define PYTHIAGEANT_ROOTOUTPUT_HH

#include "Configuration.hh"

namespace pg {

struct GeneratorParticleRecord {
  int event = -1;
  int bcid = -1;
  int subevent = -1;
  int index = -1;
  int pdg = 0;
  int status = 0;
  int mother1 = 0;
  int mother2 = 0;
  int daughter1 = 0;
  int daughter2 = 0;
  int isFinal = 0;
  int isVisible = 0;
  double pxGeV = 0.0;
  double pyGeV = 0.0;
  double pzGeV = 0.0;
  double energyGeV = 0.0;
  double massGeV = 0.0;
  double eta = 0.0;
  double phi = 0.0;
  double xProdMm = 0.0;
  double yProdMm = 0.0;
  double zProdMm = 0.0;
  double tProdMmOverC = 0.0;
};

class RootOutput {
 public:
  static void Book();
  static void BeginRun(const Configuration& configuration);
  static void EndRun();
  static void WriteGeneratorParticle(const GeneratorParticleRecord& record);
  static void WriteEventAndHits(const Configuration& configuration);

 private:
  static int CurrentRunId();
};

}  // namespace pg

#endif

