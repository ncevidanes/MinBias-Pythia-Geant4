#include "Configuration.hh"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace pg {
namespace {

std::string Trim(std::string value) {
  const auto first =
      std::find_if_not(value.begin(), value.end(), [](unsigned char c) {
        return std::isspace(c) != 0;
      });
  const auto last =
      std::find_if_not(value.rbegin(), value.rend(), [](unsigned char c) {
        return std::isspace(c) != 0;
      }).base();
  if (first >= last) {
    return {};
  }
  return std::string(first, last);
}

bool ParseBool(const std::string& value, const std::string& key) {
  std::string normalized = value;
  std::transform(normalized.begin(), normalized.end(), normalized.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  if (normalized == "true" || normalized == "yes" || normalized == "1") {
    return true;
  }
  if (normalized == "false" || normalized == "no" || normalized == "0") {
    return false;
  }
  throw std::runtime_error("Valor booleano inválido para " + key + ": " +
                           value);
}

int ParseInt(const std::string& value, const std::string& key) {
  try {
    std::size_t parsed = 0;
    const int result = std::stoi(value, &parsed);
    if (parsed != value.size()) {
      throw std::runtime_error("caracteres adicionais");
    }
    return result;
  } catch (const std::exception&) {
    throw std::runtime_error("Valor inteiro inválido para " + key + ": " +
                             value);
  }
}

double ParseDouble(const std::string& value, const std::string& key) {
  try {
    std::size_t parsed = 0;
    const double result = std::stod(value, &parsed);
    if (parsed != value.size() || !std::isfinite(result)) {
      throw std::runtime_error("valor não finito ou caracteres adicionais");
    }
    return result;
  } catch (const std::exception&) {
    throw std::runtime_error("Valor numérico inválido para " + key + ": " +
                             value);
  }
}

std::filesystem::path Resolve(const std::filesystem::path& base,
                              const std::string& value) {
  std::filesystem::path path(value);
  if (path.is_relative()) {
    path = base / path;
  }
  return std::filesystem::weakly_canonical(path);
}

}  // namespace

Configuration Configuration::Load(const std::filesystem::path& filename) {
  Configuration result;
  result.sourceFile = std::filesystem::absolute(filename);

  std::ifstream input(result.sourceFile);
  if (!input) {
    throw std::runtime_error("Não foi possível abrir a configuração: " +
                             result.sourceFile.string());
  }

  std::unordered_map<std::string, std::string> values;
  std::string rawLine;
  int lineNumber = 0;
  while (std::getline(input, rawLine)) {
    ++lineNumber;
    const auto comment = rawLine.find('#');
    const std::string line = Trim(rawLine.substr(0, comment));
    if (line.empty()) {
      continue;
    }
    const auto separator = line.find('=');
    if (separator == std::string::npos) {
      throw std::runtime_error(result.sourceFile.string() + ":" +
                               std::to_string(lineNumber) +
                               ": esperado 'chave = valor'");
    }
    const std::string key = Trim(line.substr(0, separator));
    const std::string value = Trim(line.substr(separator + 1));
    if (key.empty() || value.empty()) {
      throw std::runtime_error(result.sourceFile.string() + ":" +
                               std::to_string(lineNumber) +
                               ": chave ou valor vazio");
    }
    if (!values.emplace(key, value).second) {
      throw std::runtime_error(result.sourceFile.string() + ":" +
                               std::to_string(lineNumber) +
                               ": chave duplicada: " + key);
    }
  }

  static const std::unordered_set<std::string> allowedKeys{
      "generator_mode",
      "events",              "first_bcid",
      "threads",             "seed_base",
      "interaction_mode",    "mean_interactions",
      "fixed_interactions",  "pythia_config",
      "physics_list",        "production_cut_mm",
      "beam_sigma_x_mm",     "beam_sigma_y_mm",
      "beam_sigma_z_mm",     "beam_sigma_t_ns",
      "max_abs_eta",          "transport_neutrinos",
      "generator_audit",      "check_overlaps",
      "print_every",          "output",
      "single_particle_pdg",
      "single_particle_kinetic_energy_gev",
      "single_particle_eta",  "single_particle_phi",
  };
  for (const auto& [key, value] : values) {
    (void)value;
    if (allowedKeys.count(key) == 0) {
      throw std::runtime_error("Chave desconhecida: " + key);
    }
  }

  const auto get = [&values](const std::string& key) -> const std::string& {
    const auto iterator = values.find(key);
    if (iterator == values.end()) {
      throw std::runtime_error("Chave obrigatória ausente: " + key);
    }
    return iterator->second;
  };
  const auto optional = [&values](const std::string& key,
                                  const std::string& fallback) {
    const auto iterator = values.find(key);
    return iterator == values.end() ? fallback : iterator->second;
  };

  result.generatorMode = optional("generator_mode", "pythia");
  result.events = ParseInt(get("events"), "events");
  result.firstBcid = ParseInt(optional("first_bcid", "0"), "first_bcid");
  result.threads = ParseInt(get("threads"), "threads");
  result.seedBase = ParseInt(get("seed_base"), "seed_base");
  if (result.generatorMode == "pythia") {
    result.interactionMode = get("interaction_mode");
    result.meanInteractions =
        ParseDouble(get("mean_interactions"), "mean_interactions");
  } else {
    result.interactionMode = optional("interaction_mode", "poisson");
    result.meanInteractions =
        ParseDouble(optional("mean_interactions", "1.0"),
                    "mean_interactions");
  }
  result.fixedInteractions =
      ParseInt(optional("fixed_interactions", "1"), "fixed_interactions");
  result.physicsList = get("physics_list");
  result.productionCutMm =
      ParseDouble(optional("production_cut_mm", "1.0"),
                  "production_cut_mm");
  result.beamSigmaXmm =
      ParseDouble(optional("beam_sigma_x_mm", "0.0"), "beam_sigma_x_mm");
  result.beamSigmaYmm =
      ParseDouble(optional("beam_sigma_y_mm", "0.0"), "beam_sigma_y_mm");
  result.beamSigmaZmm =
      ParseDouble(optional("beam_sigma_z_mm", "0.0"), "beam_sigma_z_mm");
  result.beamSigmaTns =
      ParseDouble(optional("beam_sigma_t_ns", "0.0"), "beam_sigma_t_ns");
  result.maxAbsEta =
      ParseDouble(optional("max_abs_eta", "1.8"), "max_abs_eta");
  result.transportNeutrinos =
      ParseBool(optional("transport_neutrinos", "false"),
                "transport_neutrinos");
  result.generatorAudit =
      ParseBool(optional("generator_audit", "false"), "generator_audit");
  result.checkOverlaps =
      ParseBool(optional("check_overlaps", "false"), "check_overlaps");
  result.printEvery =
      ParseInt(optional("print_every", "10"), "print_every");
  if (result.generatorMode == "single_particle") {
    result.singleParticlePdg =
        ParseInt(get("single_particle_pdg"), "single_particle_pdg");
    result.singleParticleKineticEnergyGeV = ParseDouble(
        get("single_particle_kinetic_energy_gev"),
        "single_particle_kinetic_energy_gev");
    result.singleParticleEta =
        ParseDouble(get("single_particle_eta"), "single_particle_eta");
    result.singleParticlePhi =
        ParseDouble(get("single_particle_phi"), "single_particle_phi");
  } else {
    result.singleParticlePdg =
        ParseInt(optional("single_particle_pdg", "11"),
                 "single_particle_pdg");
    result.singleParticleKineticEnergyGeV = ParseDouble(
        optional("single_particle_kinetic_energy_gev", "10.0"),
        "single_particle_kinetic_energy_gev");
    result.singleParticleEta =
        ParseDouble(optional("single_particle_eta", "0.0"),
                    "single_particle_eta");
    result.singleParticlePhi =
        ParseDouble(optional("single_particle_phi", "0.0"),
                    "single_particle_phi");
  }

  const auto base = result.sourceFile.parent_path();
  if (result.generatorMode == "pythia") {
    result.pythiaConfig = Resolve(base, get("pythia_config"));
  } else if (values.count("pythia_config") != 0) {
    result.pythiaConfig = Resolve(base, values.at("pythia_config"));
  }
  result.outputFile = Resolve(base, get("output"));

  result.Validate();
  return result;
}

void Configuration::Validate() const {
  if (generatorMode != "pythia" && generatorMode != "single_particle") {
    throw std::runtime_error(
        "generator_mode deve ser 'pythia' ou 'single_particle'");
  }
  if (events <= 0) {
    throw std::runtime_error("events deve ser positivo");
  }
  if (threads <= 0) {
    throw std::runtime_error("threads deve ser positivo");
  }
  if (firstBcid < 0 ||
      events - 1 > std::numeric_limits<int>::max() - firstBcid) {
    throw std::runtime_error(
        "o intervalo de BCIDs deve caber em um inteiro não negativo");
  }
  if (seedBase <= 0) {
    throw std::runtime_error("seed_base deve ser positivo");
  }
  if (interactionMode != "poisson" && interactionMode != "fixed") {
    throw std::runtime_error(
        "interaction_mode deve ser 'poisson' ou 'fixed'");
  }
  if (!std::isfinite(meanInteractions) || meanInteractions < 0.0) {
    throw std::runtime_error(
        "mean_interactions deve ser finito e não negativo");
  }
  if (fixedInteractions < 0) {
    throw std::runtime_error("fixed_interactions não pode ser negativo");
  }
  if (!std::isfinite(productionCutMm) || productionCutMm <= 0.0) {
    throw std::runtime_error(
        "production_cut_mm deve ser finito e positivo");
  }
  if (!std::isfinite(beamSigmaXmm) || beamSigmaXmm < 0.0 ||
      !std::isfinite(beamSigmaYmm) || beamSigmaYmm < 0.0 ||
      !std::isfinite(beamSigmaZmm) || beamSigmaZmm < 0.0 ||
      !std::isfinite(beamSigmaTns) || beamSigmaTns < 0.0) {
    throw std::runtime_error(
        "os sigmas do feixe devem ser finitos e não negativos");
  }
  if (!std::isfinite(maxAbsEta) || maxAbsEta <= 0.0 || maxAbsEta > 1.8) {
    throw std::runtime_error(
        "max_abs_eta deve estar em (0, 1.8] para esta geometria");
  }
  if (printEvery <= 0) {
    throw std::runtime_error("print_every deve ser positivo");
  }
  if (generatorMode == "pythia" &&
      !std::filesystem::is_regular_file(pythiaConfig)) {
    throw std::runtime_error("Arquivo PYTHIA inexistente: " +
                             pythiaConfig.string());
  }
  if (singleParticlePdg == 0) {
    throw std::runtime_error("single_particle_pdg não pode ser zero");
  }
  if (!std::isfinite(singleParticleKineticEnergyGeV) ||
      singleParticleKineticEnergyGeV <= 0.0) {
    throw std::runtime_error(
        "single_particle_kinetic_energy_gev deve ser finita e positiva");
  }
  if (!std::isfinite(singleParticleEta) ||
      std::abs(singleParticleEta) > maxAbsEta) {
    throw std::runtime_error(
        "single_particle_eta deve ser finita e respeitar max_abs_eta");
  }
  constexpr double kPi = 3.14159265358979323846;
  if (!std::isfinite(singleParticlePhi) || singleParticlePhi < -kPi ||
      singleParticlePhi > kPi) {
    throw std::runtime_error(
        "single_particle_phi deve estar no intervalo [-pi, pi]");
  }
}

void Configuration::Print(std::ostream& output) const {
  output << std::boolalpha << std::setprecision(12)
         << "config = " << sourceFile << '\n'
         << "generator_mode = " << generatorMode << '\n'
         << "events = " << events << '\n'
         << "first_bcid = " << firstBcid << '\n'
         << "threads = " << threads << '\n'
         << "seed_base = " << seedBase << '\n'
         << "interaction_mode = " << interactionMode << '\n'
         << "mean_interactions = " << meanInteractions << '\n'
         << "fixed_interactions = " << fixedInteractions << '\n'
         << "pythia_config = " << pythiaConfig << '\n'
         << "physics_list = " << physicsList << '\n'
         << "production_cut_mm = " << productionCutMm << '\n'
         << "beam_sigma_x_mm = " << beamSigmaXmm << '\n'
         << "beam_sigma_y_mm = " << beamSigmaYmm << '\n'
         << "beam_sigma_z_mm = " << beamSigmaZmm << '\n'
         << "beam_sigma_t_ns = " << beamSigmaTns << '\n'
         << "max_abs_eta = " << maxAbsEta << '\n'
         << "transport_neutrinos = " << transportNeutrinos << '\n'
         << "generator_audit = " << generatorAudit << '\n'
         << "check_overlaps = " << checkOverlaps << '\n'
         << "print_every = " << printEvery << '\n'
         << "single_particle_pdg = " << singleParticlePdg << '\n'
         << "single_particle_kinetic_energy_gev = "
         << singleParticleKineticEnergyGeV << '\n'
         << "single_particle_eta = " << singleParticleEta << '\n'
         << "single_particle_phi = " << singleParticlePhi << '\n'
         << "output = " << outputFile << '\n';
}

std::string Configuration::NormalizedText() const {
  std::ostringstream output;
  Print(output);
  return output.str();
}

void Configuration::WriteManifest() const {
  const auto parent = outputFile.parent_path();
  if (!parent.empty()) {
    std::filesystem::create_directories(parent);
  }
  const std::filesystem::path manifest =
      outputFile.string() + ".manifest.txt";
  std::ofstream output(manifest);
  if (!output) {
    throw std::runtime_error("Não foi possível gravar o manifesto: " +
                             manifest.string());
  }
  output << NormalizedText();
}

}  // namespace pg
