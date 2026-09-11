#ifndef PYTHIAGEANT_INTERRUPTION_HH
#define PYTHIAGEANT_INTERRUPTION_HH

namespace pg {

class Interruption final {
 public:
  static void Install();

  static bool Requested() noexcept;

  static int SignalNumber() noexcept;

  static void BeginCommitPhase() noexcept;

  static bool CommitPhaseStarted() noexcept;

  static void ThrowIfRequested();
};

}  // namespace pg

#endif
