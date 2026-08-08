#ifndef PYTHIAGEANT_SEEDPOLICY_HH
#define PYTHIAGEANT_SEEDPOLICY_HH

namespace pg {

inline constexpr long long kPythiaWorkerSeedStride = 104729LL;
inline constexpr long long kPythiaMaximumSeed = 900000000LL;

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

}  // namespace pg

#endif
