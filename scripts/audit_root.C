#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TLeafC.h>
#include <TObjArray.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {

class AuditResult {
 public:
  void Check(const bool condition, const std::string& message) {
    if (condition) {
      return;
    }
    ++failures_;
    std::cerr << "[FAIL] " << message << '\n';
  }

  int Failures() const { return failures_; }

 private:
  int failures_ = 0;
};

TTree* RequireTree(TFile& file, const char* name, AuditResult& audit) {
  auto* tree = file.Get<TTree>(name);
  audit.Check(tree != nullptr, std::string("TTree ausente: ") + name);
  return tree;
}

void CheckBranches(TTree& tree, const std::vector<std::string>& expected,
                   AuditResult& audit) {
  audit.Check(tree.GetListOfBranches()->GetEntries() ==
                  static_cast<int>(expected.size()),
              std::string(tree.GetName()) + " possui número inesperado de branches");
  for (const auto& name : expected) {
    audit.Check(tree.GetBranch(name.c_str()) != nullptr,
                std::string(tree.GetName()) + ": branch ausente: " + name);
  }
}

bool NearlyEqual(const double left, const double right) {
  const double scale = std::max({1.0, std::abs(left), std::abs(right)});
  return std::abs(left - right) <= 1.0e-10 * scale;
}

TLeaf* FindOnlyLeaf(TBranch& branch) {
  if (auto* leaf = branch.GetLeaf(branch.GetName())) {
    return leaf;
  }
  TObjArray* leaves = branch.GetListOfLeaves();
  if (leaves && leaves->GetEntries() == 1) {
    return static_cast<TLeaf*>(leaves->At(0));
  }
  return nullptr;
}

std::string ReadTextBranch(TTree& tree, const char* name,
                           AuditResult& audit) {
  TBranch* branch = tree.GetBranch(name);
  audit.Check(branch != nullptr,
              std::string(tree.GetName()) + ": branch textual ausente: " +
                  name);
  if (!branch) {
    return {};
  }

  TLeaf* leaf = FindOnlyLeaf(*branch);
  auto* textLeaf = dynamic_cast<TLeafC*>(leaf);
  audit.Check(textLeaf != nullptr,
              std::string(tree.GetName()) + '.' + name +
                  " não está armazenada como TLeafC");
  if (!textLeaf) {
    return {};
  }

  const auto* value =
      static_cast<const char*>(textLeaf->GetValuePointer());
  audit.Check(value != nullptr,
              std::string(tree.GetName()) + '.' + name +
                  " não possui valor textual legível");
  return value ? std::string(value) : std::string();
}

}  // namespace

void audit_root(const char* filename = "outputs/minbias_smoke.root",
                const char* expectedCommit = "") {
  AuditResult audit;
  TFile file(filename, "READ");
  if (file.IsZombie()) {
    audit.Check(false, std::string("não foi possível abrir: ") + filename);
    std::cout << "AUDIT_RESULT=FAIL failures=" << audit.Failures() << '\n';
    return;
  }

  TTree* events = RequireTree(file, "events", audit);
  TTree* hits = RequireTree(file, "hits", audit);
  TTree* generator = RequireTree(file, "generator", audit);
  TTree* metadata = RequireTree(file, "metadata", audit);
  if (!events || !hits || !generator || !metadata) {
    std::cout << "AUDIT_RESULT=FAIL failures=" << audit.Failures() << '\n';
    return;
  }

  CheckBranches(*events,
                {"run", "event", "bcid", "mu_configured",
                 "n_interactions_requested", "n_interactions_generated",
                 "generation_failures", "generator_particles",
                 "transported_particles", "unknown_pdg_particles",
                 "total_edep_mev", "rejected_not_final",
                 "rejected_neutrino_disabled",
                 "rejected_invisible_non_neutrino",
                 "rejected_outside_eta_acceptance", "unlineaged_steps",
                 "segmentation_failures"},
                audit);
  CheckBranches(*hits,
                {"run", "event", "bcid", "subevent", "cell_id",
                 "subdetector", "sampling", "side", "eta_index",
                 "phi_index", "eta_center", "phi_center", "edep_mev",
                 "time_mean_ns", "time_first_ns", "leading_pdg",
                 "leading_track_id", "leading_parent_id", "steps"},
                audit);
  CheckBranches(*generator,
                {"run", "event", "bcid", "subevent", "index", "pdg",
                 "status", "mother1", "mother2", "daughter1", "daughter2",
                 "is_final", "is_visible", "px_gev", "py_gev", "pz_gev",
                 "energy_gev", "mass_gev", "eta", "phi", "x_prod_mm",
                 "y_prod_mm", "z_prod_mm", "t_prod_mm_over_c",
                 "accepted_for_transport", "rejection_code"},
                audit);
  CheckBranches(*metadata,
                {"schema_version", "project_version", "git_commit",
                 "git_describe", "root_version", "geant4_version",
                 "pythia_version", "run", "events", "first_bcid", "threads",
                 "seed_base", "geant4_master_seed", "pythia_seed_base",
                 "pythia_worker_seed_stride", "pythia_seed_max",
                 "interaction_mode", "mean_interactions",
                 "fixed_interactions", "pythia_config", "physics_list",
                 "production_cut_mm", "beam_sigma_x_mm", "beam_sigma_y_mm",
                 "beam_sigma_z_mm", "beam_sigma_t_ns", "max_abs_eta",
                 "transport_neutrinos", "generator_audit", "check_overlaps",
                 "print_every", "config_file", "output_file",
                 "normalized_config"},
                audit);

  audit.Check(metadata->GetEntries() == 1,
              "metadata deve conter exatamente uma entrada");

  int schemaVersion = -1;
  int configuredEvents = -1;
  int firstBcid = -1;
  int generatorAudit = -1;
  if (metadata->GetEntries() == 1) {
    metadata->SetBranchAddress("schema_version", &schemaVersion);
    metadata->SetBranchAddress("events", &configuredEvents);
    metadata->SetBranchAddress("first_bcid", &firstBcid);
    metadata->SetBranchAddress("generator_audit", &generatorAudit);
    metadata->GetEntry(0);
    const std::string projectVersion =
        ReadTextBranch(*metadata, "project_version", audit);
    const std::string gitCommit =
        ReadTextBranch(*metadata, "git_commit", audit);
    const std::string gitDescribe =
        ReadTextBranch(*metadata, "git_describe", audit);
    const std::string rootVersion =
        ReadTextBranch(*metadata, "root_version", audit);
    const std::string geant4Version =
        ReadTextBranch(*metadata, "geant4_version", audit);
    const std::string pythiaVersion =
        ReadTextBranch(*metadata, "pythia_version", audit);
    audit.Check(schemaVersion == 1, "schema_version deve ser 1");
    audit.Check(configuredEvents > 0, "metadata.events deve ser positivo");
    audit.Check(firstBcid >= 0, "metadata.first_bcid não pode ser negativo");
    audit.Check(generatorAudit == 0 || generatorAudit == 1,
                "metadata.generator_audit deve ser booleano");
    audit.Check(projectVersion == "0.1.0",
                "metadata.project_version deve ser 0.1.0");
    audit.Check(gitCommit.size() == 40 && gitCommit != "unknown",
                "metadata.git_commit não contém um SHA completo");
    if (expectedCommit[0] != '\0') {
      audit.Check(gitCommit == expectedCommit,
                  "metadata.git_commit diverge do commit auditado");
    }
    audit.Check(gitDescribe.find("dirty") == std::string::npos &&
                    gitDescribe != "unknown" && !gitDescribe.empty(),
                "metadata.git_describe é desconhecido ou indica árvore suja");
    audit.Check(rootVersion != "unavailable" && !rootVersion.empty(),
                "metadata.root_version não foi resolvida");
    audit.Check(!geant4Version.empty(),
                "metadata.geant4_version está vazia");
    audit.Check(!pythiaVersion.empty(),
                "metadata.pythia_version está vazia");
    metadata->ResetBranchAddresses();
  }

  audit.Check(events->GetEntries() == configuredEvents,
              "events não contém uma entrada por bunch crossing configurado");

  int event = -1;
  int bcid = -1;
  int requested = -1;
  int generated = -1;
  int generationFailures = -1;
  int generatorParticles = -1;
  int transported = -1;
  int unknownPdg = -1;
  int rejectedNotFinal = -1;
  int rejectedNeutrino = -1;
  int rejectedInvisible = -1;
  int rejectedEta = -1;
  int unlineagedSteps = -1;
  int segmentationFailures = -1;
  double muConfigured = -1.0;
  double totalEnergy = -1.0;

  events->SetBranchAddress("event", &event);
  events->SetBranchAddress("bcid", &bcid);
  events->SetBranchAddress("mu_configured", &muConfigured);
  events->SetBranchAddress("n_interactions_requested", &requested);
  events->SetBranchAddress("n_interactions_generated", &generated);
  events->SetBranchAddress("generation_failures", &generationFailures);
  events->SetBranchAddress("generator_particles", &generatorParticles);
  events->SetBranchAddress("transported_particles", &transported);
  events->SetBranchAddress("unknown_pdg_particles", &unknownPdg);
  events->SetBranchAddress("total_edep_mev", &totalEnergy);
  events->SetBranchAddress("rejected_not_final", &rejectedNotFinal);
  events->SetBranchAddress("rejected_neutrino_disabled", &rejectedNeutrino);
  events->SetBranchAddress("rejected_invisible_non_neutrino",
                           &rejectedInvisible);
  events->SetBranchAddress("rejected_outside_eta_acceptance", &rejectedEta);
  events->SetBranchAddress("unlineaged_steps", &unlineagedSteps);
  events->SetBranchAddress("segmentation_failures", &segmentationFailures);

  std::set<int> eventIds;
  std::map<int, int> eventBcids;
  std::map<int, int> requestedByEvent;
  std::map<int, double> eventEnergy;
  long long expectedGeneratorEntries = 0;
  for (Long64_t entry = 0; entry < events->GetEntries(); ++entry) {
    events->GetEntry(entry);
    audit.Check(eventIds.insert(event).second,
                "event contém identificador duplicado: " +
                    std::to_string(event));
    eventBcids[event] = bcid;
    requestedByEvent[event] = requested;
    eventEnergy[event] = totalEnergy;
    expectedGeneratorEntries += generatorParticles;

    audit.Check(event >= 0 && bcid == firstBcid + event,
                "relação bcid = first_bcid + event foi violada");
    audit.Check(std::isfinite(muConfigured) && muConfigured >= 0.0,
                "mu_configured inválido no evento " + std::to_string(event));
    audit.Check(requested >= 0 && generated >= 0 && generationFailures >= 0 &&
                    requested == generated + generationFailures,
                "contabilidade de interações inválida no evento " +
                    std::to_string(event));
    audit.Check(generatorParticles >= 0 && transported >= 0 &&
                    unknownPdg >= 0 && rejectedNotFinal >= 0 &&
                    rejectedNeutrino >= 0 && rejectedInvisible >= 0 &&
                    rejectedEta >= 0 &&
                    generatorParticles == transported + unknownPdg +
                                              rejectedNotFinal +
                                              rejectedNeutrino +
                                              rejectedInvisible + rejectedEta,
                "contabilidade de partículas inválida no evento " +
                    std::to_string(event));
    audit.Check(std::isfinite(totalEnergy) && totalEnergy >= 0.0,
                "energia total inválida no evento " + std::to_string(event));
    audit.Check(unlineagedSteps == 0,
                "passos sem linhagem no evento " + std::to_string(event));
    audit.Check(segmentationFailures == 0,
                "falhas de segmentação no evento " + std::to_string(event));
  }
  events->ResetBranchAddresses();

  int hitEvent = -1;
  int hitBcid = -1;
  int subevent = -1;
  int subdetector = -1;
  int sampling = -1;
  int side = 0;
  int etaIndex = -1;
  int phiIndex = -1;
  int steps = -1;
  double cellId = -1.0;
  double etaCenter = 0.0;
  double phiCenter = 0.0;
  double energy = 0.0;
  double meanTime = 0.0;
  double firstTime = 0.0;

  hits->SetBranchAddress("event", &hitEvent);
  hits->SetBranchAddress("bcid", &hitBcid);
  hits->SetBranchAddress("subevent", &subevent);
  hits->SetBranchAddress("cell_id", &cellId);
  hits->SetBranchAddress("subdetector", &subdetector);
  hits->SetBranchAddress("sampling", &sampling);
  hits->SetBranchAddress("side", &side);
  hits->SetBranchAddress("eta_index", &etaIndex);
  hits->SetBranchAddress("phi_index", &phiIndex);
  hits->SetBranchAddress("eta_center", &etaCenter);
  hits->SetBranchAddress("phi_center", &phiCenter);
  hits->SetBranchAddress("edep_mev", &energy);
  hits->SetBranchAddress("time_mean_ns", &meanTime);
  hits->SetBranchAddress("time_first_ns", &firstTime);
  hits->SetBranchAddress("steps", &steps);

  std::map<int, double> hitEnergy;
  for (Long64_t entry = 0; entry < hits->GetEntries(); ++entry) {
    hits->GetEntry(entry);
    const auto eventIterator = requestedByEvent.find(hitEvent);
    audit.Check(eventIterator != requestedByEvent.end(),
                "hit referencia evento inexistente");
    if (eventIterator != requestedByEvent.end()) {
      audit.Check(hitBcid == eventBcids.at(hitEvent),
                  "hit possui BCID divergente do evento");
      audit.Check(subevent >= 0 && subevent < eventIterator->second,
                  "hit possui subevento fora do intervalo solicitado");
    }
    audit.Check(std::isfinite(cellId) && cellId >= 0.0 &&
                    cellId <= 8388607.0 && std::floor(cellId) == cellId,
                "cell_id inválido");
    audit.Check(sampling >= 0 && sampling <= 9,
                "sampling inválido em hits");
    audit.Check((sampling <= 3 && subdetector == 0) ||
                    (sampling >= 4 && subdetector == 1),
                "subdetector incompatível com sampling");
    audit.Check(side == -1 || side == 1, "side inválido em hits");
    audit.Check(etaIndex >= 0 && phiIndex >= 0 && phiIndex <= 255,
                "índice de célula inválido em hits");
    audit.Check(std::isfinite(etaCenter) && std::isfinite(phiCenter),
                "centro de célula não finito");
    audit.Check(std::isfinite(energy) && energy > 0.0 &&
                    std::isfinite(meanTime) && std::isfinite(firstTime) &&
                    steps > 0,
                "depósito inválido em hits");
    hitEnergy[hitEvent] += energy;
  }
  hits->ResetBranchAddresses();

  for (const auto& [eventId, expectedEnergy] : eventEnergy) {
    audit.Check(NearlyEqual(hitEnergy[eventId], expectedEnergy),
                "soma de hits diverge de total_edep_mev no evento " +
                    std::to_string(eventId));
  }

  audit.Check(generatorAudit == 1
                  ? generator->GetEntries() == expectedGeneratorEntries
                  : generator->GetEntries() == 0,
              "número de entradas em generator incompatível com a configuração");

  int generatorEvent = -1;
  int generatorBcid = -1;
  int generatorSubevent = -1;
  int accepted = -1;
  int rejectionCode = -1;
  generator->SetBranchAddress("event", &generatorEvent);
  generator->SetBranchAddress("bcid", &generatorBcid);
  generator->SetBranchAddress("subevent", &generatorSubevent);
  generator->SetBranchAddress("accepted_for_transport", &accepted);
  generator->SetBranchAddress("rejection_code", &rejectionCode);
  for (Long64_t entry = 0; entry < generator->GetEntries(); ++entry) {
    generator->GetEntry(entry);
    const auto eventIterator = requestedByEvent.find(generatorEvent);
    audit.Check(eventIterator != requestedByEvent.end(),
                "generator referencia evento inexistente");
    if (eventIterator != requestedByEvent.end()) {
      audit.Check(generatorBcid == eventBcids.at(generatorEvent),
                  "generator possui BCID divergente do evento");
      audit.Check(generatorSubevent >= 0 &&
                      generatorSubevent < eventIterator->second,
                  "generator possui subevento fora do intervalo solicitado");
    }
    audit.Check(rejectionCode >= 0 && rejectionCode <= 5,
                "rejection_code fora do domínio");
    audit.Check((accepted == 1 && rejectionCode == 0) ||
                    (accepted == 0 && rejectionCode != 0),
                "accepted_for_transport diverge de rejection_code");
  }
  generator->ResetBranchAddresses();

  if (audit.Failures() == 0) {
    std::cout << "AUDIT_RESULT=PASS events=" << events->GetEntries()
              << " hits=" << hits->GetEntries()
              << " generator=" << generator->GetEntries() << '\n';
  } else {
    std::cout << "AUDIT_RESULT=FAIL failures=" << audit.Failures() << '\n';
  }
}
