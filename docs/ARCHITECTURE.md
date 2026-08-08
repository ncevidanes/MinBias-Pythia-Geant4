# Arquitetura

## Decisão: uma execução, módulos separados

O Lorenzetti separa geração, simulação, digitalização e reconstrução em
transformações distintas. Essa organização é correta para grandes campanhas e
reprocessamento. Aqui, a necessidade imediata é eliminar a interface CSV e
reduzir o número de comandos sem criar um programa monolítico.

O executável único contém este fluxo:

1. `Configuration` resolve e valida os parâmetros.
2. `PrimaryGeneratorAction` mantém uma instância PYTHIA por trabalhador.
3. Para cada bunch crossing, sorteia `N_int` e gera as subcolisões.
4. Partículas finais visíveis são convertidas em `G4PrimaryParticle`.
5. `DetectorConstruction` constrói o calorímetro de amostragem.
6. `CalorimeterSD` agrega deposições por célula e subevento.
7. `RootOutput` grava `events`, `hits`, `generator` e `metadata`.

Não existe arquivo intermediário entre PYTHIA e Geant4.

## Responsabilidades

| Componente | Responsabilidade única |
|---|---|
| `Configuration` | leitura, resolução de caminhos e validação |
| `Sampling` | definições imutáveis das camadas e granularidades |
| `DetectorConstruction` | materiais e volumes Geant4 |
| `PrimaryGeneratorAction` | colisões PYTHIA e primárias Geant4 |
| `LineageInfo` / `TrackingAction` | propagação do identificador do subevento |
| `CalorimeterSD` | scoring e agregação por célula |
| `EventState` | estado local à thread de um único evento |
| `RootOutput` | esquema ROOT, dados dos eventos e proveniência da execução |
| `RunAction` / `EventAction` | ciclo de vida do arquivo e dos eventos |

## Checkpoints

O fluxo principal é em memória. Há três mecanismos de auditoria:

- `<saida>.manifest.txt`: representação legível dos parâmetros resolvidos;
- TTree `metadata`: configuração normalizada, sementes, versões e proveniência incorporadas ao ROOT;
- TTree `generator`: registro completo do PYTHIA, opcional.

`metadata` possui uma entrada por execução e é sempre gravada. O manifesto e
essa TTree descrevem a mesma execução em formatos complementares. A auditoria
detalhada do gerador pode ser ativada em amostras pequenas sem impor o custo do
registro completo a toda campanha. Para intercâmbio com outro simulador,
HepMC3 continua sendo o formato recomendado; ele não é necessário como
contrato interno desta execução.

## Multithreading

O Geant4 cria ações por trabalhador. Cada trabalhador recebe:

- uma instância PYTHIA;
- um gerador pseudoaleatório para Poisson e beam spot;
- um `EventState` thread-local.

`SeedPolicy` deriva de `seed_base` a semente mestre do Geant4 e a semente-base
do PYTHIA. Para o trabalhador, aplica uma derivação determinística pelo seu
identificador, com stride `104729`, e normaliza o resultado para o intervalo
aceito pelo PYTHIA, cujo máximo é `900000000`. Esses parâmetros são persistidos
em `metadata`.

O número de threads faz parte da definição reprodutível da campanha porque
determina quantas instâncias e sequências PYTHIA participam da execução. Em
máquinas com cerca de 7 GiB de RAM, comece com uma ou duas threads.
