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
- `metadata` contém exatamente uma entrada e 34 branches;
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
- `seed_policy`.

O teste `seed_policy` cobre normalização, limites, sementes por trabalhador,
wrap-around e ausência de colisões no intervalo exercitado pelo teste.

## 3. Geração

Em uma amostra com `generator_audit = true`, verificar:

- todos os beams são prótons;
- `sqrt(s) = 14 TeV`;
- somente processos inelásticos foram habilitados;
- distribuição de `n_interactions_requested` compatível com Poisson;
- simetria de eta e uniformidade de phi;
- taxa de falhas do `pythia.next()` próxima de zero.

## 4. Transporte unitário

Antes de minimum-bias em larga escala, acrescente um modo de partículas únicas
e teste elétrons, fótons e píons em 1, 10 e 100 GeV. Avalie:

- conservação contábil da energia;
- profundidade e largura dos chuveiros;
- resposta e resolução por sampling;
- estabilidade com a production cut.

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
