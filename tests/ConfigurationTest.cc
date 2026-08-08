#include "Configuration.hh"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

class TemporaryDirectory {
 public:
  TemporaryDirectory() {
    const auto stamp = std::chrono::high_resolution_clock::now()
                           .time_since_epoch()
                           .count();
    path_ = std::filesystem::temp_directory_path() /
            ("minbias-configuration-test-" + std::to_string(stamp));
    if (!std::filesystem::create_directory(path_)) {
      throw std::runtime_error("Could not create temporary directory");
    }
  }

  ~TemporaryDirectory() { std::filesystem::remove_all(path_); }

  const std::filesystem::path& Path() const { return path_; }

 private:
  std::filesystem::path path_;
};

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void Write(const std::filesystem::path& path, const std::string& text) {
  std::ofstream output(path);
  if (!output) {
    throw std::runtime_error("Could not write " + path.string());
  }
  output << text;
}

std::string ValidConfiguration() {
  return R"(events = 3
first_bcid = 7
threads = 1
seed_base = 512
interaction_mode = poisson
mean_interactions = 1.5
fixed_interactions = 1
pythia_config = pythia.cmnd
physics_list = FTFP_BERT_ATL
production_cut_mm = 1.0
beam_sigma_x_mm = 0.0
beam_sigma_y_mm = 0.0
beam_sigma_z_mm = 0.0
beam_sigma_t_ns = 0.0
max_abs_eta = 1.8
transport_neutrinos = false
generator_audit = true
check_overlaps = true
print_every = 1
output = output.root
)";
}

void ExpectRejected(const std::filesystem::path& configPath,
                    const std::string& text,
                    const std::string& expectedMessage) {
  Write(configPath, text);
  try {
    (void)pg::Configuration::Load(configPath);
  } catch (const std::exception& error) {
    Require(std::string(error.what()).find(expectedMessage) !=
                std::string::npos,
            "Unexpected error for rejected configuration: " +
                std::string(error.what()));
    return;
  }
  throw std::runtime_error("Invalid configuration was accepted");
}

std::string Replace(std::string text, const std::string& from,
                    const std::string& to) {
  const auto position = text.find(from);
  Require(position != std::string::npos, "Test fixture token was not found");
  text.replace(position, from.size(), to);
  return text;
}

}  // namespace

int main() {
  try {
    const TemporaryDirectory temporary;
    const auto configPath = temporary.Path() / "test.conf";
    Write(temporary.Path() / "pythia.cmnd", "SoftQCD:inelastic = on\n");

    Write(configPath, ValidConfiguration());
    const pg::Configuration configuration =
        pg::Configuration::Load(configPath);
    Require(configuration.events == 3, "events changed while parsing");
    Require(configuration.firstBcid == 7, "first_bcid changed while parsing");
    Require(configuration.generatorAudit,
            "generator_audit changed while parsing");
    Require(configuration.pythiaConfig ==
                std::filesystem::weakly_canonical(
                    temporary.Path() / "pythia.cmnd"),
            "relative PYTHIA path was not resolved from the config directory");

    ExpectRejected(configPath,
                   ValidConfiguration() + "generator_audi = true\n",
                   "Chave desconhecida: generator_audi");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "events = 3",
                           "events = 3abc"),
                   "Valor inteiro inválido para events");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "mean_interactions = 1.5",
                           "mean_interactions = nan"),
                   "Valor numérico inválido para mean_interactions");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "beam_sigma_z_mm = 0.0",
                           "beam_sigma_z_mm = -1.0"),
                   "sigmas do feixe");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "first_bcid = 7",
                           "first_bcid = 2147483647"),
                   "intervalo de BCIDs");

    std::cout << "Configuration tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Configuration test failed: " << error.what() << std::endl;
    return 1;
  }
}
