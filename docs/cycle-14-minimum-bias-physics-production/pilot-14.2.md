# Ciclo 14.2: piloto controlado de minimum bias

## Resultado

Aprovado. 100 BCs da configuração nominal, na tag
`cycle-14.1-pre-reorganization` (`51240a8`), executados em 2026-11-27:

| Verificação | Resultado |
|---|---|
| `audit_root.C` nos três arquivos | PASS, schema 4 |
| Partição: monolítico (BC 0 a 99) contra shards A (0 a 49) e B (50 a 99) | PASS: `events` e `hits` idênticos bit a bit; metadados iguais fora de `OPERATIONAL_METADATA` |
| Repetição do shard B (duas execuções independentes) | `events` e `hits` idênticos bit a bit |
| Contadores de falha por BC | zero em todos os 100 BCs |
| Pile-up | compatível com Poisson de μ = 50 |

O piloto não muda nenhum arquivo do contrato. Os 19 hashes de
`evidence/physics-contract-files.sha256` conferem no checkout usado.

## Configuração

Binário compilado na tag com `./run.sh config/production.conf --dry-run`, que
reconfigura o CMake e grava `git_commit = 51240a8...`. O dry-run saiu idêntico
a `evidence/production-dry-run.txt` a partir da inicialização do Geant4.
Ambiente igual ao de `evidence/environment.txt`: PYTHIA 8.312, Geant4 11.3.2,
ROOT 6.36.06, CMake 4.2.3, `threads = 1`.

| Arquivo | Comando | BCs |
|---|---|---|
| `monolithic.root` | `--config config/production.conf --events 100` | 0 a 99 |
| `shard-a.root` | `--config config/production.conf --events 50` | 0 a 49 |
| `shard-b.root` | `--config shard-b.conf` | 50 a 99 |

`shard-b.conf` difere de `production.conf` só em `events`, `first_bcid`,
`output` e no caminho absoluto de `pythia_config`, que aponta para o mesmo
`config/pythia_minbias.cmnd`, como no piloto de schema 4 do Ciclo 11. Os BCs
0 a 99 são os primeiros da produção nominal, porque a semente é event-stable
por BCID.

## Comparação de partição

O `scripts/analyze_partition_root.py` do Ciclo 11 carrega todas as linhas em
memória. Com 19,7 milhões de hits de cada lado, ele ficou horas sem saída numa
máquina de 6 GB e foi interrompido. A comparação foi feita com
`evidence/pilot-14.2/scripts/compare_partition_stream.py`, que lê em blocos
com uproot e aplica a mesma regra: árvores científicas bit a bit, com `run` e
`event` excluídos como em `GLOBAL_FIELDS`, e metadados iguais fora de
`OPERATIONAL_METADATA`.

Validação desse comparador:

- no piloto de schema 4 do Ciclo 11 (`outputs/cycle11-partition-schema4-pilot`),
  ele e o `analyze_partition_root.py` dão PASS;
- com a ordem dos shards trocada, ele dá FAIL e aponta os branches que
  diferem nas três árvores.

Diferença de método: o comparador do Ciclo 11 indexa as linhas pelas chaves
globais (`bcid`, `subevent`, `cell_id` em `hits`), e a ordem não importa;
este compara na ordem de gravação, o que é mais estrito e vale porque
`threads = 1`.

## Execução substituída do shard B

A primeira execução do shard B usou uma cópia de `pythia_minbias.cmnd` em
outra pasta. O conteúdo era o mesmo (SHA-256 `f746771d...`), mas o caminho
gravado em `pythia_config` diferia, e a comparação deu FAIL só nesse campo.
O shard B foi refeito apontando para o arquivo original. A execução antiga
está em `outputs/cycle14-2-pilot/superseded/`, com hash em
`artifacts.sha256`, e serviu de teste de repetibilidade: as árvores das duas
execuções são idênticas bit a bit.

## Física, por BC (monolítico, 100 BCs)

| Grandeza | Média | Desvio-padrão | Mín. | Máx. |
|---|---|---|---|---|
| Interações geradas | 49,77 | 6,5 | 39 | 66 |
| Partículas do gerador | 27 423 | 5 382 | 16 810 | 38 804 |
| Partículas transportadas | 2 717 | 568 | 1 574 | 3 890 |
| Energia depositada (GeV) | 327,8 | 74,8 | 174,5 | 483,5 |

Pile-up: a média de 49,77 dá pull de -0,33 em relação a μ = 50. A razão
variância/média é 0,841; para Poisson com 100 BCs, o desvio-padrão dessa
razão é sqrt(2/99) = 0,142, então o valor está a -1,12 sigma de 1.

`generation_failures`, `unknown_pdg_particles`, `unlineaged_steps` e
`segmentation_failures` são zero em todos os BCs. A árvore `generator` está
vazia porque `generator_audit = false` na configuração nominal.

## Mensagens do PYTHIA

Apareceram `BeamRemnants::setKinematics`, `SimpleSpaceShower::pT2nearThreshold`
e avisos de `SimpleSpaceShower` e `MultipartonInteractions::init`
(`evidence/pilot-14.2/pythia-messages.txt`). O PYTHIA imprime cada mensagem
só na primeira ocorrência, e `app/main.cc` não chama `pythia.stat()`, então o
log não dá a frequência. O indicador de perda é `generation_failures`, que é
zero. Medir a frequência exigiria mudar `app/main.cc`, que está no contrato.

## Recursos e estimativa para a produção

| Execução | CPU (s) | Parede | Memória máx. | Concorrência |
|---|---|---|---|---|
| monolítico, 100 BCs | 10 440 | 2:54:28 | 184 MB | 3 processos por 1h55, depois só |
| shard A, 50 BCs | 6 879 | 1:55:07 | 184 MB | 3 processos |
| shard B, 50 BCs | 4 332 | 1:12:23 | 196 MB | sozinho |
| shard B substituído, 50 BCs | 6 733 | 1:52:43 | 174 MB | 3 processos |

As duas execuções do shard B fazem o mesmo trabalho, bit a bit, e diferem em
55% de CPU: a concorrência infla o tempo nesta máquina. A melhor medida é o
shard B sozinho, 87 s por BC; o monolítico, com concorrência em parte da
execução, dá 104 s. Para 3000 BCs com `threads = 1`, a estimativa fica entre
72 h e 87 h (3 a 3,6 dias), desde que a produção rode sem outros processos
pesados. Tamanho: 12,0 MB por BC, cerca de 36 GB.

## Evidência

`evidence/pilot-14.2/`:

- `artifacts.sha256`: ROOT e manifestos, inclusive o shard B substituído;
- manifestos dos três arquivos, `shard-b.conf` e `shard-b-superseded.conf`;
- `partition.json`, `repeat-shard-b.json`, `physics-summary.json`;
- `timing.txt`, `pythia-messages.txt`;
- `scripts/`: execução, comparação e resumo físico.

Os ROOT (2,4 GB) não estão no repositório. Ficam em
`outputs/cycle14-2-pilot/` no disco de trabalho, conferíveis por
`artifacts.sha256`.
