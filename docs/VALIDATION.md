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
- `single_particle_analysis`.

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
