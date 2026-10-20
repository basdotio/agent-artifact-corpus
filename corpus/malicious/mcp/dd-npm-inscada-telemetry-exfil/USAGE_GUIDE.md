# inSCADA MCP Server — Usage Guide

## Quick Start

inSCADA MCP Server provides 39 tools for managing inSCADA platform through natural language via Claude Desktop. This guide helps you use it efficiently with minimal token consumption.

### Golden Rule: Always specify space and project

```
claude space, Energy Monitoring Demo, ActivePower_kW değeri nedir?
```

Without space/project info, Claude makes extra API calls to discover them — wasting tokens.

---

## Scenarios

### 1. Read Live Values

No guide needed. Ask directly.

**Single variable:**
```
claude space, Energy Monitoring Demo, ActivePower_kW değeri?
```

**Multiple variables:**
```
claude space, Energy Monitoring Demo, tüm değişkenlerin anlık değerlerini göster
```

**Connection status:**
```
claude space, Energy Monitoring Demo, bağlantı durumlarını kontrol et
```

> Response is compact by default — only value, name, date. Say "detaylı ver" for full API response with raw values, flags, extras.

---

### 2. Historical Data & Charts

No guide needed. Specify time range.

**Line chart:**
```
claude space, Energy Monitoring Demo, ActivePower_kW son 24 saat grafiği
```

**Compare variables:**
```
claude space, Energy Monitoring Demo, ActivePower_kW ve ReactivePower_kVAR karşılaştır, son 6 saat
```

**Statistics:**
```
claude space, Energy Monitoring Demo, ActivePower_kW 7 gün istatistik
```

**Live gauge:**
```
claude space, Energy Monitoring Demo, Temperature_C gauge 0-80°C
```

---

### 3. Discover Variables

No guide needed.

```
claude space, Energy Monitoring Demo, değişkenleri listele
```

```
claude space, Energy Monitoring Demo, "Power" içeren değişkenleri listele
```

> Variable list is compact by default — only id, name, type, unit, dsc. Say "detaylı listele" for connection_id, scale, log_type etc.

---

### 4. Alarms & Status

No guide needed.

```
claude space, aktif alarmları göster
```

```
claude space, Energy Monitoring Demo, proje durumu
```

---

### 5. Write Scripts ⚠️

**Guide REQUIRED.** Nashorn ES5 rules are critical.

```
inscada guide oku. claude space, Energy Monitoring Demo, her 10 saniyede 
sıcaklık 60°C üzerine çıkınca bildirim gönderen script yaz
```

```
inscada guide oku. claude space, Energy Monitoring Demo, 
"Chart_ActiveReactivePower" scriptini oku ve grafik renklerini değiştir
```

**Search scripts (no guide needed):**
```
claude space, scriptlerde "getVariableValue" ara
```

---

### 6. Create Animations ⚠️

**Guide REQUIRED.** SVG rules and element types are critical.

```
inscada guide oku. claude space, Energy Monitoring Demo için 
ActivePower_kW, Voltage_V, Current_A gösteren SVG animation oluştur
```

---

### 7. Dashboards

Template = no guide needed. Custom HTML = guide recommended.

**Template (fast):**
```
claude space, Energy Monitoring Demo, ActivePower_kW gauge dashboard, 0-1000 kW
```

**Multi-chart:**
```
claude space, Energy Monitoring Demo, multi_chart dashboard 
ActivePower_kW, Voltage_V, Current_A
```

**Custom HTML:**
```
inscada guide oku. claude space, Energy Monitoring Demo için 
özel HTML dashboard — üstte 3 gauge, altta trend grafiği
```

---

### 8. Export

No guide needed.

```
claude space, Energy Monitoring Demo, ActivePower_kW 24 saat verisini Excel'e aktar
```

---

### 9. API Discovery

No guide needed.

```
inSCADA API'de alarm endpoint'leri bul
```

---

## Quick Reference

| Task | Prompt | Guide? |
|------|--------|--------|
| Live value | `claude space, proje, değişken değeri?` | No |
| Chart | `claude space, proje, değişken son 24 saat grafiği` | No |
| Gauge | `claude space, proje, değişken gauge 0-100` | No |
| Stats | `claude space, proje, değişken 7 gün istatistik` | No |
| Alarms | `claude space, aktif alarmlar` | No |
| Project status | `claude space, proje durumu` | No |
| Variables | `claude space, proje, değişkenleri listele` | No |
| Script write | `inscada guide oku. claude space, proje, script yaz...` | **Yes** |
| Animation | `inscada guide oku. claude space, proje, animation oluştur...` | **Yes** |
| Dashboard (template) | `claude space, proje, gauge dashboard değişken 0-1000 kW` | No |
| Dashboard (custom) | `inscada guide oku. claude space, proje, özel dashboard...` | **Yes** |
| Excel export | `claude space, proje, değişken 24 saat Excel` | No |
| API discovery | `API'de alarm endpoint'leri bul` | No |

---

## Compact vs Verbose Responses

By default, tool responses return only essential fields to save tokens:

### inscada_get_live_value

**Compact (default):**
```json
{"value": 421.79, "name": "ActivePower_kW", "dsc": "Total active power", "date": "2026-04-03T00:43:08"}
```

**Verbose ("detaylı ver"):**
```json
{"@class": "...NumberVariableValue", "flags": {"scaled": true}, "value": 421.79, "extras": {"raw_value": 306.73}, "variableShortInfo": {"dsc": "...", "frame": "...", "device": "...", "connection": "..."}, "dateInMs": 1775166188708}
```

**Savings: 64%**

### inscada_get_live_values

**Compact (default):**
```json
{"ActivePower_kW": {"value": 421.79, "date": "2026-04-03..."}, "Voltage_V": {"value": 232.9, "date": "2026-04-03..."}}
```

**Verbose:** Full API response with flags, extras, variableShortInfo per variable.

**Savings: 83%**

### list_variables

**Compact (default):**
```json
[{"id": 23227, "name": "ActivePower_kW", "type": "Float", "unit": "kW", "dsc": "Total active power"}]
```

**Verbose:** Adds connection_id, project_id, is_active, eng_zero_scale, eng_full_scale, log_type, code.

**Savings: 61%**

---

## Cost Estimates (Sonnet 4.6, April 2026)

Prices: Input $3/MTok, Output $15/MTok. Rate: 1 USD ≈ 44.50 TL.

| Scenario | Input Tokens | Output Tokens | USD | TL |
|----------|-------------|---------------|-----|-----|
| Live value query | ~6,400 | ~300 | $0.024 | ~1.0 TL |
| Line chart | ~6,400 | ~3,000 | $0.064 | ~2.8 TL |
| Script writing (with guide) | ~8,800 | ~7,900 | $0.145 | ~6.4 TL |
| Animation creation (with guide) | ~9,600 | ~11,200 | $0.197 | ~8.7 TL |
| Dashboard (template) | ~6,400 | ~1,500 | $0.042 | ~1.9 TL |

### With compact responses (default)

| Scenario | Before optimization | After optimization | Savings |
|----------|--------------------|--------------------|---------|
| Live value query | ~1.7 TL | ~1.0 TL | **41%** |
| 10 variables batch | ~3.2 TL | ~1.5 TL | **53%** |
| List variables (500) | ~4.8 TL | ~2.5 TL | **48%** |

### Cost-saving tips

- **Always specify space + project** — saves 500-1000 discovery tokens
- **Guide only when needed** — saves ~4,000 tokens for simple queries
- **Compact is default** — say "detaylı" only when you need raw values
- **Haiku 4.5 for simple queries** — 67% cheaper than Sonnet
- **Batch API** — 50% off for non-urgent bulk operations
- **Prompt Caching** — tool definitions cached at 10% cost after first call

---

## Tool List (39 tools)

### Space & Data
`set_space` · `list_spaces` · `list_projects` · `list_variables` · `search_variables` · `list_scripts` · `get_script` · `update_script` · `list_connections` · `search_in_scripts`

### Animation
`list_animations` · `get_animation`

### SCADA Operations
`inscada_get_live_value` · `inscada_get_live_values` · `inscada_set_value` · `inscada_get_fired_alarms` · `inscada_connection_status` · `inscada_project_status` · `inscada_run_script` · `inscada_script_status` · `inscada_logged_values` · `inscada_logged_stats`

### Charts
`chart_line` · `chart_bar` · `chart_gauge` · `chart_multi` · `chart_forecast`

### Custom Menus
`list_custom_menus` · `get_custom_menu` · `get_custom_menu_by_name` · `create_custom_menu` · `update_custom_menu` · `delete_custom_menu`

### Export & API
`export_excel` · `inscada_api_endpoints` · `inscada_api_schema` · `inscada_api`

### Guide
`inscada_guide` · `inscada_animation_guide`
