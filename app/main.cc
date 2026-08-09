#include "ActionInitialization.hh"
#include "Configuration.hh"
#include "DetectorConstruction.hh"

#include "G4PhysListFactory.hh"
#include "G4RunManager.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4VModularPhysicsList.hh"
#include "Randomize.hh"

#ifdef G4MULTITHREADED
#include "G4MTRunManager.hh"
#endif

#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

void PrintUsage(const char* executable) {
  std::cout
      << "Uso: " << executable << " --config ARQUIVO [opções]\n"
      << "  --events N\n"
      << "  --mu VALOR\n"
      << "  --threads N\n"
      << "  --seed N\n"
      << "  --output ARQUIVO.root\n"
      << "  --physics-list NOME\n"
      << "  --generator-mode pythia|single_particle\n"
      << "  --particle-pdg PDG\n"
      << "  --particle-kinetic-energy-gev VALOR\n"
      << "  --particle-eta VALOR\n"
      << "  --particle-phi VALOR\n"
      << "  --dry-run\n";
}

std::string RequireValue(int& index, const int argc, char** argv,
                         const std::string& option) {
  if (index + 1 >= argc) {
    throw std::runtime_error("Valor ausente para " + option);
  }
  return argv[++index];
}

}  // namespace

int main(int argc, char** argv) {
  try {
    std::filesystem::path configurationPath;
    bool dryRun = false;

    for (int index = 1; index < argc; ++index) {
      const std::string argument = argv[index];
      if (argument == "--config") {
        configurationPath =
            RequireValue(index, argc, argv, argument);
      } else if (argument == "--help" || argument == "-h") {
        PrintUsage(argv[0]);
        return 0;
      } else if (argument == "--dry-run") {
        dryRun = true;
      } else if (argument == "--events" || argument == "--mu" ||
                 argument == "--threads" || argument == "--seed" ||
                 argument == "--output" ||
                 argument == "--physics-list" ||
                 argument == "--generator-mode" ||
                 argument == "--particle-pdg" ||
                 argument == "--particle-kinetic-energy-gev" ||
                 argument == "--particle-eta" ||
                 argument == "--particle-phi") {
        ++index;
        if (index >= argc) {
          throw std::runtime_error("Valor ausente para " + argument);
        }
      } else {
        throw std::runtime_error("Opção desconhecida: " + argument);
      }
    }

    if (configurationPath.empty()) {
      PrintUsage(argv[0]);
      return 2;
    }

    pg::Configuration configuration =
        pg::Configuration::Load(configurationPath);

    for (int index = 1; index < argc; ++index) {
      const std::string argument = argv[index];
      if (argument == "--config") {
        ++index;
      } else if (argument == "--events") {
        configuration.events =
            std::stoi(RequireValue(index, argc, argv, argument));
      } else if (argument == "--mu") {
        configuration.meanInteractions =
            std::stod(RequireValue(index, argc, argv, argument));
        configuration.interactionMode = "poisson";
      } else if (argument == "--threads") {
        configuration.threads =
            std::stoi(RequireValue(index, argc, argv, argument));
      } else if (argument == "--seed") {
        configuration.seedBase =
            std::stoi(RequireValue(index, argc, argv, argument));
      } else if (argument == "--output") {
        configuration.outputFile = std::filesystem::absolute(
            RequireValue(index, argc, argv, argument));
      } else if (argument == "--physics-list") {
        configuration.physicsList =
            RequireValue(index, argc, argv, argument);
      } else if (argument == "--generator-mode") {
        configuration.generatorMode =
            RequireValue(index, argc, argv, argument);
      } else if (argument == "--particle-pdg") {
        configuration.singleParticlePdg =
            std::stoi(RequireValue(index, argc, argv, argument));
      } else if (argument == "--particle-kinetic-energy-gev") {
        configuration.singleParticleKineticEnergyGeV =
            std::stod(RequireValue(index, argc, argv, argument));
      } else if (argument == "--particle-eta") {
        configuration.singleParticleEta =
            std::stod(RequireValue(index, argc, argv, argument));
      } else if (argument == "--particle-phi") {
        configuration.singleParticlePhi =
            std::stod(RequireValue(index, argc, argv, argument));
      }
    }

    configuration.Validate();
    configuration.Print(std::cout);
    if (dryRun) {
      std::cout << "Dry run concluído; nenhuma simulação foi executada.\n";
      return 0;
    }

    configuration.WriteManifest();

    G4Random::setTheSeed(
        static_cast<long>(configuration.seedBase));

    std::unique_ptr<G4RunManager> runManager(
        G4RunManagerFactory::CreateRunManager(
            G4RunManagerType::Default));

#ifdef G4MULTITHREADED
    if (auto* mtManager =
            dynamic_cast<G4MTRunManager*>(runManager.get())) {
      mtManager->SetNumberOfThreads(configuration.threads);
    }
#else
    if (configuration.threads != 1) {
      throw std::runtime_error(
          "Este Geant4 não foi compilado com multithreading.");
    }
#endif

    runManager->SetUserInitialization(
        new pg::DetectorConstruction(configuration));

    G4PhysListFactory physicsFactory;
    G4VModularPhysicsList* physics =
        physicsFactory.GetReferencePhysList(configuration.physicsList);
    if (physics == nullptr) {
      throw std::runtime_error("Lista de física desconhecida: " +
                               configuration.physicsList);
    }
    physics->SetDefaultCutValue(configuration.productionCutMm * mm);
    runManager->SetUserInitialization(physics);
    runManager->SetUserInitialization(
        new pg::ActionInitialization(configuration));

    runManager->Initialize();
    runManager->BeamOn(configuration.events);

    std::cout << "Simulação concluída: " << configuration.outputFile << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Erro: " << error.what() << '\n';
    return 1;
  }
}
