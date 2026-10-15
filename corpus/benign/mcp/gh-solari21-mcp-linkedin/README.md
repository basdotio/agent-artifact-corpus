# 🚀 MCP LinkedIn: Servidor Profesional de Contexto de Modelo (MCP)

<p align="left">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg?logo=python&logoColor=white" alt="Python" height="20"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP%20SDK-FastMCP-8A2BE2.svg" alt="MCP SDK" height="20"></a>
  <a href="https://playwright.dev/"><img src="https://img.shields.io/badge/engine-Playwright-2EAD33.svg?logo=playwright&logoColor=white" alt="Playwright" height="20"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" height="20"></a>
  <a href="https://github.com/solari21/mcp-linkedin/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" height="20"></a>
</p>

**MCP LinkedIn** es un servidor open-source de alto rendimiento construido sobre el **Model Context Protocol (MCP)**, **FastMCP** y **Playwright**. Permite a asistentes de inteligencia artificial (Claude Desktop, Gemini, Antigravity, Cursor, Cline) interactuar con LinkedIn de forma supervisada, respetuosa y orientada a la productividad profesional.

A diferencia de otros scripts de automatización opacos, **MCP LinkedIn** incorpora una filosofía estricta de **Human-in-the-Loop (HITL)** con salvaguardas obligatorias en dos fases (`confirm=True`) para acciones críticas, emulación de cadencia humana y un Plan B interactivo que permite resolver retos de seguridad sin pérdida de foco.

---

<p align="center">
  <img src="assets/infografia_mcp_linkedin.png" alt="MCP LinkedIn Infografía" width="850">
</p>

---

## 🌟 ¿Por qué MCP LinkedIn? (Comparativa Competitiva)

Actualmente existen implementaciones experimentales de MCP para LinkedIn en el ecosistema open source. La siguiente tabla resume las diferencias clave de ingeniería y fiabilidad:

| Característica / Capacidad | `stickerdaniel/linkedin-mcp` | `eliasbiondo/linkedin-mcp` | 🚀 **MCP LinkedIn (Este Proyecto)** |
|---|:---:|:---:|:---:|
| **Herramientas Disponibles** | 4 | 5 | **21 herramientas completas** |
| **Publicación Enriquecida con Imágenes** | ❌ Solo texto | ❌ No disponible | ✅ **Subida nativa HD (`expect_file_chooser`)** |
| **Primer Comentario Automático** | ❌ No | ❌ No | ✅ **Inyección automática para alcance orgánico** |
| **Control Total del Menú de 3 Puntos** | ❌ No | ❌ No | ✅ **Destacar, Guardar, Embed `<iframe>`, Editar, Borrar** |
| **Salvaguardas Human-in-the-Loop** | ❌ Ciego | ❌ Ciego | ✅ **Doble confirmación obligatoria (`confirm=True`)** |
| **Resiliencia ante Retos (2FA/CAPTCHA)** | ❌ Cuelgue / Error | ❌ Cuelgue / Error | ✅ **Plan B Interactivo sin robo de foco (`schtasks /IT`)** |
| **Sanitización de Cookies Anti-HTTP 999** | ❌ No | ❌ No | ✅ **Normalización de dominio y deduplicación `li_at`** |
| **Búsqueda 360° en Tiempo Real** | ⚠️ Parcial | ⚠️ Parcial | ✅ **Personas, Empleos con requisitos y Empresas** |
| **Inbox & Hilos de Conversación** | ⚠️ Básico | ❌ No | ✅ **Lectura de chats, hilos y envío supervisado** |
| **Emulación de Ritmo Humano** | ❌ Instantáneo | ❌ Instantáneo | ✅ **Jitter aleatorio gaussiano (1.5s - 3.0s)** |

---

## 🏛️ Arquitectura del Sistema

```mermaid
flowchart TD
    Client["🤖 Cliente MCP (Claude / Gemini / Cursor)"] -->|JSON-RPC via stdio| Server["⚡ FastMCP Server (linkedin_server.py)"]
    
    subgraph Core ["Núcleo de MCP LinkedIn"]
        Server --> Guard{"🛡️ Human-in-the-Loop\n(confirm=True)"}
        Guard -->|Acciones Críticas| ExecutionEngine["🕹️ Motor de Ejecución"]
        Guard -->|Sin Confirmación| RejectMsg["🛑 Rechazo Preventivo"]
        ExecutionEngine --> RateLimiter["⏳ Throttling & Jitter Humano"]
        RateLimiter --> BrowserManager["🌐 Browser Engine (Brave / Chromium)"]
    end
    
    subgraph Resilience ["Resiliencia y Sesión"]
        BrowserManager --> CookieSanitizer["🧹 Sanitizador Anti-HTTP 999"]
        CookieSanitizer --> SessionCheck{"¿Sesión Válida?"}
        SessionCheck -->|Sí| LinkedInWeb["💼 LinkedIn Web App"]
        SessionCheck -->|Reto / 2FA / Expirada| Fallback["🖥️ Plan B Interactivo (/IT)"]
        Fallback -->|Resolución de Usuario| LinkedInWeb
    end
```

---

## 🛠️ Catálogo Completo de Herramientas (21 Herramientas)

### A. Publicación y Distribución de Contenido
* `linkedin_create_post`: Crea publicaciones profesionales con formato, hashtags, imagen opcional en alta definición, publicación automática del primer comentario con enlaces y parámetro opcional `clean_previous_tests=True` para purga y deduplicación pre-flight de publicaciones previas de prueba.
* `linkedin_get_recent_posts`: Extrae el listado de publicaciones recientes del perfil autenticado, con conteo de impresiones y engagement.
* `linkedin_check_session`: Diagnostica la validez de la sesión activa, estado de cookies y conectividad con la plataforma.
* `linkedin_renew_session_interactive`: Despliega una ventana asistida no invasiva para resolver desafíos de 2FA o reCAPTCHA y sincronizar la sesión.

### B. Gestión de Publicaciones (Menú de 3 Puntos)
* `linkedin_toggle_feature_post`: Fija o desmarca una publicación en la sección de "Destacados" del perfil.
* `linkedin_toggle_save_post`: Almacena o retira un post de la lista de elementos guardados.
* `linkedin_get_post_embed_code`: Genera el fragmento HTML `<iframe>` para incrustar el post en sitios web externos.
* `linkedin_get_post_link`: Resuelve y limpia el enlace canónico directo y sin parámetros de rastreo.
* `linkedin_edit_post`: Abre el modal de edición de LinkedIn y actualiza el texto de una publicación existente.
* `linkedin_delete_post`: Elimina definitivamente una publicación (`confirm=True` mandatorio para evitar borrados accidentales).
* `linkedin_get_comment_settings_url`: Obtiene las directrices de configuración de privacidad de comentarios.

### C. Búsqueda y Prospección Profesional
* `linkedin_search_people`: Busca profesionales filtrando por palabras clave, cargo, empresa o ubicación.
* `linkedin_search_jobs`: Consulta ofertas laborales activas con filtros de ubicación y modalidad (remoto/híbrido).
* `linkedin_search_companies`: Localiza instituciones y empresas por sector o denominación.

### D. Bandeja de Entrada y Mensajería Supervisada
* `linkedin_get_inbox_messages`: Lee las conversaciones recientes de la bandeja `/messaging/` con marcas de lectura.
* `linkedin_get_conversation_thread`: Extrae el historial cronológico completo de un hilo de mensajes o contacto.
* `linkedin_send_message`: Redacta y envía mensajes directos con salvaguarda en dos fases (`confirm=True`).

### E. Inteligencia de Mercado, Perfiles y Feed
* `linkedin_get_profile_details`: Extracción estructurada de perfiles (Acerca de, Trayectoria laboral, Formación, Habilidades y Destacados).
* `linkedin_get_feed_posts`: Extrae las publicaciones destacadas del feed principal con conteo de reacciones.
* `linkedin_get_job_details`: Desglose exhaustivo de ofertas de empleo (requisitos clave, descripción íntegra y modalidad).
* `linkedin_get_company_details`: Información corporativa institucional (sector, tamaño de plantilla, sede y especialidades).

---

## 📦 Instalación y Puesta en Marcha

### Requisitos Previos
* **Python 3.10 o superior**
* **Navegador Brave** (recomendado para evasión nativa) o **Google Chrome / Chromium**

### Opción 1: Instalación Rápida con Instalador Asistido
Clona el repositorio y ejecuta el instalador automatizado para tu sistema operativo:

**En Windows:**
```cmd
git clone https://github.com/solari21/mcp-linkedin.git
cd mcp-linkedin
install.bat
```

**En Linux / macOS:**
```bash
git clone https://github.com/solari21/mcp-linkedin.git
cd mcp-linkedin
chmod +x install.sh
./install.sh
```

### Opción 2: Instalación Manual con Pip o Wheel Precompilado
```bash
# Modo editable para desarrollo:
pip install -e .

# O instalación directa del paquete precompilado:
pip install dist/mcp_linkedin-1.0.0-py3-none-any.whl

# Instalar los navegadores de Playwright:
playwright install chromium
```

---

## ⚙️ Configuración y Autenticación

Copia el archivo de ejemplo a `.env`:
```bash
cp .env.example .env
```

### Métodos de Autenticación Soportados

1. **Arquitectura Paso Cero CDP (Predeterminado y Recomendado - Zero-Login & Cero Fricción)**:
   * **Sincronización Pasiva en Caliente**: El servidor se conecta pasivamente al navegador del usuario (Brave Browser o Chrome en el puerto `9222`) vía Chrome DevTools Protocol (`Storage.getCookies`) mediante WebSocket directo.
   * **Cero Contraseñas y Cero Captchas**: Extrae las cookies ya autenticadas (`li_at`, `JSESSIONID`) en menos de 50 ms sin requerir credenciales en texto plano ni provocar retos reCAPTCHA.
   * **Inviolabilidad de la Sesión del Usuario (Anti-Revocación)**: Al evitar deliberadamente el login por formulario en subprocesos automatizados, se elimina por completo la política de revocación multi-sesión de LinkedIn, garantizando que el usuario **nunca sea expulsado de su sesión activa** en su navegador principal.
   * **Cero Robo de Foco**: Operación 100% silenciosa en segundo plano sin desplegar ventanas que compitan con el trabajo del usuario.

2. **Plan B Interactivo Supervisado (`linkedin_renew_session_interactive`)**:
   * Invocable de forma explícita mediante la herramienta MCP cuando el usuario o un reto puntual (2FA/reCAPTCHA) lo requiera en Windows (`schtasks /IT` con `SW_SHOWNOACTIVATE`).
   * **Erradicación de Bucles de Popups**: El servidor **NUNCA** abre ventanas físicas de forma desatendida o en bucle ante fallos de red o códigos HTTP 429/999. Si la sesión no es válida y no hay CDP activo, emite una excepción limpia `PermissionError` para que el usuario decida cuándo intervenir.

3. **Variables de Entorno (`.env`) (Entornos CI/CD / Servidores Headless)**:
   ```env
   LINKEDIN_EMAIL="tu_correo@ejemplo.com"
   LINKEDIN_PASSWORD="tu_password_seguro"
   ```

4. **Almacenamiento Persistente y Blindaje de Sesión**:
   * Las cookies se normalizan a `.linkedin.com` con esquema estricto Playwright, caducidad extendida a 1 año (`expires = now + 365 días`) y respaldo atómico inmune a sobreescrituras vacías (`.bak`) en:
   ```env
   LINKEDIN_STORAGE_STATE_FILE="./config/linkedin_storage_state.json"
   ```

> [!WARNING]
> ### 🛡️ Directrices Críticas de Resiliencia de Sesión (Lecciones de Producción)
> 1. **Prohibición de Procesos Headless Concurrentes**: Si tu navegador habitual (Brave Browser) tiene la sesión de LinkedIn abierta, **NO** inicies instancias independientes de Chromium/Playwright (`browser.launch()`). LinkedIn detecta colisiones de huellas y canales TLS simultáneos sobre la misma cuenta, revocando inmediatamente el token `li_at` y forzando la ventana de tu navegador a la pantalla de «¡Hola de nuevo!» pidiendo contraseña. Utiliza siempre la conexión por WebSocket CDP directo hacia tu pestaña activa.
> 2. **Prohibición de Formulario `/login` Automatizado**: Los scripts automatizados que introducen credenciales en el formulario web activan de inmediato los detectores de bot de LinkedIn y generan retos reCAPTCHA. La autenticación en este servidor se basa exclusivamente en tokens de sesión pasivos (`li_at`) capturados sin fricción.
> 3. **Conexión Ligera WebSocket CDP (<10ms)**: Playwright `connect_over_cdp` puede congelarse durante 180s al intentar indexar extensiones y background workers. Este servidor se comunica mediante llamadas JSON-RPC directas sobre `webSocketDebuggerUrl` a la pestaña específica, con latencia mínima y cero cuelgues.

---

## 🔌 Integración con Clientes MCP

### 1. Claude Desktop
Añade la siguiente configuración en tu archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "mcp-linkedin",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

### 2. Antigravity / Cursor / Cline
En tu archivo de configuración de servidores MCP (`mcp_config.json`):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "python",
      "args": [
        "-m",
        "linkedin_server"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

---

## 🔄 Integración Continua y Distribución (CI/CD)

El repositorio incluye flujos de trabajo automatizados con GitHub Actions para asegurar máxima fiabilidad y portabilidad:

* **CI - Build & Lint Verification (`ci.yml`)**: Valida en cada `push` y `pull request` la sintaxis Python, la integridad del AST y la compilación limpia del paquete en una matriz de entornos con Python 3.10, 3.11 y 3.12 sobre Ubuntu y Windows.
* **Build & Release Package Distribution (`publish_package.yml`)**: Al publicar un nuevo Release en GitHub o mediante ejecución manual, compila automáticamente las distribuciones Wheel (`.whl`) y tarball (`.tar.gz`), valida los metadatos con `twine check` y adjunta los binarios precompilados a la GitHub Release oficial mediante `softprops/action-gh-release@v2`.

---

## 🛡️ Filosofía Human-in-the-Loop, Propósito Ético y Respeto a la Plataforma

> [!NOTE]
> **Declaración de Propósito Ético y Respeto a la Plataforma:**  
> Este servidor MCP **no está diseñado para scraping masivo, prospección agresiva en frío ni para eludir las políticas o mecanismos de seguridad de LinkedIn**. Todo lo contrario: nace bajo un principio estricto de **mínima intrusión, uso estrictamente personal y cadencia respetuosa** con la plataforma. Creemos firmemente que la integración de la IA con redes profesionales debe sumar valor al usuario sin degradar la experiencia de la comunidad ni comprometer la integridad y estabilidad de la red.

### Salvaguardas Técnicas Implementadas
1. **Validación en Dos Fases (`confirm=True`)**: Las acciones que modifican el estado de la cuenta (como borrar una publicación o enviar un mensaje directo a un contacto) exigen confirmación explícita. Si el modelo de lenguaje intenta ejecutar la herramienta sin este parámetro, el sistema **no ejecuta la acción** y devuelve una solicitud de confirmación estructurada para el usuario humano, previniendo alucinaciones.
2. **Cadencia Humana y Anti-Saturación**: Incorpora pausas aleatorias gaussianas (*jitter* de 1.5s a 3.0s) entre peticiones para garantizar un ritmo natural y no sobrecargar la infraestructura del servicio.
3. **Supervisión Continua**: La IA actúa únicamente como un asistente personal bajo la supervisión directa y consciente de su propietario.

---

## 🙏 Créditos y Reconocimientos Open Source

Este proyecto se apoya y rinde tributo a las siguientes iniciativas y creadores de la comunidad de código abierto:

* **[@Daniel Sticker (stickerdaniel)](https://github.com/stickerdaniel/linkedin-mcp-server)**: Por los conceptos preliminares de mensajería e integración inicial de MCP con LinkedIn.
* **[@Elias Biondo (eliasbiondo)](https://github.com/eliasbiondo/linkedin-mcp-server)**: Por las ideas fundacionales sobre extracción modular de datos de perfiles.
* **[FastMCP](https://github.com/jlowin/fastmcp)**: Por proveer el framework Python más ergonómico y rápido para construir servidores MCP.
* **[Playwright](https://playwright.dev/)**: Por ofrecer el motor de automatización web más robusto y moderno del ecosistema.

---

## ⚖️ Descargo de Responsabilidad Legal (Legal Disclaimer)

> [!IMPORTANT]
> Este proyecto ha sido desarrollado con fines **estrictamente educativos, de investigación técnica sobre el protocolo Model Context Protocol (MCP) y para asistencia en productividad personal supervisada**.
> 
> * **No Afiliación**: Este software no está afiliado, respaldado, patrocinado ni certificado de ninguna forma por LinkedIn Corporation ni Microsoft Corporation.
> * **Cumplimiento de Términos**: El usuario es el único y exclusivo responsable de garantizar que el uso de esta herramienta se ajuste a los Términos de Servicio y Políticas de Uso de la plataforma LinkedIn.
> * **Uso Ético y No Invasivo**: Este software rechaza activamente el spam, el scraping masivo y cualquier uso no supervisado. El autor declina toda responsabilidad por cualquier uso indebido, abusivo o contrario a las normativas de la plataforma.

---

## 🗺️ Hoja de Ruta y TO-DO List (Roadmap)

Estado actual del proyecto y próximas funcionalidades planificadas (disponible también como tablero interactivo Kanban en [**GitHub Projects #2 - MCP LinkedIn Roadmap**](https://github.com/users/solari21/projects/2)):

### ✅ Implementado (v1.0.0)
- [x] **Publicación Oficial de Lanzamiento**: Post publicado en vivo en LinkedIn con infografía técnica y primer comentario verificado ([Ver en LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7515951568215588864/)).
- [x] **Arquitectura FastMCP 2.2+**: 21 herramientas registradas con tipado estricto e introspección de esquemas.
- [x] **Publicación Enriquecida**: Soporte para subida de imágenes HD con `expect_file_chooser()` y primer comentario automático con motor Tiptap.
- [x] **Control del Menú de 3 Puntos**: Fijar en destacados, guardar elementos, extraer snippet `<iframe>`, copiar enlace canónico, editar y eliminar publicaciones.
- [x] **Salvaguardas Human-in-the-Loop**: Confirmación en dos fases (`confirm=True`) en acciones destructivas o irreversibles.
- [x] **Plan B Interactivo sin Pérdida de Foco**: Detección de retos (2FA, reCAPTCHA) y proyección asistida con `schtasks /IT` en Windows.
- [x] **Sanitización de Cookies Anti-HTTP 999**: Normalización de dominios, desescape de comillas en `JSESSIONID` y deduplicación estricta de `li_at`.
- [x] **Búsqueda e Inteligencia 360°**: Motores de búsqueda de personas, ofertas de empleo con descripción íntegra y fichas corporativas de empresas.
- [x] **Bandeja de Entrada e Hilos**: Lectura de conversaciones recientes, consulta de hilos cronológicos y envío supervisado de mensajes.
- [x] **Empaquetado y Distribución**: Paquetes precompilados Wheel (`.whl`) y Source Distribution (`.tar.gz`) listos para instalar.

### 🛡️ Lecciones de Ingeniería y Selectores DOM en 2026
1. **Inputs Fantasma en `/login`**: LinkedIn inyecta campos ocultos en el DOM para autocompletado y WebAuthn con dimensiones 0 (`visible: false`). Se requiere forzar el pseudoselector `:visible` (`input[type="email"]:visible`, `input[type="password"]:visible`) para evitar `TimeoutError` en Playwright.
2. **Colisión de Botones SSO vs. Formulario**: El botón "Iniciar sesión con Microsoft" contiene el texto "Iniciar sesión". El envío debe realizarse mediante `Enter` en el input de contraseña (`press("Enter")`) o con coincidencia exacta de rol (`name="Iniciar sesión", exact=True`).
3. **Diálogos Modales Post-Publicación**: Tras crear una publicación, LinkedIn levanta un elemento flotante `<dialog data-testid="dialog">` que intercepta eventos de ratón. Se requiere enviar `Escape` preventivo o despachar clics mediante JavaScript nativo (`evaluate('b => b.click()')`).
4. **Editor Tiptap / ProseMirror**: La caja de comentarios no responde a `.fill()`; requiere interacción enfocada (`.click()`), tipeo con cadencia (`keyboard.type`) y saltos `Shift+Enter` para evitar envíos prematuros.
5. **Normalización Estricta de Dominio de Cookies (`.linkedin.com`)**: Restringir el dominio de `li_at` a `.www.linkedin.com` provocaba que Chromium omitiera la cookie en peticiones al dominio raíz (`linkedin.com/feed/`) y APIs internas, desencadenando redirecciones HTTP 302 hacia `/login` y bloqueos de tasa HTTP 429. Se normalizan todos los dominios canónicamente a `.linkedin.com`.
6. **Erradicación Radical del Bucle de Popups (Zero Invasive Windows)**: Se eliminó el lanzamiento automático de `trigger_interactive_session_renewal` en `ensure_authenticated()`. Si una sesión no está disponible, se emite una excepción limpia en lugar de invocar tareas en segundo plano que levanten ventanas físicas repetitivas.
7. **Persistencia Garantizada a 1 Año y Captura Pasiva CDP**: Captura en caliente de la cookie `li_at` desde la sesión activa de Brave (puerto 9222) mediante WebSocket directo (`Storage.getCookies` / `Network.getCookies`), con extensión de caducidad forzada a 365 días y respaldo atómico inmune a sobreescrituras vacías (`linkedin_storage_state.json.bak`).
8. **Prohibición de Procesos Headless Concurrentes y Revocación de `li_at`**: Al ejecutar un script en un subproceso de Playwright headless (`browser.launch()`) con cookies compartidas mientras el navegador regular (Brave) mantiene la sesión de LinkedIn abierta, el backend de LinkedIn detecta una discrepancia en huella/TLS/concurrencia de la misma cuenta. Como medida de seguridad, invalida de inmediato el token de sesión `li_at`, redirigiendo la pestaña del usuario a «¡Hola de nuevo!» para exigir la contraseña. La solución obligatoria es no lanzar navegadores secundarios si Brave está activo: toda interacción (edición, publicación, lectura) debe realizarse despachando llamadas CDP vía WebSocket directamente a la pestaña existente de Brave.
9. **Deduplicación Preventiva y Limpieza Pre-Flight de Posts Huérfanos de Prueba**: Antes de publicar una versión definitiva u oficial, el agente debe verificar las publicaciones recientes del perfil (`linkedin_get_recent_posts`) para identificar y eliminar de forma proactiva (`linkedin_delete_post(confirm=True)`) cualquier prueba preliminar o publicación duplicada, garantizando que el feed permanezca limpio y libre de posts de prueba obsoletos.
10. **Desambiguación de Botones en Comentarios Tiptap**: En el árbol DOM de LinkedIn, el botón "Comentar" coexiste en dos instancias (el toggle de la barra de acciones inferior y el disparador de envío primario de la caja de comentarios con estilos `hcbgmy hcbhay`). Es mandatorio apuntar al botón primario de envío tras la inyección de saltos de línea con `Shift+Enter` y verificar la existencia efectiva del texto en el DOM antes de dar por completada la tarea.



### 📋 Próximas Funcionalidades (Backlog)
- [ ] **Encuestas Interactivas (Polls)**: Creación y monitorización de votos en encuestas de LinkedIn.
- [ ] **Publicación Programada Nativa**: Programación de posts diferidos en fecha y hora específica.
- [ ] **Carruseles y Documentos PDF**: Soporte para publicación de presentaciones diapositiva a diapositiva.
- [ ] **Exportador de Analíticas**: Volcado estructurado de estadísticas de impresiones y reacciones a formato SQLite y CSV.
- [ ] **Webhooks Locales**: Notificaciones en tiempo real al recibir mensajes directos en la bandeja de entrada.

---

## 📄 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo [LICENSE](./LICENSE) para más detalles.
