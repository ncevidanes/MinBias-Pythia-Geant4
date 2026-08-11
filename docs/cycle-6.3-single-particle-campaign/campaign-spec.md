# Campanha de partículas únicas — Etapa 6.3D

## Objetivo

Executar e auditar uma matriz controlada de partículas únicas sobre a
geometria calorimétrica simplificada. A campanha conecta o transporte já
validado ao analisador ROOT da Etapa 6.3C e produz evidências reproduzíveis
para a validação física progressiva.

Esta etapa não altera o fluxo minimum-bias, a geometria, o scoring nem o
formato ROOT.

## Matriz fixa

| Caso | PDG | Energia cinética (GeV) | Eventos | Semente |
|---|---:|---:|---:|---:|
| `electron_1gev` | 11 | 1 | 100 | 631001 |
| `electron_10gev` | 11 | 10 | 100 | 631002 |
| `electron_100gev` | 11 | 100 | 100 | 631003 |
| `photon_1gev` | 22 | 1 | 100 | 632001 |
| `photon_10gev` | 22 | 10 | 100 | 632002 |
| `photon_100gev` | 22 | 100 | 100 | 632003 |
| `pion_plus_1gev` | 211 | 1 | 100 | 633001 |
| `pion_plus_10gev` | 211 | 10 | 100 | 633002 |
| `pion_plus_100gev` | 211 | 100 | 100 | 633003 |

Em todos os casos:

- `generator_mode = single_particle`;
- `threads = 1`;
- `single_particle_eta = 0`;
- `single_particle_phi = 0`;
- `physics_list = FTFP_BERT_ATL`;
- `production_cut_mm = 1.0`;
- `generator_audit = true`.

Para elétrons e píons, o valor informado é energia cinética. Para fótons, ela
coincide com a energia total.

## Executor

A interface canônica é:

```bash
./scripts/run_single_particle_campaign.sh --dry-run
./scripts/run_single_particle_campaign.sh
```

`--dry-run` compila, executa os seis testes CTest e confere as nove
configurações normalizadas, mas não realiza transporte nem cria ROOTs. A
execução real exige que não existam alterações rastreadas no índice ou no
worktree, para que o commit gravado na proveniência identifique o código
efetivamente usado.

O paralelismo da compilação pode ser limitado sem alterar a simulação:

```bash
./scripts/run_single_particle_campaign.sh --build-jobs 1
```

Um diretório alternativo evita sobrescrever uma campanha existente:

```bash
./scripts/run_single_particle_campaign.sh \
  --output-dir outputs/cycle6-stage63d-repeat
```

O executor recusa qualquer arquivo de destino preexistente. Uma repetição deve
usar outro diretório, preservando a primeira campanha como evidência.

## Produtos por caso

Para cada uma das nove configurações são produzidos:

- o ROOT e seu manifesto normalizado;
- o log da simulação;
- um CSV de resumo;
- um CSV com os dez samplings;
- o log da análise.

A campanha também produz:

- `campaign_summary.csv`, agregando as nove linhas de resumo;
- `campaign_manifest.tsv`, com parâmetros, commit e SHA-256 de cada ROOT;
- `campaign_validation.txt`, com o resultado das invariantes automáticas.

Todos esses produtos ficam sob `outputs/` e não são versionados.

## Verificações automáticas

O executor exige:

- seis testes CTest aprovados;
- nove simulações concluídas sem erro;
- `ANALYSIS_RESULT=PASS` em cada análise;
- uma linha de resumo e dez linhas de sampling por caso;
- `event_count = 100` e metadados incidentes iguais à matriz;
- contagens de hits e depósitos médios positivos;
- ausência de métricas não finitas;
- CSVs idênticos em duas análises independentes do mesmo ROOT;
- SHA-256 do ROOT inalterado pelas análises;
- depósito médio estritamente crescente entre 1, 10 e 100 GeV para cada
  espécie.

O aceite é identificado por:

```text
CAMPAIGN_RESULT=PASS cases=9 events_per_case=100
```

## Limites científicos

Cem eventos por ponto são suficientes para uma primeira verificação de
sanidade e tendência, não para uma caracterização calorimétrica de precisão.
As métricas são depósitos na geometria simplificada, sem calibração para
energia incidente. Elas não devem ser apresentadas como resposta oficial do
ATLAS nem como validação completa de linearidade ou resolução.

A monotonicidade é um critério mínimo de integridade. A avaliação quantitativa
de linearidade, resolução, dependência em eta e estabilidade com diferentes
`production cuts` pertence às etapas seguintes.
