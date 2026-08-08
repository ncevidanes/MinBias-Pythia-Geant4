# Third-party notices

This document records third-party material and external software relevant to
MinBias-Pythia-Geant4. It complements, but does not replace, the project's
`LICENSE` file or the license terms of the external projects listed below.

## Material adapted in this repository

### Lorenzetti Showers

- Project: [Lorenzetti Showers](https://github.com/lorenzetti-ufrj-br/lorenzetti)
- Reference commit: `5929bb15ff193bc63305f8201be7b2eb207d1557`
- Upstream license: GNU General Public License version 3
- Material used: sampling and segmentation parameters from
  `geometry/ATLAS/python/ECAL.py` and `geometry/ATLAS/python/TILE.py`
- Local destination: `src/Sampling.cc`

The parameters were converted to millimetres, simplified for direct Geant4
construction, and modified where documented. No Lorenzetti source file is
included verbatim. The C++ implementation, the direct PYTHIA-to-Geant4 bridge,
the scoring model, the particle-lineage logic, the seed policy, and the ROOT
output are implementations of this project.

Scientific reference:

> M. V. Araújo, M. Begalli, W. S. Freund, G. I. Gonçalves, M. Khandoga,
> B. Laforge, A. Leopold, J. L. Marin, B. S.-M. Peralva, J. V. F. Pinto,
> M. S. Santos, J. M. Seixas, E. F. Simas Filho, and E. E. P. Souza,
> “Lorenzetti Showers - A general-purpose framework for supporting signal
> reconstruction and triggering with calorimeters,” *Computer Physics
> Communications* 286 (2023), 108671.
> <https://doi.org/10.1016/j.cpc.2023.108671>

The detailed file-by-file analysis is recorded in
`docs/PROVENANCE_AUDIT.md`.

## External build and runtime dependencies

The following projects are required or consulted by the build and execution
workflow. Their source code and binary distributions are not included in this
repository and remain governed by their own licenses.

| Component | Role | License identified in Cycle A2 | Project page |
|---|---|---|---|
| PYTHIA 8 | generation of proton-proton collisions | GNU GPL version 2 or later | <https://pythia.org/> |
| Geant4 | particle transport and detector simulation | Geant4 Software License | <https://geant4.web.cern.ch/download/license> |
| ROOT | output format and runtime version provenance | GNU LGPL version 2.1 | <https://root.cern.ch/about/license/> |
| CMake | build-system generator | BSD 3-Clause | <https://cmake.org/licensing/> |

This source release does not redistribute those dependencies. A future binary,
container, or bundled package must be audited separately and must include every
notice and license required by the components actually distributed.

## Scientific and institutional context

The simplified calorimeter is described as **ATLAS/Lorenzetti-like** to state
its scientific inspiration and provenance. MinBias-Pythia-Geant4 does not
include Athena or ATLAS source code and is not official software of the ATLAS
Collaboration, CERN, Lorenzetti, PYTHIA, Geant4, ROOT, or CMake. Project names
and trademarks belong to their respective owners.

## Project license

MinBias-Pythia-Geant4 is distributed under `GPL-3.0-only`. See `LICENSE` and
`docs/LICENSE_AUDIT.md` for the applicable terms and the licensing decision.
