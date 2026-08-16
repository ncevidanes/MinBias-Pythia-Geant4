#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TLeafC.h>
#include <TObjArray.h>
#include <TTree.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <initializer_list>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>

namespace {

class AnalysisResult {
 public:
  void Check(const bool condition, const std::string& message) {
    if (condition) return;
    ++failures_;
    std::cerr << "[FAIL] " << message << '\n';
  }
  int Failures() const { return failures_; }

 private:
  int failures_ = 0;
};

struct StageContract {
  int events = 0;
  double meanInteractions = 0.0;
  int seed = 0;
  int generatorAudit = 0;
  int checkOverlaps = 0;
  bool requirePoisson = false;
  bool requireAllSamplings = false;
};

bool NearlyEqual(const double left, const double right) {
  const double scale = std::max({1.0, std::abs(left), std::abs(right)});
  return std::abs(left - right) <= 1.0e-10 * scale;
}

StageContract Contract(const std::string& stage, AnalysisResult& result) {
  if (stage == "7.1") return {3, 1.0, 512, 1, 1, false, false};
  if (stage == "7.2") return {500, 2.0, 513, 1, 1, true, true};
  if (stage == "7.3") return {3000, 50.0, 512, 0, 0, true, true};
  result.Check(false, "stage must be 7.1, 7.2 or 7.3");
  return {};
}

TTree* RequireTree(TFile& file, const char* name, AnalysisResult& result) {
  auto* tree = file.Get<TTree>(name);
  result.Check(tree != nullptr, std::string("missing TTree: ") + name);
  return tree;
}

void RequireBranches(TTree& tree, std::initializer_list<const char*> names,
                     AnalysisResult& result) {
  for (const char* name : names) {
    result.Check(tree.GetBranch(name) != nullptr,
                 std::string(tree.GetName()) + ": missing branch " + name);
  }
}

TLeaf* FindOnlyLeaf(TBranch& branch) {
  if (auto* leaf = branch.GetLeaf(branch.GetName())) return leaf;
  auto* leaves = branch.GetListOfLeaves();
  if (leaves && leaves->GetEntries() == 1) {
    return static_cast<TLeaf*>(leaves->At(0));
  }
  return nullptr;
}

std::string ReadTextBranch(TTree& tree, const char* name,
                           AnalysisResult& result) {
  auto* branch = tree.GetBranch(name);
  result.Check(branch != nullptr, std::string("missing text branch: ") + name);
  if (!branch) return {};
  auto* leaf = dynamic_cast<TLeafC*>(FindOnlyLeaf(*branch));
  result.Check(leaf != nullptr, std::string("invalid text branch: ") + name);
  if (!leaf) return {};
  const auto* value = static_cast<const char*>(leaf->GetValuePointer());
  result.Check(value != nullptr, std::string("unreadable text branch: ") + name);
  return value ? std::string(value) : std::string();
}

}  // namespace

void analyze_integrated_minbias(
    const char* filename,
    const char* stageValue,
    const char* outputDirectory) {
  AnalysisResult result;
  const std::string stage(stageValue);
  const StageContract contract = Contract(stage, result);
  const std::filesystem::path finalDirectory(outputDirectory);
  const std::filesystem::path temporaryDirectory =
      finalDirectory.string() + ".tmp";

  result.Check(!std::filesystem::exists(finalDirectory),
               "analysis output directory already exists");
  result.Check(!std::filesystem::exists(temporaryDirectory),
               "analysis temporary directory already exists");

  TFile file(filename, "READ");
  result.Check(!file.IsZombie(), std::string("cannot open ROOT file: ") + filename);
  if (file.IsZombie() || result.Failures() != 0) {
    std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  TTree* metadata = RequireTree(file, "metadata", result);
  TTree* events = RequireTree(file, "events", result);
  TTree* hits = RequireTree(file, "hits", result);
  TTree* generator = RequireTree(file, "generator", result);
  if (!metadata || !events || !hits || !generator) {
    std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  RequireBranches(*metadata,
                  {"events", "mean_interactions", "seed_base", "threads",
                   "transport_neutrinos", "generator_audit", "check_overlaps",
                   "production_cut_mm", "max_abs_eta", "interaction_mode",
                   "physics_list", "generator_mode"},
                  result);
  RequireBranches(*events,
                  {"event", "mu_configured", "n_interactions_requested",
                   "n_interactions_generated", "generation_failures",
                   "generator_particles", "transported_particles",
                   "unknown_pdg_particles", "total_edep_mev",
                   "rejected_not_final", "rejected_neutrino_disabled",
                   "rejected_invisible_non_neutrino",
                   "rejected_outside_eta_acceptance", "unlineaged_steps",
                   "segmentation_failures"},
                  result);
  RequireBranches(*hits, {"event", "sampling", "edep_mev"}, result);
  if (result.Failures() != 0) {
    std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  int configuredEvents = -1;
  int seed = -1;
  int threads = -1;
  int transportNeutrinos = -1;
  int generatorAudit = -1;
  int checkOverlaps = -1;
  double meanInteractions = -1.0;
  double productionCutMm = -1.0;
  double maxAbsEta = -1.0;
  result.Check(metadata->GetEntries() == 1,
               "metadata must contain exactly one entry");
  if (metadata->GetEntries() == 1) {
    metadata->SetBranchAddress("events", &configuredEvents);
    metadata->SetBranchAddress("mean_interactions", &meanInteractions);
    metadata->SetBranchAddress("seed_base", &seed);
    metadata->SetBranchAddress("threads", &threads);
    metadata->SetBranchAddress("transport_neutrinos", &transportNeutrinos);
    metadata->SetBranchAddress("generator_audit", &generatorAudit);
    metadata->SetBranchAddress("check_overlaps", &checkOverlaps);
    metadata->SetBranchAddress("production_cut_mm", &productionCutMm);
    metadata->SetBranchAddress("max_abs_eta", &maxAbsEta);
    metadata->GetEntry(0);
    const std::string interactionMode =
        ReadTextBranch(*metadata, "interaction_mode", result);
    const std::string physicsList =
        ReadTextBranch(*metadata, "physics_list", result);
    const std::string generatorMode =
        ReadTextBranch(*metadata, "generator_mode", result);
    result.Check(interactionMode == "poisson", "interaction mode must be poisson");
    result.Check(physicsList == "FTFP_BERT_ATL", "physics list mismatch");
    result.Check(generatorMode == "pythia", "generator mode must be pythia");
    metadata->ResetBranchAddresses();
  }

  result.Check(configuredEvents == contract.events, "configured event count mismatch");
  result.Check(NearlyEqual(meanInteractions, contract.meanInteractions),
               "configured interaction mean mismatch");
  result.Check(seed == contract.seed, "configured seed mismatch");
  result.Check(threads == 1, "transport must use one thread");
  result.Check(transportNeutrinos == 0, "neutrino transport must be disabled");
  result.Check(generatorAudit == contract.generatorAudit,
               "generator audit policy mismatch");
  result.Check(checkOverlaps == contract.checkOverlaps,
               "overlap-check policy mismatch");
  result.Check(NearlyEqual(productionCutMm, 1.0), "production cut must be 1 mm");
  result.Check(NearlyEqual(maxAbsEta, 1.8), "max_abs_eta must be 1.8");
  result.Check(events->GetEntries() == configuredEvents,
               "events tree entry count mismatch");

  int event = -1;
  int requested = -1;
  int generated = -1;
  int failures = -1;
  int generatorParticles = -1;
  int transported = -1;
  int unknown = -1;
  int rejectedNotFinal = -1;
  int rejectedNeutrino = -1;
  int rejectedInvisible = -1;
  int rejectedEta = -1;
  int unlineagedSteps = -1;
  int segmentationFailures = -1;
  double eventMu = -1.0;
  double eventEnergy = -1.0;
  events->SetBranchAddress("event", &event);
  events->SetBranchAddress("mu_configured", &eventMu);
  events->SetBranchAddress("n_interactions_requested", &requested);
  events->SetBranchAddress("n_interactions_generated", &generated);
  events->SetBranchAddress("generation_failures", &failures);
  events->SetBranchAddress("generator_particles", &generatorParticles);
  events->SetBranchAddress("transported_particles", &transported);
  events->SetBranchAddress("unknown_pdg_particles", &unknown);
  events->SetBranchAddress("total_edep_mev", &eventEnergy);
  events->SetBranchAddress("rejected_not_final", &rejectedNotFinal);
  events->SetBranchAddress("rejected_neutrino_disabled", &rejectedNeutrino);
  events->SetBranchAddress("rejected_invisible_non_neutrino", &rejectedInvisible);
  events->SetBranchAddress("rejected_outside_eta_acceptance", &rejectedEta);
  events->SetBranchAddress("unlineaged_steps", &unlineagedSteps);
  events->SetBranchAddress("segmentation_failures", &segmentationFailures);

  long long totalRequested = 0;
  long long totalGenerated = 0;
  long long totalFailures = 0;
  long long totalGeneratorParticles = 0;
  long long totalTransported = 0;
  long long totalUnknown = 0;
  double totalEnergy = 0.0;
  double requestedSquareSum = 0.0;
  std::set<int> eventIds;
  for (Long64_t entry = 0; entry < events->GetEntries(); ++entry) {
    events->GetEntry(entry);
    result.Check(eventIds.insert(event).second, "duplicate event identifier");
    result.Check(NearlyEqual(eventMu, meanInteractions), "event mu mismatch");
    result.Check(requested >= 0 && generated >= 0 && failures >= 0 &&
                     requested == generated + failures,
                 "interaction accounting mismatch");
    result.Check(generatorParticles >= 0 && transported >= 0 && unknown == 0 &&
                     rejectedNotFinal >= 0 && rejectedNeutrino >= 0 &&
                     rejectedInvisible >= 0 && rejectedEta >= 0 &&
                     generatorParticles == transported + unknown +
                         rejectedNotFinal + rejectedNeutrino +
                         rejectedInvisible + rejectedEta,
                 "particle accounting mismatch");
    result.Check(unlineagedSteps == 0 && segmentationFailures == 0,
                 "lineage or segmentation failure");
    result.Check(std::isfinite(eventEnergy) && eventEnergy >= 0.0,
                 "invalid event energy");
    totalRequested += requested;
    totalGenerated += generated;
    totalFailures += failures;
    totalGeneratorParticles += generatorParticles;
    totalTransported += transported;
    totalUnknown += unknown;
    totalEnergy += eventEnergy;
    requestedSquareSum += static_cast<double>(requested) * requested;
  }
  events->ResetBranchAddresses();

  int hitEvent = -1;
  int sampling = -1;
  double hitEnergy = -1.0;
  hits->SetBranchAddress("event", &hitEvent);
  hits->SetBranchAddress("sampling", &sampling);
  hits->SetBranchAddress("edep_mev", &hitEnergy);
  std::array<long long, 10> samplingHits{};
  std::array<double, 10> samplingEnergy{};
  double totalHitEnergy = 0.0;
  for (Long64_t entry = 0; entry < hits->GetEntries(); ++entry) {
    hits->GetEntry(entry);
    result.Check(eventIds.count(hitEvent) == 1, "hit references unknown event");
    result.Check(sampling >= 0 && sampling < 10, "invalid hit sampling");
    result.Check(std::isfinite(hitEnergy) && hitEnergy > 0.0,
                 "invalid hit energy");
    if (sampling >= 0 && sampling < 10 && std::isfinite(hitEnergy) &&
        hitEnergy > 0.0) {
      ++samplingHits.at(static_cast<std::size_t>(sampling));
      samplingEnergy.at(static_cast<std::size_t>(sampling)) += hitEnergy;
      totalHitEnergy += hitEnergy;
    }
  }
  hits->ResetBranchAddresses();
  result.Check(NearlyEqual(totalHitEnergy, totalEnergy), "energy closure mismatch");
  result.Check(hits->GetEntries() > 0, "minimum-bias sample contains no hits");

  int observedSamplings = 0;
  for (const auto count : samplingHits) {
    if (count > 0) ++observedSamplings;
    if (contract.requireAllSamplings) {
      result.Check(count > 0, "required sampling is not observed");
    }
  }

  const double expectedInteractions = configuredEvents * meanInteractions;
  const double poissonZ = expectedInteractions > 0.0
      ? std::abs(totalRequested - expectedInteractions) /
            std::sqrt(expectedInteractions)
      : 0.0;
  if (contract.requirePoisson) {
    result.Check(poissonZ <= 5.0, "Poisson count lies outside five sigma");
  }
  const double requestedMean = configuredEvents > 0
      ? static_cast<double>(totalRequested) / configuredEvents
      : 0.0;
  const double requestedVariance = configuredEvents > 1
      ? std::max(0.0,
                 (requestedSquareSum -
                  configuredEvents * requestedMean * requestedMean) /
                     (configuredEvents - 1))
      : 0.0;
  result.Check(std::isfinite(requestedVariance) && requestedVariance >= 0.0,
               "invalid requested-interaction variance");
  result.Check(generatorAudit == 1
                   ? generator->GetEntries() == totalGeneratorParticles
                   : generator->GetEntries() == 0,
               "generator entry count mismatch");

  if (result.Failures() != 0) {
    std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  try {
    std::filesystem::create_directories(temporaryDirectory);
    const std::array<const char*, 10> samplingNames{
        "PSB", "EMB1", "EMB2", "EMB3", "TileCal1", "TileCal2",
        "TileCal3", "TileExt1", "TileExt2", "TileExt3"};
    std::ofstream summary(temporaryDirectory / "integrated_summary.csv");
    std::ofstream samplings(temporaryDirectory / "sampling_summary.csv");
    std::ofstream validation(temporaryDirectory / "integrated_validation.txt");
    if (!summary || !samplings || !validation) {
      throw std::runtime_error("cannot create analysis products");
    }
    summary << std::setprecision(17)
            << "stage,bunch_crossings,mean_interactions,seed,threads,"
               "transport_neutrinos,generator_audit,check_overlaps,"
               "requested_interactions,generated_interactions,"
               "generation_failures,generator_particles,transported_particles,"
               "unknown_pdg_particles,total_energy_mev,hit_count,"
               "generator_entries,observed_samplings,requested_mean,"
               "requested_variance,poisson_z\n"
            << stage << ',' << configuredEvents << ',' << meanInteractions << ','
            << seed << ',' << threads << ',' << transportNeutrinos << ','
            << generatorAudit << ',' << checkOverlaps << ',' << totalRequested
            << ',' << totalGenerated << ',' << totalFailures << ','
            << totalGeneratorParticles << ',' << totalTransported << ','
            << totalUnknown << ',' << totalEnergy << ',' << hits->GetEntries()
            << ',' << generator->GetEntries() << ',' << observedSamplings << ','
            << requestedMean << ',' << requestedVariance << ',' << poissonZ
            << '\n';
    samplings << std::setprecision(17)
              << "sampling,name,hit_count,total_energy_mev,energy_fraction\n";
    for (std::size_t index = 0; index < samplingNames.size(); ++index) {
      const double fraction = totalEnergy > 0.0
          ? samplingEnergy.at(index) / totalEnergy
          : 0.0;
      samplings << index << ',' << samplingNames.at(index) << ','
                << samplingHits.at(index) << ',' << samplingEnergy.at(index)
                << ',' << fraction << '\n';
    }
    validation << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=PASS\n"
               << "stage=" << stage << '\n'
               << "energy_closure=PASS\n"
               << "particle_accounting=PASS\n"
               << "sampling_coverage="
               << (contract.requireAllSamplings ? "PASS" : "STRUCTURAL")
               << '\n'
               << "poisson_consistency="
               << (contract.requirePoisson ? "PASS" : "NOT_APPLICABLE")
               << '\n';
    summary.close();
    samplings.close();
    validation.close();
    std::filesystem::rename(temporaryDirectory, finalDirectory);
  } catch (const std::exception& error) {
    std::filesystem::remove_all(temporaryDirectory);
    std::cerr << "[FAIL] " << error.what() << '\n';
    std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=FAIL failures=1\n";
    return;
  }

  std::cout << "INTEGRATED_MINBIAS_ANALYSIS_RESULT=PASS stage=" << stage
            << " events=" << configuredEvents
            << " requested=" << totalRequested
            << " generated=" << totalGenerated
            << " failures=" << totalFailures
            << " samplings=" << observedSamplings << '\n';
}
