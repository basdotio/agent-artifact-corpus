---
name: html-js-card
description: Crea card per Home Assistant usando la custom card html-js-card di Silvio. Usa questo skill SEMPRE quando Silvio chiede di creare, modificare o aggiornare una card Lovelace per Home Assistant, oppure quando menziona dashboard HA, card personalizzate, visualizzazione sensori, o vuole mostrare dati di Home Assistant in una card. Lo skill contiene la struttura YAML corretta, le variabili disponibili, i pattern CSS con le variabili HA, i pattern di aggiornamento, gli esempi di componenti riutilizzabili e le convenzioni di naming delle entità del sistema di Silvio.
---

# html-js-card Skill

Questo skill guida la creazione di card Lovelace per Home Assistant usando la custom card `html-js-card` installata nel sistema di Silvio. Produce sempre YAML completo e funzionante, pronto da incollare nell'editor Lovelace.

---

## Struttura YAML della card

```yaml
type: custom:html-js-card
title: Titolo card          # opzionale — ometti se non serve
height: 400px               # opzionale — default: auto
padding: 12px 16px 16px     # opzionale — padding del contenuto
overflow: hidden            # opzionale: hidden | auto | scroll
update_interval: 30         # opzionale — secondi tra aggiornamenti automatici
entities:                   # lista entità HA da iniettare come oggetto
  - sensor.nome_entita
  - input_number.altro
scripts:                    # librerie CDN da caricare (opzionale)
  - https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js
content: |
  <!-- HTML qui -->
  <script>
    // JavaScript qui
  </script>
```

**Parametri obbligatori:** solo `type` e `content`.

---

## Variabili JavaScript disponibili

Dentro ogni `<script>` nel `content` sono disponibili automaticamente:

| Variabile | Tipo | Descrizione |
|-----------|------|-------------|
| `hass` | Object | Oggetto HA completo — accesso a tutti gli stati, servizi, auth |
| `entities` | Object | Solo le entità dichiarate in `entities:` — accesso per entity_id |
| `card` | HTMLElement | Elemento DOM contenitore — usa `card.querySelector()` per trovare elementi |
| `config` | Object | Configurazione YAML della card |
| `shadow` | ShadowRoot | Shadow DOM della card |

### Accesso agli stati
```javascript
// Tramite entities (solo quelle dichiarate)
const val = entities['sensor.temperatura']?.state;
const attr = entities['sensor.temperatura']?.attributes?.unit_of_measurement;

// Tramite hass (tutte le entità)
const val = hass.states['sensor.qualsiasi']?.state;
```

### Chiamare servizi HA
```javascript
// Sintassi: hass.callService(domain, service, data)
hass.callService('input_number', 'set_value', {
  entity_id: 'input_number.soglia', value: 2000
});
hass.callService('button', 'press', { entity_id: 'button.reset' });
hass.callService('input_boolean', 'turn_on', { entity_id: 'input_boolean.flag' });
hass.callService('input_datetime', 'set_datetime', {
  entity_id: 'input_datetime.data', datetime: '2025-01-01 10:00:00'
});
```

### Aprire popup nativo HA (more-info)
```javascript
function moreInfo(entityId) {
  card.dispatchEvent(new CustomEvent('hass-more-info', {
    bubbles: true, composed: true, detail: { entityId }
  }));
}
// Uso: onclick="moreInfo('sensor.temperatura')"
```

---

## Pattern aggiornamento

La card riceve aggiornamenti da HA tramite evento `hass-update`. Pattern standard:

```javascript
function aggiorna(hassObj, entsObj) {
  // aggiorna UI con i nuovi valori
  card.querySelector('#valore').textContent = entsObj['sensor.x']?.state || '—';
}

// Prima esecuzione all'avvio
window._hjc_hass = hass;
aggiorna(hass, entities);

// Aggiornamenti successivi da HA
card.addEventListener('hass-update', e => {
  window._hjc_hass = e.detail.hass;
  aggiorna(e.detail.hass, e.detail.entities);
});
```

> **Importante:** salva sempre `hass` in `window._hjc_hass` per averlo disponibile nelle funzioni globali (onclick, slider, bottoni).

---

## CSS — variabili Home Assistant

Usa SEMPRE le variabili CSS di HA per compatibilità con tema chiaro/scuro:

```css
/* Testi */
color: var(--primary-text-color);      /* testo principale */
color: var(--secondary-text-color);    /* testo secondario/muted */
color: var(--disabled-text-color);     /* testo disabilitato/hint */

/* Sfondi */
background: var(--card-background-color);        /* sfondo card bianco */
background: var(--secondary-background-color);   /* sfondo sezioni interne */

/* Bordi */
border: 1px solid var(--divider-color);  /* bordi sottili */

/* Colori semantici */
color: var(--success-color);   background: var(--success-color)22;  /* verde */
color: var(--warning-color);   background: var(--warning-color)22;  /* arancione */
color: var(--error-color);     background: var(--error-color)22;    /* rosso */
color: var(--primary-color);   /* colore principale del tema */
```

> **Nota:** `22` in fondo al colore è opacità ~13% in hex — utile per badge e sfondi leggeri.

---

## Componenti riutilizzabili

### Blocco sezione
```html
<div style="background:var(--secondary-background-color);border-radius:10px;padding:12px 14px;margin-bottom:10px;">
  <div style="font-size:10px;font-weight:600;color:var(--disabled-text-color);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">
    TITOLO SEZIONE
  </div>
  <!-- contenuto -->
</div>
```

### Metric card (griglia 2/3/4 colonne)
```html
<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
  <div style="background:var(--card-background-color);border-radius:8px;padding:8px 10px;border:1px solid var(--divider-color);cursor:pointer;"
       onclick="moreInfo('sensor.entita')">
    <div style="font-size:10px;color:var(--disabled-text-color);margin-bottom:3px;">Label</div>
    <div style="font-size:18px;font-weight:500;" id="val-id">—</div>
  </div>
</div>
```

### Barra progresso con colore dinamico
```html
<div style="background:var(--divider-color);border-radius:99px;height:8px;overflow:hidden;margin:8px 0;">
  <div id="bar" style="height:100%;border-radius:99px;width:0%;transition:width .8s ease;background:var(--success-color);"></div>
</div>
```
```javascript
function aggiornaBarra(perc) {
  const bar = card.querySelector('#bar');
  bar.style.width = Math.min(perc, 100) + '%';
  bar.style.background = perc >= 100 ? 'var(--error-color)'
    : perc >= 80 ? 'var(--warning-color)'
    : 'var(--success-color)';
}
```

### Badge stato
```html
<span id="badge" style="display:inline-flex;align-items:center;font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;background:var(--success-color)22;color:var(--success-color);">
  Ok
</span>
```
```javascript
function aggiornaBadge(perc) {
  const b = card.querySelector('#badge');
  if (perc >= 100) {
    b.style.cssText = 'display:inline-flex;align-items:center;font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;background:var(--error-color)22;color:var(--error-color);';
    b.textContent = '⚠ Critico';
  } else if (perc >= 80) {
    b.style.cssText = 'display:inline-flex;align-items:center;font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;background:var(--warning-color)22;color:var(--warning-color);';
    b.textContent = 'Attenzione';
  } else {
    b.style.cssText = 'display:inline-flex;align-items:center;font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;background:var(--success-color)22;color:var(--success-color);';
    b.textContent = 'Ok';
  }
}
```

### Righe info (label + valore)
```html
<div style="border-top:1px solid var(--divider-color);padding-top:8px;">
  <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:12px;border-bottom:1px solid var(--divider-color);">
    <span style="color:var(--disabled-text-color);">Label</span>
    <span style="color:var(--primary-text-color);font-weight:500;cursor:pointer;"
          onclick="moreInfo('sensor.entita')" id="val-riga">—</span>
  </div>
</div>
```

### Bottone azione
```html
<button onclick="azioneFn()"
  style="display:flex;align-items:center;gap:5px;background:none;border:1px solid var(--divider-color);border-radius:8px;padding:7px 12px;font-size:12px;color:var(--secondary-text-color);cursor:pointer;transition:background .15s;"
  onmouseover="this.style.background='var(--secondary-background-color)'"
  onmouseout="this.style.background='none'">
  Azione
</button>
```

### Dialog di conferma
```html
<div id="conf" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:999;align-items:center;justify-content:center;">
  <div style="background:var(--card-background-color);border-radius:12px;padding:22px 18px;max-width:280px;text-align:center;">
    <div style="font-size:15px;font-weight:500;margin-bottom:7px;">Titolo conferma</div>
    <div style="font-size:12px;color:var(--secondary-text-color);margin-bottom:16px;line-height:1.6;">Testo descrittivo.</div>
    <div style="display:flex;gap:8px;justify-content:center;">
      <button onclick="closeConf()" style="padding:7px 18px;border-radius:8px;border:1px solid var(--divider-color);font-size:13px;cursor:pointer;background:none;color:var(--secondary-text-color);">Annulla</button>
      <button onclick="doAzione()" style="padding:7px 18px;border-radius:8px;border:none;font-size:13px;cursor:pointer;background:var(--error-color)22;color:var(--error-color);">Conferma</button>
    </div>
  </div>
</div>
```
```javascript
window.openConf  = () => { card.querySelector('#conf').style.display = 'flex'; };
window.closeConf = () => { card.querySelector('#conf').style.display = 'none'; };
```

### Grafico a barre con Chart.js (richiede scripts: Chart.js)
```yaml
scripts:
  - https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js
```
```html
<div style="position:relative;height:120px;"><canvas id="hc"></canvas></div>
```
```javascript
const isDark = matchMedia('(prefers-color-scheme: dark)').matches;
const colore = isDark ? '#5DCAA5' : '#1D9E75';
const coloreFill = isDark ? 'rgba(93,202,165,0.12)' : 'rgba(29,158,117,0.10)';
const coloreTesto = isDark ? 'rgba(168,165,157,0.8)' : 'rgba(107,105,96,0.8)';
const coloreGriglia = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

const ctx = card.querySelector('#hc').getContext('2d');
const chart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Lun','Mar','Mer','Gio','Ven','Sab','Dom'],
    datasets: [{ data: [0,0,0,0,0,0,0], backgroundColor: coloreFill,
      borderColor: colore, borderWidth: 1.5, borderRadius: 4, borderSkipped: false }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: { legend: { display: false }, tooltip: {
      backgroundColor: isDark ? '#252523' : '#fff',
      borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
      borderWidth: 1,
      callbacks: { label: c => c.parsed.y.toFixed(1) + ' unità' }
    }},
    scales: {
      x: { grid: { display: false }, ticks: { color: coloreTesto, font: { size: 10 } }, border: { display: false } },
      y: { grid: { color: coloreGriglia }, ticks: { color: coloreTesto, font: { size: 10 } }, border: { display: false } }
    }
  }
});
```

### Sparkline (grafico linea mini)
```html
<div style="height:46px;flex:1;"><canvas id="spark"></canvas></div>
```
```javascript
const sparkData = Array(22).fill(0);
const sCtx = card.querySelector('#spark').getContext('2d');
const sparkC = new Chart(sCtx, {
  type: 'line',
  data: { labels: sparkData.map((_,i)=>i),
    datasets: [{ data: [...sparkData], borderColor: colore, borderWidth: 1.5,
      fill: true, backgroundColor: coloreFill, tension: 0.4, pointRadius: 0 }] },
  options: { responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false, min: 0 } } }
});
// Aggiorna sparkline con nuovo valore:
// sparkData.shift(); sparkData.push(nuovoValore);
// sparkC.data.datasets[0].data = [...sparkData]; sparkC.update('none');
```

### Slider
```html
<input type="range" min="0" max="100" step="1" value="50" id="sld"
  oninput="aggiornaSld(this.value)"
  style="-webkit-appearance:none;appearance:none;width:90px;height:4px;background:var(--secondary-background-color);border-radius:2px;outline:none;cursor:pointer;">
<style>
  #sld::-webkit-slider-thumb { -webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:var(--primary-color);cursor:pointer; }
</style>
```

### Dot live animato
```html
<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--success-color);margin-right:5px;animation:lpulse 2s ease-in-out infinite;"></span>
<style>@keyframes lpulse{0%,100%{opacity:1}50%{opacity:0.25}}</style>
```

---

## Utilità JavaScript

### Formattazione numeri italiana
```javascript
function fmt(v, decimali = 1) {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  return n.toLocaleString('it-IT', { minimumFractionDigits: decimali, maximumFractionDigits: decimali });
}
// fmt(1234.5)   → "1.234,5"
// fmt(1234.5,0) → "1.235"
```

### Formattazione data da input_datetime
```javascript
function fmtData(rawState) {
  if (!rawState || rawState === 'unknown' || rawState === 'unavailable') return '—';
  const dt = new Date(rawState);
  return dt.toLocaleDateString('it-IT', { day:'2-digit', month:'2-digit', year:'numeric' })
    + ' ' + dt.toLocaleTimeString('it-IT', { hour:'2-digit', minute:'2-digit' });
}
```

### Storia entità via API HA
```javascript
async function caricaStorico(entityId, ore, hassObj) {
  const start = new Date(Date.now() - ore * 3600000).toISOString();
  const token = hassObj.auth?.data?.access_token || '';
  const r = await fetch(
    `/api/history/period/${start}?filter_entity_id=${entityId}&minimal_response=true`,
    { headers: { Authorization: 'Bearer ' + token } }
  );
  const data = await r.json();
  return data[0] || [];
}
```

---

## Convenzioni entità — sistema di Silvio

### Acqua depuratore
```
sensor.controllo_acqua_acqua_buona_flusso       — flusso L/min
sensor.controllo_acqua_acqua_buona_litri        — litri totali (con offset reset)
sensor.esp32_acqua_depuratore_acqua_buona_metri_cubi
sensor.acqua_buona_litri_dalla_cartuccia        — litri dalla cartuccia
sensor.acqua_buona_usura_cartuccia              — % usura
sensor.acqua_buona_litri_rimanenti_cartuccia    — L rimanenti
sensor.acqua_buona_giorni_dalla_cartuccia       — giorni in uso
sensor.acqua_buona_stato_cartuccia              — testo stato
sensor.acqua_buona_giornaliera                  — utility_meter giornaliero
sensor.acqua_buona_settimanale                  — utility_meter settimanale
sensor.acqua_buona_mensile                      — utility_meter mensile
sensor.acqua_buona_annuale                      — utility_meter annuale
input_datetime.data_cambio_cartuccia_buona
input_number.soglia_cambio_cartuccia
input_number.acqua_buona_litri_al_reset
input_boolean.avviso_cartuccia_inviato
button.reset_acqua_buona_cambio_cartuccia
```

### Energia solare (EPCube + Tigo)
```
sensor.epcube_*    — inverter/batteria EPCube HES-EU1-710G
sensor.tigo_*      — ottimizzatori Tigo
```

### Nomi dashboard Lovelace
```
Vaira             — dashboard principale
Vaira-Cell        — versione mobile
Tigo              — dashboard solare Tigo
```

### Assistente HA
```
Nome configurato: Amira (= Claude in ambiente HA di Silvio)
```

---

## ❌ ERRORI COMUNI — NON FARE MAI

> Questi errori producono card bloccate su "Caricamento..." o completamente non funzionanti.

| ❌ SBAGLIATO | ✅ CORRETTO |
|---|---|
| Campo `js:` separato nel YAML | Il JS va **sempre** dentro `<script>` nel `content` |
| `this.hass` | `hass` (variabile iniettata automaticamente) |
| `this.querySelector(...)` | `card.querySelector(...)` |
| `document.querySelector(...)` | `card.querySelector(...)` — nel shadow DOM `document` non vede gli elementi |
| IIFE `(function(){ ... })()` come pattern principale | Script normale con `aggiorna()` + `hass-update` |
| Funzioni locali nei `onclick` inline senza `window.` | `window.fn = function(){}` + `onclick="fn()"` |
| Nessun listener `hass-update` | Sempre `card.addEventListener('hass-update', ...)` |
| `hass.callService(...)` dentro `onclick` diretto | Salvare `hass` in `window._hjc_hass` e usarlo nei callback |

**Il campo `js:` NON ESISTE in html-js-card.** Qualsiasi codice JS scritto fuori dal `content` viene ignorato — la card mostra solo l'HTML statico iniziale (es. "Caricamento...") senza mai aggiornarsi.

---

## Regole di output

1. **Produci sempre YAML completo** — non snippet parziali. Il risultato deve essere incollabile direttamente nell'editor Lovelace.
2. **Salva sempre `hass` in `window._hjc_hass`** nelle funzioni init, per averlo accessibile nei callback globali.
3. **Usa sempre variabili CSS HA** — mai colori hardcoded (eccetto Chart.js che richiede valori espliciti, usa i valori esatti del tema scuro/chiaro come mostrato negli esempi).
4. **`moreInfo` su tutti i valori numerici cliccabili** — ogni dato che ha un'entità corrispondente deve aprire il popup HA al click.
5. **Pattern hass-update obbligatorio** — sempre ascoltare `hass-update` per aggiornamenti in tempo reale.
6. **`window.nomeFunzione`** per tutte le funzioni chiamate da `onclick` inline nell'HTML — le funzioni dichiarate normalmente non sono accessibili dall'HTML nel shadow DOM.
7. **`card.querySelector()`** invece di `document.querySelector()` — nel shadow DOM `document` non vede gli elementi della card.
8. **Conferma dialog per azioni distruttive** — reset, eliminazione, scrittura su entità sensibili.
