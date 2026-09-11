#include "OutputTransaction.hh"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

namespace {

class TemporaryDirectory {
 public:
  TemporaryDirectory() {
    const auto stamp =
        std::chrono::high_resolution_clock::now()
            .time_since_epoch()
            .count();

    path_ =
        std::filesystem::temp_directory_path() /
        ("minbias-output-transaction-test-" +
         std::to_string(stamp));

    if (!std::filesystem::create_directory(path_)) {
      throw std::runtime_error(
          "Could not create temporary directory");
    }
  }

  ~TemporaryDirectory() {
    std::filesystem::remove_all(path_);
  }

  const std::filesystem::path& Path() const {
    return path_;
  }

 private:
  std::filesystem::path path_;
};

void Require(
    const bool condition,
    const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void Write(
    const std::filesystem::path& path,
    const std::string& text) {
  std::ofstream output(path);

  if (!output) {
    throw std::runtime_error(
        "Could not write " + path.string());
  }

  output << text;
}

std::string Read(
    const std::filesystem::path& path) {
  std::ifstream input(path);

  if (!input) {
    throw std::runtime_error(
        "Could not read " + path.string());
  }

  return std::string(
      std::istreambuf_iterator<char>(input),
      std::istreambuf_iterator<char>());
}

template <typename Function>
void RequireThrows(
    Function&& function,
    const std::string& description) {
  try {
    function();
  } catch (const std::exception&) {
    return;
  }

  throw std::runtime_error(
      "Expected exception: " + description);
}

void TestDerivedPaths() {
  const std::filesystem::path finalPath =
      "/tmp/example.root";

  const auto staging =
      pg::OutputTransaction::StagingPath(finalPath);

  const auto manifest =
      pg::OutputTransaction::ManifestPath(finalPath);

  Require(
      staging.parent_path() ==
          finalPath.parent_path(),
      "Staging output must share final directory");

  Require(
      staging.filename() ==
          ".example.root.partial.root",
      "Unexpected staging file name");

  Require(
      staging.extension() == ".root",
      "Staging output must retain ROOT extension");

  Require(
      manifest ==
          std::filesystem::path(
              "/tmp/example.root.manifest.txt"),
      "Unexpected manifest path");
}

void TestReadyContract() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "result.root";

  const auto stagingPath =
      pg::OutputTransaction::StagingPath(
          finalPath);

  const auto manifestPath =
      pg::OutputTransaction::ManifestPath(
          finalPath);

  pg::OutputTransaction::ValidateReady(
      finalPath);

  Write(finalPath, "existing");

  RequireThrows(
      [&] {
        pg::OutputTransaction::ValidateReady(
            finalPath);
      },
      "existing final output must be rejected");

  std::filesystem::remove(finalPath);

  Write(stagingPath, "stale");

  RequireThrows(
      [&] {
        pg::OutputTransaction::ValidateReady(
            finalPath);
      },
      "stale staging output must be rejected");

  std::filesystem::remove(stagingPath);

  Write(manifestPath, "stale-manifest");

  RequireThrows(
      [&] {
        pg::OutputTransaction::ValidateReady(
            finalPath);
      },
      "stale manifest must be rejected");
}

void TestPublication() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "result.root";

  const auto stagingPath =
      pg::OutputTransaction::StagingPath(
          finalPath);

  Write(stagingPath, "complete-output");

  pg::OutputTransaction::Publish(
      finalPath);

  Require(
      std::filesystem::exists(finalPath),
      "Published output is missing");

  Require(
      !std::filesystem::exists(stagingPath),
      "Staging output remained after publication");

  Require(
      Read(finalPath) == "complete-output",
      "Published output content changed");
}

void TestPublishRejectsMissingStaging() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "result.root";

  RequireThrows(
      [&] {
        pg::OutputTransaction::Publish(
            finalPath);
      },
      "missing staging must be rejected");

  Require(
      !std::filesystem::exists(finalPath),
      "Missing staging created final output");
}

void TestPublishRejectsExistingFinal() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "result.root";

  const auto stagingPath =
      pg::OutputTransaction::StagingPath(
          finalPath);

  Write(finalPath, "preserve-final");
  Write(stagingPath, "do-not-publish");

  RequireThrows(
      [&] {
        pg::OutputTransaction::Publish(
            finalPath);
      },
      "existing final must never be replaced");

  Require(
      Read(finalPath) == "preserve-final",
      "Existing final output was modified");

  Require(
      Read(stagingPath) == "do-not-publish",
      "Staging output was unexpectedly modified");
}

void TestGuardCleansIncompleteArtifacts() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "failure.root";

  const auto stagingPath =
      pg::OutputTransaction::StagingPath(
          finalPath);

  const auto manifestPath =
      pg::OutputTransaction::ManifestPath(
          finalPath);

  bool controlledFailureObserved = false;

  try {
    pg::OutputTransactionGuard transaction(
        finalPath);

    Write(
        stagingPath,
        "partial-root");

    Write(
        manifestPath,
        "partial-manifest");

    throw std::runtime_error(
        "synthetic controlled failure");
  } catch (const std::runtime_error& error) {
    Require(
        std::string(error.what()) ==
            "synthetic controlled failure",
        "Unexpected controlled failure exception");

    controlledFailureObserved = true;
  }

  Require(
      controlledFailureObserved,
      "Synthetic controlled failure was not observed");

  Require(
      !std::filesystem::exists(finalPath),
      "Controlled failure published final output");

  Require(
      !std::filesystem::exists(stagingPath),
      "Controlled failure left staging output");

  Require(
      !std::filesystem::exists(manifestPath),
      "Controlled failure left manifest");
}

void TestGuardCommitPublishesAndPreservesManifest() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "success.root";

  const auto stagingPath =
      pg::OutputTransaction::StagingPath(
          finalPath);

  const auto manifestPath =
      pg::OutputTransaction::ManifestPath(
          finalPath);

  {
    pg::OutputTransactionGuard transaction(
        finalPath);

    Write(
        stagingPath,
        "complete-root");

    Write(
        manifestPath,
        "complete-manifest");

    transaction.Commit();
  }

  Require(
      std::filesystem::exists(finalPath),
      "Commit did not publish final output");

  Require(
      !std::filesystem::exists(stagingPath),
      "Commit left staging output");

  Require(
      std::filesystem::exists(manifestPath),
      "Commit removed valid manifest");

  Require(
      Read(finalPath) == "complete-root",
      "Committed ROOT content changed");

  Require(
      Read(manifestPath) ==
          "complete-manifest",
      "Committed manifest content changed");
}

void TestStaleManifestIsPreservedOnRejection() {
  TemporaryDirectory temporary;

  const auto finalPath =
      temporary.Path() / "result.root";

  const auto manifestPath =
      pg::OutputTransaction::ManifestPath(
          finalPath);

  Write(
      manifestPath,
      "preserve-manifest");

  RequireThrows(
      [&] {
        pg::OutputTransactionGuard transaction(
            finalPath);
      },
      "guard must reject stale manifest");

  Require(
      Read(manifestPath) ==
          "preserve-manifest",
      "Rejected stale manifest was modified");
}

}  // namespace

int main() {
  try {
    TestDerivedPaths();
    TestReadyContract();
    TestPublication();
    TestPublishRejectsMissingStaging();
    TestPublishRejectsExistingFinal();

    TestGuardCleansIncompleteArtifacts();
    TestGuardCommitPublishesAndPreservesManifest();
    TestStaleManifestIsPreservedOnRejection();

    std::cout
        << "OutputTransactionTest: PASS\n";

    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "OutputTransactionTest: FAIL: "
        << error.what()
        << '\n';

    return 1;
  }
}
