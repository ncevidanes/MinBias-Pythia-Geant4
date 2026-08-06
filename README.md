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
PYTHIA 8.312 e Geant4 11.3.2. A versão exata carregada deve ser registrada no
log de cada campanha.

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

O arquivo contém três TTrees:

| TTree | Conteúdo |
|---|---|
| `events` | metadados do bunch crossing, \(\mu\), interações sorteadas/geradas, falhas e contagens de partículas |
| `hits` | energia depositada por `(evento, subevento, célula)`, tempo médio ponderado por energia e maior contribuição individual |
| `generator` | registro completo do PYTHIA para auditoria; preenchido somente com `generator_audit = true` |

Campos principais de `hits`:

```text
run, event, bcid, subevent, cell_id, subdetector, sampling,
side, eta_index, phi_index, eta_center, phi_center,
edep_mev, time_mean_ns, time_first_ns,
leading_pdg, leading_track_id, leading_parent_id
```

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

Cada trabalhador recebe uma instância independente do PYTHIA e uma semente
derivada de `seed_base`. Uma execução é reprodutível quando são mantidos:

- versões de PYTHIA e Geant4;
- arquivo `.cmnd`;
- configuração `.conf`;
- número de threads;
- `seed_base`;
- lista de física.

Além do ROOT, o programa grava `<saida>.manifest.txt` com a configuração
resolvida.

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
