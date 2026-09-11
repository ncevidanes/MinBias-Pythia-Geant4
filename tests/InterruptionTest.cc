#include "Interruption.hh"

#include <csignal>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void Require(
    const bool condition,
    const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void TestSigint() {
  pg::Interruption::Install();

  Require(
      !pg::Interruption::Requested(),
      "Fresh SIGINT state must not be requested");

  std::raise(SIGINT);

  Require(
      pg::Interruption::Requested(),
      "SIGINT request was not recorded");

  Require(
      pg::Interruption::SignalNumber() == SIGINT,
      "Unexpected SIGINT signal number");
}

void TestSigterm() {
  pg::Interruption::Install();

  std::raise(SIGTERM);

  Require(
      pg::Interruption::Requested(),
      "SIGTERM request was not recorded");

  Require(
      pg::Interruption::SignalNumber() == SIGTERM,
      "Unexpected SIGTERM signal number");
}

void TestCommitLinearization() {
  pg::Interruption::Install();

  pg::Interruption::BeginCommitPhase();

  Require(
      pg::Interruption::CommitPhaseStarted(),
      "Commit phase was not recorded");

  std::raise(SIGINT);

  Require(
      !pg::Interruption::Requested(),
      "Post-commit-phase signal must not cancel publication");
}

void TestThrowContract() {
  pg::Interruption::Install();

  std::raise(SIGTERM);

  try {
    pg::Interruption::ThrowIfRequested();
  } catch (const std::runtime_error&) {
    return;
  }

  throw std::runtime_error(
      "ThrowIfRequested did not throw");
}

}  // namespace

int main() {
  try {
    TestSigint();
    TestSigterm();
    TestCommitLinearization();
    TestThrowContract();

    std::cout
        << "InterruptionTest: PASS\n";

    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "InterruptionTest: FAIL: "
        << error.what()
        << '\n';

    return 1;
  }
}
