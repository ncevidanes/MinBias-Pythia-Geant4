#include "LineageInfo.hh"

#include "G4ios.hh"

namespace pg {

PrimaryLineageInfo::PrimaryLineageInfo(const int subevent,
                                       const int primaryPdg)
    : subevent_(subevent), primaryPdg_(primaryPdg) {}

void PrimaryLineageInfo::Print() const {
  G4cout << "PrimaryLineageInfo(subevent=" << subevent_
         << ", primaryPdg=" << primaryPdg_ << ')' << G4endl;
}

TrackLineageInfo::TrackLineageInfo(const int subevent, const int primaryPdg)
    : subevent_(subevent), primaryPdg_(primaryPdg) {}

TrackLineageInfo::TrackLineageInfo(const PrimaryLineageInfo& primary)
    : subevent_(primary.Subevent()), primaryPdg_(primary.PrimaryPdg()) {}

void TrackLineageInfo::Print() const {
  G4cout << "TrackLineageInfo(subevent=" << subevent_
         << ", primaryPdg=" << primaryPdg_ << ')' << G4endl;
}

}  // namespace pg

