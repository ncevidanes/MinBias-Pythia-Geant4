# Ciclo 14.1: registro do fechamento do gate

## Decisão

O responsável pelo projeto declarou em 2026-11-26 que o gate de congelamento
do Ciclo 14.1 passou (decisão D2 de `docs/plano-reorganizacao.md`). Com isso,
a regra "Production authorization rule" de `physics-contract.md` está
satisfeita, e a produção nominal de minimum bias está autorizada no commit
abaixo.

Commit autorizado: `51240a8641426e8f4a48cac49da0a8accbb97224`
(tag `cycle-14.1-pre-reorganization`).

## Por que `physics-contract.md` não foi editado

`physics-contract.md` ainda se declara "freeze candidate". O arquivo consta de
`evidence/freeze-candidate-artifacts.sha256`, e editá-lo quebraria esse
inventário. Por isso ele fica como está, e este arquivo registra o fechamento.
Quem lê o contrato deve ler este registro em conjunto.

## Evidência existente no commit autorizado

Gerada no Ciclo 14.1 e não reexecutada neste registro:

- `evidence/production-contract-ctest.txt`: 13 testes, 0 falhas, 148,44 s;
- `evidence/production-dry-run.txt`: dry-run de `config/production.conf`
  concluído com `FTFP_BERT_ATL`, sem simulação;
- `evidence/environment.txt`: PYTHIA 8.312, Geant4 11.3.2, ROOT 6.36.06,
  CMake 4.2.3.

## Verificação feita em 2026-11-27

No checkout de `51240a8`, a partir da raiz do repositório:

```bash
sha256sum -c docs/cycle-14-minimum-bias-physics-production/evidence/physics-contract-files.sha256
sha256sum -c docs/cycle-14-minimum-bias-physics-production/evidence/freeze-candidate-artifacts.sha256
```

Resultado: todas as 19 entradas do primeiro inventário e as 5 do segundo
estão `OK`. CTest e dry-run não foram reexecutados nesta verificação.

## Validade

A autorização vale para os 19 arquivos com os hashes do inventário. Qualquer
mudança em um deles, inclusive `app/main.cc` no PR 15.7 previsto no plano,
exige nova revisão do contrato antes de outra produção.
