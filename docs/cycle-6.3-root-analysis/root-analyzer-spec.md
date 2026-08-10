# Contrato do analisador ROOT de partículas únicas

## Objetivo

Implementar um analisador C++ independente da simulação que leia arquivos
ROOT com `schema_version = 2` e `generator_mode = single_particle`.

O analisador fornecerá as métricas necessárias à campanha da Etapa 6.3C,
sem alterar os arquivos ROOT de entrada.

## Limites

Esta etapa não inclui:

- produção da campanha de nove configurações;
- geração de gráficos;
- ajuste de calibração;
- interpretação dos depósitos como resposta oficial do ATLAS;
- análise física do modo minimum-bias `pythia`.

A macro `scripts/audit_root.C` continuará responsável pela integridade
estrutural e contábil. O novo programa será responsável pelas métricas
físicas de partículas únicas.

## Interface de linha de comando

    ./build/single_particle_analyzer --input <arquivo.root> \
      --summary-csv <resumo.csv> --sampling-csv <samplings.csv>

Em caso de sucesso, o programa imprimirá:

    ANALYSIS_RESULT=PASS

Entradas inválidas produzirão código de saída diferente de zero e:

    ANALYSIS_RESULT=FAIL

## Dados utilizados

### metadata

- `schema_version`;
- `git_commit`;
- `generator_mode`;
- `single_particle_pdg`;
- `single_particle_kinetic_energy_gev`;
- `single_particle_eta`;
- `single_particle_phi`.

### events

- `event`;
- `total_edep_mev`.

### hits

- `event`;
- `sampling`;
- `eta_center`;
- `phi_center`;
- `edep_mev`.

## Resumo por execução

O arquivo indicado por `--summary-csv` conterá uma linha com:

- proveniência e parâmetros incidentes;
- número de eventos e hits;
- depósito médio de energia;
- desvio-padrão amostral do depósito;
- resposta média, definida pelo depósito médio dividido pela energia cinética;
- resolução relativa, definida pelo desvio-padrão dividido pela média;
- centroide e largura em índice de sampling;
- larguras ponderadas em eta e phi.

O centroide em sampling será uma métrica operacional e não será denominado
profundidade física em milímetros.

## Resumo por sampling

O arquivo indicado por `--sampling-csv` conterá exatamente dez linhas,
inclusive para samplings sem depósito:

    0 PSB
    1 EMB1
    2 EMB2
    3 EMB3
    4 TileCal1
    5 TileCal2
    6 TileCal3
    7 TileExt1
    8 TileExt2
    9 TileExt3

Para cada sampling serão registrados:

- depósito médio por evento;
- desvio-padrão amostral;
- fração do depósito total;
- largura ponderada em eta;
- largura ponderada em phi.

Eventos sem hits em determinado sampling contribuirão com energia zero.

## Convenções estatísticas

- todas as energias serão tratadas em MeV;
- o desvio-padrão amostral usará denominador `N - 1`;
- a diferença angular em phi será reduzida ao intervalo `[-pi, pi]`;
- somas e estatísticas serão calculadas em precisão dupla;
- valores não finitos ou energias negativas serão rejeitados;
- a soma das energias dos samplings deverá coincidir com
  `events.total_edep_mev` dentro de tolerância numérica.

## Arquivos planejados

- `include/SingleParticleAnalysis.hh`;
- `src/SingleParticleAnalysis.cc`;
- `app/analyze_single_particle.cc`;
- `tests/SingleParticleAnalysisTest.cc`;
- `CMakeLists.txt`;
- `README.md`;
- `docs/VALIDATION.md`.

## Critérios de aceite

- build sem avisos novos;
- seis testes CTest aprovados;
- rejeição explícita de esquema ou modo de gerador incompatível;
- análise aprovada do elétron de 10 GeV produzido na Etapa 6.3A;
- depósito médio reproduzindo aproximadamente `2306.779052 MeV`;
- duas execuções produzindo CSVs idênticos;
- nenhuma modificação nos ROOT de entrada.
