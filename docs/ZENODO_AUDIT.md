# Auditoria de arquivamento e DOI no Zenodo — Ciclo A6

**Projeto:** MinBias-Pythia-Geant4

**Data da auditoria:** 2026-08-13

**Commit-base da documentação:** `4da9b77f6832cd2de9670d7b8a00312bbeb4a23b`

**Release auditada:** `v0.1.0`

**Commit arquivado:** `19a3c12c071aa9db0fc2a9bc5a554bd8ecd1d052`

**Resultado:** aprovado após a aplicação e validação das alterações deste ciclo.

## 1. Objetivo

Encerrar o fluxo de publicação da primeira release com identificadores
persistentes verificáveis, registrar a relação entre GitHub e Zenodo e
substituir a referência provisória do software por uma citação definitiva.

Esta auditoria documenta um objeto já publicado. Ela não altera a tag
`v0.1.0`, o commit arquivado nem o arquivo depositado no Zenodo.

## 2. Identificadores persistentes

| Papel | Identificador | Destino |
|---|---|---|
| DOI conceitual | `10.5281/zenodo.21862454` | coleção de versões do projeto |
| DOI da versão | `10.5281/zenodo.21862455` | registro imutável de `v0.1.0` |
| Registro Zenodo | `21862455` | metadados e arquivo da versão |
| Tag Git | `v0.1.0` | commit `19a3c12c071aa9db0fc2a9bc5a554bd8ecd1d052` |

O DOI específico da versão deve ser usado quando a reprodutibilidade exigir a
identificação exata de `v0.1.0`. O DOI conceitual deve ser usado quando a
referência for ao projeto e à sua versão mais recente.

## 3. GitHub Release

A release pública foi conferida com os seguintes dados:

| Campo | Valor |
|---|---|
| Repositório | `ncevidanes/MinBias-Pythia-Geant4` |
| Tag | `v0.1.0` |
| Commit da tag | `19a3c12c071aa9db0fc2a9bc5a554bd8ecd1d052` |
| Publicação | `2026-08-09T15:46:20Z` |
| Estado | publicada; não é rascunho nem pré-release |
| URL | `https://github.com/ncevidanes/MinBias-Pythia-Geant4/releases/tag/v0.1.0` |

## 4. Registro Zenodo

Os metadados públicos do registro `21862455` foram conferidos pela interface e
pela API do Zenodo:

| Campo | Valor verificado |
|---|---|
| Título | `MinBias-Pythia-Geant4` |
| Criador | `Assis, Nelson Cevidanes Nascimento` |
| Versão | `v0.1.0` |
| Data de publicação | `2026-08-09` |
| Tipo de recurso | Software |
| Acesso | aberto |
| Publicador | Zenodo |
| Licença exibida | GNU General Public License v3.0 only |
| Identificador de licença na API | `gpl-3.0` (identificador legado do registro) |
| DOI da versão | `10.5281/zenodo.21862455` |
| DOI conceitual | `10.5281/zenodo.21862454` |

A licença exibida publicamente coincide com `GPL-3.0-only`, declarado no
`CITATION.cff` e no arquivo `LICENSE`. A API serializa o identificador legado
`gpl-3.0`; a interface do registro explicita o significado como GNU General
Public License v3.0 only.

## 5. Arquivo depositado

O registro contém um único arquivo:

| Campo | Valor |
|---|---|
| Nome | `ncevidanes/MinBias-Pythia-Geant4-v0.1.0.zip` |
| Tamanho | 88.724 bytes |
| Checksum | `md5:bb23d404eacdb798e88cdcbd49a97ee3` |

O arquivo pertence ao registro da versão e permanece associado ao DOI
`10.5281/zenodo.21862455`. O checksum permite detectar alteração dos bytes
depositados.

## 6. Cadeia de identidade

A cadeia auditada é:

```text
DOI conceitual 10.5281/zenodo.21862454
  -> versão 10.5281/zenodo.21862455
  -> registro Zenodo 21862455
  -> MinBias-Pythia-Geant4-v0.1.0.zip
  -> tag GitHub v0.1.0
  -> commit 19a3c12c071aa9db0fc2a9bc5a554bd8ecd1d052
```

O registro Zenodo também aponta para o repositório de código e para a árvore da
tag `v0.1.0` como trabalho relacionado.

## 7. Política de citação

A citação recomendada para a versão auditada é:

> Assis, N. C. N. (2026). *MinBias-Pythia-Geant4* (Version v0.1.0)
> [Computer software]. Zenodo.
> <https://doi.org/10.5281/zenodo.21862455>

A citação do software não substitui a referência ao artigo *Lorenzetti
Showers* quando os parâmetros derivados da geometria forem relevantes. O DOI
do artigo permanece `10.1016/j.cpc.2023.108671`.

## 8. Escopo temporal

O depósito auditado representa somente o conteúdo da tag `v0.1.0`. Alterações
posteriores presentes na `master`, incluindo a infraestrutura de partículas
únicas e a campanha estatística do Ciclo 6.4, não fazem parte desse arquivo.
Elas deverão integrar uma versão futura, após nova auditoria de release.

## 9. Alterações documentais do A6

| Arquivo | Ação | Finalidade |
|---|---|---|
| `CITATION.cff` | atualizar | registrar data, DOI conceitual, DOI da versão e artefato |
| `README.md` | atualizar | publicar badge DOI e substituir a citação provisória |
| `docs/ZENODO_AUDIT.md` | adicionar | preservar a cadeia de publicação e os achados da auditoria |

## 10. Validação

Após aplicar as alterações, devem ser verificados:

- sintaxe e esquema CFF 1.2.0;
- versão `0.1.0` e data `2026-08-09`;
- presença dos dois DOI no CFF, README e nesta auditoria;
- licença `GPL-3.0-only` no CFF;
- manutenção da referência ao artigo do Lorenzetti;
- inexistência de alterações em código-fonte, testes ou configuração;
- `git diff --check` sem erros.

Os testes de regressão permanecem obrigatórios antes da publicação do commit,
embora o A6 tenha escopo exclusivamente documental.

## 11. Critério de encerramento

O Ciclo A6 estará encerrado quando:

- os três arquivos documentais forem validados e versionados;
- o commit for publicado em branch própria;
- o pull request for revisado e mesclado na `master`;
- a `master` local e remota apontarem para o mesmo commit;
- os oito arquivos locais anteriormente não rastreados permanecerem fora do
  escopo do commit.

Nenhuma nova tag ou versão Zenodo deve ser criada para este ciclo documental.
