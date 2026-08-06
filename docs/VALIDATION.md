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
- o ROOT contém `events`, `hits` e `generator`.

## 2. Geração

Em uma amostra com `generator_audit = true`, verificar:

- todos os beams são prótons;
- `sqrt(s) = 14 TeV`;
- somente processos inelásticos foram habilitados;
- distribuição de `n_interactions_requested` compatível com Poisson;
- simetria de eta e uniformidade de phi;
- taxa de falhas do `pythia.next()` próxima de zero.

## 3. Transporte unitário

Antes de minimum-bias em larga escala, acrescente um modo de partículas únicas
e teste elétrons, fótons e píons em 1, 10 e 100 GeV. Avalie:

- conservação contábil da energia;
- profundidade e largura dos chuveiros;
- resposta e resolução por sampling;
- estabilidade com a production cut.

## 4. Geometria

Conferir separadamente:

- materiais NIST;
- raios e extensões em z;
- número e espessura das placas;
- granularidade lógica em eta e phi;
- transição barrel/extended barrel;
- células na fronteira de phi.

## 5. Reprodutibilidade

Executar duas vezes com a mesma configuração e comparar:

- `manifest.txt`;
- número de interações;
- número de partículas transportadas;
- soma de energia por evento/célula.

Para multithreading, manter também o mesmo número de threads.

## 6. Produção

Executar primeiro:

```bash
./run.sh config/production.conf --events 10 --mu 10
./run.sh config/production.conf --events 100 --mu 50
```

Somente depois:

```bash
./run.sh config/production.conf
```

Registrar tempo, memória máxima, tamanho do ROOT e versões das dependências.

