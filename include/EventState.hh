#ifndef PYTHIAGEANT_EVENTSTATE_HH
#define PYTHIAGEANT_EVENTSTATE_HH

#include <map>

namespace pg {

struct CellKey {
  int subevent = -1;
  int sampling = -1;
  int side = 0;
  int etaIndex = -1;
  int phiIndex = -1;

  bool operator<(const CellKey& other) const;
};

struct CellDeposit {
  int subdetector = -1;
  double cellId = -1.0;
  double etaCenter = 0.0;
  double phiCenter = 0.0;
  double energyMeV = 0.0;
  double energyTimeMeVNs = 0.0;
  double firstTimeNs = 0.0;
  double largestStepMeV = 0.0;
  int leadingPdg = 0;
  int leadingTrackId = -1;
  int leadingParentId = -1;
  int steps = 0;
};

class EventState {
 public:
  static EventState& Instance();

  void Reset(int eventIdValue, int bcidValue);
  void RecordDeposit(const CellKey& key, int subdetector, double cellId,
                     double etaCenter, double phiCenter, double energyMeV,
                     double timeNs, int pdg, int trackId, int parentId);

  int eventId = -1;
  int bcid = -1;
  int requestedInteractions = 0;
  int generatedInteractions = 0;
  int generationFailures = 0;
  int generatorParticles = 0;
  int transportedParticles = 0;
  int unknownPdgParticles = 0;
  std::map<CellKey, CellDeposit> deposits;

 private:
  EventState() = default;
};

}  // namespace pg

#endif

