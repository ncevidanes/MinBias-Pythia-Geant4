#ifndef PYTHIAGEANT_STABLERANDOM_HH
#define PYTHIAGEANT_STABLERANDOM_HH

#include "SeedPolicy.hh"

#include <cmath>
#include <cstdint>
#include <random>
#include <stdexcept>

namespace pg {

inline bool IsVertexSeedStream(const SeedStream stream) {
  switch (stream) {
    case SeedStream::kVertexX:
    case SeedStream::kVertexY:
    case SeedStream::kVertexZ:
    case SeedStream::kVertexT:
      return true;
    default:
      return false;
  }
}

inline std::mt19937_64 MakeStableRandomEngine(
    const std::uint64_t seedBase,
    const std::uint64_t bcid,
    const std::uint64_t subevent,
    const SeedStream stream) {
  return std::mt19937_64(
      StableSeed64(seedBase, bcid, subevent, stream));
}

inline int DrawStablePoisson(
    const double mean,
    const std::uint64_t seedBase,
    const std::uint64_t bcid) {
  if (!std::isfinite(mean) || mean < 0.0) {
    throw std::invalid_argument(
        "stable Poisson mean must be finite and non-negative");
  }

  if (mean == 0.0) {
    return 0;
  }

  auto engine = MakeStableRandomEngine(
      seedBase,
      bcid,
      0ULL,
      SeedStream::kInteractionCount);

  std::poisson_distribution<int> distribution(mean);
  return distribution(engine);
}

inline double DrawStableVertexGaussian(
    const double sigma,
    const std::uint64_t seedBase,
    const std::uint64_t bcid,
    const std::uint64_t subevent,
    const SeedStream stream) {
  if (!IsVertexSeedStream(stream)) {
    throw std::invalid_argument(
        "stable vertex Gaussian requires a vertex stream");
  }

  if (sigma == 0.0) {
    return 0.0;
  }

  auto engine = MakeStableRandomEngine(
      seedBase,
      bcid,
      subevent,
      stream);

  std::normal_distribution<double> distribution(0.0, sigma);
  return distribution(engine);
}

}  // namespace pg

#endif
