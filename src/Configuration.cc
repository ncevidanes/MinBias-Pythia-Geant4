#include "Configuration.hh"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

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

  result.events = std::stoi(get("events"));
  result.firstBcid = std::stoi(optional("first_bcid", "0"));
  result.threads = std::stoi(get("threads"));
  result.seedBase = std::stoi(get("seed_base"));
  result.interactionMode = get("interaction_mode");
  result.meanInteractions = std::stod(get("mean_interactions"));
  result.fixedInteractions =
      std::stoi(optional("fixed_interactions", "1"));
  result.physicsList = get("physics_list");
  result.productionCutMm =
      std::stod(optional("production_cut_mm", "1.0"));
  result.beamSigmaXmm = std::stod(optional("beam_sigma_x_mm", "0.0"));
  result.beamSigmaYmm = std::stod(optional("beam_sigma_y_mm", "0.0"));
  result.beamSigmaZmm = std::stod(optional("beam_sigma_z_mm", "0.0"));
  result.beamSigmaTns = std::stod(optional("beam_sigma_t_ns", "0.0"));
  result.maxAbsEta = std::stod(optional("max_abs_eta", "1.8"));
  result.transportNeutrinos =
      ParseBool(optional("transport_neutrinos", "false"),
                "transport_neutrinos");
  result.generatorAudit =
      ParseBool(optional("generator_audit", "false"), "generator_audit");
  result.checkOverlaps =
      ParseBool(optional("check_overlaps", "false"), "check_overlaps");
  result.printEvery = std::stoi(optional("print_every", "10"));

  const auto base = result.sourceFile.parent_path();
  result.pythiaConfig = Resolve(base, get("pythia_config"));
  result.outputFile = Resolve(base, get("output"));

  result.Validate();
  return result;
}

void Configuration::Validate() const {
  if (events <= 0) {
    throw std::runtime_error("events deve ser positivo");
  }
  if (threads <= 0) {
    throw std::runtime_error("threads deve ser positivo");
  }
  if (seedBase <= 0) {
    throw std::runtime_error("seed_base deve ser positivo");
  }
  if (interactionMode != "poisson" && interactionMode != "fixed") {
    throw std::runtime_error(
        "interaction_mode deve ser 'poisson' ou 'fixed'");
  }
  if (meanInteractions < 0.0) {
    throw std::runtime_error("mean_interactions não pode ser negativo");
  }
  if (fixedInteractions < 0) {
    throw std::runtime_error("fixed_interactions não pode ser negativo");
  }
  if (productionCutMm <= 0.0) {
    throw std::runtime_error("production_cut_mm deve ser positivo");
  }
  if (maxAbsEta <= 0.0 || maxAbsEta > 1.8) {
    throw std::runtime_error(
        "max_abs_eta deve estar em (0, 1.8] para esta geometria");
  }
  if (printEvery <= 0) {
    throw std::runtime_error("print_every deve ser positivo");
  }
  if (!std::filesystem::is_regular_file(pythiaConfig)) {
    throw std::runtime_error("Arquivo PYTHIA inexistente: " +
                             pythiaConfig.string());
  }
}

void Configuration::Print(std::ostream& output) const {
  output << std::boolalpha << std::setprecision(12)
         << "config = " << sourceFile << '\n'
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

