---
name: create-pr
description: "Cria um Pull Request padronizado com título, descrição e documentação detalhada de cada commit. Use quando for abrir um PR, quando o usuário pedir 'abre o PR', 'cria o PR', 'make a PR', 'open pull request'."
user-invocable: true
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git show:*), Bash(git status:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(gh pr create:*), Bash(gh pr view:*)
---

# Skill: Criar Pull Request Padronizado

## Descrição

Gera um PR com título objetivo, descrição de contexto e documentação detalhada de cada commit — incluindo ID, mensagem e o que foi adicionado/modificado naquele commit específico.

---

## Processo obrigatório

### Passo 1 — Identifique o branch base e o range de commits

```bash
git branch --show-current           # branch atual
git rev-parse --abbrev-ref HEAD     # confirma o branch
git log main...HEAD --oneline       # commits que serão incluídos no PR
```

Se não houver commits além do `main`, pare e avise o usuário.

### Passo 2 — Analise cada commit individualmente

Para cada commit listado no Passo 1, execute:

```bash
git show <commit-hash> --stat       # arquivos alterados e volume de mudanças
git show <commit-hash> -p           # diff completo
```

Entenda **o que cada commit faz** antes de escrever qualquer coisa.

### Passo 3 — Identifique as issues fechadas por este PR

Execute para ver as issues abertas relacionadas ao escopo do PR:

```bash
gh issue list --repo <owner>/<repo> --state open
```

Inspecione os commits e o nome da branch para identificar quais issues este PR resolve. Regras:
- Se o PR implementa uma US específica (ex: US-004), procure a issue correspondente (`[US-004]`) e inclua `Closes #N`
- Se o PR fecha múltiplas issues, inclua uma linha `Closes #N` por issue
- Se nenhuma issue se aplica, omita a seção — **nunca invente ou assuma issues**
- Em caso de dúvida, pergunte ao usuário: "Este PR fecha alguma issue específica?"

### Passo 4 — Monte o corpo do PR

Use o template abaixo. Preencha com base na análise dos commits.

---

## Template do PR

```markdown
## Descrição

<Resumo em 2–4 frases sobre o objetivo geral do PR. O que foi implementado? Por que? Qual problema resolve?>

---

## Closes

Closes #N
<!-- Repita uma linha por issue fechada. Remova esta seção se não fechar nenhuma issue. -->

---

## Commits

### `<hash-curto>` — <mensagem do commit>

<Descrição detalhada do que foi adicionado ou modificado neste commit. Mencione:
- Quais arquivos foram criados/alterados
- Qual a responsabilidade de cada arquivo novo
- Decisões de design relevantes (ex: por que essa camada, por que esse padrão)
- Impacto em outros módulos, se houver>

---

### `<hash-curto>` — <mensagem do commit>

<Mesma estrutura acima>

---

[repita para cada commit]

---

## Checklist

- [ ] Todos os testes passando
- [ ] Sem arquivos de configuração sensíveis (.env, secrets)
- [ ] Import rules do DDD respeitadas (domain não importa infra)
- [ ] Swagger documentado em endpoints novos
- [ ] Isolamento por organizationId em queries MongoDB
```

---

## Regras de qualidade

- **Título do PR:** `<tipo>(<escopo>): <descrição imperativa em inglês>` — máximo 72 caracteres.
  - Exemplos: `feat(forms): add question ordering`, `fix(auth): validate token expiration on form access`
- **Hash curto:** use os primeiros 7 caracteres (`git log --format="%h %s"`)
- **Descrição por commit:** mínimo 3 linhas. Deve ser compreensível sem abrir o diff.
- **Nunca copie apenas a mensagem do commit** como descrição — adicione contexto real.

---

## Passo 5 — Crie o PR

```bash
gh pr create \
  --title "<tipo>(<escopo>): <descrição>" \
  --body "$(cat <<'EOF'
<corpo gerado no Passo 3>
EOF
)"
```

Após criar, exiba a URL do PR para o usuário.

---

## Checklist de execução

Antes de chamar `gh pr create`:

- [ ] Listou todos os commits do range `main...HEAD`
- [ ] Analisou o diff de cada commit individualmente
- [ ] Título segue o padrão `tipo(escopo): descrição`
- [ ] Cada commit tem hash + mensagem + descrição detalhada
- [ ] Checklist do template está no corpo do PR
- [ ] Identificou e incluiu `Closes #N` para todas as issues fechadas por este PR
