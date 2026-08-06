#ifndef PYTHIAGEANT_LINEAGEINFO_HH
#define PYTHIAGEANT_LINEAGEINFO_HH

#include "G4VUserPrimaryParticleInformation.hh"
#include "G4VUserTrackInformation.hh"

namespace pg {

class PrimaryLineageInfo final : public G4VUserPrimaryParticleInformation {
 public:
  PrimaryLineageInfo(int subevent, int primaryPdg);

  int Subevent() const { return subevent_; }
  int PrimaryPdg() const { return primaryPdg_; }
  void Print() const override;

 private:
  int subevent_;
  int primaryPdg_;
};

class TrackLineageInfo final : public G4VUserTrackInformation {
 public:
  TrackLineageInfo(int subevent, int primaryPdg);
  explicit TrackLineageInfo(const PrimaryLineageInfo& primary);
  TrackLineageInfo(const TrackLineageInfo&) = default;

  int Subevent() const { return subevent_; }
  int PrimaryPdg() const { return primaryPdg_; }
  void Print() const override;

 private:
  int subevent_;
  int primaryPdg_;
};

}  // namespace pg

#endif

