# PYTHIA → Geant4 em uma única execução

Este projeto substitui o fluxo provisório

```text
PYTHIA → CSV → Geant4 → CSV
```

por um fluxo em memória:

```text
PYTHIA 8 → primárias Geant4 → calorímetro de amostragem → ROOT
```

O usuário executa um único comando. Internamente, cada classe continua tendo
uma responsabilidade: configuração, geração, geometria, transporte, scoring e
persistência.

## O que a simulação representa

- Colisões `pp` a 14 TeV.
- Minimum-bias **inelástico** com `SoftQCD:inelastic = on`.
- Um evento Geant4 corresponde a um bunch crossing.
- Em modo `poisson`, o número de interações é
  \(N_{\mathrm{int}}\sim\mathrm{Poisson}(\mu)\).
- A passagem PYTHIA → Geant4 ocorre diretamente em memória.
- A lista de física padrão é `FTFP_BERT_ATL`, selecionada pelo
  `G4PhysListFactory`.
- A saída é ROOT pelo sistema de análise do próprio Geant4.

## Limite científico da geometria

A geometria fornecida é uma implementação **ATLAS/Lorenzetti-like** do barrel:
PSB, EMB1–EMB3, TileCal1–TileCal3 e TileExt1–TileExt3. Ela usa os materiais
NIST do Geant4 e os parâmetros do exemplo Lorenzetti disponibilizado no
projeto. Ela não deve ser descrita como a geometria oficial completa do ATLAS.
EMEC e HEC não estão implementados nesta versão; por isso a configuração
limita a geração transportada a `|eta| <= 1.8`.

## Dependências

- compilador C++17;
- CMake 3.20 ou superior;
- PYTHIA 8 com `pythia8-config` no `PATH`;
- Geant4 11.2 ou superior, compilado com suporte a ROOT para a saída `.root`.

O código é compatível com o ambiente já observado no projeto:
PYTHIA 8.312 e Geant4 11.3.2. As versões efetivamente carregadas são gravadas
na TTree `metadata` e devem permanecer também no log de cada campanha.

## Comando único

Ative o ambiente que contém PYTHIA e Geant4 e execute:

```bash
chmod +x run.sh
./run.sh config/smoke.conf
```

O script valida a configuração, configura o CMake, compila somente o necessário
e inicia a simulação. Para produção:

```bash
./run.sh config/production.conf
```

Sobrescritas úteis:

```bash
./run.sh config/production.conf \
  --events 100 \
  --mu 10 \
  --threads 2 \
  --output outputs/teste_mu10.root
```

`BUILD_JOBS` controla apenas a compilação. O padrão é 2 para reduzir o risco de
OOM:

```bash
BUILD_JOBS=1 ./run.sh config/smoke.conf
```

## Saída ROOT

O arquivo contém quatro TTrees:

| TTree | Conteúdo |
|---|---|
| `events` | metadados do bunch crossing, \(\mu\), interações sorteadas/geradas, falhas e contagens de partículas |
| `hits` | energia depositada por `(evento, subevento, célula)`, tempo médio ponderado por energia e maior contribuição individual |
| `generator` | registro completo do PYTHIA para auditoria; preenchido somente com `generator_audit = true` |
| `metadata` | uma entrada por execução com configuração normalizada, política de sementes, versões e proveniência |

Campos principais de `hits`:

```text
run, event, bcid, subevent, cell_id, subdetector, sampling,
side, eta_index, phi_index, eta_center, phi_center,
edep_mev, time_mean_ns, time_first_ns,
leading_pdg, leading_track_id, leading_parent_id
```

A TTree `metadata` possui uma entrada e 34 branches:

```text
schema_version, project_version, git_commit, git_describe,
root_version, geant4_version, pythia_version,
run, events, first_bcid, threads,
seed_base, geant4_master_seed, pythia_seed_base,
pythia_worker_seed_stride, pythia_seed_max,
interaction_mode, mean_interactions, fixed_interactions,
pythia_config, physics_list, production_cut_mm,
beam_sigma_x_mm, beam_sigma_y_mm, beam_sigma_z_mm, beam_sigma_t_ns,
max_abs_eta, transport_neutrinos, generator_audit, check_overlaps,
print_every, config_file, output_file, normalized_config
```

Isso permite auditar o arquivo ROOT sem depender do diretório em que a
simulação foi executada.

Mapeamento de `sampling`:

| Código | Sampling |
|---:|---|
| 0 | PSB |
| 1 | EMB1 |
| 2 | EMB2 |
| 3 | EMB3 |
| 4 | TileCal1 |
| 5 | TileCal2 |
| 6 | TileCal3 |
| 7 | TileExt1 |
| 8 | TileExt2 |
| 9 | TileExt3 |

## Reprodutibilidade

O mestre do Geant4 e cada trabalhador do PYTHIA recebem sementes derivadas de
`seed_base`. A política normaliza a semente do PYTHIA para seu intervalo válido
e separa os trabalhadores com `pythia_worker_seed_stride = 104729`, respeitando
`pythia_seed_max = 900000000`.

Uma execução é reprodutível quando são mantidos:

- versões do projeto, Git, ROOT, Geant4 e PYTHIA;
- arquivo `.cmnd`;
- configuração `.conf`;
- número de threads;
- `seed_base`;
- lista de física.

O número de threads faz parte do contrato porque altera a distribuição dos
eventos entre as instâncias PYTHIA dos trabalhadores.

Além da TTree `metadata`, incorporada ao ROOT, o programa grava
`<saida>.manifest.txt` como representação legível da configuração resolvida.
Os dois registros são complementares: o manifesto facilita a inspeção no
terminal e `metadata` mantém a proveniência junto aos dados.

## Inspeção rápida

```bash
root -l -q 'scripts/inspect_root.C("outputs/minbias_smoke.root")'
```

Leia também:

- `docs/ARCHITECTURE.md`;
- `docs/VALIDATION.md`.

## Referências técnicas

- [PYTHIA 8](https://pythia.org/) e o exemplo oficial
  [`main327`](https://www.pythia.org/latest-manual/examples/main327.html),
  que usa `SoftQCD:inelastic`;
- [Geant4 Book for Application Developers](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/index.html);
- [exemplos calorimétricos B4 do Geant4](https://geant4.web.cern.ch/documentation/pipelines/master/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html);
- [guia oficial da lista FTFP_BERT](https://geant4.web.cern.ch/documentation/dev/plg_html/PhysicsListGuide/reference_PL/FTFP_BERT.html);
- [Lorenzetti](https://github.com/lorenzetti-ufrj-br/lorenzetti), usado
  como referência para a estrutura modular e os parâmetros da geometria
  simplificada.

## Licença e atribuição

Copyright (C) 2026 Nelson Cevidanes Nascimento de Assis.

O código deste repositório é distribuído sob a **GNU General Public License
v3.0 only**, identificada por `GPL-3.0-only`. Consulte o arquivo `LICENSE`.

Os parâmetros de amostragem em `src/Sampling.cc` foram derivados do exemplo de
geometria ATLAS do Lorenzetti, especificamente de
`geometry/ATLAS/python/ECAL.py` e `TILE.py` no commit
`5929bb15ff193bc63305f8201be7b2eb207d1557`. Eles foram convertidos para
milímetros, simplificados para construção direta no Geant4 e modificados onde
documentado. Nenhum arquivo-fonte do Lorenzetti é incluído literalmente.

PYTHIA, Geant4, ROOT e CMake são projetos independentes, não são incorporados
a este repositório e permanecem sujeitos às respectivas licenças. A análise
detalhada está em `docs/LICENSE_AUDIT.md`.
