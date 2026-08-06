#include "RootOutput.hh"

#include "EventState.hh"

#include "G4AnalysisManager.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"

#include <numeric>

namespace pg {
namespace {

constexpr int kEventsNtuple = 0;
constexpr int kHitsNtuple = 1;
constexpr int kGeneratorNtuple = 2;

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
  analysis->FinishNtuple();
}

void RootOutput::BeginRun(const Configuration& configuration) {
  G4AnalysisManager::Instance()->OpenFile(configuration.outputFile.string());
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
    analysis->FillNtupleDColumn(kHitsNtuple, 4, deposit.cellId);
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

