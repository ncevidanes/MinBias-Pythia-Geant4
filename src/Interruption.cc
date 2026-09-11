#include "Interruption.hh"

#include <atomic>
#include <csignal>
#include <stdexcept>
#include <string>

#include <signal.h>

namespace {

static_assert(
    std::atomic<int>::is_always_lock_free,
    "Signal handling requires lock-free atomic<int>");

std::atomic<int> gSignalNumber{0};
std::atomic<int> gCommitPhase{0};

extern "C" void PythiaGeantSignalHandler(
    const int signalNumber) noexcept {
  // Signal-handler contract:
  // - lock-free atomics only;
  // - no allocation;
  // - no streams;
  // - no filesystem;
  // - no ROOT/Geant4;
  // - no exceptions.
  if (gCommitPhase.load(
          std::memory_order_relaxed) == 0) {
    gSignalNumber.store(
        signalNumber,
        std::memory_order_relaxed);
  }
}

void InstallHandler(const int signalNumber) {
  struct sigaction action{};
  action.sa_handler = PythiaGeantSignalHandler;
  action.sa_flags = 0;

  if (::sigemptyset(&action.sa_mask) != 0) {
    throw std::runtime_error(
        "Unable to initialize signal mask");
  }

  if (::sigaction(
          signalNumber,
          &action,
          nullptr) != 0) {
    throw std::runtime_error(
        "Unable to install signal handler for signal " +
        std::to_string(signalNumber));
  }
}

}  // namespace

namespace pg {

void Interruption::Install() {
  gSignalNumber.store(
      0,
      std::memory_order_relaxed);

  gCommitPhase.store(
      0,
      std::memory_order_relaxed);

  InstallHandler(SIGINT);
  InstallHandler(SIGTERM);
}

bool Interruption::Requested() noexcept {
  return gSignalNumber.load(
             std::memory_order_relaxed) != 0;
}

int Interruption::SignalNumber() noexcept {
  return gSignalNumber.load(
      std::memory_order_relaxed);
}

void Interruption::BeginCommitPhase() noexcept {
  // Linearization point:
  // signals observed before this point suppress publication;
  // signals delivered afterwards are treated as post-run.
  gCommitPhase.store(
      1,
      std::memory_order_release);
}

bool Interruption::CommitPhaseStarted() noexcept {
  return gCommitPhase.load(
             std::memory_order_acquire) != 0;
}

void Interruption::ThrowIfRequested() {
  const int signalNumber = SignalNumber();

  if (signalNumber == 0) {
    return;
  }

  throw std::runtime_error(
      "Simulation interrupted by signal " +
      std::to_string(signalNumber));
}

}  // namespace pg
