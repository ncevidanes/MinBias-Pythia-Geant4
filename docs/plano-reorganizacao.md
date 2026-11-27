# Plano de reorganização do simulador de minimum bias

## Status

Proposta em revisão. Nenhuma alteração de código, configuração ou evidência
é feita por este documento. As decisões D1 a D4 foram tomadas em 2026-11-26
e estão registradas na seção 7. A ordem escolhida é produzir antes (P).

Objetivo: um simulador de minimum bias completo e focado, com comandos
simples e inteligíveis.

Commit de base: `51240a8` (merge do PR #21, congelamento do contrato do
Ciclo 14.1). Os inventários
`docs/cycle-14-minimum-bias-physics-production/evidence/physics-contract-files.sha256`
e `freeze-candidate-artifacts.sha256` foram conferidos com `sha256sum -c`
nesse commit, com todos os arquivos aprovados.

## 1. Inventário

Categorias:

- (a) núcleo do simulador de minimum bias;
- (b) evidência histórica de validação, que precisa continuar reproduzível;
- (c) fora do escopo.

Nenhum arquivo das pastas inventariadas cai na categoria (c): todos servem ao
núcleo ou a algum ciclo de validação. Pela decisão D3, a categoria (c)
contém uma capacidade, não um arquivo: a digitização (forma de pulso, ruído,
ADC, filtro ótimo) fica com outra ferramenta da cadeia de leitura.

### Onde ficam os itens (b)

- **Tag `cycle-14.1-pre-reorganization` em `51240a8`.** É a única garantia de
  reprodução exata. Os scripts de campanha localizam a raiz com
  `Path(__file__).parents[1]`, chamam `run.sh` ou `build/pythia_geant` e
  passam `--particle-*`. Além disso,
  `docs/cycle-6.5-longitudinal-containment/evidence/containment_provenance.sha256`
  grava o caminho `scripts/analyze_longitudinal_containment.py`.
- **`validation/cycle-XX/`** recebe scripts, testes, configurações e o
  analisador classificados como (b). Os caminhos são ajustados na mudança, e
  os testes de unidade continuam registrados no CTest.
- **`docs/cycle-*` permanece onde está.** As evidências citam caminhos
  `docs/cycle-...`, e mover essas pastas quebraria `sha256sum -c`.

### app/

| Arquivo | Cat. | Justificativa |
|---|---|---|
| main.cc | a | |
| analyze_single_particle.cc | b | Analisador das campanhas de partícula única, Ciclos 6.3 a 6.6 |

### include/ e src/

Todos (a), exceto:

| Arquivo | Cat. | Justificativa |
|---|---|---|
| include/SingleParticleAnalysis.hh, src/SingleParticleAnalysis.cc | b | Biblioteca do analisador de partícula única |

`SingleParticleKinematics.hh` e os ramos de partícula única em
`PrimaryGeneratorAction`, `Configuration` e `RootOutput` ficam em (a) por
necessidade: retirá-los muda o schema 4 (colunas 37 a 41 de `metadata`).
Pela decisão D1, permanecem no código.

### scripts/

(a): `audit_root.C`, `compare_root.C`, `inspect_root.C`,
`validate_project.py`, `root_schema_contract.py`, `audit_release.sh`,
`run_coverage.sh`.

| Arquivo | Cat. | Justificativa |
|---|---|---|
| run_single_particle_campaign.sh | b | Executor da campanha 3×3 do Ciclo 6.3 |
| run_statistical_single_particle_campaign.py, aggregate_single_particle_statistics.py | b | Executor e agregador do Ciclo 6.4 |
| analyze_longitudinal_containment.py | b | Ciclo 6.5; o caminho está gravado na evidência |
| run_hadronic_tail_systematics.py, aggregate_hadronic_tail_systematics.py | b | Ciclo 6.6 |
| preflight_integrated_minbias.py, run_integrated_minbias_campaign.py, analyze_integrated_minbias.C | b | Ciclo 7 |
| preflight_neutrino_transport.py, run_neutrino_transport_campaign.py, analyze_neutrino_transport.C | b | Ciclo 8 |
| preflight_neutrino_transport_stage83.py, run_neutrino_transport_stage83.py | b | Ciclo 8.3 |
| preflight_performance_reproducibility.py, run_performance_reproducibility.py, analyze_performance_reproducibility.py | b | Ciclos 9 a 11; o analisador também é usado pelos testes dos Ciclos 10 e 11 |
| analyze_partition_stability.py, analyze_partition_root.py | b | Ciclo 11; o critério de partição serve à produção particionada (seção 5) |

### config/

(a): `production.conf`, `pythia_minbias.cmnd`, `smoke.conf`.

| Arquivo | Cat. | Justificativa |
|---|---|---|
| poisson_mu2.conf | b | Ciclo 7, lido por `preflight_integrated_minbias.py` |
| neutrinos_on_100.conf, neutrinos_off_100.conf, neutrinos_smoke.conf | b | Ciclo 8, lidos por `preflight_neutrino_transport.py` |
| single_particle.conf | b | Ciclos 6.3 a 6.6 |

### tests/

(a): os 14 testes C++ exceto `SingleParticleAnalysisTest.cc`, mais
`test_cli_invalid_inputs.py` e `test_root_schema_contract.py`.

| Arquivo | Cat. | Justificativa |
|---|---|---|
| SingleParticleAnalysisTest.cc, test_single_particle_analyzer_cli.py | b | Testam o analisador de partícula única |
| test_statistical_aggregator.py, test_statistical_campaign_executor.py | b | Ciclo 6.4 |
| test_longitudinal_containment.py | b | Ciclo 6.5 |
| test_hadronic_tail_systematics.py, test_hadronic_tail_aggregator.py | b | Ciclo 6.6 |
| test_integrated_minbias_preflight.py, test_integrated_minbias_executor.py | b | Ciclo 7 |
| test_neutrino_transport_{preflight,executor}.py, test_neutrino_transport_stage83_{preflight,executor}.py | b | Ciclo 8 |
| test_performance_reproducibility_{preflight,executor,analyzer}.py | b | Ciclo 9 |
| test_cycle10_metadata_analyzer.py | b | Ciclo 10 |
| test_cycle11_schema4_analyzer.py, test_partition_stability_analyzer.py, test_partition_root_adapter.py | b | Ciclo 11 |

### docs/

(a): `ARCHITECTURE.md`, `VALIDATION.md` (a seção 4 vira ponteiro para o
histórico), `continuous-integration.md`, `operations/failure-contracts.md`,
`operations/quality-gates.md`, `user-guide/guia_execucao_simulador.tex` e
`cycle-14-minimum-bias-physics-production/` (contrato vigente).

As pastas de ciclo são classificadas por pasta, porque cada uma é a evidência
de um único ciclo.

| Pasta ou arquivo | Cat. | Justificativa |
|---|---|---|
| PROVENANCE_AUDIT.md, LICENSE_AUDIT.md, CITATION_AUDIT.md, TECHNICAL_AUDIT.md, ZENODO_AUDIT.md | b | Auditorias A1 a A6 da release v0.1.0; os fatos vigentes estão em LICENSE, THIRD_PARTY_NOTICES.md e CITATION.cff |
| cycle-6.3-root-analysis/ (1 arquivo), cycle-6.3-single-particle-campaign/ (7) | b | Contrato do analisador e campanha 3×3 |
| cycle-6.4 (7), cycle-6.5 (5), cycle-6.6 (8) | b | Estatística, contenção longitudinal e cauda hadrônica |
| cycle-7 (8), cycle-8 (19) | b | Minimum bias integrado e transporte de neutrinos |
| cycle-9 (2), cycle-10 (2), cycle-11 (8), cycle-12 (3) | b | Desempenho, reprodutibilidade event-stable, partição e continuidade do schema 4 |

### Afetados fora das pastas inventariadas

- `ci/lightweight/CMakeLists.txt`: contém caminhos de testes, e o workflow
  exige 19 unidades de tradução.
- `ci/coverage-baseline.env`: exige 36 testes no CTest.
- `run.sh`: hoje (a); passa a motor legado das campanhas históricas.

## 2. Lacunas

V: verificado no código. D: dedução, com a base indicada.

| # | Lacuna | V/D | Evidência |
|---|---|---|---|
| 1 | Não há pile-up fora do tempo. Um G4Event é um bunch crossing; não existe espaçamento entre bunches nem sobreposição de BCs vizinhos. | V | `PrimaryGeneratorAction::GeneratePrimaries` usa `bcid = firstBcid + eventId`; nenhuma chave de espaçamento em `allowedKeys` de `Configuration.cc` |
| 2 | Não há janela de integração temporal; depósitos atrasados, por exemplo de nêutrons lentos, somam no mesmo BC. | V | `CalorimeterSD::ProcessHits` aceita qualquer `GetGlobalTime` |
| 3 | Região luminosa parcial: quatro gaussianas independentes por subevento, centradas em zero, sem correlação z–t, sem ângulo de cruzamento e sem deslocamento. Os sigmas nominais são 0, e o contrato proíbe substituí-los sem revisão. | V | `DrawStableVertexGaussian`, `config/production.conf`, `physics-contract.md` |
| 4 | Saída por célula e por BC parcial: `hits` é esparso por `(bcid, subevent, célula)`; o total por BC exige somar subeventos fora do simulador; células sem depósito não aparecem e o ROOT não traz mapa de células, então não é possível enumerá-las sem o código de `CellSegmentation`. `cell_id` é gravado como double. | V | `src/RootOutput.cc` (linhas 60 a 79), `EventState::RecordDeposit` |
| 5 | Apenas energia visível, sem fração de amostragem nem calibração. | V | O detector sensível só é associado aos volumes ativos em `DetectorConstruction.cc` |
| 6 | Não há digitização: forma de pulso, ruído, ADC, filtro ótimo. Fora do escopo pela decisão D3; deixa de ser lacuna. O que resta como lacuna é a interface: a saída por célula e por BC (item 4) precisa ser consumível pela ferramenta de digitização. | V (ausência) | Nenhuma ocorrência em `src/` e `include/` |
| 7 | Não há campo magnético nem material antes do calorímetro. | V | O mundo é vácuo e `ConstructSDandField` só registra detectores sensíveis. D: sem o solenoide, partículas carregadas de baixo pT chegam ao calorímetro; o efeito não foi medido |
| 8 | Cobertura limitada a \|eta\| ≤ 1.8, sem EMEC, HEC e FCal. | V | `Configuration::Validate`, README |
| 9 | O tune do PYTHIA não é fixado. | V/D | V: `pythia_minbias.cmnd` não tem `Tune:pp`. D: vale o padrão do PYTHIA 8.312 (Monash, segundo o manual, a conferir), não o A3 usado pelo ATLAS para pile-up |
| 10 | μ é constante na execução, sem perfil bunch a bunch. | V | Um único `meanInteractions` |
| 11 | Produção particionada sem `--first-bcid` na CLI e sem ferramenta de junção. | V/D | V para a CLI (`app/main.cc`). Para a junção, foram verificados apenas os nomes e cabeçalhos dos scripts |
| 12 | `git_commit` é capturado no configure do CMake, não no build. | V | `CMakeLists.txt`, linha 110. Hoje `run.sh` sempre reconfigura; separar build de execução cria risco de proveniência defasada |

As lacunas 1 a 4, 7 e 9 mudam a física e, pela regra do contrato do Ciclo
14.1, exigem revisão do contrato. Ficam para ciclos posteriores, fora desta
reorganização.

## 3. Interface de comando

Quatro subcomandos. Em relação ao ponto de partida (`run`, `check`,
`inspect`), a compilação ganha um comando próprio (`build`) e a comparação de
arquivos entra em `inspect`.

```bash
minbias build --jobs 2
```

Sempre reconfigura e compila, o que resolve a lacuna 12. `--jobs` substitui
`BUILD_JOBS`.

```bash
minbias run --mu 50 --events 3000 --output outputs/mb_mu50.root
```

Opções: `--config` (padrão `config/production.conf`), `--mu`, `--events`,
`--seed`, `--threads`, `--output` e `--dry-run`. Não compila. Recusa-se a
executar se `build/` não existir ou se o commit gravado em
`generated/BuildInfo.hh` diferir de `HEAD`. `--mu` continua forçando
`interaction_mode = poisson`, como já faz `main.cc`. `--physics-list` e
`--production-cut-mm` saem do `run`: são parâmetros do contrato e mudam pelo
arquivo `.conf`.

```bash
minbias check
minbias check --full
```

Sem opção: confere dependências, valida a configuração, faz o dry-run de
`production.conf`, executa o smoke duas vezes com a mesma semente e aplica
`audit_root.C` e a comparação canônica. Com `--full`: CTest completo e
`audit_release.sh`.

```bash
minbias inspect outputs/mb_mu50.root
minbias inspect depois.root --against antes.root
```

Executa `inspect_root.C` e `audit_root.C`. Com `--against`, faz a comparação
canônica da seção 5.

### `--generator-mode` e `--particle-*`

Saem da interface `minbias`. O modo de partícula única continua acessível por
`minbias run --config validation/cycle-06/single_particle.conf`. As opções
**não** são removidas do binário `pythia_geant`: as campanhas 6.3, 6.4 e 6.6
as passam por `run.sh`, e removê-las alteraria `main.cc` sem ganho para quem
usa `minbias`.

### Implementação

Script Python `minbias` na raiz (o CTest já exige Python 3.10), chamando
`build/pythia_geant`. Não toca nenhum arquivo do contrato. `--first-bcid`
exige alterar `main.cc` e fica isolado no PR 15.7.

## 4. Contrato do Ciclo 14.1

Arquivos do inventário `physics-contract-files.sha256` tocados:

- PRs 15.1 a 15.6: nenhum.
- PR 15.7 (`--first-bcid`): `app/main.cc`.

Como a decisão D1 mantém o modo de partícula única, `Configuration`,
`PrimaryGeneratorAction`, `RootOutput` e `RootSchema` não são tocados e o
schema 4 se mantém.

Efeito indireto: `production-contract-ctest.txt` executa testes que vão para
`validation/` (`integrated_minbias_*`, `performance_*`, `partition_*`). Depois
do PR 15.4, repetir o gate exige regenerar essa evidência com a nova
numeração, mesmo sem mudança de hash.

### Ordem P: produzir antes

Produção de 3000 BCs com μ = 50 na tag `cycle-14.1-pre-reorganization`, com
`./run.sh config/production.conf`; reorganização depois.

Pré-requisito atendido: pela decisão D2, o gate do Ciclo 14.1 já passou, e
esta ordem pode começar imediatamente.

Custo: a proveniência da produção aponta para o commit anterior e para a
interface `run.sh`. A equivalência da reorganização é provada contra um
subconjunto de BCIDs da produção, com o comparador de partição do Ciclo 11.
É barato porque a identidade aleatória é event-stable por BCID.

### Ordem R: reorganizar antes

- R1, sem o PR 15.7: os hashes continuam válidos. Custo: a produção espera
  seis PRs, e o gate precisa ser refeito no novo commit (subconjunto do
  CTest, cerca de 145 s na evidência, e dry-run), com evidência regenerada.
- R2, com o PR 15.7: o hash de `main.cc` muda. Custo: nova revisão do
  contrato (inventário de hashes e `physics-contract.md`) e gate completo
  antes de produzir.

O tempo de produção não foi estimado: o Ciclo 9 tem medidas, mas para outra
configuração.

### Ordem escolhida: P (decisão D4)

1. PR 15.0: tag `cycle-14.1-pre-reorganization` em `51240a8` e registro do
   fechamento do gate.
2. Produção nominal na tag, com `./run.sh config/production.conf`, sem
   sobrescritas. ROOT, manifesto, log, tempo, memória máxima e hashes ficam
   registrados como evidência do Ciclo 14.
3. PRs 15.1 a 15.6, nenhum deles tocando arquivos do contrato. Além dos casos
   C1 a C5 da seção 5, cada PR que toca execução refaz um subconjunto de
   BCIDs da produção e o compara com as entradas correspondentes do arquivo
   de produção, com `scripts/analyze_partition_root.py`.
4. PR 15.7, se for feito, vem por último. Como altera `app/main.cc`, exige
   revisão do inventário de hashes antes de qualquer produção posterior, mas
   não afeta a produção já feita.

## 5. Critério de aceite

1. Referência A: build da tag. Candidato B: build do head de cada PR. Os dois
   são construídos e executados no mesmo caminho absoluto (um worktree
   reaproveitado), na mesma máquina, com o ambiente registrado como em
   `environment.txt`. Assim `config_file`, `output_file`, `pythia_config` e
   `normalized_config` coincidem.
2. Casos executados com `pythia_geant` diretamente, com os mesmos argumentos
   em A e B:
   - C1: `config/smoke.conf`;
   - C2: `config/production.conf --events 20 --mu 50`;
   - C3: C2 com `--threads 2`, apenas em B, comparado com o C2 de A;
   - C4: `config/single_particle.conf`;
   - C5: arquivo `.conf` temporário em `outputs/`, com sigmas de feixe não
     nulos e `first_bcid = 100`, para exercitar os caminhos que a
     configuração nominal zera.

   Em B, cada caso também é executado via `minbias run` e precisa dar
   resultado idêntico ao da chamada direta.
3. `scripts/compare_root.C`: `events`, `hits` e `generator` idênticos bit a
   bit. Hoje o script compara `metadata` inteira, e `git_commit` e
   `git_describe` diferem por construção, então falharia sempre. O PR 15.1
   acrescenta um terceiro argumento opcional com os branches de `metadata` a
   excluir; o padrão vazio mantém o comportamento usado por
   `audit_release.sh`. Exclusões permitidas: `{git_commit, git_describe}`;
   em C3, também `threads`, como em `OPERATIONAL_METADATA` do Ciclo 11; em
   C4, depois que o `.conf` mudar de pasta, também `config_file` e
   `normalized_config`, com o manifesto comparado sem a linha `config =`.
   `VERSION` não muda nesses PRs.
4. `scripts/audit_root.C(arquivo, commit)` com `AUDIT_RESULT=PASS` para todos
   os arquivos, de A e de B.
5. Manifestos idênticos com `diff -u`.
6. CSVs do `single_particle_analyzer` sobre C4 idênticos byte a byte.
7. `sha256sum -c physics-contract-files.sha256` aprovado em todo PR fora do
   15.7.
8. CTest com zero falhas e contagem declarada no PR. Contagem de unidades do
   lightweight e baseline de cobertura atualizadas deliberadamente quando
   mudarem.

Hashes dos ROOT, logs e resultados ficam em
`docs/cycle-15-reorganization/evidence/`, no formato dos ciclos anteriores.

## 6. Sequência de PRs

| PR | Conteúdo | Prova |
|---|---|---|
| 15.0 | Tag `cycle-14.1-pre-reorganization` em `51240a8`; este plano; `docs/cycle-15-reorganization/contract.md` com a seção 5; registro do fechamento do gate do Ciclo 14.1 (decisão D2) | Apenas documentação; hashes aprovados |
| 15.1 | Lista de exclusão opcional em `compare_root.C`, com teste | A contra A sem exclusão: PASS; A contra B com `{git_commit, git_describe}`: PASS; CTest 37 |
| 15.2 | Script `minbias` com os quatro subcomandos, testes de parsing e de entradas inválidas, verificação do commit do build | C1 a C5, chamada direta contra `minbias`, idênticos; CTest 38 |
| 15.3 | Partícula única para `validation/cycle-06/`: analisador, biblioteca, teste C++, scripts, testes e `.conf`; caminhos no CMake e em `ci/lightweight` | Seção 5 completa; contagem do CTest inalterada; CSVs de C4 idênticos |
| 15.4 | Ciclos 7 a 11 para `validation/cycle-07` a `validation/cycle-11`: scripts, testes e `.conf`, com `parents[1]` ajustado | Seção 5; contagem do CTest inalterada |
| 15.5 | Documentação: README centrado em `minbias`, guia `.tex`, seção 4 de `VALIDATION.md` como ponteiro, `validation/README.md` com a tabela ciclo, commit e pasta, contagens em `quality-gates.md` | Apenas documentação; links conferidos |
| 15.6 | `run.sh` documentado como motor legado das campanhas históricas, sem mudança de código | `bash -n` e `audit_release.sh` |
| 15.7 | Opcional: `--first-bcid` em `main.cc` e em `minbias run`; revisão do inventário de hashes | Seção 5 e gate completo do Ciclo 14; vem depois da produção (decisão D4) |

Pela decisão D4, a produção nominal roda entre o PR 15.0 e o PR 15.1.

## 7. Decisões

Tomadas pelo responsável pelo projeto em 2026-11-26.

- **D1. Modo de partícula única: manter no código.** Fica como modo de
  validação, acessível por `--config`, fora da interface `minbias`. Nenhum
  hash do contrato muda por causa dele, e o schema 4 se mantém.
- **D2. Gate do Ciclo 14.1: já passou.** A produção em larga escala está
  autorizada, e a ordem P não tem pré-requisito pendente. Observação: no
  commit `51240a8`, `physics-contract.md` ainda se declara candidato ao
  congelamento, e o repositório não contém o registro do fechamento do gate.
  Esse registro deve entrar no PR 15.0 ou antes da produção, para que a
  autorização fique rastreável.
- **D3. Digitização: fora do escopo.** Forma de pulso, ruído, ADC e filtro
  ótimo ficam com outra ferramenta da cadeia de leitura. A lacuna 6 passa à
  categoria (c), e a saída por célula e por BC (lacuna 4) passa a ser a
  interface com essa ferramenta.

- **D4. Ordem: produzir antes (P).** A produção nominal roda na tag
  `cycle-14.1-pre-reorganization`, depois do PR 15.0 e antes do PR 15.1. A
  sequência está na seção 4.
