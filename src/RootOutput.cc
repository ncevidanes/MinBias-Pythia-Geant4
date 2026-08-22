#include "RootOutput.hh"

#include "BuildInfo.hh"
#include "EventState.hh"
#include "SeedPolicy.hh"

#include "G4AnalysisManager.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"

#ifdef G4MULTITHREADED
#include "G4Threading.hh"
#endif

#include <cstdint>
#include <numeric>

namespace pg {
namespace {

constexpr int kEventsNtuple = 0;
constexpr int kHitsNtuple = 1;
constexpr int kGeneratorNtuple = 2;
constexpr int kMetadataNtuple = 3;

static_assert(kMaxPackedCellId < (CellId{1} << 53),
              "Packed cell IDs must be exactly representable as doubles.");

bool IsMetadataWriter() {
#ifdef G4MULTITHREADED
  return G4Threading::G4GetThreadId() == 0;
#else
  return true;
#endif
}

}  // namespace

void RootOutput::Book() {
  auto* analysis = G4AnalysisManager::Instance();
  analysis->SetVerboseLevel(1);
  analysis->SetDefaultFileType("root");
  analysis->SetNtupleMerging(true);

  analysis->CreateNtuple("events", "Bunch-crossing metadata");
  analysis->CreateNtupleIColumn("run");
  analysis->CreateNtupleIColumn("event");
  analysis->CreateNtupleIColumn("bcid");
  analysis->CreateNtupleDColumn("mu_configured");
  analysis->CreateNtupleIColumn("n_interactions_requested");
  analysis->CreateNtupleIColumn("n_interactions_generated");
  analysis->CreateNtupleIColumn("generation_failures");
  analysis->CreateNtupleIColumn("generator_particles");
  analysis->CreateNtupleIColumn("transported_particles");
  analysis->CreateNtupleIColumn("unknown_pdg_particles");
  analysis->CreateNtupleDColumn("total_edep_mev");
  analysis->CreateNtupleIColumn("rejected_not_final");
  analysis->CreateNtupleIColumn("rejected_neutrino_disabled");
  analysis->CreateNtupleIColumn("rejected_invisible_non_neutrino");
  analysis->CreateNtupleIColumn("rejected_outside_eta_acceptance");
  analysis->CreateNtupleIColumn("unlineaged_steps");
  analysis->CreateNtupleIColumn("segmentation_failures");
  analysis->FinishNtuple();

  analysis->CreateNtuple("hits", "Cell deposits by subevent");
  analysis->CreateNtupleIColumn("run");
  analysis->CreateNtupleIColumn("event");
  analysis->CreateNtupleIColumn("bcid");
  analysis->CreateNtupleIColumn("subevent");
  analysis->CreateNtupleDColumn("cell_id");
  analysis->CreateNtupleIColumn("subdetector");
  analysis->CreateNtupleIColumn("sampling");
  analysis->CreateNtupleIColumn("side");
  analysis->CreateNtupleIColumn("eta_index");
  analysis->CreateNtupleIColumn("phi_index");
  analysis->CreateNtupleDColumn("eta_center");
  analysis->CreateNtupleDColumn("phi_center");
  analysis->CreateNtupleDColumn("edep_mev");
  analysis->CreateNtupleDColumn("time_mean_ns");
  analysis->CreateNtupleDColumn("time_first_ns");
  analysis->CreateNtupleIColumn("leading_pdg");
  analysis->CreateNtupleIColumn("leading_track_id");
  analysis->CreateNtupleIColumn("leading_parent_id");
  analysis->CreateNtupleIColumn("steps");
  analysis->FinishNtuple();

  analysis->CreateNtuple("generator", "Complete PYTHIA event record");
  analysis->CreateNtupleIColumn("run");
  analysis->CreateNtupleIColumn("event");
  analysis->CreateNtupleIColumn("bcid");
  analysis->CreateNtupleIColumn("subevent");
  analysis->CreateNtupleIColumn("index");
  analysis->CreateNtupleIColumn("pdg");
  analysis->CreateNtupleIColumn("status");
  analysis->CreateNtupleIColumn("mother1");
  analysis->CreateNtupleIColumn("mother2");
  analysis->CreateNtupleIColumn("daughter1");
  analysis->CreateNtupleIColumn("daughter2");
  analysis->CreateNtupleIColumn("is_final");
  analysis->CreateNtupleIColumn("is_visible");
  analysis->CreateNtupleDColumn("px_gev");
  analysis->CreateNtupleDColumn("py_gev");
  analysis->CreateNtupleDColumn("pz_gev");
  analysis->CreateNtupleDColumn("energy_gev");
  analysis->CreateNtupleDColumn("mass_gev");
  analysis->CreateNtupleDColumn("eta");
  analysis->CreateNtupleDColumn("phi");
  analysis->CreateNtupleDColumn("x_prod_mm");
  analysis->CreateNtupleDColumn("y_prod_mm");
  analysis->CreateNtupleDColumn("z_prod_mm");
  analysis->CreateNtupleDColumn("t_prod_mm_over_c");
  analysis->CreateNtupleIColumn("accepted_for_transport");
  analysis->CreateNtupleIColumn("rejection_code");
  analysis->FinishNtuple();

  analysis->CreateNtuple("metadata", "Run configuration and provenance");
  analysis->CreateNtupleIColumn("schema_version");
  analysis->CreateNtupleSColumn("project_version");
  analysis->CreateNtupleSColumn("git_commit");
  analysis->CreateNtupleSColumn("git_describe");
  analysis->CreateNtupleSColumn("root_version");
  analysis->CreateNtupleSColumn("geant4_version");
  analysis->CreateNtupleSColumn("pythia_version");
  analysis->CreateNtupleIColumn("run");
  analysis->CreateNtupleIColumn("events");
  analysis->CreateNtupleIColumn("first_bcid");
  analysis->CreateNtupleIColumn("threads");
  analysis->CreateNtupleIColumn("seed_base");
  analysis->CreateNtupleIColumn("geant4_master_seed");
  analysis->CreateNtupleSColumn("seed_policy");
  analysis->CreateNtupleSColumn("seed_identity");
  analysis->CreateNtupleSColumn("seed_mixer");
  analysis->CreateNtupleIColumn("pythia_initialization_seed");
  analysis->CreateNtupleIColumn("pythia_seed_max");
  analysis->CreateNtupleSColumn("pythia_reseed_scope");
  analysis->CreateNtupleSColumn("interaction_mode");
  analysis->CreateNtupleDColumn("mean_interactions");
  analysis->CreateNtupleIColumn("fixed_interactions");
  analysis->CreateNtupleSColumn("pythia_config");
  analysis->CreateNtupleSColumn("physics_list");
  analysis->CreateNtupleDColumn("production_cut_mm");
  analysis->CreateNtupleDColumn("beam_sigma_x_mm");
  analysis->CreateNtupleDColumn("beam_sigma_y_mm");
  analysis->CreateNtupleDColumn("beam_sigma_z_mm");
  analysis->CreateNtupleDColumn("beam_sigma_t_ns");
  analysis->CreateNtupleDColumn("max_abs_eta");
  analysis->CreateNtupleIColumn("transport_neutrinos");
  analysis->CreateNtupleIColumn("generator_audit");
  analysis->CreateNtupleIColumn("check_overlaps");
  analysis->CreateNtupleIColumn("print_every");
  analysis->CreateNtupleSColumn("config_file");
  analysis->CreateNtupleSColumn("output_file");
  analysis->CreateNtupleSColumn("normalized_config");
  analysis->CreateNtupleSColumn("generator_mode");
  analysis->CreateNtupleIColumn("single_particle_pdg");
  analysis->CreateNtupleDColumn(
      "single_particle_kinetic_energy_gev");
  analysis->CreateNtupleDColumn("single_particle_eta");
  analysis->CreateNtupleDColumn("single_particle_phi");
  analysis->FinishNtuple();
}

void RootOutput::BeginRun(const Configuration& configuration) {
  auto* analysis = G4AnalysisManager::Instance();
  analysis->OpenFile(configuration.outputFile.string());

  if (IsMetadataWriter()) {
    WriteMetadata(configuration);
  }
}

void RootOutput::WriteMetadata(const Configuration& configuration) {
  auto* analysis = G4AnalysisManager::Instance();

  const int pythiaInitializationSeed =
      PythiaSeedForStableTuple(
          static_cast<std::uint64_t>(configuration.seedBase),
          0ULL,
          0ULL,
          SeedStream::kPythiaInitialization);

  analysis->FillNtupleIColumn(
      kMetadataNtuple, 0, build::kRootSchemaVersion);
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 1, std::string(build::kProjectVersion));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 2, std::string(build::kGitCommit));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 3, std::string(build::kGitDescribe));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 4, std::string(build::kRootVersion));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 5, std::string(build::kGeant4Version));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 6, std::string(build::kPythiaVersion));
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 7, CurrentRunId());
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 8, configuration.events);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 9, configuration.firstBcid);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 10, configuration.threads);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 11, configuration.seedBase);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 12, configuration.seedBase);
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 13, std::string(kSeedPolicyName));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 14, std::string(kSeedIdentityName));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 15, std::string(kSeedMixerName));
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 16, pythiaInitializationSeed);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 17,
      static_cast<int>(kPythiaMaximumSeed));
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 18, "subevent");
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 19, configuration.interactionMode);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 20, configuration.meanInteractions);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 21, configuration.fixedInteractions);
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 22, configuration.pythiaConfig.string());
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 23, configuration.physicsList);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 24, configuration.productionCutMm);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 25, configuration.beamSigmaXmm);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 26, configuration.beamSigmaYmm);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 27, configuration.beamSigmaZmm);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 28, configuration.beamSigmaTns);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 29, configuration.maxAbsEta);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 30,
      configuration.transportNeutrinos ? 1 : 0);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 31,
      configuration.generatorAudit ? 1 : 0);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 32,
      configuration.checkOverlaps ? 1 : 0);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 33, configuration.printEvery);
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 34, configuration.sourceFile.string());
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 35, configuration.outputFile.string());
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 36, configuration.NormalizedText());
  analysis->FillNtupleSColumn(
      kMetadataNtuple, 37, configuration.generatorMode);
  analysis->FillNtupleIColumn(
      kMetadataNtuple, 38, configuration.singleParticlePdg);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 39,
      configuration.singleParticleKineticEnergyGeV);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 40, configuration.singleParticleEta);
  analysis->FillNtupleDColumn(
      kMetadataNtuple, 41, configuration.singleParticlePhi);
  analysis->AddNtupleRow(kMetadataNtuple);
}

void RootOutput::EndRun() {
  auto* analysis = G4AnalysisManager::Instance();
  analysis->Write();
  analysis->CloseFile();
}

int RootOutput::CurrentRunId() {
  const auto* run = G4RunManager::GetRunManager()->GetCurrentRun();
  return run == nullptr ? 0 : run->GetRunID();
}

void RootOutput::WriteGeneratorParticle(
    const GeneratorParticleRecord& record) {
  auto* analysis = G4AnalysisManager::Instance();
  analysis->FillNtupleIColumn(kGeneratorNtuple, 0, CurrentRunId());
  analysis->FillNtupleIColumn(kGeneratorNtuple, 1, record.event);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 2, record.bcid);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 3, record.subevent);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 4, record.index);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 5, record.pdg);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 6, record.status);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 7, record.mother1);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 8, record.mother2);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 9, record.daughter1);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 10, record.daughter2);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 11, record.isFinal);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 12, record.isVisible);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 13, record.pxGeV);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 14, record.pyGeV);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 15, record.pzGeV);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 16, record.energyGeV);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 17, record.massGeV);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 18, record.eta);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 19, record.phi);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 20, record.xProdMm);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 21, record.yProdMm);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 22, record.zProdMm);
  analysis->FillNtupleDColumn(kGeneratorNtuple, 23,
                              record.tProdMmOverC);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 24,
                              record.acceptedForTransport);
  analysis->FillNtupleIColumn(kGeneratorNtuple, 25,
                              record.rejectionCode);
  analysis->AddNtupleRow(kGeneratorNtuple);
}

void RootOutput::WriteEventAndHits(const Configuration& configuration) {
  auto* analysis = G4AnalysisManager::Instance();
  const EventState& state = EventState::Instance();

  double totalEnergyMeV = 0.0;
  for (const auto& [key, deposit] : state.deposits) {
    (void)key;
    totalEnergyMeV += deposit.energyMeV;
  }

  analysis->FillNtupleIColumn(kEventsNtuple, 0, CurrentRunId());
  analysis->FillNtupleIColumn(kEventsNtuple, 1, state.eventId);
  analysis->FillNtupleIColumn(kEventsNtuple, 2, state.bcid);
  analysis->FillNtupleDColumn(kEventsNtuple, 3,
                              configuration.meanInteractions);
  analysis->FillNtupleIColumn(kEventsNtuple, 4,
                              state.requestedInteractions);
  analysis->FillNtupleIColumn(kEventsNtuple, 5,
                              state.generatedInteractions);
  analysis->FillNtupleIColumn(kEventsNtuple, 6, state.generationFailures);
  analysis->FillNtupleIColumn(kEventsNtuple, 7, state.generatorParticles);
  analysis->FillNtupleIColumn(kEventsNtuple, 8, state.transportedParticles);
  analysis->FillNtupleIColumn(kEventsNtuple, 9, state.unknownPdgParticles);
  analysis->FillNtupleDColumn(kEventsNtuple, 10, totalEnergyMeV);
  analysis->FillNtupleIColumn(kEventsNtuple, 11, state.rejectedNotFinal);
  analysis->FillNtupleIColumn(kEventsNtuple, 12,
                              state.rejectedNeutrinoDisabled);
  analysis->FillNtupleIColumn(kEventsNtuple, 13,
                              state.rejectedInvisibleNonNeutrino);
  analysis->FillNtupleIColumn(kEventsNtuple, 14,
                              state.rejectedOutsideEtaAcceptance);
  analysis->FillNtupleIColumn(kEventsNtuple, 15, state.unlineagedSteps);
  analysis->FillNtupleIColumn(kEventsNtuple, 16,
                              state.segmentationFailures);
  analysis->AddNtupleRow(kEventsNtuple);

  for (const auto& [key, deposit] : state.deposits) {
    const double meanTime =
        deposit.energyMeV > 0.0
            ? deposit.energyTimeMeVNs / deposit.energyMeV
            : 0.0;

    analysis->FillNtupleIColumn(kHitsNtuple, 0, CurrentRunId());
    analysis->FillNtupleIColumn(kHitsNtuple, 1, state.eventId);
    analysis->FillNtupleIColumn(kHitsNtuple, 2, state.bcid);
    analysis->FillNtupleIColumn(kHitsNtuple, 3, key.subevent);
    analysis->FillNtupleDColumn(kHitsNtuple, 4,
                                static_cast<double>(deposit.cellId));
    analysis->FillNtupleIColumn(kHitsNtuple, 5, deposit.subdetector);
    analysis->FillNtupleIColumn(kHitsNtuple, 6, key.sampling);
    analysis->FillNtupleIColumn(kHitsNtuple, 7, key.side);
    analysis->FillNtupleIColumn(kHitsNtuple, 8, key.etaIndex);
    analysis->FillNtupleIColumn(kHitsNtuple, 9, key.phiIndex);
    analysis->FillNtupleDColumn(kHitsNtuple, 10, deposit.etaCenter);
    analysis->FillNtupleDColumn(kHitsNtuple, 11, deposit.phiCenter);
    analysis->FillNtupleDColumn(kHitsNtuple, 12, deposit.energyMeV);
    analysis->FillNtupleDColumn(kHitsNtuple, 13, meanTime);
    analysis->FillNtupleDColumn(kHitsNtuple, 14, deposit.firstTimeNs);
    analysis->FillNtupleIColumn(kHitsNtuple, 15, deposit.leadingPdg);
    analysis->FillNtupleIColumn(kHitsNtuple, 16,
                                deposit.leadingTrackId);
    analysis->FillNtupleIColumn(kHitsNtuple, 17,
                                deposit.leadingParentId);
    analysis->FillNtupleIColumn(kHitsNtuple, 18, deposit.steps);
    analysis->AddNtupleRow(kHitsNtuple);
  }
}

}  // namespace pg

