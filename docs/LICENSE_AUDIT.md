# Auditoria de licença e atribuição — Ciclo A2

**Projeto:** MinBias-Pythia-Geant4
**Data da auditoria:** 2026-08-08
**Commit de entrada:** `00ff4367599f149507ddebd851305826b2bcc6e2`
**Licença adotada:** `GPL-3.0-only`
**Resultado:** aprovado após a aplicação integral das alterações deste ciclo.

## 1. Objetivo

Definir uma licença explícita para o projeto, preservar a atribuição dos
parâmetros geométricos identificados no Ciclo A1 e verificar o tratamento das
dependências externas antes da primeira versão citável.

Este relatório é uma auditoria técnica de conformidade de software e não
substitui aconselhamento jurídico profissional.

## 2. Decisão de licenciamento

O código próprio do MinBias-Pythia-Geant4 será distribuído sob a **GNU General
Public License, version 3 only**, com o identificador SPDX
`GPL-3.0-only`.

A escolha é conservadora e coerente com três fatos:

1. o Lorenzetti declara publicamente a licença GNU GPL v3.0;
2. o Ciclo A1 não encontrou código-fonte do Lorenzetti copiado ou adaptado,
   mas identificou parâmetros geométricos derivados de `ECAL.py` e `TILE.py`;
3. o PYTHIA é disponibilizado sob GPL v2 ou posterior, o que permite optar
   pela versão 3 ao formar a combinação executável.

Não foi adotado `GPL-3.0-or-later`, pois a documentação do Lorenzetti
consultada não concede explicitamente a opção de versões posteriores.

## 3. Atribuição ao Lorenzetti

O arquivo `src/Sampling.cc` deve conter, antes dos includes:

- o identificador `SPDX-License-Identifier: GPL-3.0-only`;
- o titular e o ano do código deste projeto;
- os caminhos `geometry/ATLAS/python/ECAL.py` e `TILE.py`;
- o commit de referência `5929bb15ff193bc63305f8201be7b2eb207d1557`;
- a declaração de conversão, simplificação e modificação dos parâmetros;
- a declaração de que nenhum arquivo-fonte do Lorenzetti foi incluído
  literalmente.

Essa atribuição não transfere ao Lorenzetti a autoria da implementação C++,
da ponte PYTHIA→Geant4, do scoring, da linhagem ou da persistência ROOT.

A referência científica completa ao artigo *Lorenzetti Showers* será
consolidada no `THIRD_PARTY_NOTICES.md` e no `CITATION.cff` durante o
Ciclo A3.

## 4. Dependências e compatibilidade operacional

| Componente | Condição observada | Presença no repositório | Decisão para a versão-fonte |
|---|---|---|---|
| Lorenzetti | GNU GPL v3.0 | Nenhum arquivo-fonte; somente parâmetros derivados | Licença GPL v3 e atribuição específica |
| PYTHIA 8 | GNU GPL v2 ou posterior; diretrizes MCnet separadas | Não incorporado; localizado e ligado no ambiente do usuário | Compatível com GPL v3; manter como dependência externa |
| Geant4 | Geant4 Software License 1.0 | Não incorporado; localizado pelo CMake | Manter como dependência externa |
| ROOT | GNU LGPL v2.1 | Não incorporado; `root-config` é consultado apenas para proveniência quando disponível | Manter como dependência externa |
| CMake | BSD 3-Clause | Nenhum código do CMake incorporado | Ferramenta externa de construção |

O repositório e o futuro arquivo-fonte do Zenodo não redistribuem o código,
as bibliotecas ou os binários dessas dependências. Por isso, suas licenças não
devem ser copiadas para o arquivo `LICENSE` do projeto como se fossem uma
licença conjunta.

Se uma versão futura distribuir executáveis, bibliotecas, contêineres ou
pacotes que incluam dependências, será necessária uma auditoria específica do
artefato. Em particular, uma redistribuição do Geant4 deve preservar os avisos
e as condições da licença Geant4, e uma redistribuição de componentes LGPL
deve cumprir os requisitos aplicáveis da LGPL.

## 5. Arquivos alterados neste ciclo

| Arquivo | Ação | Finalidade |
|---|---|---|
| `LICENSE` | Adicionar o texto integral da GNU GPL v3 | Tornar explícitas as condições de distribuição |
| `src/Sampling.cc` | Adicionar cabeçalho SPDX e aviso de origem | Preservar licença e atribuição no ponto materialmente derivado |
| `README.md` | Adicionar seção “Licença e atribuição” | Informar usuários e redistribuidores |
| `docs/LICENSE_AUDIT.md` | Adicionar este relatório | Registrar a decisão e seu escopo |

Não é necessário inserir o aviso do Lorenzetti em todos os arquivos do
projeto, pois o Ciclo A1 localizou a relação material somente em
`src/Sampling.cc`. A aplicação sistemática de cabeçalhos SPDX a todos os
arquivos próprios pode ser feita futuramente, sem alterar a licença global já
estabelecida pelo `LICENSE` e pelo README.

## 6. Obrigações práticas

Ao redistribuir o código-fonte deste projeto:

1. manter o arquivo `LICENSE`;
2. manter os avisos de copyright, SPDX e atribuição;
3. marcar modificações relevantes e suas datas quando aplicável;
4. disponibilizar o código-fonte correspondente sob a mesma licença;
5. não apresentar o projeto como software oficial do ATLAS, do Lorenzetti,
   do PYTHIA, do Geant4 ou do ROOT.

As saídas científicas produzidas pela execução, como TTrees e arquivos ROOT,
não se tornam automaticamente GPL. A licença alcança a saída somente quando
o próprio conteúdo da saída constituir uma obra coberta pela licença.

## 7. Limite da aprovação

O Ciclo A2 aprova a **release de código-fonte**. Ele não aprova
automaticamente:

- imagens de contêiner;
- pacotes binários;
- distribuições que incorporem PYTHIA, Geant4 ou ROOT;
- dados ou geometrias adicionais de terceiros;
- uso de marcas ou logotipos de terceiros.

Esses casos exigem nova verificação do artefato efetivamente distribuído.

## 8. Validação antes do commit

Após aplicar as alterações, executar:

```bash
test -f LICENSE
grep -n "GPL-3.0-only" README.md src/Sampling.cc docs/LICENSE_AUDIT.md
grep -n "5929bb15ff193bc63305f8201be7b2eb207d1557" \
  README.md src/Sampling.cc docs/LICENSE_AUDIT.md
git diff --check
git status --short
```

Como as mudanças são documentais e um comentário C++, não alteram o
comportamento do executável. Ainda assim, o teste de regressão pode ser
repetido:

```bash
ctest --test-dir build-v0 --output-on-failure
```

## 9. Critério de encerramento

O Ciclo A2 estará encerrado quando:

- `LICENSE` existir com o texto integral da GPL v3;
- `src/Sampling.cc` contiver o aviso específico;
- o README declarar `GPL-3.0-only`;
- este relatório estiver versionado;
- `git diff --check` e os testes existentes forem aprovados;
- o commit for publicado sem alterações não relacionadas.

**Commit sugerido:**

```text
legal: adopt GPL-3.0-only and preserve attribution
```
