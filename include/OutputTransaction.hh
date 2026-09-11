#ifndef PYTHIAGEANT_OUTPUTTRANSACTION_HH
#define PYTHIAGEANT_OUTPUTTRANSACTION_HH

#include <filesystem>

namespace pg {

class OutputTransaction {
 public:
  static std::filesystem::path StagingPath(
      const std::filesystem::path& finalPath);

  static std::filesystem::path ManifestPath(
      const std::filesystem::path& finalPath);

  static void ValidateReady(
      const std::filesystem::path& finalPath);

  static void Publish(
      const std::filesystem::path& finalPath);
};

class OutputTransactionGuard final {
 public:
  explicit OutputTransactionGuard(
      std::filesystem::path finalPath);

  ~OutputTransactionGuard() noexcept;

  OutputTransactionGuard(
      const OutputTransactionGuard&) = delete;

  OutputTransactionGuard& operator=(
      const OutputTransactionGuard&) = delete;

  OutputTransactionGuard(
      OutputTransactionGuard&&) = delete;

  OutputTransactionGuard& operator=(
      OutputTransactionGuard&&) = delete;

  void Commit();

 private:
  std::filesystem::path finalPath_;
  std::filesystem::path stagingPath_;
  std::filesystem::path manifestPath_;
  bool committed_ = false;
};

}  // namespace pg

#endif
