# Auditoria de proveniência — Ciclo A1

**Projeto:** MinBias-Pythia-Geant4  
**Data da auditoria:** 2026-08-08  
**Commit auditado:** `72d9a7dde9fe0820768fd010e84d0a6f02793597`  
**Resultado:** aprovado para avançar ao Ciclo A2, com atribuição explícita dos parâmetros geométricos derivados do Lorenzetti.

## 1. Objetivo

Determinar, para todos os arquivos presentes no histórico público do projeto até o commit auditado, se o conteúdo é:

1. implementação original;
2. inspirado conceitualmente no Lorenzetti;
3. baseado em parâmetros do Lorenzetti;
4. código adaptado do Lorenzetti; ou
5. código copiado literalmente do Lorenzetti.

Esta auditoria trata de proveniência técnica. A decisão final de licenciamento será formalizada no Ciclo A2.

## 2. Fontes comparadas

### Projeto auditado

- Repositório: <https://github.com/ncevidanes/MinBias-Pythia-Geant4>
- Commit: <https://github.com/ncevidanes/MinBias-Pythia-Geant4/commit/72d9a7dde9fe0820768fd010e84d0a6f02793597>
- Histórico examinado: seis commits, do baseline `fd8b09f355cbb8fd036fe3ba159d553772b9a0d0` ao commit auditado.
- Inventário reconstruído pelo histórico: 47 arquivos.

### Material do Lorenzetti

- Pasta fornecida no Google Drive: <https://drive.google.com/drive/folders/1aSgLuOYWcJ-YBC-pg9l69wOAgy2ek66h>
- Repositório arquivado correspondente: <https://github.com/lorenzetti-hep/lorenzetti>
- Commit de referência do snapshot: <https://github.com/lorenzetti-hep/lorenzetti/commit/5929bb15ff193bc63305f8201be7b2eb207d1557>
- Repositório atual indicado pelo projeto: <https://github.com/lorenzetti-ufrj-br/lorenzetti>
- Licença encontrada no snapshot: GNU GPL v3.

Onze arquivos críticos da pasta do Drive foram comparados byte a byte com o commit `5929bb1` do repositório arquivado. Os onze coincidiram, incluindo `ECAL.py`, `TILE.py`, `ATLASConstruction.py`, o núcleo Geant4, o gerador Pythia, `mb.card`, `README.md` e `LICENSE`. Assim, o material do Drive ficou ancorado a uma revisão pública e identificável.

## 3. Método

Foram realizadas quatro verificações complementares:

1. reconstrução do inventário do projeto a partir dos seis commits públicos;
2. comparação textual normalizada dos 32 arquivos C++, cabeçalhos e testes do projeto com 35 arquivos relevantes do núcleo Geant4, da geometria ATLAS e do gerador Lorenzetti;
3. comparação dos 14 arquivos restantes de texto do projeto com 14 documentos, scripts, configurações e arquivos de build correspondentes do Lorenzetti;
4. inspeção do arquivo binário `PythiaGeantOneStage_V06.zip`.

A triagem textual procurou linhas significativas iguais e sequências consecutivas de dez tokens. Não foi encontrada nenhuma sequência de dez tokens compartilhada entre os dois projetos. As únicas linhas iguais foram construções triviais de C++/Geant4, como uma diretiva de multithreading, uma declaração antecipada de classe e um membro com nome genérico. Elas não constituem evidência de cópia.

A ausência de coincidência textual não foi usada para avaliar a geometria: números convertidos de Python para C++ foram verificados semanticamente e por unidade.

## 4. Resultado executivo

| Categoria | Resultado |
|---|---|
| Código copiado literalmente do Lorenzetti | Não detectado |
| Blocos de implementação adaptados do Lorenzetti | Não detectados |
| Parâmetros derivados do Lorenzetti | Sim — concentrados em `src/Sampling.cc` |
| Inspiração arquitetural no Lorenzetti | Sim — declarada no README e em `docs/ARCHITECTURE.md` |
| Configuração minimum-bias copiada | Não; há parâmetros padrão comuns, mas a seleção de processo é diferente |
| Arquivos com proveniência incerta | Nenhum no inventário de 47 arquivos |

Conclusão: a implementação C++ é própria, mas a tabela de samplings não deve ser descrita somente como “inspirada”. Ela é uma adaptação identificável dos parâmetros geométricos de `geometry/ATLAS/python/ECAL.py` e `geometry/ATLAS/python/TILE.py` do Lorenzetti.

## 5. Mapeamento dos parâmetros geométricos

### LAr barrel

Fonte: [`ECAL.py` no commit de referência](https://github.com/lorenzetti-hep/lorenzetti/blob/5929bb15ff193bc63305f8201be7b2eb207d1557/geometry/ATLAS/python/ECAL.py).  
Destino: [`src/Sampling.cc` no projeto auditado](https://github.com/ncevidanes/MinBias-Pythia-Geant4/blob/72d9a7dde9fe0820768fd010e84d0a6f02793597/src/Sampling.cc).

Foram preservados ou convertidos:

- PSB: raio de 146 cm, uma camada, 0,01 mm de absorvedor, 1,1 cm de região ativa, `DeltaEta = 0.025` e `DeltaPhi = pi/32`;
- EMB1: raio de 150 cm, 16 camadas, espessuras 1,51 mm e 4,49 mm;
- EMB2: 55 camadas, espessuras 1,7 mm e 4,3 mm, `DeltaEta = 0.025` e `DeltaPhi = pi/128`;
- EMB3: nove camadas, espessuras 1,7 mm e 4,3 mm, `DeltaEta = 0.05` e `DeltaPhi = pi/128`;
- comprimento total de 6,8 m convertido para semicomprimento de 3400 mm no `G4Tubs`.

Há uma alteração documentável: o Lorenzetti usa `DeltaEta = 0.00325` no EMB1, enquanto o projeto usa `0.003125`. Portanto, esse valor não é uma cópia literal e deve ser descrito como uma correção/alteração adotada pelo projeto.

### Tile barrel e extended barrel

Fonte: [`TILE.py` no commit de referência](https://github.com/lorenzetti-hep/lorenzetti/blob/5929bb15ff193bc63305f8201be7b2eb207d1557/geometry/ATLAS/python/TILE.py).  
Destino: [`src/Sampling.cc` no projeto auditado](https://github.com/ncevidanes/MinBias-Pythia-Geant4/blob/72d9a7dde9fe0820768fd010e84d0a6f02793597/src/Sampling.cc).

Foram preservados ou convertidos:

- raio interno de 228,3 cm;
- números de camadas 4, 11 e 5;
- pares de espessura 6,0/4,0 cm e 6,2/3,8 cm;
- granularidades `DeltaEta = 0.1, 0.1, 0.2` e `DeltaPhi = pi/32`;
- barrel com semicomprimento de 3024 mm;
- extended barrel com comprimento total de 2,83 m, convertido para semicomprimento de 1415 mm;
- centro longitudinal `3704 mm + 1415 mm` para os lados A e B.

O projeto também introduz mudanças próprias: materiais NIST do Geant4, limites explícitos em `|eta|`, representação C++ imutável, construção direta por `G4Tubs` e uma segmentação lógica com identificador de célula empacotado.

## 6. Geração minimum-bias e execução

O arquivo Lorenzetti `generator/evtgen/data/minbias_config.cmnd` usa `SoftQCD:all = on` e o fluxo de `examples/mb.card` é dividido em duas etapas, com um ROOT intermediário entre geração e simulação.

O projeto usa `SoftQCD:inelastic = on`, conforme também documentado pelo exemplo oficial `main327` do PYTHIA, e transporta as partículas diretamente para o Geant4 em memória. Logo, a configuração e a ponte de execução não são cópias do fluxo Lorenzetti.

Existem parâmetros comuns que devem permanecer rastreáveis:

- feixes de prótons `2212 + 2212` a 14 TeV;
- semente exemplar `512`, também presente em `mb.card`;
- nomes de ações que coincidem com interfaces padrão do Geant4.

Esses elementos, isoladamente, não formam um bloco de código copiado. A composição, o controle de pile-up Poisson, a política de sementes por trabalhador, a auditoria do gerador e a escrita ROOT foram implementados no projeto.

## 7. Classificação dos arquivos do projeto

| Grupo de arquivos | Classificação | Relação com Lorenzetti | Ação de proveniência |
|---|---|---|---|
| `src/Sampling.cc` | Parâmetros adaptados; implementação C++ própria | Deriva as tabelas de `ECAL.py` e `TILE.py` | Atribuição explícita e licença compatível |
| `include/Sampling.hh` | Implementação original | Modelo de dados criado para representar os samplings | Referenciar junto de `Sampling.cc` |
| `src/DetectorConstruction.cc` e cabeçalho | Implementação original | Mesmo papel conceitual e nomes padrão do Geant4; código e construção diferem | Citar influência arquitetural |
| `src/PrimaryGeneratorAction.cc` e cabeçalho | Implementação original | Geração direta Pythia→Geant4, diferente do adaptador Lorenzetti/HepMC | Nenhuma atribuição de código |
| `ActionInitialization`, `EventAction`, `RunAction` | Implementação original | Interfaces e nomes padrão do Geant4 | Nenhuma atribuição de código |
| `CalorimeterSD`, `EventState`, `LineageInfo`, `TrackingAction`, `RootOutput` | Implementação original | Pipeline de scoring, linhagem e ROOT próprio | Nenhuma atribuição de código |
| `CellSegmentation`, `ParticleDecision`, `SeedPolicy` e respectivos testes | Implementação original | Funcionalidades dos ciclos posteriores sem equivalente copiado no conjunto comparado | Nenhuma atribuição de código |
| `Configuration`, `app/main.cc`, arquivos `.conf` e `run.sh` | Implementação original | CLI de comando único inspirada no objetivo operacional, não no código Lorenzetti | Mencionar influência de workflow |
| `config/pythia_minbias.cmnd` | Configuração própria com parâmetros padrão | Feixes/energia comuns; processo diferente de `minbias_config.cmnd` | Citar PYTHIA e Lorenzetti como referências técnicas |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md` | Texto original | A relação com Lorenzetti já é declarada | Tornar a origem dos parâmetros mais específica |
| CMake, `BuildInfo.hh.in`, scripts e `.gitignore` | Implementação original | Nenhum bloco textual correspondente detectado | Nenhuma ação adicional |
| `PythiaGeantOneStage_V06.zip` | Snapshot próprio redundante | Seus 37 arquivos coincidem exatamente com os blobs do commit inicial `fd8b09f` | Remover antes da release para evitar duplicação |

## 8. Texto recomendado de atribuição

O seguinte aviso pode ser usado em `src/Sampling.cc` e desenvolvido em `THIRD_PARTY_NOTICES.md`:

> The detector sampling parameters in this file were derived from the Lorenzetti ATLAS geometry example, specifically `geometry/ATLAS/python/ECAL.py` and `TILE.py` at commit `5929bb15ff193bc63305f8201be7b2eb207d1557`. The parameters were converted to millimetres, simplified for direct Geant4 construction, and modified where documented. No Lorenzetti source file is included verbatim.

Referência científica obrigatória nas próximas etapas:

> M. V. Araújo et al., “Lorenzetti Showers - A general-purpose framework for
> supporting signal reconstruction and triggering with calorimeters,”
> *Computer Physics Communications* 286 (2023), 108671,
> DOI: <https://doi.org/10.1016/j.cpc.2023.108671>.

## 9. Decisão do Ciclo A1

O Ciclo A1 está tecnicamente concluído porque todos os 47 arquivos do inventário público receberam uma classificação de proveniência e o arquivo ZIP foi inspecionado.

Para preservar essa conclusão no repositório:

1. adicionar este relatório como `docs/PROVENANCE_AUDIT.md`;
2. remover `PythiaGeantOneStage_V06.zip` antes da release, preservando-o no histórico Git;
3. iniciar o Ciclo A2 com GNU GPL v3 como opção conservadora e compatível;
4. adicionar um aviso de origem em `src/Sampling.cc` sem atribuir ao Lorenzetti as partes implementadas originalmente neste projeto.

**Commit sugerido para registrar o A1:**

```text
docs: audit Lorenzetti provenance
```
