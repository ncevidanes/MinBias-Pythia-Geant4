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

std::string ValidSingleParticleConfiguration() {
  return R"(generator_mode = single_particle
events = 2
first_bcid = 9
threads = 1
seed_base = 900
physics_list = FTFP_BERT_ATL
production_cut_mm = 1.0
max_abs_eta = 1.8
generator_audit = true
print_every = 1
single_particle_pdg = 11
single_particle_kinetic_energy_gev = 10.0
single_particle_eta = 0.25
single_particle_phi = -1.5
output = single.root
)";
}

void ExpectAccepted(const std::filesystem::path& configPath,
                    const std::string& text) {
  Write(configPath, text);
  try {
    (void)pg::Configuration::Load(configPath);
  } catch (const std::exception& error) {
    throw std::runtime_error(
        "Valid boundary configuration was rejected: " +
        std::string(error.what()));
  }
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
    Require(configuration.generatorMode == "pythia",
            "legacy configuration did not default to PYTHIA");
    Require(configuration.firstBcid == 7, "first_bcid changed while parsing");
    Require(configuration.generatorAudit,
            "generator_audit changed while parsing");
    Require(configuration.pythiaConfig ==
                std::filesystem::weakly_canonical(
                    temporary.Path() / "pythia.cmnd"),
            "relative PYTHIA path was not resolved from the config directory");

    Write(configPath, ValidSingleParticleConfiguration());
    const pg::Configuration singleParticle =
        pg::Configuration::Load(configPath);
    Require(singleParticle.generatorMode == "single_particle",
            "single-particle generator mode changed while parsing");
    Require(singleParticle.pythiaConfig.empty(),
            "single-particle mode unexpectedly requires a PYTHIA file");
    Require(singleParticle.singleParticlePdg == 11,
            "single-particle PDG changed while parsing");
    Require(singleParticle.singleParticleKineticEnergyGeV == 10.0,
            "single-particle kinetic energy changed while parsing");
    Require(singleParticle.singleParticleEta == 0.25,
            "single-particle eta changed while parsing");
    Require(singleParticle.singleParticlePhi == -1.5,
            "single-particle phi changed while parsing");

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
    ExpectRejected(configPath,
                   Replace(ValidSingleParticleConfiguration(),
                           "generator_mode = single_particle",
                           "generator_mode = gun"),
                   "generator_mode");
    ExpectRejected(configPath,
                   Replace(ValidSingleParticleConfiguration(),
                           "single_particle_pdg = 11",
                           "single_particle_pdg = 0"),
                   "single_particle_pdg");
    ExpectRejected(configPath,
                   Replace(ValidSingleParticleConfiguration(),
                           "single_particle_kinetic_energy_gev = 10.0",
                           "single_particle_kinetic_energy_gev = 0.0"),
                   "single_particle_kinetic_energy_gev");
    ExpectRejected(configPath,
                   Replace(ValidSingleParticleConfiguration(),
                           "single_particle_eta = 0.25",
                           "single_particle_eta = 2.0"),
                   "single_particle_eta");
    ExpectRejected(configPath,
                   Replace(ValidSingleParticleConfiguration(),
                           "single_particle_phi = -1.5",
                           "single_particle_phi = 4.0"),
                   "single_particle_phi");

    // Structural syntax failures.
    ExpectRejected(configPath,
                   ValidConfiguration() +
                       "this_line_has_no_key_value_separator\n",
                   "esperado 'chave = valor'");
    ExpectRejected(configPath, ValidConfiguration() + " = 1\n",
                   "chave ou valor vazio");
    ExpectRejected(configPath, ValidConfiguration() + "events = \n",
                   "chave ou valor vazio");
    ExpectRejected(configPath, ValidConfiguration() + "events = 4\n",
                   "chave duplicada: events");

    // Required PYTHIA configuration keys.
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "events = 3\n", ""),
                   "Chave obrigatória ausente: events");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "threads = 1\n", ""),
                   "Chave obrigatória ausente: threads");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "seed_base = 512\n", ""),
                   "Chave obrigatória ausente: seed_base");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "interaction_mode = poisson\n", ""),
        "Chave obrigatória ausente: interaction_mode");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "mean_interactions = 1.5\n", ""),
        "Chave obrigatória ausente: mean_interactions");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(),
                           "pythia_config = pythia.cmnd\n", ""),
                   "Chave obrigatória ausente: pythia_config");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(),
                           "physics_list = FTFP_BERT_ATL\n", ""),
                   "Chave obrigatória ausente: physics_list");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "output = output.root\n", ""),
                   "Chave obrigatória ausente: output");

    // Strict boolean parsing.
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "transport_neutrinos = false",
                "transport_neutrinos = perhaps"),
        "Valor booleano inválido para transport_neutrinos");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "generator_audit = true",
                "generator_audit = enabled"),
        "Valor booleano inválido para generator_audit");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "check_overlaps = true",
                "check_overlaps = maybe"),
        "Valor booleano inválido para check_overlaps");

    // Integer-domain validation.
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "events = 3", "events = 0"),
                   "events deve ser positivo");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "threads = 1",
                           "threads = 0"),
                   "threads deve ser positivo");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "seed_base = 512",
                           "seed_base = 0"),
                   "seed_base deve ser positivo");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "first_bcid = 7",
                           "first_bcid = -1"),
                   "intervalo de BCIDs");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "events = 3",
                "events = 999999999999999999999999999999"),
        "Valor inteiro inválido para events");

    // Interaction-model validation.
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "interaction_mode = poisson",
                "interaction_mode = random"),
        "interaction_mode deve ser 'poisson' ou 'fixed'");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "mean_interactions = 1.5",
                "mean_interactions = -0.1"),
        "mean_interactions deve ser finito e não negativo");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "fixed_interactions = 1",
                "fixed_interactions = -1"),
        "fixed_interactions não pode ser negativo");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "mean_interactions = 1.5",
                "mean_interactions = inf"),
        "Valor numérico inválido para mean_interactions");

    // Geometry and run-control limits.
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "production_cut_mm = 1.0",
                "production_cut_mm = 0.0"),
        "production_cut_mm deve ser finito e positivo");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "max_abs_eta = 1.8",
                           "max_abs_eta = 0.0"),
                   "max_abs_eta deve estar em (0, 1.8]");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "max_abs_eta = 1.8",
                           "max_abs_eta = 1.8001"),
                   "max_abs_eta deve estar em (0, 1.8]");
    ExpectRejected(configPath,
                   Replace(ValidConfiguration(), "print_every = 1",
                           "print_every = 0"),
                   "print_every deve ser positivo");
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "beam_sigma_t_ns = 0.0",
                "beam_sigma_t_ns = -0.1"),
        "sigmas do feixe");

    // File validation.
    ExpectRejected(
        configPath,
        Replace(ValidConfiguration(), "pythia_config = pythia.cmnd",
                "pythia_config = definitely-missing-pythia.cmnd"),
        "Arquivo PYTHIA inexistente");

    // Mandatory single-particle parameters.
    ExpectRejected(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_pdg = 11\n", ""),
        "Chave obrigatória ausente: single_particle_pdg");
    ExpectRejected(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_kinetic_energy_gev = 10.0\n", ""),
        "Chave obrigatória ausente: single_particle_kinetic_energy_gev");
    ExpectRejected(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_eta = 0.25\n", ""),
        "Chave obrigatória ausente: single_particle_eta");
    ExpectRejected(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_phi = -1.5\n", ""),
        "Chave obrigatória ausente: single_particle_phi");

    // Valid boundary regression matrix.
    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "events = 3", "events = 1"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "first_bcid = 7",
                "first_bcid = 0"));

    ExpectAccepted(
        configPath,
        Replace(
            Replace(ValidConfiguration(), "events = 3", "events = 1"),
            "first_bcid = 7", "first_bcid = 2147483647"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "seed_base = 512",
                "seed_base = 1"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "mean_interactions = 1.5",
                "mean_interactions = 0.0"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "fixed_interactions = 1",
                "fixed_interactions = 0"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "production_cut_mm = 1.0",
                "production_cut_mm = 1e-300"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "transport_neutrinos = false",
                "transport_neutrinos = yes"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "generator_audit = true",
                "generator_audit = 1"));

    ExpectAccepted(
        configPath,
        Replace(ValidConfiguration(), "check_overlaps = true",
                "check_overlaps = 0"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_pdg = 11",
                "single_particle_pdg = -11"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_kinetic_energy_gev = 10.0",
                "single_particle_kinetic_energy_gev = 1e-300"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_eta = 0.25",
                "single_particle_eta = 1.8"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_eta = 0.25",
                "single_particle_eta = -1.8"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_phi = -1.5",
                "single_particle_phi = 3.14159265358979323846"));

    ExpectAccepted(
        configPath,
        Replace(ValidSingleParticleConfiguration(),
                "single_particle_phi = -1.5",
                "single_particle_phi = -3.14159265358979323846"));

    std::cout << "Configuration tests passed" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Configuration test failed: " << error.what() << std::endl;
    return 1;
  }
}
