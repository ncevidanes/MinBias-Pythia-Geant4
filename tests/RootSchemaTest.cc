#include "RootSchema.hh"

#include <iostream>
#include <stdexcept>

namespace {

void Require(const bool condition, const char* message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

}  // namespace

int main() {
  try {
    using namespace pg::root_schema;

    Require(kCurrentVersion == 4, "Current ROOT schema changed");
    Require(IsSupportedVersion(2), "Schema 2 is not supported");
    Require(IsSupportedVersion(3), "Schema 3 is not supported");
    Require(IsSupportedVersion(4), "Schema 4 is not supported");
    Require(!IsSupportedVersion(1), "Schema 1 was accepted");
    Require(!IsSupportedVersion(5), "Unknown future schema was accepted");
    Require(!HasEventTransportSeed(3),
            "Schema 3 unexpectedly has a transport seed");
    Require(HasEventTransportSeed(4),
            "Schema 4 transport seed is not recognized");
    Require(!HasEventTransportSeed(5),
            "Unknown future schema inherited schema 4 semantics");
    Require(kEventBranchesV2V3.size() == 17,
            "Historical event branch count changed");
    Require(kEventBranchesV4.size() == 18,
            "Schema 4 event branch count changed");
    Require(kEventBranchesV4.back() == "geant4_transport_seed",
            "Schema 4 transport-seed branch changed");
    Require(kHitBranches.size() == 19, "Hit branch count changed");
    Require(kGeneratorBranches.size() == 26,
            "Generator branch count changed");
    Require(kMetadataBranchesV2.size() == 39,
            "Schema 2 metadata branch count changed");
    Require(kMetadataBranchesV3.size() == 42,
            "Schema 3 metadata branch count changed");
    Require(kMetadataBranchesV4.size() == 48,
            "Schema 4 metadata branch count changed");
    Require(kMetadataBranchesV4.back() ==
                "geant4_transport_reseed_scope",
            "Schema 4 transport metadata changed");

    std::cout << "ROOT schema contract tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "ROOT schema contract test failed: "
              << error.what() << std::endl;
    return 1;
  }
}
