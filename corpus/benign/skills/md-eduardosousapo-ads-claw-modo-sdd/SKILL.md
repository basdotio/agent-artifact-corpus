---
name: modo-sdd
description: "Ativa o Modo SDD (Spec-Driven Development) para orientar o processo de desenvolvimento e criação de projetos de forma guiada, estruturada, ágil e segura."
---

# Modo-SDD (Spec-Driven Development)

## Visão Geral
Você está atuando no Modo SDD. O Spec-Driven Development (SDD) é uma abordagem onde a **especificação** orienta centralmente o processo de construção antes do código ser escrito. O objetivo é evitar improviso (*vibe coding*), reduzir ambiguidade, mitigar *drift* de arquitetura e evitar retrabalho estrutural.

A metodologia baseia-se em planejar, especificar e documentar todas as etapas da solução de software antes de implementá-la, proporcionando previsibilidade para o trabalho e permitindo que o desenvolvimento guiado por IA seja significativamente mais eficiente.

## Regras de Ouro
1. **Pense, Planeje e Especifique ANTES de codar.** Nenhuma implementação isolada ou componente oficial do projeto deve ser codificada sem que os artefatos base estejam validados pelo usuário.
2. **Siga o fluxo rigorosamente:** `Ideia/Intenção -> PRD -> SPEC -> PLAN -> TASKS -> Implementação Guiada -> Validação`.
3. Utilize os templates localizados na pasta `assets/` para gerar os documentos (PRD, SPEC, PLAN, TASKS, RULES).
4. Mantenha os arquivos teóricos e referências na pasta `references/` e estimule sua leitura caso haja divergências conceituais.
5. Qualquer código gerado por essa skill para auditar ou gerenciar o próprio processo SDD deve ficar na pasta `scripts/`.

## Fluxo Ágil e Guiado (Workflow)

Ao assumir o Modo SDD, você DEVE transitar com o usuário pelas seguintes etapas. **Não pule etapas** a menos que o usuário exija explicitamente.

### Passo 1: Entendimento e Intenção (PRD)
- Questione o usuário sobre a ideia principal, o problema a resolver, para quem é destinado e o porquê da importância (O quê e Por quê).
- Gere e preencha o documento `PRD.md` (Product Requirements Document) usando o template aplicável.
- Valide esse artefato junto ao usuário.

### Passo 2: Criação da Especificação (SPEC)
- Traduza a intenção em comportamento esperado, regras de negócio funcionais/não funcionais, casos de uso, critérios de aceite, casos de borda e limitações de escopo.
- Gere o documento `SPEC.md`.
- Solicite a validação do usuário.

### Passo 3: Plano Técnico (PLAN)
- Após a Spec, crie o planejamento técnico do *como* será construído (Stack escolhida, arquitetura, design do BD, contratos de API, autenticação, etc.).
- Gere o documento `PLAN.md` e o `RULES.md` (regras e convenções gerais).
- Valide os riscos e definições arquiteturais.

### Passo 4: Quebra em Tarefas Executáveis (TASKS)
- Quebre o plano técnico em **tarefas muito pequenas e executáveis**.
- Estabeleça ordem de execução, rastreio de dependências e checkpoints de validação.
- Gere o arquivo `TASKS.md`.

### Passo 5: Implementação Guiada
- Siga estritamente o `TASKS.md`. Codifique uma etapa por vez.
- Consulte `SPEC.md` e `PLAN.md` constantemente para evitar divagações (*drift*).
- **Sob nenhuma hipótese** adicione lógicas ou extensões não mapeadas sem antes reavaliar a Spec.

### Passo 6: Validação Contra a Spec
- Ao final de um ciclo de tarefas, verifique se a funcionalidade não apenas executa sem erros, mas se cumpre os **Critérios de Aceite** e respeita as **Regras de Negócio/Restrições** declaradas no `SPEC.md`.

## Scripts Utilitários
- O arquivo `scripts/validate_sdd.ps1` ou `scripts/validate_sdd.sh` pode ser utilizado para auditar se os arquivos de SDD básicos foram de fato criados no diretório do projeto. Acione quando apropriado.

## Triggers (Gatilhos)
Responda de imediato ao estilo SDD caso encontre palavras ou comandos como:
* "Ative o modo SDD"
* "Vamos iniciar um app usando metodologias de spec"
* "Crie um projeto usando SDD"
* "Metodologia spec-driven"
* "Gere a documentação base do meu projeto"
