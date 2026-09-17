---
name: DS-160 Official Map Reference
description: Consulta à pasta ds160map/ como fonte de verdade do formulário DS-160 oficial. Use para adicionar campos faltantes, validar IDs HTML, conferir options de selects, maxLengths e fluxos condicionais. NUNCA remover configurações existentes no projeto — apenas ADICIONAR o que falta.
---

# DS-160 Official Map Reference

## Propósito

A pasta `ds160map/` contém o **HTML real extraído do site oficial do DS-160** (CEAC - ceac.state.gov).
Ela é a **fonte de verdade** para:

- **IDs HTML** dos campos (ex: `ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_SURNAME`)
- **Options de selects** com valores exatos (ex: país `BRZL` = BRAZIL)
- **maxLength** de cada campo de texto
- **Fluxos condicionais** (qual campo aparece baseado em qual seleção)
- **URLs** das páginas oficiais
- **Tooltips/labels** em PT-BR e EN

## ⚠️ REGRA ABSOLUTA

> **NUNCA remover ou modificar configurações já existentes no projeto (schema, field-map, normalize).**
> **A pasta ds160map é usada APENAS para ADICIONAR** campos, options ou validações que faltam.
> O projeto já tem configurações avançadas adaptadas ao sistema; a ds160map serve como suplemento.

## Estrutura da Pasta

```
ds160map/
└── DS160/
    ├── 1 - Complete/                    ← Páginas de preenchimento
    │   ├── 1- Getting Started/          ← Login, segurança, retrieve
    │   ├── 2 - Personal/               ← Personal 1 e 2
    │   ├── 3 - Travel/                 ← Inclui variantes por visa type
    │   │   ├── Purpose of Trip to the US/
    │   │   │   ├── B/   (B1, B1B2, B2)
    │   │   │   ├── F/   (F1, F2-CH, F2-SP)
    │   │   │   ├── J/   (J1, J2-CH, J2-SP)
    │   │   │   └── O/   (O1, O2, O3-CH, O3-SP)
    │   │   ├── Person Entity Paying for Your Trip/
    │   │   │   ├── Self
    │   │   │   ├── Other Person
    │   │   │   ├── Other Company Organization
    │   │   │   ├── Present Employer
    │   │   │   └── Employer in the US
    │   │   ├── Standard No specific travel plans.md
    │   │   └── Standard Yes specific travel plans.md
    │   ├── 4 - Travel Companions/      ← 3 variantes
    │   ├── 5 - Previous U.S. Travel/
    │   ├── 6 - Address and Phone/
    │   ├── 7 - Passport/               ← Regular vs Other
    │   ├── 8 - U.S. Contact/           ← Person vs Organization
    │   ├── 9 - Family/                 ← Relatives, Spouse, Deceased, Former
    │   ├── 10 - Work Education Tranning/ ← Present, Previous, Additional
    │   ├── 11 - Security and Background/ ← Parts 1-5
    │   ├── 12 - Student Exchange Visa/  ← F e J com sub-variantes
    │   │   ├── F/
    │   │   │   ├── Specify STUDENT (F1)/     → SEVIS + Additional Contact
    │   │   │   ├── Specify CHILD OF AN F1 (F2)/   → SEVIS
    │   │   │   └── Specify SPOUSE OF AN F1 (F2)/  → SEVIS
    │   │   └── J/
    │   │       ├── Specify EXCHANGE VISITOR (J1)/  → SEVIS + Additional Contact
    │   │       ├── Specify CHILD OF A J1 (J2)/     → SEVIS
    │   │       └── Specify SPOUSE OF A J1 (J2)/    → SEVIS
    │   └── 13 - Temporary Work Visa/   ← O1 e O2
    │       └── O/
    │           ├── Specify EXTRAORDINARY ABILITY (O1)/ → Temporary Work
    │           └── Specify ALIEN ACCOMPANYING ASSISTING (O2)/ → Temporary Work
    ├── 2 - Photo/                       ← Upload de foto (Step 1 e 2)
    ├── 3 - Review/                      ← (vazio)
    ├── 4 - Sign/                        ← Sign and Submit (3 partes)
    └── 5 - Dowload/                     ← Thank you, Print App, Print Confirm
```

## Como Consultar

### 1. Para auditar campos de uma seção

Abra o arquivo MD correspondente à seção. Exemplo para Personal 1:
```
ds160map/DS160/1 - Complete/2 - Personal/1 - Personal 1.md
```

Procure por tags `<input>`, `<select>`, `<textarea>` para encontrar:
- **IDs**: `id="ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_SURNAME"`
- **maxLength**: `maxlength="33"` 
- **type**: `type="text"`, `type="radio"`, `type="checkbox"`
- **tabindex**: Ordem de tabulação (útil para preenchimento)

### 2. Para verificar options de um select

Procure por `<select>` e liste as `<option>`. Exemplo:
```html
<option value="M">MARRIED</option>
<option value="C">COMMON LAW MARRIAGE</option>
<option value="P">CIVIL UNION/DOMESTIC PARTNERSHIP</option>
```
Compare com o `options` array no schema.js correspondente.

### 3. Para verificar fluxos condicionais por tipo de visto

Vá até a pasta do tipo de visto:
```
ds160map/DS160/1 - Complete/3 - Travel/Purpose of Trip to the US/F/
```
Aqui você encontra os `<option>` de Specify para cada categoria:
- `F1-F1` → STUDENT (F1)
- `F2-CH` → CHILD OF AN F1 (F2)
- `F2-SP` → SPOUSE OF AN F1 (F2)

### 4. Para verificar campos SEVIS/Student Exchange

```
ds160map/DS160/1 - Complete/12 - Student Exchange Visa/F/Specify STUDENT (F1)/
```
Contém: SEVIS.md (campos SEVIS) + Additional Contact.md (campos F1/J1 only)

### 5. Para verificar campos Temporary Work (O visa)

```
ds160map/DS160/1 - Complete/13 - Temporary Work Visa/O/Specify EXTRAORDINARY ABILITY (O1)/
```
Contém: Temporary Work.md (petition number, employer info, etc.)

### 6. Para verificar processo de Sign/Submit

```
ds160map/DS160/4 - Sign/
```
Contém 3 etapas com todos os campos e textos de confirmação.

## Mapeamento: ds160map → pages/ do projeto

| ds160map Pasta | pages/ Pasta do Projeto |
|---|---|
| `2 - Personal/1 - Personal 1.md` | `02-personal1/` |
| `2 - Personal/2 - Personal 2.md` | `03-personal2/` |
| `3 - Travel/Standard *.md` | `04-travel/` |
| `4 - Travel Companions/` | `05-travel-companions/` |
| `5 - Previous U.S. Travel/` | `06-previous-us-travel/` |
| `6 - Address and Phone/` | `07-address-phone/` |
| `7 - Passport/` | `08-passport/` |
| `8 - U.S. Contact/` | `09-us-contact/` |
| `9 - Family/Relatives.md` | `10-family-parents/` |
| `9 - Family/Spouse.md` | `11-family-spouse/` |
| `9 - Family/Deceased Spouse.md` | `12-deceased-spouse/` |
| `9 - Family/Former Spouse.md` | `13-prev-spouse/` |
| `10 - Work Education/1 - Present.md` | `14-work-education-current/` |
| `10 - Work Education/2 - Previous.md` | `15-work-education-previous/` |
| `10 - Work Education/3 - Additional.md` | `16-work-education-additional/` |
| `11 - Security and Background/` | `17-security/` |
| `12 - Student Exchange Visa/` | `18-student-exchange/` + `19a-student-add-contact/` |
| `13 - Temporary Work Visa/` | `19-petition-info/` |
| `2 - Photo/` | `20-photo-upload/` |
| *(Review é UI-only)* | `21-review/` |
| `4 - Sign/` | `22-sign/` |

## Formato dos Arquivos

Cada `.md` contém:
1. **URL da página** (primeira linha): `URL: https://ceac.state.gov/GenNIV/General/complete/complete_personal.aspx?node=Personal1`
2. **HTML real** extraído do `<div id="content-main">` do site oficial
3. **Tooltips em PT-BR** dentro de `tip='...'` — úteis para labels traduzidos
4. **Valores preenchidos** de exemplo (ex: `value="SOUZA SILVA"`)

## Workflow de Auditoria

1. **Escolha a seção** a auditar (ex: `pages/08-passport/`)
2. **Abra o arquivo** correspondente em ds160map (ex: `7 - Passport/Passport (Regular, Official, Diplomatic, Laissez-Passer).md`)
3. **Extraia** todos os `<input>`, `<select>`, `<textarea>` com seus IDs e atributos
4. **Compare** com o `schema.js` e `field-map.js` da pasta pages/
5. **Identifique** campos faltantes no schema ou field-map
6. **ADICIONE** apenas os campos faltantes, sem remover os existentes
7. **Verifique** options de selects e maxLengths

## Dados Importantes Extraíveis

### Tipos de Visto Documentados

| Categoria | Sub-tipos | Páginas Extras |
|---|---|---|
| B (Business/Tourism) | B1, B1B2, B2 | Nenhuma |
| F (Academic Student) | F1, F2-CH, F2-SP | SEVIS + Additional Contact (F1 only) |
| J (Exchange Visitor) | J1, J2-CH, J2-SP | SEVIS + Additional Contact (J1 only) |
| O (Extraordinary) | O1, O2 | Temporary Work |

### Tipos de Payer Documentados

| Payer | Campos Extras |
|---|---|
| Self | Nenhum |
| Other Person | Nome, telefone, email, endereço, relacionamento |
| Other Company/Organization | Nome, telefone, endereço, relacionamento |
| Present Employer | Nome da empresa/escola |
| Employer in the US | Nome da empresa |

### Tipos de Passport Documentados

| Tipo | Campos |
|---|---|
| Regular, Official, Diplomatic, Laissez-Passer | Número, data emissão, data expiração, país, cidade |
| Other | Campos alternativos para documentos não-passaporte |
