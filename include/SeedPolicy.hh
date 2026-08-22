#ifndef PYTHIAGEANT_SEEDPOLICY_HH
#define PYTHIAGEANT_SEEDPOLICY_HH

#include <cstdint>

namespace pg {

inline constexpr char kSeedPolicyName[] = "event-stable-v1";
inline constexpr char kSeedIdentityName[] = "bcid";
inline constexpr char kSeedMixerName[] = "splitmix64-v1";

inline constexpr long long kPythiaMaximumSeed = 900000000LL;

/*
 * Legacy Cycle 9 worker-seed policy.
 *
 * These symbols remain temporarily because the production generator and
 * ROOT metadata still consume them. Cycle 10 integration will remove that
 * dependency after the event-stable primitive is independently validated.
 */
inline constexpr long long kPythiaWorkerSeedStride = 104729LL;

inline int NormalizePythiaSeed(const long long seed) {
  const long long normalized =
      ((seed - 1) % kPythiaMaximumSeed +
       kPythiaMaximumSeed) %
          kPythiaMaximumSeed +
      1;
  return static_cast<int>(normalized);
}

inline int PythiaSeedForWorker(const int seedBase, const int threadId) {
  const int normalizedThreadId = threadId < 0 ? 0 : threadId;
  return NormalizePythiaSeed(
      static_cast<long long>(seedBase) +
      kPythiaWorkerSeedStride * normalizedThreadId);
}

/*
 * Event-stable Cycle 10 policy.
 *
 * Scientific streams are keyed exclusively by:
 *
 *   (seed_base, bcid, subevent, stream_id)
 *
 * Worker identity and scheduling order do not participate.
 */
enum class SeedStream : std::uint64_t {
  kPythiaInitialization = 1ULL,
  kInteractionCount = 2ULL,
  kPythiaSubevent = 3ULL,
  kVertexX = 4ULL,
  kVertexY = 5ULL,
  kVertexZ = 6ULL,
  kVertexT = 7ULL,
};

inline constexpr std::uint64_t kStableSeedDomain =
    0x243F6A8885A308D3ULL;

inline constexpr std::uint64_t SplitMix64(
    std::uint64_t value) {
  value += 0x9E3779B97F4A7C15ULL;
  value =
      (value ^ (value >> 30U)) *
      0xBF58476D1CE4E5B9ULL;
  value =
      (value ^ (value >> 27U)) *
      0x94D049BB133111EBULL;
  return value ^ (value >> 31U);
}

/*
 * Tuple-composition rule frozen by Cycle 10 known-vector tests.
 *
 * Each tuple component is injected in contract order and separated
 * by one full SplitMix64 transformation.
 */
inline constexpr std::uint64_t StableSeed64(
    const std::uint64_t seedBase,
    const std::uint64_t bcid,
    const std::uint64_t subevent,
    const SeedStream stream) {
  std::uint64_t value = kStableSeedDomain;

  value = SplitMix64(value ^ seedBase);
  value = SplitMix64(value ^ bcid);
  value = SplitMix64(value ^ subevent);
  value = SplitMix64(
      value ^ static_cast<std::uint64_t>(stream));

  return value;
}

inline constexpr int PythiaSeedFromStableSeed(
    const std::uint64_t stableSeed) {
  return static_cast<int>(
      1ULL +
      stableSeed %
          static_cast<std::uint64_t>(kPythiaMaximumSeed));
}

inline constexpr int PythiaSeedForStableTuple(
    const std::uint64_t seedBase,
    const std::uint64_t bcid,
    const std::uint64_t subevent,
    const SeedStream stream) {
  return PythiaSeedFromStableSeed(
      StableSeed64(seedBase, bcid, subevent, stream));
}

}  // namespace pg

#endif
