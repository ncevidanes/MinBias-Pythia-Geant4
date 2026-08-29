#include "StableRandom.hh"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

void Require(const bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void CheckStableEngineReconstruction() {
  auto first = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      3ULL,
      pg::SeedStream::kVertexX);

  auto second = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      3ULL,
      pg::SeedStream::kVertexX);

  for (int index = 0; index < 32; ++index) {
    Require(
        first() == second(),
        "Reconstructed stable engines diverged");
  }
}

void CheckPoissonDeterminism() {
  const int first =
      pg::DrawStablePoisson(
          20.0,
          9512ULL,
          42ULL);

  const int unrelated =
      pg::DrawStablePoisson(
          20.0,
          9512ULL,
          99ULL);

  const int second =
      pg::DrawStablePoisson(
          20.0,
          9512ULL,
          42ULL);

  (void)unrelated;

  Require(
      first == second,
      "Poisson draw changed after an unrelated event");

  Require(
      pg::DrawStablePoisson(
          0.0,
          9512ULL,
          42ULL) == 0,
      "Zero-mean Poisson draw was not zero");

  bool negativeMeanRejected = false;
  try {
    (void)pg::DrawStablePoisson(
        -1.0,
        9512ULL,
        42ULL);
  } catch (const std::invalid_argument&) {
    negativeMeanRejected = true;
  }

  Require(
      negativeMeanRejected,
      "Negative Poisson mean was not rejected");

  bool nonFiniteMeanRejected = false;
  try {
    (void)pg::DrawStablePoisson(
        std::numeric_limits<double>::infinity(),
        9512ULL,
        42ULL);
  } catch (const std::invalid_argument&) {
    nonFiniteMeanRejected = true;
  }

  Require(
      nonFiniteMeanRejected,
      "Non-finite Poisson mean was not rejected");
}

void CheckZeroSigma() {
  const pg::SeedStream streams[] = {
      pg::SeedStream::kVertexX,
      pg::SeedStream::kVertexY,
      pg::SeedStream::kVertexZ,
      pg::SeedStream::kVertexT,
  };

  for (const auto stream : streams) {
    Require(
        pg::DrawStableVertexGaussian(
            0.0,
            9512ULL,
            42ULL,
            1ULL,
            stream) == 0.0,
        "Zero sigma did not return exact zero");
  }
}

void CheckVertexDeterminism() {
  const pg::SeedStream streams[] = {
      pg::SeedStream::kVertexX,
      pg::SeedStream::kVertexY,
      pg::SeedStream::kVertexZ,
      pg::SeedStream::kVertexT,
  };

  for (const auto stream : streams) {
    const double first =
        pg::DrawStableVertexGaussian(
            1.25,
            9512ULL,
            42ULL,
            7ULL,
            stream);

    const double second =
        pg::DrawStableVertexGaussian(
            1.25,
            9512ULL,
            42ULL,
            7ULL,
            stream);

    Require(
        first == second,
        "Identical vertex tuple was not deterministic");

    Require(
        std::isfinite(first),
        "Vertex Gaussian produced a non-finite value");
  }
}

void CheckOrderIndependence() {
  const double xBefore =
      pg::DrawStableVertexGaussian(
          1.0,
          9512ULL,
          42ULL,
          5ULL,
          pg::SeedStream::kVertexX);

  const double y =
      pg::DrawStableVertexGaussian(
          1.0,
          9512ULL,
          42ULL,
          5ULL,
          pg::SeedStream::kVertexY);

  const double t =
      pg::DrawStableVertexGaussian(
          1.0,
          9512ULL,
          42ULL,
          5ULL,
          pg::SeedStream::kVertexT);

  const double xAfter =
      pg::DrawStableVertexGaussian(
          1.0,
          9512ULL,
          42ULL,
          5ULL,
          pg::SeedStream::kVertexX);

  Require(
      xBefore == xAfter,
      "Vertex X depended on draw order");

  Require(std::isfinite(y), "Vertex Y was non-finite");
  Require(std::isfinite(t), "Vertex T was non-finite");
}

void CheckTupleIsolationAtEngineLevel() {
  auto x0 = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      0ULL,
      pg::SeedStream::kVertexX);

  auto x1 = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      1ULL,
      pg::SeedStream::kVertexX);

  auto y0 = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      0ULL,
      pg::SeedStream::kVertexY);

  Require(
      x0() != x1(),
      "Changing subevent did not isolate engine stream");

  auto x0Again = pg::MakeStableRandomEngine(
      9512ULL,
      42ULL,
      0ULL,
      pg::SeedStream::kVertexX);

  Require(
      x0Again() != y0(),
      "Changing coordinate did not isolate engine stream");
}

void CheckInvalidVertexStreamRejected() {
  bool rejected = false;

  try {
    (void)pg::DrawStableVertexGaussian(
        1.0,
        9512ULL,
        42ULL,
        0ULL,
        pg::SeedStream::kPythiaSubevent);
  } catch (const std::invalid_argument&) {
    rejected = true;
  }

  Require(
      rejected,
      "Non-vertex stream was accepted for vertex Gaussian");
}

}  // namespace

int main() {
  try {
    CheckStableEngineReconstruction();
    CheckPoissonDeterminism();
    CheckZeroSigma();
    CheckVertexDeterminism();
    CheckOrderIndependence();
    CheckTupleIsolationAtEngineLevel();
    CheckInvalidVertexStreamRejected();

    std::cout
        << "Stable auxiliary RNG tests passed"
        << std::endl;

    return 0;
  } catch (const std::exception& error) {
    std::cerr
        << "Stable auxiliary RNG test failed: "
        << error.what()
        << std::endl;

    return 1;
  }
}
