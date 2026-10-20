# @inscada/mcp-server

inSCADA MCP Server — SCADA operations via [Model Context Protocol](https://modelcontextprotocol.io).

Connect Claude Desktop, VS Code Copilot, Cursor, or any MCP client to your inSCADA system. 39 tools for live values, alarms, scripts, historical data, charts, Excel export, and more.

> **Note:** This MCP server is designed for **inSCADA JDK11** edition.

---

inSCADA MCP Server — [Model Context Protocol](https://modelcontextprotocol.io) uzerinden SCADA operasyonlari.

Claude Desktop, VS Code Copilot, Cursor veya herhangi bir MCP istemcisini inSCADA sisteminize baglayin. Canli deger, alarm, script, tarihsel veri, grafik, Excel disa aktarma ve daha fazlasi icin 39 arac.

> **Not:** Bu MCP sunucusu **inSCADA JDK11** surumu icin tasarlanmistir.

## What is this? / Bu ne ise yarar?

This MCP server lets AI assistants (like Claude) directly interact with your inSCADA system using natural language.

Bu MCP sunucusu, AI asistanlarin (Claude gibi) dogal dil kullanarak inSCADA sisteminizle etkilesime girmesini saglar.

### Application Development / Uygulama Gelistirme

Build and maintain SCADA applications through natural language. Write and debug scripts, design animations and faceplates, create custom menus, and explore your project structure.

Dogal dil ile SCADA uygulamalari gelistirin. Script yazin ve hata ayiklayin, animasyon ve faceplate tasarlayin, ozel menuler olusturun, proje yapinizi kesfedin.

### Data Analytics / Veri Analitigi

Analyze historical data, generate trend charts, create forecasts, and export reports — without writing queries or configuring dashboards.

Tarihsel verileri analiz edin, trend grafikleri olusturun, tahminler uretin ve raporlari disa aktarin — sorgu yazmadan veya dashboard yapilandirmadan.

### Operations & Monitoring / Operasyon ve Izleme

Monitor your SCADA system in real time. Check live values, view active alarms, inspect connection status, and track project health.

SCADA sisteminizi gercek zamanli izleyin. Canli degerleri kontrol edin, aktif alarmlari goruntuleyin, baglanti durumunu inceleyin ve proje sagligini takip edin.

## Installation / Kurulum

Two ways to install / Iki farkli kurulum yontemi:

### Method 1: Extension File (Recommended for end users / Son kullanicilar icin onerilen)

1. Download `inscada-mcp-server.mcpb` from [Releases](https://github.com/inscada-app/ins-mcp-desktop-extension/releases) or [inscada.com/download](https://www.inscada.com/download/)
2. Double-click the file — Claude Desktop opens automatically
3. Fill in the form: **inSCADA URL**, **Username**, **Password**
4. Done! The extension appears in Claude Desktop with icon and description.

`inscada-mcp-server.mcpb` dosyasini indirin, cift tiklayin, formu doldurun. Claude Desktop'ta ikon ve aciklamasiyla gorunur.

### Method 2: JSON Configuration (For developers / Gelistiriciler icin)

Add to your Claude Desktop config:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "inscada": {
      "command": "npx",
      "args": ["-y", "@inscada/mcp-server"]
    }
  }
}
```

On first run, the server will prompt for inSCADA URL, username, and password.

Ilk calistirmada sunucu, inSCADA URL, kullanici adi ve sifre sorar.

### Difference / Fark

| | Extension (.mcpb) | JSON Config |
|---|---|---|
| **Setup** | Double-click + GUI form | Edit JSON file manually |
| **UI** | Icon, description, config panel in Claude Desktop | Tools only, no UI |
| **Credentials** | GUI form, passwords masked | Prompted on first run |
| **Updates** | Download new .mcpb | Update JSON or `npx` fetches latest |
| **Best for** | End users, operators | Developers, CI/CD |

## Requirements / Gereksinimler

- [Node.js](https://nodejs.org) 18+
- A running inSCADA instance / Calisan bir inSCADA sunucusu

## Usage Examples / Kullanim Ornekleri

### Example 1: Monitor Live Values / Canli Degerleri Izleme

**User prompt:**
> "What is the current value of AN01_Active_Power?"

**What happens:**
1. Claude calls `list_projects` to find the project
2. Claude calls `inscada_get_live_value` with the variable name
3. Returns the current value, timestamp, and variable details

**Expected result:**
> AN01_Active_Power = 142.5 kW (last updated: 2026-03-05 14:32:10)

---

### Example 2: Analyze Historical Data / Tarihsel Veri Analizi

**User prompt:**
> "Show me the temperature trend for the last 24 hours and forecast the next 6 hours"

**What happens:**
1. Claude calls `inscada_logged_values` to fetch 24h of historical data
2. Analyzes the data pattern (min, max, avg, trend direction)
3. Generates forecast values based on the pattern
4. Calls `chart_forecast` to render the combined chart

**Expected result:**
A chart showing the historical temperature as a solid line and the 6-hour forecast as a dashed line with diamond markers.

---

### Example 3: Write a SCADA Script / SCADA Scripti Yazma

**User prompt:**
> "Write a script that checks if the boiler temperature exceeds 90 degrees and sends an email alert"

**What happens:**
1. Claude calls `inscada_guide` to load script writing rules (Nashorn ES5)
2. Generates a script following inSCADA conventions:
   ```javascript
   function main() {
     var temp = ins.getVariableValue("Boiler_Temperature");
     if (temp.value > 90) {
       ins.sendMail(["operator"], "High Temperature Alert",
         "Boiler temperature is " + temp.value + " C");
       ins.writeLog("WARN", "BoilerCheck", "Temperature exceeded 90C: " + temp.value);
     }
   }
   main();
   ```
3. Calls `update_script` to save the code (requires user confirmation)

**Expected result:**
Script is saved and ready to be scheduled. User confirms the write operation through the confirmation dialog.

---

### Example 4: Create a Dashboard Menu / Dashboard Menusu Olusturma

**User prompt:**
> "Create a gauge dashboard for AN01_Active_Power with a line chart"

**What happens:**
1. Claude calls `list_projects` to find the project ID
2. Calls `create_custom_menu` with the `gauge_and_chart` template, variable name, and project ID
3. A custom menu page is created in inSCADA with a live gauge and historical chart

**Expected result:**
A new menu item appears in inSCADA with a real-time gauge (updating every 2 seconds) and a time-series chart showing the last hour of data.

---

### Example 5: Export Data to Excel / Veriyi Excel'e Aktarma

**User prompt:**
> "Export all project scripts to an Excel file"

**What happens:**
1. Claude calls `list_projects` to get all projects
2. Calls `list_scripts` for each project
3. Calls `export_excel` with the collected data organized in sheets

**Expected result:**
An Excel file with project names as sheets, each containing script names, descriptions, schedule types, and status.

## Tools (39) / Araclar (39)

### Space Management

| Tool | Type | Description |
|------|------|-------------|
| `set_space` | Read | Switch active space / Aktif space degistirme |

### Data / Veri

| Tool | Type | Description |
|------|------|-------------|
| `list_spaces` | Read | List spaces / Space listesi |
| `list_projects` | Read | List projects / Proje listesi |
| `list_variables` | Read | List all variables (tags) / Tum degiskenleri listele |
| `search_variables` | Read | Search variables by name, description, type / Degisken ara |
| `list_scripts` | Read | List scripts / Script listesi |
| `get_script` | Read | Get script code & details / Script kodu ve detaylari |
| `update_script` | Write | Update script code / Script guncelleme |
| `list_connections` | Read | List connections / Baglanti listesi |
| `search_in_scripts` | Read | Search text in scripts / Scriptlerde metin arama |

### Animation / Animasyon

| Tool | Type | Description |
|------|------|-------------|
| `list_animations` | Read | List animations / Animasyon listesi |
| `get_animation` | Read | Get animation details / Animasyon detaylari |

### SCADA (REST API)

| Tool | Type | Description |
|------|------|-------------|
| `inscada_get_live_value` | Read | Read live value / Canli deger okuma |
| `inscada_get_live_values` | Read | Read multiple live values / Coklu canli deger |
| `inscada_set_value` | Write | Write value to variable / Deger yazma |
| `inscada_get_fired_alarms` | Read | Get active alarms / Aktif alarmlar |
| `inscada_connection_status` | Read | Connection status / Baglanti durumu |
| `inscada_project_status` | Read | Project status / Proje durumu |
| `inscada_run_script` | Write | Execute script / Script calistirma |
| `inscada_script_status` | Read | Script status / Script durumu |
| `inscada_logged_values` | Read | Historical log data / Tarihsel log verileri |
| `inscada_logged_stats` | Read | Statistics (min, max, avg, sum) / Istatistikler |

### Generic API

| Tool | Type | Description |
|------|------|-------------|
| `inscada_api_endpoints` | Read | List available API endpoints / API endpoint listesi |
| `inscada_api_schema` | Read | Get endpoint schema / Endpoint semasi |
| `inscada_api` | Write | Call any API endpoint / Herhangi bir API cagrisi |

### Charts / Grafikler

| Tool | Type | Description |
|------|------|-------------|
| `chart_line` | Read | Time series line chart / Zaman serisi cizgi grafik |
| `chart_bar` | Read | Bar chart / Cubuk grafik |
| `chart_gauge` | Read | Live gauge / Canli gosterge |
| `chart_multi` | Read | Multi-series chart / Coklu seri grafik |
| `chart_forecast` | Read | Forecast chart / Tahmin grafigi |

### Custom Menus / Menuler

| Tool | Type | Description |
|------|------|-------------|
| `list_custom_menus` | Read | List menus / Menu listesi |
| `get_custom_menu` | Read | Get menu details / Menu detaylari |
| `get_custom_menu_by_name` | Read | Find menu by name / Isme gore menu arama |
| `create_custom_menu` | Write | Create menu / Menu olusturma |
| `update_custom_menu` | Write | Update menu / Menu guncelleme |
| `delete_custom_menu` | Write | Delete menu / Menu silme |

### Export / Disa Aktarma

| Tool | Type | Description |
|------|------|-------------|
| `export_excel` | Write | Export to Excel (.xlsx) / Excel disa aktarma |

### Guide / Kilavuz

| Tool | Type | Description |
|------|------|-------------|
| `inscada_guide` | Read | Load usage rules and best practices / Kullanim kurallari ve en iyi pratikler |
| `inscada_animation_guide` | Read | Detailed animation element rules, return types, dynamic props / Animasyon element kurallari, return tipleri, dinamik props |

## Security / Guvenlik

All tools have MCP safety annotations (`readOnlyHint`, `destructiveHint`, `openWorldHint`).

Destructive tools require user confirmation:

- `inscada_set_value` — Writes to real equipment / Gercek ekipmana yazma
- `inscada_run_script` — Executes server-side script / Sunucu tarafinda script calistirma
- `update_script` — Modifies script code / Script kodunu degistirme
- `inscada_api` (POST/PUT/DELETE) — Modifies data via generic API / Genel API ile veri degistirme

## Privacy Policy

### Data Collection
This MCP server acts as a bridge between AI assistants and your inSCADA system. It does **not** collect, store, or transmit any data to third parties.

### Data Flow
- All communication is between the MCP client (e.g. Claude Desktop) and your inSCADA instance
- Credentials (username/password) are stored locally in your MCP client configuration
- No data is sent to inSCADA (the company) or any external service
- Optional anonymous telemetry (tool call counts, error rates) can be sent to the inSCADA telemetry server for improving the product. No personal data or SCADA values are included.

### Data Storage
- No user data is stored by this server
- Session tokens are kept in memory only and discarded on exit
- Downloaded Excel files are stored in the system temp directory and are not automatically cleaned up

### Contact
For privacy questions: habib.kara@inscada.com

## License / Lisans

MIT
