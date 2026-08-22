#include "PrimaryGeneratorAction.hh"

#include "EventState.hh"
#include "LineageInfo.hh"
#include "RootOutput.hh"
#include "SeedPolicy.hh"
#include "StableRandom.hh"
#include "SingleParticleKinematics.hh"

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
#include <cstdint>
#include <memory>
#include <sstream>
#include <string>
#include <utility>

namespace pg {

PrimaryGeneratorAction::PrimaryGeneratorAction(Configuration configuration)
    : configuration_(std::move(configuration)) {
  const int seed = PythiaSeedForWorker(
      configuration_.seedBase,
      G4Threading::G4GetThreadId());
  if (configuration_.generatorMode != "pythia") {
    return;
  }

  pythia_ = std::make_unique<Pythia8::Pythia>();
  if (!pythia_->readFile(configuration_.pythiaConfig.string())) {
    G4ExceptionDescription message;
    message << "Falha ao ler " << configuration_.pythiaConfig;
    G4Exception("PrimaryGeneratorAction", "PythiaConfig", FatalException,
                message);
  }

  pythia_->readString("Random:setSeed = on");
  pythia_->readString("Random:seed = " + std::to_string(seed));

  if (!pythia_->init()) {
    G4Exception("PrimaryGeneratorAction", "PythiaInit", FatalException,
                "O PYTHIA não pôde ser inicializado.");
  }
}

int PrimaryGeneratorAction::DrawInteractionCount(
    const int bcid) const {
  if (configuration_.interactionMode == "fixed") {
    return configuration_.fixedInteractions;
  }

  return DrawStablePoisson(
      configuration_.meanInteractions,
      static_cast<std::uint64_t>(configuration_.seedBase),
      static_cast<std::uint64_t>(bcid));
}

double PrimaryGeneratorAction::DrawGaussian(
    const int bcid,
    const int subevent,
    const SeedStream stream,
    const double sigma) const {
  return DrawStableVertexGaussian(
      sigma,
      static_cast<std::uint64_t>(configuration_.seedBase),
      static_cast<std::uint64_t>(bcid),
      static_cast<std::uint64_t>(subevent),
      stream);
}

void PrimaryGeneratorAction::AuditPythiaParticle(
    const int eventId, const int bcid, const int subevent, const int index,
    const ParticleRejectionCode rejectionCode) {
  if (!configuration_.generatorAudit) {
    return;
  }

  const auto& particle = pythia_->event[index];
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

  if (configuration_.generatorMode == "single_particle") {
    GenerateSingleParticle(event);
    return;
  }
  GeneratePythiaPrimaries(event);
}

void PrimaryGeneratorAction::GeneratePythiaPrimaries(G4Event* event) {
  EventState& state = EventState::Instance();
  state.requestedInteractions = DrawInteractionCount(state.bcid);

  auto* particleTable = G4ParticleTable::GetParticleTable();

  for (int subevent = 0; subevent < state.requestedInteractions;
       ++subevent) {
    if (!pythia_->next()) {
      ++state.generationFailures;
      continue;
    }
    ++state.generatedInteractions;
    state.generatorParticles += pythia_->event.size();

    const double collisionXmm =
        DrawGaussian(
            state.bcid, subevent, SeedStream::kVertexX,
            configuration_.beamSigmaXmm);
    const double collisionYmm =
        DrawGaussian(
            state.bcid, subevent, SeedStream::kVertexY,
            configuration_.beamSigmaYmm);
    const double collisionZmm =
        DrawGaussian(
            state.bcid, subevent, SeedStream::kVertexZ,
            configuration_.beamSigmaZmm);
    const double collisionTns =
        DrawGaussian(
            state.bcid, subevent, SeedStream::kVertexT,
            configuration_.beamSigmaTns);

    for (int index = 0; index < pythia_->event.size(); ++index) {
      const auto& particle = pythia_->event[index];
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
      AuditPythiaParticle(state.eventId, state.bcid, subevent, index,
                          rejectionCode);

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

void PrimaryGeneratorAction::GenerateSingleParticle(G4Event* event) {
  EventState& state = EventState::Instance();
  state.requestedInteractions = 1;
  state.generatedInteractions = 1;
  state.generatorParticles = 1;

  G4ParticleDefinition* definition =
      G4ParticleTable::GetParticleTable()->FindParticle(
          configuration_.singleParticlePdg);
  const bool isNeutrino = IsNeutrinoPdg(configuration_.singleParticlePdg);

  ParticleDecisionInput decisionInput;
  decisionInput.isFinal = true;
  decisionInput.isVisible = !isNeutrino;
  decisionInput.transportNeutrinos = configuration_.transportNeutrinos;
  decisionInput.hasGeantDefinition = definition != nullptr;
  decisionInput.pdg = configuration_.singleParticlePdg;
  decisionInput.eta = configuration_.singleParticleEta;
  decisionInput.maxAbsEta = configuration_.maxAbsEta;

  const ParticleRejectionCode rejectionCode =
      ClassifyParticle(decisionInput);
  state.RecordGeneratorDecision(rejectionCode);

  const double massGeV =
      definition == nullptr ? 0.0 : definition->GetPDGMass() / GeV;
  const SingleParticleKinematics kinematics =
      MakeSingleParticleKinematics(
          configuration_.singleParticleKineticEnergyGeV, massGeV,
          configuration_.singleParticleEta,
          configuration_.singleParticlePhi);

  if (configuration_.generatorAudit) {
    RootOutput::WriteGeneratorParticle(GeneratorParticleRecord{
        state.eventId,
        state.bcid,
        0,
        0,
        configuration_.singleParticlePdg,
        1,
        0,
        0,
        0,
        0,
        1,
        isNeutrino ? 0 : 1,
        kinematics.pxGeV,
        kinematics.pyGeV,
        kinematics.pzGeV,
        kinematics.totalEnergyGeV,
        massGeV,
        configuration_.singleParticleEta,
        configuration_.singleParticlePhi,
        0.0,
        0.0,
        0.0,
        0.0,
        rejectionCode == ParticleRejectionCode::kAccepted ? 1 : 0,
        static_cast<int>(rejectionCode),
    });
  }

  if (rejectionCode != ParticleRejectionCode::kAccepted) {
    return;
  }

  auto* primary = new G4PrimaryParticle(
      definition, kinematics.pxGeV * GeV, kinematics.pyGeV * GeV,
      kinematics.pzGeV * GeV, kinematics.totalEnergyGeV * GeV);
  primary->SetUserInformation(
      new PrimaryLineageInfo(0, configuration_.singleParticlePdg));

  auto* vertex = new G4PrimaryVertex(
      DrawGaussian(
          state.bcid, 0, SeedStream::kVertexX,
          configuration_.beamSigmaXmm) * mm,
      DrawGaussian(
          state.bcid, 0, SeedStream::kVertexY,
          configuration_.beamSigmaYmm) * mm,
      DrawGaussian(
          state.bcid, 0, SeedStream::kVertexZ,
          configuration_.beamSigmaZmm) * mm,
      DrawGaussian(
          state.bcid, 0, SeedStream::kVertexT,
          configuration_.beamSigmaTns) * ns);
  vertex->SetPrimary(primary);
  event->AddPrimaryVertex(vertex);
  ++state.transportedParticles;
}

}  // namespace pg
