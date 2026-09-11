#include "OutputTransaction.hh"

#include <system_error>
#include <utility>

#include <stdexcept>
#include <string>

namespace pg {

std::filesystem::path OutputTransaction::StagingPath(
    const std::filesystem::path& finalPath) {
  if (finalPath.empty() || finalPath.filename().empty()) {
    throw std::invalid_argument(
        "Output path must contain a file name");
  }

  const std::string stagingName =
      "." + finalPath.filename().string() + ".partial.root";

  return finalPath.parent_path() / stagingName;
}

std::filesystem::path OutputTransaction::ManifestPath(
    const std::filesystem::path& finalPath) {
  if (finalPath.empty() || finalPath.filename().empty()) {
    throw std::invalid_argument(
        "Output path must contain a file name");
  }

  return std::filesystem::path(
      finalPath.string() + ".manifest.txt");
}

void OutputTransaction::ValidateReady(
    const std::filesystem::path& finalPath) {
  const auto stagingPath = StagingPath(finalPath);
  const auto manifestPath = ManifestPath(finalPath);

  if (std::filesystem::exists(finalPath)) {
    throw std::runtime_error(
        "Output file already exists: " +
        finalPath.string());
  }

  if (std::filesystem::exists(stagingPath)) {
    throw std::runtime_error(
        "Staging output already exists: " +
        stagingPath.string());
  }

  if (std::filesystem::exists(manifestPath)) {
    throw std::runtime_error(
        "Output manifest already exists: " +
        manifestPath.string());
  }
}

void OutputTransaction::Publish(
    const std::filesystem::path& finalPath) {
  const auto stagingPath = StagingPath(finalPath);

  if (std::filesystem::exists(finalPath)) {
    throw std::runtime_error(
        "Refusing to replace existing output file: " +
        finalPath.string());
  }

  if (!std::filesystem::exists(stagingPath)) {
    throw std::runtime_error(
        "Staging output is missing: " +
        stagingPath.string());
  }

  std::filesystem::rename(
      stagingPath,
      finalPath);
}

OutputTransactionGuard::OutputTransactionGuard(
    std::filesystem::path finalPath)
    : finalPath_(std::move(finalPath)),
      stagingPath_(
          OutputTransaction::StagingPath(finalPath_)),
      manifestPath_(
          OutputTransaction::ManifestPath(finalPath_)) {
  OutputTransaction::ValidateReady(finalPath_);
}

OutputTransactionGuard::~OutputTransactionGuard() noexcept {
  if (committed_) {
    return;
  }

  std::error_code error;

  std::filesystem::remove(
      stagingPath_,
      error);

  error.clear();

  std::filesystem::remove(
      manifestPath_,
      error);
}

void OutputTransactionGuard::Commit() {
  OutputTransaction::Publish(finalPath_);
  committed_ = true;
}

}  // namespace pg
