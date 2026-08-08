#include "PrimaryGeneratorAction.hh"

#include "EventState.hh"
#include "LineageInfo.hh"
#include "RootOutput.hh"
#include "SeedPolicy.hh"

#include "G4Event.hh"
#include "G4Exception.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <string>
#include <utility>

namespace pg {

PrimaryGeneratorAction::PrimaryGeneratorAction(Configuration configuration)
    : configuration_(std::move(configuration)) {
  const int seed = PythiaSeedForWorker(
      configuration_.seedBase,
      G4Threading::G4GetThreadId());
  random_.seed(static_cast<std::mt19937_64::result_type>(seed));

  if (!pythia_.readFile(configuration_.pythiaConfig.string())) {
    G4ExceptionDescription message;
    message << "Falha ao ler " << configuration_.pythiaConfig;
    G4Exception("PrimaryGeneratorAction", "PythiaConfig", FatalException,
                message);
  }

  pythia_.readString("Random:setSeed = on");
  pythia_.readString("Random:seed = " + std::to_string(seed));

  if (!pythia_.init()) {
    G4Exception("PrimaryGeneratorAction", "PythiaInit", FatalException,
                "O PYTHIA não pôde ser inicializado.");
  }
}

int PrimaryGeneratorAction::DrawInteractionCount() {
  if (configuration_.interactionMode == "fixed") {
    return configuration_.fixedInteractions;
  }
  std::poisson_distribution<int> distribution(
      configuration_.meanInteractions);
  return distribution(random_);
}

double PrimaryGeneratorAction::DrawGaussian(const double sigma) {
  if (sigma == 0.0) {
    return 0.0;
  }
  std::normal_distribution<double> distribution(0.0, sigma);
  return distribution(random_);
}

void PrimaryGeneratorAction::AuditPythiaParticle(
    const int eventId, const int bcid, const int subevent, const int index,
    const ParticleRejectionCode rejectionCode) {
  if (!configuration_.generatorAudit) {
    return;
  }

  const auto& particle = pythia_.event[index];
  RootOutput::WriteGeneratorParticle(GeneratorParticleRecord{
      eventId,
      bcid,
      subevent,
      index,
      particle.id(),
      particle.status(),
      particle.mother1(),
      particle.mother2(),
      particle.daughter1(),
      particle.daughter2(),
      particle.isFinal() ? 1 : 0,
      particle.isVisible() ? 1 : 0,
      particle.px(),
      particle.py(),
      particle.pz(),
      particle.e(),
      particle.m(),
      particle.eta(),
      particle.phi(),
      particle.xProd(),
      particle.yProd(),
      particle.zProd(),
      particle.tProd(),
      rejectionCode == ParticleRejectionCode::kAccepted ? 1 : 0,
      static_cast<int>(rejectionCode),
  });
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event) {
  EventState& state = EventState::Instance();
  const int eventId = event->GetEventID();
  const int bcid = configuration_.firstBcid + eventId;
  state.Reset(eventId, bcid);
  state.requestedInteractions = DrawInteractionCount();

  auto* particleTable = G4ParticleTable::GetParticleTable();

  for (int subevent = 0; subevent < state.requestedInteractions;
       ++subevent) {
    if (!pythia_.next()) {
      ++state.generationFailures;
      continue;
    }
    ++state.generatedInteractions;
    state.generatorParticles += pythia_.event.size();

    const double collisionXmm =
        DrawGaussian(configuration_.beamSigmaXmm);
    const double collisionYmm =
        DrawGaussian(configuration_.beamSigmaYmm);
    const double collisionZmm =
        DrawGaussian(configuration_.beamSigmaZmm);
    const double collisionTns =
        DrawGaussian(configuration_.beamSigmaTns);

    for (int index = 0; index < pythia_.event.size(); ++index) {
      const auto& particle = pythia_.event[index];
      G4ParticleDefinition* definition =
          particleTable->FindParticle(particle.id());

      ParticleDecisionInput decisionInput;
      decisionInput.isFinal = particle.isFinal();
      decisionInput.isVisible = particle.isVisible();
      decisionInput.transportNeutrinos = configuration_.transportNeutrinos;
      decisionInput.hasGeantDefinition = definition != nullptr;
      decisionInput.pdg = particle.id();
      decisionInput.eta = particle.eta();
      decisionInput.maxAbsEta = configuration_.maxAbsEta;

      const ParticleRejectionCode rejectionCode =
          ClassifyParticle(decisionInput);
      state.RecordGeneratorDecision(rejectionCode);
      AuditPythiaParticle(eventId, bcid, subevent, index, rejectionCode);

      if (rejectionCode != ParticleRejectionCode::kAccepted) {
        continue;
      }

      auto* primary = new G4PrimaryParticle(
          definition, particle.px() * GeV, particle.py() * GeV,
          particle.pz() * GeV, particle.e() * GeV);
      primary->SetUserInformation(
          new PrimaryLineageInfo(subevent, particle.id()));

      const double vertexX =
          (collisionXmm + particle.xProd()) * mm;
      const double vertexY =
          (collisionYmm + particle.yProd()) * mm;
      const double vertexZ =
          (collisionZmm + particle.zProd()) * mm;
      const double vertexT =
          collisionTns * ns + particle.tProd() * mm / c_light;

      auto* vertex =
          new G4PrimaryVertex(vertexX, vertexY, vertexZ, vertexT);
      vertex->SetPrimary(primary);
      event->AddPrimaryVertex(vertex);
      ++state.transportedParticles;
    }
  }
}

}  // namespace pg
