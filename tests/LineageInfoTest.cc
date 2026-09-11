#include "LineageInfo.hh"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void CheckPrimaryLineage() {
  const pg::PrimaryLineageInfo primary(17, 211);

  Require(primary.Subevent() == 17,
          "PrimaryLineageInfo changed the subevent");
  Require(primary.PrimaryPdg() == 211,
          "PrimaryLineageInfo changed the primary PDG");

  primary.Print();
}

void CheckDirectTrackLineage() {
  const pg::TrackLineageInfo track(23, -13);

  Require(track.Subevent() == 23,
          "TrackLineageInfo direct constructor changed the subevent");
  Require(track.PrimaryPdg() == -13,
          "TrackLineageInfo direct constructor changed the primary PDG");

  track.Print();
}

void CheckPrimaryToTrackPropagation() {
  const pg::PrimaryLineageInfo primary(31, 22);
  const pg::TrackLineageInfo track(primary);

  Require(track.Subevent() == primary.Subevent(),
          "Primary-to-track conversion changed the subevent");
  Require(track.PrimaryPdg() == primary.PrimaryPdg(),
          "Primary-to-track conversion changed the primary PDG");
}

void CheckTrackCopy() {
  const pg::TrackLineageInfo original(47, 2212);
  const pg::TrackLineageInfo copy(original);

  Require(copy.Subevent() == original.Subevent(),
          "TrackLineageInfo copy changed the subevent");
  Require(copy.PrimaryPdg() == original.PrimaryPdg(),
          "TrackLineageInfo copy changed the primary PDG");
}

void CheckBoundaryValues() {
  const pg::PrimaryLineageInfo primary(-1, 0);
  const pg::TrackLineageInfo track(primary);

  Require(primary.Subevent() == -1,
          "PrimaryLineageInfo altered sentinel subevent");
  Require(primary.PrimaryPdg() == 0,
          "PrimaryLineageInfo altered sentinel PDG");
  Require(track.Subevent() == -1,
          "TrackLineageInfo altered propagated sentinel subevent");
  Require(track.PrimaryPdg() == 0,
          "TrackLineageInfo altered propagated sentinel PDG");
}

}  // namespace

int main() {
  try {
    CheckPrimaryLineage();
    CheckDirectTrackLineage();
    CheckPrimaryToTrackPropagation();
    CheckTrackCopy();
    CheckBoundaryValues();

    std::cout << "LineageInfo tests passed" << std::endl;
    return 0;

  } catch (const std::exception& error) {
    std::cerr << "LineageInfo test failed: " << error.what() << std::endl;
    return 1;
  }
}
