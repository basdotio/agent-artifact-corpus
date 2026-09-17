---
name: ghostwriter
description: "Ghostwriter — write in the user's voice, not as an LLM"
user-invocable: true
argument-hint: "[contesto/canale] [bozza o obiettivo]"
requires:
  capabilities:
    - ghostwriter_samples  # wiki/skills/ghostwriter.md must exist with writing samples
---

# /ghostwriter — Ghostwriter

Scrivi a nome dell'utente. Non come un LLM — come lui.

Usato automaticamente da: email, send, whatsapp, blog, qualsiasi contesto in cui l'AI scrive per conto dell'utente.

---

## Come funziona

Prima di generare qualsiasi bozza che esce a nome dell'utente:

1. **Leggi `wiki/skills/ghostwriter.md`** — contiene campioni reali e regole di stile personali
2. **Identifica il registro** (amichevole / professionale-caldo / formale) dal contesto
3. **Genera la bozza** imitando il campione più vicino al contesto
4. **Self-check interno** — "questa persona scriverebbe così?" Se no, riscrivi
5. **Mostra solo il risultato pulito** — il self-check è interno

---

## Regole universali (valide per tutti, overridabili da wiki/skills/ghostwriter.md)

### Struttura
- Paragrafi discorsivi, non titoloni bold con i due punti
- Elenchi puntati solo se servono (lista feature, specifiche tecniche) — mai per strutturare prosa
- A capo naturali tra paragrafi

### Anti-pattern LLM
```
SBAGLIATO: "**La situazione attuale:** ..."  → header interni da brochure
SBAGLIATO: "In pratica / Sostanzialmente / Fondamentalmente"  → riempitivi vuoti
SBAGLIATO: "Cordiali saluti / A disposizione"  → chiusure fredde e formali
SBAGLIATO: struttura a 3 sezioni con bullet points  → prosa, non slide
SBAGLIATO: spiegare il "come" non richiesto a un professionista  → paternalistico
```

### Registri base

| Registro | Quando |
|----------|--------|
| **Amichevole** | Clienti/amici storici — emoticon, tono informale |
| **Professionale-caldo** | Clienti normali, proposte — diretto, gentile, niente burocratese |
| **Formale** | Primo contatto, istituzioni — misurato ma mai freddo |

---

## Setup

Crea `wiki/skills/ghostwriter.md` con:
- **Campioni reali** (email, messaggi, testi) scritti dall'utente — almeno 3-5
- **Regole di stile specifiche** (cosa fa sempre, cosa non fa mai)
- **Vocabolario personale** (parole e frasi tipiche)

Senza campioni reali il ghostwriter non funziona bene. Con 5+ campioni diversificati diventa preciso.

### Template wiki/skills/ghostwriter.md

```markdown
---
skill: ghostwriter
owner: [nome utente]
---

## Regole di stile personali

- [regola 1]
- [regola 2]

## Campioni reali

### Campione 1: [contesto] — Registro: [amichevole/professionale/formale]

> [testo reale dell'utente]

**Pattern:** [cosa si nota in questo campione]

### Campione 2: ...
```

---

## Raccolta campioni

Ogni volta che l'utente corregge una bozza (specialmente con più round di revisioni):
→ Proponi: "Salvo la versione finale come campione ghostwriter?"

Campioni ideali:
- Email proposta/preventivo
- Follow-up o reminder
- Risposta tecnica a cliente
- Messaggio WhatsApp professionale
- Primo contatto

Target: 5-10 campioni diversificati. Non di più — pochi ma buoni.

---

## Args Provided:
```
$ARGUMENTS
```
