# Auditoria de documentação científica e citação — Ciclo A3

**Projeto:** MinBias-Pythia-Geant4

**Data da auditoria:** 2026-08-08

**Commit de entrada:** `ba67313680755bfaf7593921f1df1f1721176e04`

**Versão-alvo:** `0.1.0`

**Resultado:** aprovado após a aplicação integral e a validação das alterações
deste ciclo.

## 1. Objetivo

Tornar explícitos os metadados de citação do software, separar a autoria do
projeto das referências científicas que o fundamentam e consolidar os avisos
de material de terceiros antes da primeira release arquivada.

## 2. Decisão de citação

O objeto principal de citação é o próprio software **MinBias-Pythia-Geant4**,
de autoria de Nelson Cevidanes Nascimento de Assis. O artigo *Lorenzetti
Showers* é registrado como referência relacionada porque fundamenta os
parâmetros geométricos identificados nos Ciclos A1 e A2; seus autores não são
apresentados como autores deste software.

O `CITATION.cff` usa o esquema CFF 1.2.0 e declara:

- título e tipo do objeto;
- autor e contato;
- versão `0.1.0`, já coerente com `CMakeLists.txt` e `VERSION`;
- repositório de código;
- licença `GPL-3.0-only`;
- resumo e palavras-chave;
- referência completa ao artigo do Lorenzetti, com DOI
  `10.1016/j.cpc.2023.108671`.

## 3. Campos deliberadamente adiados

Não foram inventados metadados ainda inexistentes:

- `date-released` será acrescentado no Ciclo A5 com a data efetiva da release;
- os DOI conceitual e específico da versão serão acrescentados no Ciclo A6;
- ORCID e afiliação permanecerão ausentes até serem confirmados pelo autor.

A ausência desses campos opcionais não invalida o CFF nem impede que o GitHub
apresente a função “Cite this repository”.

## 4. Avisos de terceiros

`THIRD_PARTY_NOTICES.md` registra:

1. os parâmetros derivados de `ECAL.py` e `TILE.py` do Lorenzetti;
2. o commit upstream usado na auditoria;
3. as transformações realizadas e os componentes implementados originalmente;
4. a referência científica completa;
5. PYTHIA, Geant4, ROOT e CMake como dependências externas;
6. o limite da aprovação para uma release de código-fonte;
7. a inexistência de vínculo oficial com ATLAS, CERN ou os projetos citados.

O documento não incorpora nem substitui licenças de terceiros. Uma futura
distribuição binária, imagem de contêiner ou pacote com dependências deverá
passar por auditoria própria.

## 5. Atualização do README

O README passa a:

- apontar para as auditorias e avisos de terceiros;
- fornecer uma referência provisória antes do DOI;
- explicar que o DOI específico da versão substituirá a URL do repositório
  após o arquivamento;
- distinguir a citação do software da citação do artigo do Lorenzetti;
- ligar diretamente o artigo e seu DOI na seção de referências técnicas;
- corrigir em `docs/PROVENANCE_AUDIT.md` a autoria bibliográfica que havia sido
  atribuída incorretamente a J. H. B. de Carvalho et al.

## 6. Arquivos deste ciclo

| Arquivo | Ação | Finalidade |
|---|---|---|
| `CITATION.cff` | adicionar | fornecer metadados estruturados de citação |
| `THIRD_PARTY_NOTICES.md` | adicionar | consolidar atribuições e dependências externas |
| `README.md` | atualizar | documentar como citar e tornar os avisos localizáveis |
| `docs/PROVENANCE_AUDIT.md` | corrigir | registrar M. V. Araújo et al. como autores do artigo do Lorenzetti |
| `docs/CITATION_AUDIT.md` | adicionar | registrar decisões, validações e pendências |

## 7. Validação

Após aplicar o patch, executar:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("CITATION.cff").read_text(encoding="utf-8"))
required = {"cff-version", "message", "title", "authors"}
missing = sorted(required - data.keys())
if missing:
    raise SystemExit("campos CFF ausentes: " + ", ".join(missing))
if data["cff-version"] != "1.2.0":
    raise SystemExit("versão CFF inesperada")
if data.get("version") != Path("VERSION").read_text().strip():
    raise SystemExit("CITATION.cff e VERSION divergem")
if data.get("license") != "GPL-3.0-only":
    raise SystemExit("licença CFF inesperada")
print("CITATION.cff: YAML e metadados básicos válidos")
PY

grep -n "10.1016/j.cpc.2023.108671" \
  CITATION.cff THIRD_PARTY_NOTICES.md README.md \
  docs/PROVENANCE_AUDIT.md docs/CITATION_AUDIT.md

grep -n "GPL-3.0-only" \
  CITATION.cff THIRD_PARTY_NOTICES.md README.md docs/CITATION_AUDIT.md

git diff --check
ctest --test-dir build-v0 --output-on-failure
```

Além dessas verificações portáveis, o arquivo deve ser validado contra o
esquema oficial Citation File Format 1.2.0 antes do commit.

## 8. Critério de encerramento

O Ciclo A3 estará encerrado quando:

- o `CITATION.cff` passar pela validação do esquema CFF 1.2.0;
- título, autor, versão, licença e repositório estiverem coerentes;
- o DOI do Lorenzetti constar nos cinco arquivos previstos;
- `THIRD_PARTY_NOTICES.md` estiver versionado;
- o README explicar a citação anterior e posterior ao DOI;
- `git diff --check` e os testes de regressão forem aprovados;
- o commit for publicado sem alterações não relacionadas.

**Commit sugerido:**

```text
docs: add citation metadata and third-party notices
```
