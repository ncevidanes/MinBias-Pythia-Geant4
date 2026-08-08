# Auditoria técnica e protocolo de fechamento — Ciclo A4

**Projeto:** MinBias-Pythia-Geant4

**Data da preparação:** 2026-08-08

**Commit de entrada:** `685988d8eb7d8f9f34f2de0e2d92a00aa0083b10`

**Versão-alvo:** `0.1.0`

## 1. Objetivo

Definir uma candidata tecnicamente auditável para a primeira release, eliminar
artefatos que não pertencem ao código-fonte e transformar as verificações dos
ciclos anteriores em testes e scripts reproduzíveis.

O A4 aprova a infraestrutura técnica do simulador. Ele não certifica que a
geometria simplificada reproduz a resposta física completa do ATLAS; essa
afirmação exigiria a campanha de partículas únicas descrita em
`docs/VALIDATION.md`.

## 2. Achados da revisão estática

### 2.1 Arquivo ZIP redundante

`PythiaGeantOneStage_V06.zip` era uma fotografia do commit inicial já contido
no próprio histórico Git. Sua permanência duplicaria código antigo dentro do
arquivo-fonte da release. O arquivo foi removido da candidata e `/*.zip` passou
a ser ignorado na raiz.

### 2.2 Higiene da árvore de trabalho

O `.gitignore` original reconhecia apenas `build/`. A candidata passa a ignorar
diretórios `build*`, saídas ROOT, manifestos, logs, patches, caches Python,
registros `cycle*.txt` e ZIPs de raiz. Isso cobre os artefatos observados nos
ciclos de desenvolvimento sem excluir configurações científicas por padrão.

### 2.3 Validação de configuração

O parser C++ e o pré-validador Python aceitavam chaves desconhecidas. Um erro de
digitação em um parâmetro opcional poderia, portanto, ativar silenciosamente o
valor padrão. O parser C++ também aceitava sufixos numéricos após um prefixo
válido, e alguns valores não finitos ou sigmas negativos não eram rejeitados.

A candidata:

- rejeita chaves não declaradas;
- exige conversão integral do texto numérico;
- rejeita `NaN` e infinitos;
- exige sigmas do feixe não negativos;
- protege o intervalo inteiro de BCIDs;
- ignora linhas comentadas ao verificar os comandos obrigatórios do PYTHIA;
- acrescenta o teste CTest `configuration`.

### 2.4 Verificação ROOT

`scripts/inspect_root.C` não mostrava a TTree `metadata`, embora ela fizesse
parte do contrato documentado. A candidata inclui `metadata` na inspeção rápida
e acrescenta `scripts/audit_root.C`, que verifica:

- presença e esquema exato das quatro TTrees;
- uma única entrada e 34 branches em `metadata`;
- versão do esquema, versão do projeto, commit, estado limpo e versões das
  dependências;
- uma entrada de `events` por bunch crossing configurado;
- contabilidade de interações, partículas e rejeições;
- ausência de passos sem linhagem e falhas de segmentação;
- validade dos identificadores e índices de células;
- vínculo de hits e partículas do gerador aos eventos e subeventos;
- igualdade entre `events.total_edep_mev` e a soma dos hits;
- coerência entre `generator_audit` e o número de registros do gerador.

`scripts/compare_root.C` compara duas execuções entrada a entrada e branch a
branch, incluindo strings de `metadata`.

## 3. Auditoria integrada

`scripts/audit_release.sh` deve ser executado no ambiente com PYTHIA, Geant4 e
ROOT. Ele recusa alterações rastreadas não commitadas e então:

1. registra o SHA e as versões das ferramentas;
2. valida todas as configurações versionadas;
3. realiza um build limpo em diretório novo;
4. executa os quatro testes CTest;
5. verifica a ajuda da CLI e dry runs de smoke e produção reduzida;
6. executa duas simulações smoke com o mesmo caminho lógico, configuração,
   semente e uma thread;
7. audita os dois ROOTs e exige manifestos idênticos;
8. compara exatamente as quatro TTrees;
9. inspeciona `git archive` e rejeita builds, outputs, ROOTs, manifestos e ZIPs;
10. grava todas as evidências em um diretório novo sob `outputs/`.

Execução:

```bash
./scripts/audit_release.sh
```

O número de processos de compilação pode ser reduzido em máquinas com pouca
memória:

```bash
BUILD_JOBS=1 ./scripts/audit_release.sh
```

## 4. Critério de aprovação

O A4 somente está aprovado quando o log contém os três marcadores:

```text
AUDIT_RESULT=PASS
COMPARE_RESULT=PASS
A4_RESULT=PASS commit=<SHA de 40 caracteres>
```

O SHA deve:

- coincidir com `HEAD` e `origin/master`;
- aparecer em `metadata.git_commit`;
- ser exatamente o commit que receberá a tag `v0.1.0` no Ciclo A5.

Se qualquer correção posterior criar um novo commit, a auditoria completa deve
ser repetida. A tag não pode apontar para um commit que não tenha produzido um
`A4_RESULT=PASS`.

## 5. Limite da aprovação

A aprovação técnica cobre build, testes de unidade, configuração, execução
smoke, integridade do ROOT, proveniência e reprodutibilidade para uma thread.
Ela não autoriza descrever a versão como geometria oficial do ATLAS nem como
resposta calorimétrica calibrada. Antes da produção de 3.000 bunch crossings ou
de conclusões de física, permanece obrigatória a validação com elétrons,
fótons e píons em energias controladas, além do estudo de production cuts.
