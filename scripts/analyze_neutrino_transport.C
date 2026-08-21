#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TLeafC.h>
#include <TObjArray.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <initializer_list>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>

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

bool NearlyEqual(const double left, const double right) {
  const double scale = std::max({1.0, std::abs(left), std::abs(right)});
  return std::abs(left - right) <= 1.0e-10 * scale;
}

bool SameGeneratorFloatingValue(const double left, const double right) {
  if (std::isnan(left) || std::isnan(right)) {
    return std::isnan(left) && std::isnan(right);
  }
  if (std::isinf(left) || std::isinf(right)) return left == right;
  return NearlyEqual(left, right);
}

bool IsNeutrinoPdg(const int pdg) {
  const int absolute = std::abs(pdg);
  return absolute == 12 || absolute == 14 || absolute == 16 ||
         absolute == 18;
}

TTree* RequireTree(TFile& file, const char* name, AnalysisResult& result) {
  auto* tree = file.Get<TTree>(name);
  result.Check(tree != nullptr,
               std::string(file.GetName()) + ": missing TTree " + name);
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

struct MetadataRecord {
  int events = -1;
  int firstBcid = -1;
  int threads = -1;
  int seed = -1;
  int transportNeutrinos = -1;
  int generatorAudit = -1;
  int checkOverlaps = -1;
  double meanInteractions = -1.0;
  double productionCutMm = -1.0;
  double maxAbsEta = -1.0;
  std::string interactionMode;
  std::string physicsList;
  std::string generatorMode;
};

MetadataRecord ReadMetadata(TTree& tree, AnalysisResult& result) {
  RequireBranches(
      tree,
      {"events", "first_bcid", "threads", "seed_base",
       "transport_neutrinos", "generator_audit", "check_overlaps",
       "mean_interactions", "production_cut_mm", "max_abs_eta",
       "interaction_mode", "physics_list", "generator_mode"},
      result);
  MetadataRecord record;
  result.Check(tree.GetEntries() == 1,
               std::string(tree.GetName()) + ": metadata must have one entry");
  if (result.Failures() != 0 || tree.GetEntries() != 1) return record;
  tree.SetBranchAddress("events", &record.events);
  tree.SetBranchAddress("first_bcid", &record.firstBcid);
  tree.SetBranchAddress("threads", &record.threads);
  tree.SetBranchAddress("seed_base", &record.seed);
  tree.SetBranchAddress("transport_neutrinos", &record.transportNeutrinos);
  tree.SetBranchAddress("generator_audit", &record.generatorAudit);
  tree.SetBranchAddress("check_overlaps", &record.checkOverlaps);
  tree.SetBranchAddress("mean_interactions", &record.meanInteractions);
  tree.SetBranchAddress("production_cut_mm", &record.productionCutMm);
  tree.SetBranchAddress("max_abs_eta", &record.maxAbsEta);
  tree.GetEntry(0);
  record.interactionMode = ReadTextBranch(tree, "interaction_mode", result);
  record.physicsList = ReadTextBranch(tree, "physics_list", result);
  record.generatorMode = ReadTextBranch(tree, "generator_mode", result);
  tree.ResetBranchAddresses();
  return record;
}

void ValidateMetadataPair(const MetadataRecord& off,
                          const MetadataRecord& on,
                          const int expectedEvents,
                          const int expectedSeed,
                          AnalysisResult& result) {
  for (const auto* record : {&off, &on}) {
    result.Check(record->events == expectedEvents,
                 "metadata event count mismatch");
    result.Check(record->firstBcid == 0, "metadata first BCID mismatch");
    result.Check(record->threads == 1, "metadata thread count mismatch");
    result.Check(record->seed == expectedSeed, "metadata seed mismatch");
    result.Check(record->generatorAudit == 1,
                 "generator audit must be enabled");
    result.Check(record->checkOverlaps == 1,
                 "overlap check must be enabled");
    result.Check(NearlyEqual(record->meanInteractions, 1.0),
                 "metadata interaction mean mismatch");
    result.Check(NearlyEqual(record->productionCutMm, 1.0),
                 "metadata production cut mismatch");
    result.Check(NearlyEqual(record->maxAbsEta, 1.8),
                 "metadata eta acceptance mismatch");
    result.Check(record->interactionMode == "poisson",
                 "metadata interaction mode mismatch");
    result.Check(record->physicsList == "FTFP_BERT_ATL",
                 "metadata physics-list mismatch");
    result.Check(record->generatorMode == "pythia",
                 "metadata generator mode mismatch");
  }
  result.Check(off.transportNeutrinos == 0,
               "OFF metadata must disable neutrino transport");
  result.Check(on.transportNeutrinos == 1,
               "ON metadata must enable neutrino transport");
  result.Check(off.events == on.events && off.firstBcid == on.firstBcid &&
                   off.threads == on.threads && off.seed == on.seed &&
                   off.generatorAudit == on.generatorAudit &&
                   off.checkOverlaps == on.checkOverlaps &&
                   NearlyEqual(off.meanInteractions, on.meanInteractions) &&
                   NearlyEqual(off.productionCutMm, on.productionCutMm) &&
                   NearlyEqual(off.maxAbsEta, on.maxAbsEta) &&
                   off.interactionMode == on.interactionMode &&
                   off.physicsList == on.physicsList &&
                   off.generatorMode == on.generatorMode,
               "metadata pair differs outside the neutrino switch");
}

struct EventRecord {
  int event = -1;
  int bcid = -1;
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
  double energy = -1.0;
};

std::map<int, EventRecord> ReadEvents(TTree& tree, AnalysisResult& result,
                                      const std::string& label) {
  RequireBranches(
      tree,
      {"event", "bcid", "n_interactions_requested",
       "n_interactions_generated", "generation_failures",
       "generator_particles", "transported_particles",
       "unknown_pdg_particles", "total_edep_mev", "rejected_not_final",
       "rejected_neutrino_disabled", "rejected_invisible_non_neutrino",
       "rejected_outside_eta_acceptance", "unlineaged_steps",
       "segmentation_failures"},
      result);
  std::map<int, EventRecord> records;
  if (result.Failures() != 0) return records;
  EventRecord record;
  tree.SetBranchAddress("event", &record.event);
  tree.SetBranchAddress("bcid", &record.bcid);
  tree.SetBranchAddress("n_interactions_requested", &record.requested);
  tree.SetBranchAddress("n_interactions_generated", &record.generated);
  tree.SetBranchAddress("generation_failures", &record.failures);
  tree.SetBranchAddress("generator_particles", &record.generatorParticles);
  tree.SetBranchAddress("transported_particles", &record.transported);
  tree.SetBranchAddress("unknown_pdg_particles", &record.unknown);
  tree.SetBranchAddress("total_edep_mev", &record.energy);
  tree.SetBranchAddress("rejected_not_final", &record.rejectedNotFinal);
  tree.SetBranchAddress("rejected_neutrino_disabled", &record.rejectedNeutrino);
  tree.SetBranchAddress("rejected_invisible_non_neutrino",
                        &record.rejectedInvisible);
  tree.SetBranchAddress("rejected_outside_eta_acceptance", &record.rejectedEta);
  tree.SetBranchAddress("unlineaged_steps", &record.unlineagedSteps);
  tree.SetBranchAddress("segmentation_failures", &record.segmentationFailures);
  for (Long64_t entry = 0; entry < tree.GetEntries(); ++entry) {
    tree.GetEntry(entry);
    result.Check(records.emplace(record.event, record).second,
                 label + ": duplicate event identifier");
    result.Check(record.event >= 0 && record.bcid >= 0,
                 label + ": negative event or BCID");
    result.Check(record.requested >= 0 && record.generated >= 0 &&
                     record.failures >= 0 &&
                     record.requested == record.generated + record.failures,
                 label + ": interaction accounting mismatch");
    result.Check(record.generatorParticles >= 0 && record.transported >= 0 &&
                     record.unknown == 0 && record.rejectedNotFinal >= 0 &&
                     record.rejectedNeutrino >= 0 &&
                     record.rejectedInvisible >= 0 && record.rejectedEta >= 0 &&
                     record.generatorParticles ==
                         record.transported + record.unknown +
                             record.rejectedNotFinal + record.rejectedNeutrino +
                             record.rejectedInvisible + record.rejectedEta,
                 label + ": particle accounting mismatch");
    result.Check(record.unlineagedSteps == 0 &&
                     record.segmentationFailures == 0,
                 label + ": lineage or segmentation failure");
    result.Check(std::isfinite(record.energy) && record.energy >= 0.0,
                 label + ": invalid event energy");
  }
  tree.ResetBranchAddresses();
  return records;
}

using GeneratorKey = std::tuple<int, int, int>;

struct GeneratorRecord {
  int event = -1;
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
  int accepted = 0;
  int rejection = -1;
  double px = 0.0;
  double py = 0.0;
  double pz = 0.0;
  double energy = 0.0;
  double mass = 0.0;
  double eta = 0.0;
  double phi = 0.0;
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
  double t = 0.0;
};

std::map<GeneratorKey, GeneratorRecord> ReadGenerator(
    TTree& tree, AnalysisResult& result, const std::string& label) {
  RequireBranches(
      tree,
      {"event", "subevent", "index", "pdg", "status", "mother1",
       "mother2", "daughter1", "daughter2", "is_final", "is_visible",
       "px_gev", "py_gev", "pz_gev", "energy_gev", "mass_gev", "eta",
       "phi", "x_prod_mm", "y_prod_mm", "z_prod_mm",
       "t_prod_mm_over_c", "accepted_for_transport", "rejection_code"},
      result);
  std::map<GeneratorKey, GeneratorRecord> records;
  if (result.Failures() != 0) return records;
  GeneratorRecord record;
  tree.SetBranchAddress("event", &record.event);
  tree.SetBranchAddress("subevent", &record.subevent);
  tree.SetBranchAddress("index", &record.index);
  tree.SetBranchAddress("pdg", &record.pdg);
  tree.SetBranchAddress("status", &record.status);
  tree.SetBranchAddress("mother1", &record.mother1);
  tree.SetBranchAddress("mother2", &record.mother2);
  tree.SetBranchAddress("daughter1", &record.daughter1);
  tree.SetBranchAddress("daughter2", &record.daughter2);
  tree.SetBranchAddress("is_final", &record.isFinal);
  tree.SetBranchAddress("is_visible", &record.isVisible);
  tree.SetBranchAddress("px_gev", &record.px);
  tree.SetBranchAddress("py_gev", &record.py);
  tree.SetBranchAddress("pz_gev", &record.pz);
  tree.SetBranchAddress("energy_gev", &record.energy);
  tree.SetBranchAddress("mass_gev", &record.mass);
  tree.SetBranchAddress("eta", &record.eta);
  tree.SetBranchAddress("phi", &record.phi);
  tree.SetBranchAddress("x_prod_mm", &record.x);
  tree.SetBranchAddress("y_prod_mm", &record.y);
  tree.SetBranchAddress("z_prod_mm", &record.z);
  tree.SetBranchAddress("t_prod_mm_over_c", &record.t);
  tree.SetBranchAddress("accepted_for_transport", &record.accepted);
  tree.SetBranchAddress("rejection_code", &record.rejection);
  for (Long64_t entry = 0; entry < tree.GetEntries(); ++entry) {
    tree.GetEntry(entry);
    const GeneratorKey key{record.event, record.subevent, record.index};
    result.Check(records.emplace(key, record).second,
                 label + ": duplicate generator key");
  }
  tree.ResetBranchAddresses();
  return records;
}

bool SameGeneratorContent(const GeneratorRecord& left,
                          const GeneratorRecord& right) {
  return left.pdg == right.pdg && left.status == right.status &&
         left.mother1 == right.mother1 && left.mother2 == right.mother2 &&
         left.daughter1 == right.daughter1 &&
         left.daughter2 == right.daughter2 &&
         left.isFinal == right.isFinal && left.isVisible == right.isVisible &&
         SameGeneratorFloatingValue(left.px, right.px) &&
         SameGeneratorFloatingValue(left.py, right.py) &&
         SameGeneratorFloatingValue(left.pz, right.pz) &&
         SameGeneratorFloatingValue(left.energy, right.energy) &&
         SameGeneratorFloatingValue(left.mass, right.mass) &&
         SameGeneratorFloatingValue(left.eta, right.eta) &&
         SameGeneratorFloatingValue(left.phi, right.phi) &&
         SameGeneratorFloatingValue(left.x, right.x) &&
         SameGeneratorFloatingValue(left.y, right.y) &&
         SameGeneratorFloatingValue(left.z, right.z) &&
         SameGeneratorFloatingValue(left.t, right.t);
}

using HitKey = std::tuple<int, int, std::int64_t>;

struct HitRecord {
  int event = -1;
  int bcid = -1;
  int subevent = -1;
  int sampling = -1;
  int side = 0;
  int etaIndex = -1;
  int phiIndex = -1;
  double cellId = -1.0;
  double energy = -1.0;
};

struct HitData {
  std::map<HitKey, HitRecord> records;
  std::map<int, long long> countsByEvent;
  std::map<int, double> energyByEvent;
  double totalEnergy = 0.0;
};

HitData ReadHits(TTree& tree, AnalysisResult& result,
                 const std::string& label) {
  RequireBranches(
      tree,
      {"event", "bcid", "subevent", "cell_id", "sampling", "side",
       "eta_index", "phi_index", "edep_mev"},
      result);
  HitData data;
  if (result.Failures() != 0) return data;
  HitRecord record;
  tree.SetBranchAddress("event", &record.event);
  tree.SetBranchAddress("bcid", &record.bcid);
  tree.SetBranchAddress("subevent", &record.subevent);
  tree.SetBranchAddress("cell_id", &record.cellId);
  tree.SetBranchAddress("sampling", &record.sampling);
  tree.SetBranchAddress("side", &record.side);
  tree.SetBranchAddress("eta_index", &record.etaIndex);
  tree.SetBranchAddress("phi_index", &record.phiIndex);
  tree.SetBranchAddress("edep_mev", &record.energy);
  for (Long64_t entry = 0; entry < tree.GetEntries(); ++entry) {
    tree.GetEntry(entry);
    result.Check(record.event >= 0 && record.bcid >= 0 && record.subevent >= 0,
                 label + ": invalid hit event identity");
    result.Check(record.sampling >= 0 && record.sampling < 10,
                 label + ": invalid hit sampling");
    result.Check(std::isfinite(record.cellId) && record.cellId >= 0.0 &&
                     record.cellId == std::floor(record.cellId),
                 label + ": invalid packed cell identifier");
    result.Check(std::isfinite(record.energy) && record.energy > 0.0,
                 label + ": invalid hit energy");
    if (!std::isfinite(record.cellId) || record.cellId < 0.0) continue;
    const auto packed = static_cast<std::int64_t>(std::llround(record.cellId));
    const HitKey key{record.event, record.subevent, packed};
    result.Check(data.records.emplace(key, record).second,
                 label + ": duplicate hit key");
    ++data.countsByEvent[record.event];
    data.energyByEvent[record.event] += record.energy;
    data.totalEnergy += record.energy;
  }
  tree.ResetBranchAddresses();
  return data;
}

struct HitComparison {
  long long changed = 0;
  long long missingOff = 0;
  long long missingOn = 0;
  double l1 = 0.0;
  double maximum = 0.0;
};

HitComparison CompareHits(const HitData& off, const HitData& on,
                          AnalysisResult& result) {
  HitComparison comparison;
  std::set<HitKey> keys;
  for (const auto& [key, record] : off.records) {
    (void)record;
    keys.insert(key);
  }
  for (const auto& [key, record] : on.records) {
    (void)record;
    keys.insert(key);
  }
  for (const auto& key : keys) {
    const auto offIterator = off.records.find(key);
    const auto onIterator = on.records.find(key);
    const bool hasOff = offIterator != off.records.end();
    const bool hasOn = onIterator != on.records.end();
    if (!hasOff) {
      ++comparison.missingOff;
      comparison.l1 += std::abs(onIterator->second.energy);
      comparison.maximum =
          std::max(comparison.maximum, std::abs(onIterator->second.energy));
      continue;
    }
    if (!hasOn) {
      ++comparison.missingOn;
      comparison.l1 += std::abs(offIterator->second.energy);
      comparison.maximum =
          std::max(comparison.maximum, std::abs(offIterator->second.energy));
      continue;
    }
    const HitRecord& left = offIterator->second;
    const HitRecord& right = onIterator->second;
    result.Check(left.bcid == right.bcid && left.sampling == right.sampling &&
                     left.side == right.side && left.etaIndex == right.etaIndex &&
                     left.phiIndex == right.phiIndex,
                 "paired hit geometry mismatch");
    const double difference = right.energy - left.energy;
    const double absolute = std::abs(difference);
    comparison.l1 += absolute;
    comparison.maximum = std::max(comparison.maximum, absolute);
    if (!NearlyEqual(left.energy, right.energy)) ++comparison.changed;
  }
  return comparison;
}

}  // namespace

void analyze_neutrino_transport(const char* offFilename,
                                const char* onFilename,
                                const char* outputDirectory,
                                const int expectedEvents = 100,
                                const int expectedSeed = 512,
                                const bool requirePositiveEligible = true) {
  AnalysisResult result;
  result.Check(expectedEvents > 0, "expected event count must be positive");
  result.Check(expectedSeed > 0, "expected seed must be positive");
  const std::filesystem::path finalDirectory(outputDirectory);
  const std::filesystem::path temporaryDirectory =
      finalDirectory.string() + ".tmp";
  result.Check(!std::filesystem::exists(finalDirectory),
               "analysis output directory already exists");
  result.Check(!std::filesystem::exists(temporaryDirectory),
               "analysis temporary directory already exists");

  TFile offFile(offFilename, "READ");
  TFile onFile(onFilename, "READ");
  result.Check(!offFile.IsZombie(),
               std::string("cannot open OFF ROOT file: ") + offFilename);
  result.Check(!onFile.IsZombie(),
               std::string("cannot open ON ROOT file: ") + onFilename);
  if (result.Failures() != 0) {
    std::cout << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  TTree* offMetadata = RequireTree(offFile, "metadata", result);
  TTree* onMetadata = RequireTree(onFile, "metadata", result);
  TTree* offEventsTree = RequireTree(offFile, "events", result);
  TTree* onEventsTree = RequireTree(onFile, "events", result);
  TTree* offHitsTree = RequireTree(offFile, "hits", result);
  TTree* onHitsTree = RequireTree(onFile, "hits", result);
  TTree* offGeneratorTree = RequireTree(offFile, "generator", result);
  TTree* onGeneratorTree = RequireTree(onFile, "generator", result);
  if (result.Failures() != 0 || !offMetadata || !onMetadata ||
      !offEventsTree || !onEventsTree || !offHitsTree || !onHitsTree ||
      !offGeneratorTree || !onGeneratorTree) {
    std::cout << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  const MetadataRecord offMeta = ReadMetadata(*offMetadata, result);
  const MetadataRecord onMeta = ReadMetadata(*onMetadata, result);
  ValidateMetadataPair(offMeta, onMeta, expectedEvents, expectedSeed, result);
  const auto offEvents = ReadEvents(*offEventsTree, result, "OFF");
  const auto onEvents = ReadEvents(*onEventsTree, result, "ON");
  const auto offGenerator = ReadGenerator(*offGeneratorTree, result, "OFF");
  const auto onGenerator = ReadGenerator(*onGeneratorTree, result, "ON");
  const HitData offHits = ReadHits(*offHitsTree, result, "OFF");
  const HitData onHits = ReadHits(*onHitsTree, result, "ON");

  result.Check(offEvents.size() == static_cast<std::size_t>(expectedEvents) &&
                   onEvents.size() == static_cast<std::size_t>(expectedEvents),
               "paired event trees have an unexpected event count");
  result.Check(offGenerator.size() == onGenerator.size(),
               "paired generator entry counts differ");

  std::map<int, int> eligibleByEvent;
  std::map<int, int> outsideByEvent;
  long long eligibleNeutrinos = 0;
  long long outsideNeutrinos = 0;
  for (const auto& [key, offRecord] : offGenerator) {
    const auto onIterator = onGenerator.find(key);
    result.Check(onIterator != onGenerator.end(),
                 "generator key missing from ON condition");
    if (onIterator == onGenerator.end()) continue;
    const GeneratorRecord& onRecord = onIterator->second;
    result.Check(SameGeneratorContent(offRecord, onRecord),
                 "generator content differs outside decision fields");
    if (offRecord.rejection == 2) {
      result.Check(IsNeutrinoPdg(offRecord.pdg),
                   "neutrino-disabled code assigned to non-neutrino");
      result.Check(offRecord.isFinal == 1 && offRecord.accepted == 0,
                   "invalid OFF neutrino classification");
      if (onRecord.accepted == 1 && onRecord.rejection == 0) {
        result.Check(std::isfinite(offRecord.eta) &&
                         std::abs(offRecord.eta) <= 1.8,
                     "accepted neutrino lies outside eta acceptance");
        ++eligibleNeutrinos;
        ++eligibleByEvent[offRecord.event];
      } else if (onRecord.accepted == 0 && onRecord.rejection == 4) {
        result.Check(!std::isfinite(offRecord.eta) ||
                         std::abs(offRecord.eta) > 1.8,
                     "outside-eta neutrino classification mismatch");
        ++outsideNeutrinos;
        ++outsideByEvent[offRecord.event];
      } else {
        result.Check(false,
                     "neutrino decision did not resolve to accepted or outside eta");
      }
    } else {
      result.Check(offRecord.accepted == onRecord.accepted &&
                       offRecord.rejection == onRecord.rejection,
                   "non-neutrino generator decision changed");
    }
  }
  if (requirePositiveEligible) {
    result.Check(eligibleNeutrinos > 0,
                 "eligible neutrino count must be positive");
  }

  long long offTransportedTotal = 0;
  long long onTransportedTotal = 0;
  long long requestedInteractionsTotal = 0;
  long long generatedInteractionsTotal = 0;
  long long generationFailuresTotal = 0;
  long long unknownPdgParticlesTotal = 0;
  long long unlineagedStepsTotal = 0;
  long long segmentationFailuresTotal = 0;
  double offEnergyTotal = 0.0;
  double onEnergyTotal = 0.0;
  double eventEnergyAbsoluteDifference = 0.0;
  for (int event = 0; event < expectedEvents; ++event) {
    const auto offIterator = offEvents.find(event);
    const auto onIterator = onEvents.find(event);
    result.Check(offIterator != offEvents.end() && onIterator != onEvents.end(),
                 "paired event identifier missing");
    if (offIterator == offEvents.end() || onIterator == onEvents.end()) continue;
    const EventRecord& off = offIterator->second;
    const EventRecord& on = onIterator->second;
    result.Check(off.bcid == event && on.bcid == event,
                 "paired BCID coverage mismatch");
    result.Check(off.requested == on.requested &&
                     off.generated == on.generated &&
                     off.failures == on.failures &&
                     off.generatorParticles == on.generatorParticles &&
                     off.unknown == on.unknown &&
                     off.rejectedNotFinal == on.rejectedNotFinal &&
                     off.rejectedInvisible == on.rejectedInvisible &&
                     off.unlineagedSteps == on.unlineagedSteps &&
                     off.segmentationFailures == on.segmentationFailures,
                 "paired event accounting differs outside neutrino fields");
    const int eligible = eligibleByEvent[event];
    const int outside = outsideByEvent[event];
    result.Check(off.rejectedNeutrino == eligible + outside &&
                     on.rejectedNeutrino == 0,
                 "event neutrino rejection accounting mismatch");
    result.Check(on.rejectedEta - off.rejectedEta == outside,
                 "outside-eta neutrino migration mismatch");
    result.Check(on.transported - off.transported == eligible,
                 "transported-particle delta mismatch");
    offTransportedTotal += off.transported;
    onTransportedTotal += on.transported;
    requestedInteractionsTotal += off.requested;
    generatedInteractionsTotal += off.generated;
    generationFailuresTotal += off.failures;
    unknownPdgParticlesTotal += off.unknown;
    unlineagedStepsTotal += off.unlineagedSteps;
    segmentationFailuresTotal += off.segmentationFailures;
    offEnergyTotal += off.energy;
    onEnergyTotal += on.energy;
    eventEnergyAbsoluteDifference += std::abs(on.energy - off.energy);
  }
  result.Check(onTransportedTotal - offTransportedTotal == eligibleNeutrinos,
               "total transported-particle delta mismatch");

  const HitComparison hitComparison = CompareHits(offHits, onHits, result);
  result.Check(NearlyEqual(offHits.totalEnergy, offEnergyTotal),
               "OFF event-to-hit energy closure mismatch");
  result.Check(NearlyEqual(onHits.totalEnergy, onEnergyTotal),
               "ON event-to-hit energy closure mismatch");

  if (result.Failures() != 0) {
    std::cout << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=FAIL failures="
              << result.Failures() << '\n';
    return;
  }

  try {
    std::filesystem::create_directories(temporaryDirectory);
    std::ofstream summary(temporaryDirectory / "paired_summary.csv");
    std::ofstream events(temporaryDirectory / "paired_events.csv");
    std::ofstream validation(temporaryDirectory / "paired_validation.txt");
    if (!summary || !events || !validation) {
      throw std::runtime_error("cannot create paired analysis products");
    }
    const double energyDelta = onEnergyTotal - offEnergyTotal;
    const double relativeDelta = std::max(offEnergyTotal, onEnergyTotal) > 0.0
        ? eventEnergyAbsoluteDifference /
              std::max(offEnergyTotal, onEnergyTotal)
        : 0.0;
    summary << std::setprecision(17)
            << "events,seed,mean_interactions,eligible_neutrinos,"
               "outside_acceptance_neutrinos,"
               "off_transported,on_transported,transported_delta,"
               "off_total_energy_mev,on_total_energy_mev,energy_delta_mev,"
               "energy_abs_delta_mev,energy_relative_delta,off_hit_count,"
               "on_hit_count,changed_hit_cells,missing_off_hit_cells,"
               "missing_on_hit_cells,hit_energy_l1_mev,"
               "max_abs_hit_delta_mev,generator_entries,"
               "requested_interactions,generated_interactions,"
               "generation_failures,unknown_pdg_particles,"
               "unlineaged_steps,segmentation_failures\n"
            << expectedEvents << ',' << expectedSeed << ',' << 1.0 << ','
            << eligibleNeutrinos
            << ',' << outsideNeutrinos << ',' << offTransportedTotal << ','
            << onTransportedTotal << ','
            << (onTransportedTotal - offTransportedTotal) << ','
            << offEnergyTotal << ',' << onEnergyTotal << ',' << energyDelta
            << ',' << eventEnergyAbsoluteDifference << ',' << relativeDelta
            << ',' << offHits.records.size() << ',' << onHits.records.size()
            << ',' << hitComparison.changed << ',' << hitComparison.missingOff
            << ',' << hitComparison.missingOn << ',' << hitComparison.l1
            << ',' << hitComparison.maximum << ',' << offGenerator.size()
            << ',' << requestedInteractionsTotal << ','
            << generatedInteractionsTotal << ',' << generationFailuresTotal
            << ',' << unknownPdgParticlesTotal << ',' << unlineagedStepsTotal
            << ',' << segmentationFailuresTotal
            << '\n';
    events << std::setprecision(17)
           << "event,bcid,eligible_neutrinos,outside_acceptance_neutrinos,"
              "off_transported,on_transported,"
              "off_energy_mev,on_energy_mev,energy_delta_mev,"
              "energy_abs_delta_mev,off_hit_count,on_hit_count\n";
    for (int event = 0; event < expectedEvents; ++event) {
      const EventRecord& off = offEvents.at(event);
      const EventRecord& on = onEvents.at(event);
      const double delta = on.energy - off.energy;
      const auto offCount = offHits.countsByEvent.count(event)
          ? offHits.countsByEvent.at(event)
          : 0;
      const auto onCount = onHits.countsByEvent.count(event)
          ? onHits.countsByEvent.at(event)
          : 0;
      events << event << ',' << off.bcid << ',' << eligibleByEvent[event] << ','
             << outsideByEvent[event] << ',' << off.transported << ','
             << on.transported << ',' << off.energy << ',' << on.energy << ','
             << delta << ',' << std::abs(delta) << ',' << offCount << ','
             << onCount << '\n';
    }
    validation << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS\n"
               << "metadata_pairing=PASS\n"
               << "event_pairing=PASS\n"
               << "generator_pairing=PASS\n"
               << "particle_accounting=PASS\n"
               << "eligible_neutrinos=" << eligibleNeutrinos << '\n'
               << "outside_acceptance_neutrinos=" << outsideNeutrinos << '\n'
               << "energy_difference_classification=REPORTED_NOT_ASSUMED\n";
    summary.close();
    events.close();
    validation.close();
    std::filesystem::rename(temporaryDirectory, finalDirectory);
  } catch (const std::exception& error) {
    std::filesystem::remove_all(temporaryDirectory);
    std::cerr << "[FAIL] " << error.what() << '\n';
    std::cout << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=FAIL failures=1\n";
    return;
  }

  std::cout << "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS events="
            << expectedEvents << " seed=" << expectedSeed
            << " eligible_neutrinos=" << eligibleNeutrinos
            << " outside_acceptance_neutrinos=" << outsideNeutrinos
            << " transported_delta="
            << (onTransportedTotal - offTransportedTotal)
            << " energy_abs_delta_mev=" << eventEnergyAbsoluteDifference
            << " changed_hit_cells=" << hitComparison.changed << '\n';
}
