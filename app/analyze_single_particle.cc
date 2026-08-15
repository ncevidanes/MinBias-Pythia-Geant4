/*
 * MinBias-Pythia-Geant4
 * Copyright (C) 2026 Nelson Cevidanes Nascimento de Assis
 * SPDX-License-Identifier: GPL-3.0-only
 */

#include "SingleParticleAnalysis.hh"

#include <TFile.h>
#include <TLeaf.h>
#include <TLeafC.h>
#include <TTree.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

namespace {

constexpr int kExpectedSchemaVersion = 2;

struct Options {
  std::filesystem::path input;
  std::filesystem::path summaryCsv;
  std::filesystem::path samplingCsv;
};

struct Metadata {
  int schemaVersion = 0;
  std::string gitCommit;
  std::string generatorMode;
  int particlePdg = 0;
  double kineticEnergyGeV = 0.0;
  double eta = 0.0;
  double phi = 0.0;
  double productionCutMm = 0.0;
};

std::string Usage() {
  return
      "Usage: single_particle_analyzer --input <file.root> "
      "--summary-csv <summary.csv> --sampling-csv <samplings.csv>";
}

Options ParseOptions(const int argc, char* argv[]) {
  Options options;

  for (int index = 1; index < argc; ++index) {
    const std::string argument = argv[index];
    if (argument != "--input" &&
        argument != "--summary-csv" &&
        argument != "--sampling-csv") {
      throw std::invalid_argument(
          "Unknown argument: " + argument + "\n" + Usage());
    }

    if (index + 1 >= argc) {
      throw std::invalid_argument(
          "Missing value for " + argument + "\n" + Usage());
    }

    const std::filesystem::path value = argv[++index];
    if (value.empty()) {
      throw std::invalid_argument(
          "Empty value for " + argument + "\n" + Usage());
    }

    if (argument == "--input") {
      if (!options.input.empty()) {
        throw std::invalid_argument("Duplicate --input option");
      }
      options.input = value;
    } else if (argument == "--summary-csv") {
      if (!options.summaryCsv.empty()) {
        throw std::invalid_argument(
            "Duplicate --summary-csv option");
      }
      options.summaryCsv = value;
    } else {
      if (!options.samplingCsv.empty()) {
        throw std::invalid_argument(
            "Duplicate --sampling-csv option");
      }
      options.samplingCsv = value;
    }
  }

  if (options.input.empty() || options.summaryCsv.empty() ||
      options.samplingCsv.empty()) {
    throw std::invalid_argument(
        "All three path options are required\n" + Usage());
  }

  return options;
}

std::filesystem::path NormalizePath(
    const std::filesystem::path& path) {
  std::error_code error;
  auto normalized = std::filesystem::weakly_canonical(path, error);
  if (!error) {
    return normalized;
  }

  error.clear();
  normalized = std::filesystem::absolute(path, error);
  if (error) {
    throw std::runtime_error(
        "Unable to normalize path: " + path.string());
  }
  return normalized.lexically_normal();
}

bool SameFileOrPath(const std::filesystem::path& first,
                    const std::filesystem::path& second) {
  if (NormalizePath(first) == NormalizePath(second)) {
    return true;
  }

  std::error_code error;
  const bool equivalent =
      std::filesystem::equivalent(first, second, error);
  return !error && equivalent;
}

void ValidateDistinctPaths(const Options& options) {
  if (SameFileOrPath(options.input, options.summaryCsv) ||
      SameFileOrPath(options.input, options.samplingCsv)) {
    throw std::invalid_argument(
        "An output CSV must not replace the ROOT input");
  }
  if (SameFileOrPath(options.summaryCsv, options.samplingCsv)) {
    throw std::invalid_argument(
        "Summary and sampling CSV paths must differ");
  }
}

TTree& RequireTree(TFile& file, const char* name) {
  auto* tree = dynamic_cast<TTree*>(file.Get(name));
  if (tree == nullptr) {
    throw std::runtime_error(
        std::string("Required TTree is missing: ") + name);
  }
  return *tree;
}

TLeaf& RequireLeaf(TTree& tree, const char* name,
                   const char* expectedType) {
  auto* leaf = tree.GetLeaf(name);
  if (leaf == nullptr) {
    throw std::runtime_error(
        std::string("Required branch is missing: ") +
        tree.GetName() + "." + name);
  }

  const std::string actualType = leaf->GetTypeName();
  if (actualType != expectedType) {
    throw std::runtime_error(
        std::string("Unexpected type for ") + tree.GetName() +
        "." + name + ": expected " + expectedType +
        ", found " + actualType);
  }
  return *leaf;
}

std::string ReadStringLeaf(TLeaf& leaf,
                           const std::string& description) {
  auto* stringLeaf = dynamic_cast<TLeafC*>(&leaf);
  if (stringLeaf == nullptr) {
    throw std::runtime_error(
        description + " is not a ROOT character leaf");
  }

  const char* value = stringLeaf->GetValueString();
  if (value == nullptr) {
    throw std::runtime_error(description + " is null");
  }
  return value;
}

Metadata ReadMetadata(TTree& tree) {
  if (tree.GetEntries() != 1) {
    throw std::runtime_error(
        "metadata must contain exactly one entry");
  }

  auto& schemaLeaf = RequireLeaf(
      tree, "schema_version", "Int_t");
  auto& gitLeaf = RequireLeaf(tree, "git_commit", "Char_t");
  auto& modeLeaf = RequireLeaf(
      tree, "generator_mode", "Char_t");
  auto& pdgLeaf = RequireLeaf(
      tree, "single_particle_pdg", "Int_t");
  auto& energyLeaf = RequireLeaf(
      tree, "single_particle_kinetic_energy_gev", "Double_t");
  auto& etaLeaf = RequireLeaf(
      tree, "single_particle_eta", "Double_t");
  auto& phiLeaf = RequireLeaf(
      tree, "single_particle_phi", "Double_t");
  auto& productionCutLeaf = RequireLeaf(
      tree, "production_cut_mm", "Double_t");

  if (tree.GetEntry(0) < 0) {
    throw std::runtime_error("Unable to read metadata entry");
  }

  Metadata metadata;
  metadata.schemaVersion =
      static_cast<int>(schemaLeaf.GetValue());
  metadata.gitCommit =
      ReadStringLeaf(gitLeaf, "metadata.git_commit");
  metadata.generatorMode =
      ReadStringLeaf(modeLeaf, "metadata.generator_mode");
  metadata.particlePdg = static_cast<int>(pdgLeaf.GetValue());
  metadata.kineticEnergyGeV = energyLeaf.GetValue();
  metadata.eta = etaLeaf.GetValue();
  metadata.phi = phiLeaf.GetValue();
  metadata.productionCutMm = productionCutLeaf.GetValue();

  if (metadata.schemaVersion != kExpectedSchemaVersion) {
    throw std::runtime_error(
        "Unsupported schema_version: " +
        std::to_string(metadata.schemaVersion));
  }
  if (metadata.generatorMode != "single_particle") {
    throw std::runtime_error(
        "Unsupported generator_mode: " + metadata.generatorMode);
  }
  if (metadata.gitCommit.empty()) {
    throw std::runtime_error("metadata.git_commit is empty");
  }
  if (!std::isfinite(metadata.kineticEnergyGeV) ||
      metadata.kineticEnergyGeV <= 0.0 ||
      !std::isfinite(metadata.eta) ||
      !std::isfinite(metadata.phi) ||
      !std::isfinite(metadata.productionCutMm) ||
      metadata.productionCutMm <= 0.0) {
    throw std::runtime_error(
        "Incident particle metadata contains invalid values");
  }

  return metadata;
}

std::vector<pg::SingleParticleEventRecord> ReadEvents(
    TTree& tree) {
  auto& eventLeaf = RequireLeaf(tree, "event", "Int_t");
  auto& energyLeaf = RequireLeaf(
      tree, "total_edep_mev", "Double_t");

  const Long64_t entryCount = tree.GetEntries();
  std::vector<pg::SingleParticleEventRecord> events;
  events.reserve(static_cast<std::size_t>(entryCount));

  for (Long64_t entry = 0; entry < entryCount; ++entry) {
    if (tree.GetEntry(entry) < 0) {
      throw std::runtime_error(
          "Unable to read events entry " + std::to_string(entry));
    }
    events.push_back({
        static_cast<int>(eventLeaf.GetValue()),
        energyLeaf.GetValue(),
    });
  }
  return events;
}

std::vector<pg::SingleParticleHitRecord> ReadHits(TTree& tree) {
  auto& eventLeaf = RequireLeaf(tree, "event", "Int_t");
  auto& samplingLeaf = RequireLeaf(tree, "sampling", "Int_t");
  auto& etaLeaf = RequireLeaf(tree, "eta_center", "Double_t");
  auto& phiLeaf = RequireLeaf(tree, "phi_center", "Double_t");
  auto& energyLeaf = RequireLeaf(tree, "edep_mev", "Double_t");

  const Long64_t entryCount = tree.GetEntries();
  std::vector<pg::SingleParticleHitRecord> hits;
  hits.reserve(static_cast<std::size_t>(entryCount));

  for (Long64_t entry = 0; entry < entryCount; ++entry) {
    if (tree.GetEntry(entry) < 0) {
      throw std::runtime_error(
          "Unable to read hits entry " + std::to_string(entry));
    }
    hits.push_back({
        static_cast<int>(eventLeaf.GetValue()),
        static_cast<int>(samplingLeaf.GetValue()),
        etaLeaf.GetValue(),
        phiLeaf.GetValue(),
        energyLeaf.GetValue(),
    });
  }
  return hits;
}

std::string EscapeCsv(const std::string& value) {
  if (value.find_first_of(",\"\r\n") == std::string::npos) {
    return value;
  }

  std::string escaped;
  escaped.reserve(value.size() + 2);
  escaped.push_back('"');
  for (const char character : value) {
    if (character == '"') {
      escaped.push_back('"');
    }
    escaped.push_back(character);
  }
  escaped.push_back('"');
  return escaped;
}

std::ofstream OpenCsv(const std::filesystem::path& path) {
  std::ofstream output(path, std::ios::out | std::ios::trunc);
  if (!output) {
    throw std::runtime_error(
        "Unable to open output CSV: " + path.string());
  }
  output.imbue(std::locale::classic());
  output << std::setprecision(
      std::numeric_limits<double>::max_digits10);
  return output;
}

void FinishCsv(std::ofstream& output,
               const std::filesystem::path& path) {
  output.close();
  if (!output) {
    throw std::runtime_error(
        "Unable to finish output CSV: " + path.string());
  }
}

void WriteSummaryCsv(
    const std::filesystem::path& path,
    const Metadata& metadata,
    const pg::SingleParticleAnalysisSummary& summary) {
  auto output = OpenCsv(path);
  output
      << "schema_version,git_commit,generator_mode,"
      << "single_particle_pdg,"
      << "single_particle_kinetic_energy_gev,"
      << "single_particle_eta,single_particle_phi,"
      << "production_cut_mm,"
      << "event_count,hit_count,mean_energy_mev,"
      << "sample_stddev_energy_mev,mean_response,"
      << "relative_resolution,sampling_centroid,"
      << "sampling_width,eta_width,phi_width\n";

  output
      << metadata.schemaVersion << ','
      << EscapeCsv(metadata.gitCommit) << ','
      << EscapeCsv(metadata.generatorMode) << ','
      << metadata.particlePdg << ','
      << metadata.kineticEnergyGeV << ','
      << metadata.eta << ','
      << metadata.phi << ','
      << metadata.productionCutMm << ','
      << summary.eventCount << ','
      << summary.hitCount << ','
      << summary.meanEnergyMeV << ','
      << summary.sampleStddevEnergyMeV << ','
      << summary.meanResponse << ','
      << summary.relativeResolution << ','
      << summary.samplingCentroid << ','
      << summary.samplingWidth << ','
      << summary.etaWidth << ','
      << summary.phiWidth << '\n';

  FinishCsv(output, path);
}

void WriteSamplingCsv(
    const std::filesystem::path& path,
    const pg::SingleParticleAnalysisSummary& summary) {
  auto output = OpenCsv(path);
  output
      << "sampling,name,mean_energy_mev,"
      << "sample_stddev_energy_mev,total_energy_fraction,"
      << "eta_width,phi_width\n";

  for (const auto& sampling : summary.samplings) {
    output
        << sampling.sampling << ','
        << EscapeCsv(sampling.name) << ','
        << sampling.meanEnergyMeV << ','
        << sampling.sampleStddevEnergyMeV << ','
        << sampling.totalEnergyFraction << ','
        << sampling.etaWidth << ','
        << sampling.phiWidth << '\n';
  }

  FinishCsv(output, path);
}

}  // namespace

int main(const int argc, char* argv[]) {
  try {
    const Options options = ParseOptions(argc, argv);
    ValidateDistinctPaths(options);

    TFile input(options.input.string().c_str(), "READ");
    if (input.IsZombie()) {
      throw std::runtime_error(
          "Unable to open ROOT input: " + options.input.string());
    }

    auto& metadataTree = RequireTree(input, "metadata");
    auto& eventsTree = RequireTree(input, "events");
    auto& hitsTree = RequireTree(input, "hits");

    const Metadata metadata = ReadMetadata(metadataTree);
    const auto events = ReadEvents(eventsTree);
    const auto hits = ReadHits(hitsTree);
    const auto summary = pg::AnalyzeSingleParticleRecords(
        metadata.kineticEnergyGeV, events, hits);

    input.Close();

    WriteSummaryCsv(options.summaryCsv, metadata, summary);
    WriteSamplingCsv(options.samplingCsv, summary);

    std::cout << "ANALYSIS_RESULT=PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "ERROR: " << error.what() << '\n';
    std::cerr << "ANALYSIS_RESULT=FAIL\n";
    return 1;
  }
}
