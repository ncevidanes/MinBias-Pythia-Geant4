# Protocolo de validação

Não inicie a produção de 3.000 bunch crossings antes de completar esta ordem.

## 1. Instalação

```bash
./run.sh config/smoke.conf --dry-run
./run.sh config/smoke.conf
```

Critérios:

- PYTHIA inicializa sem configurações desconhecidas;
- `FTFP_BERT_ATL` é encontrada;
- não há sobreposições geométricas no smoke test;
- o ROOT contém `events`, `hits`, `generator` e `metadata`;
- `metadata` contém exatamente uma entrada e 39 branches;
- `generator` está preenchida quando `generator_audit = true`.

## 2. Testes de regressão

Após configurar e compilar, executar:

```bash
ctest --test-dir build-v0 -N
ctest --test-dir build-v0 --output-on-failure
```

Devem estar registrados e aprovados:

- `particle_decision`;
- `cell_segmentation`;
- `seed_policy`;
- `configuration`;
- `single_particle_kinematics`;
- `single_particle_analysis`;
- `statistical_aggregator`;
- `statistical_campaign_executor`;
- `longitudinal_containment`;
- `hadronic_tail_systematics`;
- `hadronic_tail_aggregator`.

O teste `seed_policy` cobre normalização, limites, sementes por trabalhador,
wrap-around e ausência de colisões no intervalo exercitado pelo teste.
O teste `configuration` cobre resolução de caminhos, chaves desconhecidas,
números malformados ou não finitos, sigmas negativos e overflow de BCID.
O teste `single_particle_analysis` cobre estatísticas de energia, samplings
sem depósito, larguras ponderadas e tratamento periódico de phi sem depender
de um arquivo ROOT externo.

## 3. Geração

Em uma amostra com `generator_audit = true`, verificar:

- todos os beams são prótons;
- `sqrt(s) = 14 TeV`;
- somente processos inelásticos foram habilitados;
- distribuição de `n_interactions_requested` compatível com Poisson;
- simetria de eta e uniformidade de phi;
- taxa de falhas do `pythia.next()` próxima de zero.

## 4. Transporte unitário

Antes de minimum-bias em larga escala, use o modo de partículas únicas
para testar elétrons, fótons e píons em 1, 10 e 100 GeV. Confirme na
`metadata` o modo do gerador, PDG, energia cinética, eta e phi incidentes.
Avalie:

- conservação contábil da energia;
- profundidade e largura dos chuveiros;
- resposta e resolução por sampling;
- estabilidade com a production cut.

### 4.1 Analisador ROOT

Para cada arquivo da campanha, execute o analisador independente:

```bash
./build/single_particle_analyzer \
  --input outputs/cycle6-stage63a/single_particle_schema2.root \
  --summary-csv outputs/cycle6-stage63c/summary.csv \
  --sampling-csv outputs/cycle6-stage63c/samplings.csv
```

Critérios:

- o processo termina com `ANALYSIS_RESULT=PASS`;
- o resumo possui cabeçalho e uma linha de dados;
- o arquivo por sampling possui cabeçalho e exatamente dez linhas de dados;
- duas execuções sobre o mesmo ROOT produzem CSVs idênticos byte a byte;
- o hash do ROOT de entrada permanece inalterado;
- a soma dos depósitos por sampling coincide com
  `events.total_edep_mev` dentro da tolerância numérica.

O checkpoint da Etapa 6.3C, com três elétrons de 10 GeV em eta e phi iguais a
zero, produziu depósito médio de `2306.779052037 MeV`, resposta média de
`0.230677905` e resolução relativa de `0.013059670`. Esses valores validam a
regressão do analisador para esse arquivo; a amostra de três eventos não deve
ser usada como conclusão de desempenho físico.

### 4.2 Campanha 3 × 3

A Etapa 6.3D fixa três espécies, três energias e 100 eventos por ponto. Execute
primeiro a validação sem transporte:

```bash
./scripts/run_single_particle_campaign.sh --dry-run
```

Depois de fazer commit e manter o worktree rastreado limpo, execute:

```bash
./scripts/run_single_particle_campaign.sh
```

A campanha somente é aprovada quando o terminal e
`outputs/cycle6-stage63d/campaign_validation.txt` registram
`CAMPAIGN_RESULT=PASS`. O executor verifica automaticamente:

- nove casos concluídos e analisados;
- 100 eventos e dez linhas de sampling por caso;
- parâmetros incidentes iguais à matriz documentada;
- métricas finitas, hits positivos e depósito médio positivo;
- repetição byte a byte dos CSVs;
- preservação do SHA-256 dos ROOTs;
- crescimento do depósito médio com 1, 10 e 100 GeV para cada espécie.

Preserve `campaign_summary.csv`, `campaign_manifest.tsv`,
`campaign_validation.txt`, os logs, manifestos e ROOTs. A especificação
completa está em
`docs/cycle-6.3-single-particle-campaign/campaign-spec.md`.

### 4.3 Estatística multi-semente e contenção operacional

O Ciclo 6.4 executa cinco sementes independentes por ponto da matriz 3 × 3,
com 200 eventos por execução. O agregador deve terminar com
`STATISTICAL_AGGREGATION_RESULT=PASS`, preservar os 45 identificadores de
semente como valores globalmente únicos e satisfazer o limite predefinido de
3% para o semicomprimento relativo do IC95 da média depositada.

Depois da aprovação estatística, derive as frações por sampling e a contenção
longitudinal operacional a partir das tabelas versionadas:

```bash
python3 scripts/analyze_longitudinal_containment.py \
  --summary docs/cycle-6.4-statistical-validation/evidence/statistical_summary.csv \
  --samplings docs/cycle-6.4-statistical-validation/evidence/statistical_samplings.csv \
  --output outputs/cycle6-stage65-repeat/containment_summary.csv \
  --validation outputs/cycle6-stage65-repeat/containment_validation.txt
```

Critérios:

- nove pontos, cinco execuções e 1.000 eventos agregados por ponto;
- 90 linhas de sampling e fechamento das frações dentro de `1e-9`;
- limiares de 90%, 95% e 99% alcançados no caminho central;
- elétrons e fótons alcançam 99% até `EMB3`;
- fração de `TileExt` não superior a 1% em incidência normal.

Uma fração de `TileCal3` superior a 1% produz
`outer_tail_review=REQUIRED`, mas não reprova isoladamente a análise. Esse
marcador seleciona os pontos que exigem variação controlada de eta e
`production_cut` no ciclo sistemático seguinte. `TileCal3` é um indicador de
cauda na última camada central ativa, não uma estimativa de energia invisível
fora da geometria.

Os resultados aprovados, o manifesto SHA-256 e os limites científicos estão
em `docs/cycle-6.4-statistical-validation/campaign-report.md` e
`docs/cycle-6.5-longitudinal-containment/analysis-report.md`.

### 4.4 Sistemática da cauda hadrônica

O Ciclo 6.6 fixa píons positivos de 100 GeV, phi zero, uma thread, 200 eventos
por execução e as mesmas cinco sementes em todos os pontos. A matriz combina
eta 0.0, 0.4 e 0.8 com cortes de produção 0.1, 1.0 e 10.0 mm. Antes do
transporte, valide as 45 configurações sem criar o diretório de saída:

```bash
python3 -B scripts/run_hadronic_tail_systematics.py \
  --dry-run \
  --output-dir outputs/cycle6-stage66-preflight
```

Na execução completa, o diretório final é publicado somente depois da análise
duplicada de cada ROOT e da agregação. Devem ser satisfeitos:

- nove pontos, 45 execuções e 9.000 eventos;
- as sementes 643031 a 643035 presentes em todos os pontos;
- identidade byte a byte das duas análises de cada ROOT;
- integridade SHA-256 de todos os ROOTs antes e depois da análise;
- fechamento das dez frações de sampling dentro de `1e-9`;
- oito comparações pareadas contra eta zero e corte de 1 mm;
- intervalos bilaterais de 95% pela distribuição t pareada com quatro graus
  de liberdade.

Uma meia-largura relativa do IC95 da energia média acima de 3% produz
`precision_review=REQUIRED`. Um intervalo pareado de TileCal3 ou TileExt que
exclua zero produz `systematic_review=REQUIRED`. Esses marcadores exigem
interpretação explícita e não reprovam isoladamente a campanha.

No resultado versionado, o pior marcador de precisão foi 4,275269%. A
produção-cut não produziu alteração significativa de TileCal3 em eta zero. Em
eta 0.8, TileCal3 diminuiu enquanto TileExt aumentou nos três cortes, mas a
soma das duas regiões permaneceu abaixo do baseline. O resultado é interpretado
como migração geométrica regional, não como aumento global do vazamento. Veja
`docs/cycle-6.6-hadronic-tail-systematics/analysis-report.md`.

## 5. Geometria

Conferir separadamente:

- materiais NIST;
- raios e extensões em z;
- número e espessura das placas;
- granularidade lógica em eta e phi;
- transição barrel/extended barrel;
- células na fronteira de phi.

## 6. Reprodutibilidade

Executar duas vezes com a mesma configuração e comparar:

- `<saida>.manifest.txt` e a entrada de `metadata`;
- número de interações;
- número de partículas transportadas;
- soma de energia por evento/célula.

Conferir em `metadata`, no mínimo:

- versões do projeto, Git, ROOT, Geant4 e PYTHIA;
- `threads`, `seed_base` e sementes derivadas;
- `pythia_worker_seed_stride` e `pythia_seed_max`;
- `normalized_config`.

Para multithreading, manter também o mesmo número de threads. Comparações com
números diferentes de threads validam integridade e proveniência, mas não
identidade evento a evento, pois muda a distribuição entre os geradores
PYTHIA dos trabalhadores.

Para a candidata de release, `scripts/audit_release.sh` automatiza duas
execuções com `threads = 1`, a mesma configuração, a mesma semente e o mesmo
caminho lógico de saída. O script exige manifestos idênticos e compara, branch
a branch e entrada a entrada, as TTrees `events`, `hits`, `generator` e
`metadata` por meio de `scripts/compare_root.C`.

## 7. Produção

Executar primeiro:

```bash
./run.sh config/production.conf --events 10 --mu 10
./run.sh config/production.conf --events 100 --mu 50
```

Somente depois:

```bash
./run.sh config/production.conf
```

Registrar tempo, memória máxima e tamanho do ROOT. Antes de arquivar a campanha,
confirmar que as versões e a configuração normalizada estão presentes em
`metadata` e que o manifesto correspondente foi preservado.

## 8. Fechamento técnico de release

O Ciclo A4 deve ser executado sobre um commit já criado e com a árvore
rastreada limpa:

```bash
./scripts/audit_release.sh
```

A auditoria somente é aprovada quando o log termina com:

```text
AUDIT_RESULT=PASS
COMPARE_RESULT=PASS
A4_RESULT=PASS commit=<SHA de 40 caracteres>
```

O SHA impresso deve ser o mesmo gravado em `metadata.git_commit` e o mesmo que
receberá a tag da release. A auditoria técnica não substitui a campanha de
partículas únicas da Seção 4: sem essa campanha, a versão pode ser publicada
como simulador técnico de geometria simplificada, mas não como resposta
calorimétrica fisicamente validada ou representação oficial do ATLAS.
