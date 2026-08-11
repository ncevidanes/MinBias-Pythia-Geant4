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

- compilador com suporte a C++20; o simulador permanece em C++17 e o
  analisador ROOT é compilado em C++20;
- CMake 3.20 ou superior;
- Python 3 para validar os arquivos de configuração;
- PYTHIA 8 com `pythia8-config` no `PATH`;
- ROOT 6 com `root-config` no `PATH`;
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
| `generator` | registro do gerador para auditoria; preenchido somente com `generator_audit = true` |
| `metadata` | uma entrada por execução com configuração normalizada, política de sementes, versões e proveniência |

Campos principais de `hits`:

```text
run, event, bcid, subevent, cell_id, subdetector, sampling,
side, eta_index, phi_index, eta_center, phi_center,
edep_mev, time_mean_ns, time_first_ns,
leading_pdg, leading_track_id, leading_parent_id
```

A TTree `metadata` possui uma entrada e 39 branches:

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
print_every, config_file, output_file, normalized_config,
generator_mode, single_particle_pdg,
single_particle_kinetic_energy_gev,
single_particle_eta, single_particle_phi
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

## Análise ROOT de partículas únicas

O executável `single_particle_analyzer` analisa, sem modificar, um ROOT com
`schema_version = 2` e `generator_mode = single_particle`:

```bash
./build/single_particle_analyzer \
  --input outputs/single_particle.root \
  --summary-csv outputs/single_particle_summary.csv \
  --sampling-csv outputs/single_particle_samplings.csv
```

Em caso de sucesso, o programa imprime `ANALYSIS_RESULT=PASS`. O primeiro CSV
contém uma linha de resumo da execução, com proveniência, parâmetros da
partícula incidente, contagens, resposta, resolução e larguras ponderadas. O
segundo contém exatamente dez linhas de dados, uma para cada sampling, inclusive
quando o depósito é zero.

O analisador rejeita esquema, modo, branches, tipos ou valores incompatíveis e
confere a soma das energias dos samplings contra `events.total_edep_mev`. As
métricas são operacionais para a campanha de partículas únicas; não convertem
o índice de sampling em profundidade física e não caracterizam esta geometria
simplificada como resposta oficial do ATLAS.

### Campanha controlada de partículas únicas

A Etapa 6.3D executa elétrons, fótons e píons positivos em 1, 10 e 100 GeV,
com 100 eventos por caso, uma thread e sementes fixas. Antes do transporte,
valide a matriz:

```bash
./scripts/run_single_particle_campaign.sh --dry-run
```

Após fazer commit das alterações rastreadas, execute a campanha completa:

```bash
./scripts/run_single_particle_campaign.sh
```

O executor analisa cada ROOT duas vezes, confere a identidade byte a byte dos
CSVs, verifica que o ROOT não foi modificado e agrega os nove resumos. Os
resultados são gravados em `outputs/cycle6-stage63d/`, que não é versionado.
Consulte `docs/cycle-6.3-single-particle-campaign/campaign-spec.md` para a
matriz, as sementes, os critérios de aceite e os limites de interpretação.

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
root -l -b -q 'scripts/inspect_root.C("outputs/minbias_smoke.root")'
```

Para verificar automaticamente o esquema e as invariantes contábeis:

```bash
root -l -b -q 'scripts/audit_root.C("outputs/minbias_smoke.root")'
```

Antes de criar uma tag de release, faça o commit da candidata, mantenha a
árvore rastreada limpa e execute a auditoria integrada:

```bash
./scripts/audit_release.sh
```

Ela realiza build limpo, seis testes de regressão, dry runs, duas execuções
smoke com a mesma semente, auditoria das quatro TTrees, comparação exata do
conteúdo ROOT e inspeção do arquivo-fonte produzido por `git archive`. As
evidências são gravadas sob `outputs/`, que não é versionado.

Leia também:

- `docs/ARCHITECTURE.md`;
- `docs/VALIDATION.md`;
- `docs/PROVENANCE_AUDIT.md`;
- `docs/LICENSE_AUDIT.md`;
- `docs/CITATION_AUDIT.md`;
- `docs/TECHNICAL_AUDIT.md`;
- `THIRD_PARTY_NOTICES.md`.

## Referências técnicas

- [PYTHIA 8](https://pythia.org/) e o exemplo oficial
  [`main327`](https://www.pythia.org/latest-manual/examples/main327.html),
  que usa `SoftQCD:inelastic`;
- [Geant4 Book for Application Developers](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/index.html);
- [exemplos calorimétricos B4 do Geant4](https://geant4.web.cern.ch/documentation/pipelines/master/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html);
- [guia oficial da lista FTFP_BERT](https://geant4.web.cern.ch/documentation/dev/plg_html/PhysicsListGuide/reference_PL/FTFP_BERT.html);
- [Lorenzetti](https://github.com/lorenzetti-ufrj-br/lorenzetti), usado
  como referência para a estrutura modular e os parâmetros da geometria
  simplificada, e M. V. Araújo et al., *Lorenzetti Showers - A
  general-purpose framework for supporting signal reconstruction and
  triggering with calorimeters*, Computer Physics Communications 286 (2023),
  108671, [doi:10.1016/j.cpc.2023.108671](https://doi.org/10.1016/j.cpc.2023.108671).

## Como citar

O arquivo `CITATION.cff` contém os metadados canônicos. Enquanto o DOI desta
versão ainda não tiver sido emitido, use a referência provisória:

> de Assis, N. C. N. (2026). *MinBias-Pythia-Geant4* (Version 0.1.0)
> [Computer software]. GitHub.
> <https://github.com/ncevidanes/MinBias-Pythia-Geant4>

Depois do arquivamento no Zenodo, a referência deverá usar o DOI específico da
versão `0.1.0`. O DOI conceitual será mantido para direcionar leitores à versão
mais recente do projeto.

A citação deste software não substitui a citação do artigo do Lorenzetti quando
os parâmetros da geometria derivada forem relevantes para o trabalho. Consulte
`THIRD_PARTY_NOTICES.md` para a atribuição completa.

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
