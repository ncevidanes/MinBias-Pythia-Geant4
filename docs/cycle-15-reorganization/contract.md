# Ciclo 15: contrato de equivalência da reorganização

Os PRs 15.1 a 15.6 de `docs/plano-reorganizacao.md` reorganizam o repositório
sem mudar a física. Este contrato fixa como essa equivalência é provada. O
texto abaixo reproduz a seção 5 do plano; se os dois divergirem, vale este
arquivo.

Referência A: tag `cycle-14.1-pre-reorganization` (`51240a8`).

Além disso, pela decisão D4, todo PR que toca a execução refaz um subconjunto
de BCIDs da produção nominal feita na tag e o compara com o arquivo de
produção usando `scripts/analyze_partition_root.py`.

## Critério de aceite

1. Referência A: build da tag. Candidato B: build do head de cada PR. Os dois
   são construídos e executados no mesmo caminho absoluto (um worktree
   reaproveitado), na mesma máquina, com o ambiente registrado como em
   `environment.txt`. Assim `config_file`, `output_file`, `pythia_config` e
   `normalized_config` coincidem.
2. Casos executados com `pythia_geant` diretamente, com os mesmos argumentos
   em A e B:
   - C1: `config/smoke.conf`;
   - C2: `config/production.conf --events 20 --mu 50`;
   - C3: C2 com `--threads 2`, apenas em B, comparado com o C2 de A;
   - C4: `config/single_particle.conf`;
   - C5: arquivo `.conf` temporário em `outputs/`, com sigmas de feixe não
     nulos e `first_bcid = 100`, para exercitar os caminhos que a
     configuração nominal zera.

   Em B, cada caso também é executado via `minbias run` e precisa dar
   resultado idêntico ao da chamada direta.
3. `scripts/compare_root.C`: `events`, `hits` e `generator` idênticos bit a
   bit. Hoje o script compara `metadata` inteira, e `git_commit` e
   `git_describe` diferem por construção, então falharia sempre. O PR 15.1
   acrescenta um terceiro argumento opcional com os branches de `metadata` a
   excluir; o padrão vazio mantém o comportamento usado por
   `audit_release.sh`. Exclusões permitidas: `{git_commit, git_describe}`;
   em C3, também `threads`, como em `OPERATIONAL_METADATA` do Ciclo 11; em
   C4, depois que o `.conf` mudar de pasta, também `config_file` e
   `normalized_config`, com o manifesto comparado sem a linha `config =`.
   `VERSION` não muda nesses PRs.
4. `scripts/audit_root.C(arquivo, commit)` com `AUDIT_RESULT=PASS` para todos
   os arquivos, de A e de B.
5. Manifestos idênticos com `diff -u`.
6. CSVs do `single_particle_analyzer` sobre C4 idênticos byte a byte.
7. `sha256sum -c physics-contract-files.sha256` aprovado em todo PR fora do
   15.7.
8. CTest com zero falhas e contagem declarada no PR. Contagem de unidades do
   lightweight e baseline de cobertura atualizadas deliberadamente quando
   mudarem.

Hashes dos ROOT, logs e resultados ficam em
`docs/cycle-15-reorganization/evidence/`, no formato dos ciclos anteriores.
