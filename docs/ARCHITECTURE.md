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
7. `RootOutput` grava as TTrees.

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
| `RootOutput` | esquema e escrita ROOT |
| `RunAction` / `EventAction` | ciclo de vida do arquivo e dos eventos |

## Checkpoints

O fluxo principal é em memória. Há dois checkpoints:

- `<saida>.manifest.txt`: parâmetros resolvidos;
- TTree `generator`: registro completo do PYTHIA, opcional.

Assim, a auditoria pode ser ativada em amostras pequenas sem impor o custo do
HepMC/CSV a toda campanha. Para intercâmbio com outro simulador, HepMC3 continua
sendo o formato recomendado; ele não é necessário como contrato interno desta
execução.

## Multithreading

O Geant4 cria ações por trabalhador. Cada trabalhador recebe:

- uma instância PYTHIA;
- um gerador pseudoaleatório para Poisson e beam spot;
- um `EventState` thread-local.

O número de threads faz parte da definição reprodutível da campanha. Em
máquinas com cerca de 7 GiB de RAM, comece com uma ou duas threads.

