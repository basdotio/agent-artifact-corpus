# Examples

Each example shows the **input** and the **output**. Note that every fact in the output can be traced to the input, and anything missing is marked instead of assumed.

---

## Example 1 — pt-BR, mobile, financial flow

**Input:**
> fiz um pix de 5 mil no android com o QA_USER_01 e ele não pediu o token, foi direto pro comprovante. passos: loguei, fui em Transferências PIX, digitei 5000, cliquei em Confirmar. pela RN2 acima de 1000 tem que pedir MFA. correlation id 7f3c-91ab. staging, app 4.12.0. segue print: comprovante.png

**Output:**

````markdown
## 🐞 [PIX] - App Android não solicita MFA em transferência de R$ 5.000,00

| Campo | Valor |
|---|---|
| **Tipo** | Bug |
| **Severidade** | Crítica (Blocker) *(sugerida)* |
| **Prioridade** | Altíssima *(sugerida)* |
| **Módulo** | PIX — Transferências |
| **Onde (interface)** | App Android — Transferências PIX > Confirmar |
| **Ambiente** | Staging · App Android 4.12.0 · Aparelho/versão do Android: ⚠️ NÃO INFORMADO |
| **Reprodutibilidade** | ⚠️ NÃO INFORMADO |
| **Relacionado a** | RN2 |

### Descrição e contexto
Uma transferência PIX de R$ 5.000,00 realizada no App Android foi concluída sem a solicitação do token (MFA). Pela RN2, transferências acima de R$ 1.000,00 devem exigir MFA.

**Dados técnicos**
- Correlation-ID: `7f3c-91ab`

### Passo a passo para reprodução
1. Logar no App Android com o usuário `QA_USER_01`.
2. Acessar **Transferências PIX**.
3. Digitar o valor `5000`.
4. Clicar em **Confirmar**.

### Resultado atual
A transferência é concluída e o comprovante é exibido, sem solicitar o token.

### Resultado esperado
O app deve solicitar MFA antes de concluir a transferência, conforme a **RN2** (valores acima de R$ 1.000,00).

### Justificativa da severidade *(sugerida)*
Transferência financeira concluída sem a autenticação exigida pela RN2.

### Evidências
- `comprovante.png`

### Informações faltantes
- Modelo do aparelho e versão do Android
- Reprodutibilidade (quantas tentativas, quantas falharam)
````

What the skill did **not** add: a PIX key step, "MFA enabled" or balance preconditions, fraud/impact statements, iOS/Web scope.

---

## Example 2 — English, failed automated test

**Input:** staging, Chrome, build `web-2.8.1`, story US-482 says 10% off with SAVE10. Fails 3/3 in CI.

```ts
test('applies 10% coupon', async ({ page }) => {
  await login(page, 'qa.buyer@test.com');
  await page.goto('/product/SKU-1001');
  await page.getByRole('button', { name: 'Add to cart' }).click();
  await page.goto('/checkout');
  await page.getByLabel('Coupon').fill('SAVE10');
  await page.getByRole('button', { name: 'Apply' }).click();
  await expect(page.getByTestId('order-total')).toHaveText('$90.00');
});
```
```
Error: expect(locator).toHaveText(expected)
Expected: "$90.00"
Received: "$100.00"
```

**Output (abridged):**

````markdown
## 🐞 [Checkout] - Coupon SAVE10 does not reduce order total to $90.00 on Web

| Field | Value |
|---|---|
| **Severity** | High (Major) *(suggested)* |
| **Where (interface)** | Web — `/checkout`, Coupon field |
| **Environment** | Staging · Web build web-2.8.1 · Chrome (version ⚠️ NOT PROVIDED) |
| **Reproducibility** | 3/3 in CI |
| **Found during** | Automation — `applies 10% coupon` |
| **Related to** | US-482 |

### Steps to reproduce
1. Log in as `qa.buyer@test.com`.
2. Open `/product/SKU-1001`.
3. Click **Add to cart**.
4. Go to `/checkout`.
5. Fill **Coupon** with `SAVE10`.
6. Click **Apply**.

### Actual result
Order total shows **$100.00**.

### Expected result
Order total shows **$90.00** (10% off with SAVE10), according to US-482.

### Evidence
```
Expected: "$90.00"
Received: "$100.00"
```

### Missing information
- Chrome version
- Screenshot/trace of the failing step
````

Note: the skill did not claim a "Coupon applied" message appeared — the input never said so.

---

## Example 3 — partial information: report now, short closing line

**Input:**
> achei um bug: no app iOS, homolog, o botão Salvar da tela de Perfil não faz nada. deveria salvar né

The expected behavior has a source (the user states it), so the skill writes the report right away instead of asking first. Note how short the steps are — they are only what the user described.

**Output (abridged):**

````markdown
## 🐞 [Perfil] - Botão Salvar não executa nenhuma ação no app iOS

| Campo | Valor |
|---|---|
| **Severidade** | Alta (Major) *(sugerida)* |
| **Onde (interface)** | Tela de Perfil, botão **Salvar** · Caminho até a tela: ⚠️ NÃO INFORMADO |
| **Ambiente** | Homologação · App iOS · Versão do app / iOS / aparelho: ⚠️ NÃO INFORMADO |
| **Reprodutibilidade** | ⚠️ NÃO INFORMADO |

### Passo a passo para reprodução
1. No app iOS, acessar a tela de **Perfil**.
2. Tocar em **Salvar**.

### Resultado atual
Nada acontece ao tocar em **Salvar**.

### Resultado esperado
Os dados do perfil devem ser salvos (segundo o testador).

### Evidências
⚠️ NÃO INFORMADO

### Informações faltantes
- Versão do app, versão do iOS e aparelho
- Quais campos foram alterados antes de salvar
- Evidência (print/vídeo)
- Reprodutibilidade
````

> Se puder, me manda o caminho até a tela de Perfil e a versão do app/iOS — o resto está em *Informações faltantes*. Quer que eu salve em `bug-reports/`?

What the skill did **not** add: an "edit the name field" step, a login step, a claim that no message is shown or that the data is lost.

---

## Example 4 — not a confirmed bug yet

**Input:**
> o export de relatório tá lento, acho que é bug

**Output (skill response, no report generated yet):**

> Antes de montar o reporte, faltam alguns pontos para confirmar que é um bug:
> 1. Qual é o comportamento esperado e de onde vem (história, requisito de performance, comportamento anterior)?
> 2. Quanto tempo leva hoje, e em qual ambiente/versão?
> 3. Quais passos você seguiu (relatório, filtros, volume de dados)?
> 4. Tem alguma evidência (vídeo, log, tempo medido)?
>
> Se preferir, posso registrar como **[SUSPEITA]** para alinhar com o PO.
