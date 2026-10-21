# 📋 TO-DO List & Roadmap - MCP LinkedIn

Lista de tareas, funcionalidades activas y backlog evolutivo para el servidor **MCP LinkedIn**.

> 📌 **Tablero de Seguimiento en Vivo**: Consulta el estado en tiempo real en [MCP LinkedIn Roadmap & Development (GitHub Projects V2)](https://github.com/users/solari21/projects/2).
> 📦 **Releases Oficiales**: Consulta los paquetes y notas de versión en [GitHub Releases](https://github.com/solari21/mcp-linkedin/releases).

---

## 🚀 Versión 1.0.0 (Lanzamiento Inicial - Completado)

- [x] **Arquitectura y Core MCP**:
  - [x] Migración a SDK FastMCP (mcp>=1.2.0) con decoradores `@mcp.tool()`.
  - [x] Arquitectura Paso Cero CDP: sincronización pasiva de cookies desde Brave CDP (puerto 9222) sin introducir credenciales ni provocar revocación multi-sesión.
  - [x] Gestión de ciclo de vida del navegador (Brave Browser primario con fallback a Chromium).
  - [x] Manejo inteligente de credenciales mediante `.env`, variables de entorno y archivos JSON locales.
  - [x] Soporte para modo Headless y Plan B interactivo asistido en Windows (`schtasks /IT`).

- [x] **Publicación y Distribución de Contenido**:
  - [x] Creación de publicaciones de texto con emojis y hashtags (`linkedin_create_post`).
  - [x] Carga de imágenes en alta resolución mediante `expect_file_chooser()`.
  - [x] Publicación automática de primer comentario con enlaces para evitar penalización de alcance.
  - [x] Consulta de publicaciones recientes con métricas de impresiones y engagement (`linkedin_get_recent_posts`).
  - [x] Publicación definitiva en vivo en LinkedIn con texto enriquecido íntegro, infografía técnica Blueprint v2 en alta resolución y primer comentario verificado ([Ver en LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7515951568215588864/)).

- [x] **Gobernanza de Sesión, Resiliencia y Erradicación de Logins Recurrentes**:
  - [x] **Erradicación Radical del Bucle de Popups**: Supresión definitiva de la llamada automática a `trigger_interactive_session_renewal` en `ensure_authenticated()`. Emisión de excepción limpia `PermissionError` en lugar de programar tareas en `schtasks /IT`.
  - [x] **Prohibición de Subprocesos Playwright Concurrentes**: Regla estricta contra el lanzamiento de instancias independientes de Chromium si el navegador del usuario (Brave) mantiene una sesión activa de LinkedIn, evitando la revocación automática de `li_at` por colisión de huellas en la misma cuenta.
  - [x] **Conexión Pasiva WebSocket CDP por Target**: Conexión directa y ligera (<10ms) a `ws://127.0.0.1:9222/devtools/page/<id>` para interactuar sobre la pestaña real de Brave, sorteando el cuelgue de 180s derivado de la enumeración de targets de `connect_over_cdp`.
  - [x] **Prohibición Terminante de Formulario en `/login`**: Prohibido el tecleo automatizado de usuario y contraseña en la web de login para evitar el bloqueo preventivo por bot y retos reCAPTCHA.
  - [x] **Persistencia Garantizada a 1 Año y Copia Atómica `.bak`**: Normalización obligatoria de dominios de cookies a `.linkedin.com` y extensión forzada de expiración a 365 días para `li_at`, `JSESSIONID` y cookies clave con respaldo atómico seguro.
  - [x] **Integridad Estricta de Contenido Enriquecido**: Respeto escrupuloso de los textos solicitados por el usuario (ganchos, 5 suites arquitectónicas, propósito ético, 21 herramientas, atribuciones completas a Daniel Sticker en GitHub y Elias Biondo en LinkedIn) prohibiendo resúmenes unilaterales.
  - [x] **Deduplicación Preventiva y Limpieza Pre-Flight de Posts Huérfanos**: Protocolo obligatorio antes de publicar versiones definitivas para auditar posts recientes del perfil y eliminar publicaciones de prueba obsoletas con `linkedin_delete_post(confirm=True)`.
  - [x] **Desambiguación de Selectores Tiptap en Comentarios**: Identificación precisa del botón primario de envío (`hcbgmy hcbhay`) y verificación estricta de renderizado en DOM para erradicar fallos silenciosos o comentarios en borrador.


- [x] **Control Integral del Menú de 3 Puntos**:
  - [x] Fijar y desmarcar de destacados del perfil (`linkedin_toggle_feature_post`).
  - [x] Guardar y retirar de marcadores guardados (`linkedin_toggle_save_post`).
  - [x] Extracción de código HTML `<iframe>` para incrustar posts (`linkedin_get_post_embed_code`).
  - [x] Copia y resolución de enlace canónico directo y limpio (`linkedin_get_post_link`).
  - [x] Edición de publicaciones existentes desde modal de LinkedIn (`linkedin_edit_post`).
  - [x] Eliminación segura con factor de confirmación (`linkedin_delete_post`).
  - [x] Consulta de directrices de privacidad de comentarios (`linkedin_get_comment_settings_url`).

- [x] **Búsqueda e Inteligencia Profesional**:
  - [x] Buscador de profesionales por palabras clave, cargo y ubicación (`linkedin_search_people`).
  - [x] Buscador de empleos activos con filtro de modalidad (`linkedin_search_jobs`).
  - [x] Ficha completa de oferta de trabajo con requisitos y cuerpo íntegro (`linkedin_get_job_details`).
  - [x] Buscador y ficha institucional de empresas (`linkedin_search_companies`, `linkedin_get_company_details`).
  - [x] Extracción profunda de perfil personal (`linkedin_get_profile_details`).
  - [x] Extracción de publicaciones del feed principal (`linkedin_get_feed_posts`).

- [x] **Bandeja de Entrada y Mensajería Supervisada**:
  - [x] Lectura de conversaciones en `/messaging/` con marcas de no leído (`linkedin_get_inbox_messages`).
  - [x] Consulta cronológica de hilos de mensajes específicos (`linkedin_get_conversation_thread`).
  - [x] Envío supervisado con salvaguarda en dos fases (`confirm=True`) (`linkedin_send_message`).

- [x] **Empaquetado, CI/CD y Distribución**:
  - [x] Estándar PEP 621 con `pyproject.toml` y entry points de consola (`mcp-linkedin`).
  - [x] Precompilación de paquetes Wheel (`.whl`) y tarball (`.tar.gz`) en `dist/`.
  - [x] Instaladores asistidos `install.bat` (Windows) e `install.sh` (Linux/macOS).
  - [x] Workflows de GitHub Actions para CI (lint, sintaxis y build) y distribución automática de binarios (.whl y .tar.gz) en GitHub Releases con action-gh-release.

---

---

## 🚀 Versión 1.1.0 (Inteligencia Editorial, Estrategia y Anti-IA - Completado)

- [x] **Suite de Heurística Anti-IA y Limpieza de Huella Sintética**:
  - [x] Motor de humanización en 3 pasadas (`linkedin_humanize`): purga de 17 caracteres invisibles, normalización tipográfica y sustitución de 113+ términos corporativos trillados con preservación de URLs.
  - [x] Panel heurístico de 5 verificaciones (`linkedin_detect_ai`): Burstiness, Specificity, Slop Density, Fingerprint y Voice, adaptado para evaluación natural bilingüe (EN/ES) con veredicto PASS/REVIEW/FLAGGED.

- [x] **Estrategia de Copywriting y Conversión de Alto Impacto**:
  - [x] Calibrador de ganchos contra 21 fórmulas probadas (`linkedin_hook_score`) con control de límites visibles de corte móvil (140 car) y escritorio (210 car).
  - [x] Rúbrica objetiva de 12 elementos sobre 100 puntos (`linkedin_score_profile`) con diagnóstico priorizado *Fix-First*.
  - [x] Generador de comentarios profesionales basado en 9 arquetipos de alto valor (`linkedin_generate_comment`), erradicando comentarios clónicos.
  - [x] Planificador de carruseles PDF verticales en ratio 4:5 (`linkedin_carousel_planner`) con reglas de retención y boilerplate HTML/CSS.
  - [x] Desglose y reciclaje de activos largos en 4 publicaciones semanales independientes (`linkedin_repurpose_content`).
  - [x] Secuencia de prospección por mensaje directo en 4 fases (`linkedin_dm_sequence`) con nota de invitación $\le$ 200 caracteres y follow-ups espaciados.

- [x] **Triaje de Interacciones y Detección de Bots**:
  - [x] Triaje automatizado de la bandeja de entrada (`linkedin_triage_inbox`) en LEAD, RECRUITER, PEER, ASK y SPAM, detectando secuencias frías automatizadas.
  - [x] Triaje de respuestas a publicaciones propias (`linkedin_triage_replies`) para priorizar debate y leads en la primera hora de publicación.

- [x] **Distribución Oficial y Automatización Continua (CI/CD)**:
  - [x] Publicación oficial de la Release `v1.1.0` en [GitHub Releases](https://github.com/solari21/mcp-linkedin/releases/tag/v1.1.0) con binarios precompilados (`.whl` y `.tar.gz`).
  - [x] Inclusión del módulo `linkedin_cdp.py` en `py-modules` de `pyproject.toml` para empaquetado 100% íntegro.
  - [x] Workflow de Auto-Release en push a `main` (`.github/workflows/publish_package.yml`) con resolución dinámica de versión desacoplada en script dedicado (`.github/scripts/resolve_version.py`), erradicando `python -c` inline, colisiones de entrecomillado en Bash y NameError con booleanos, anti-duplicación de changelogs y `action-gh-release@v3` (Node 24 sin advertencias).
  - [x] Infografía y Diagrama de Arquitectura de 5 capas y 6 bloques funcionales diseñado bajo el estándar editorial canónico `diagram-design` (HTML + SVG standalone y PNG de alta resolución sin distorsión).
  - [x] Diagrama de Flujo Operativo End-to-End diseñado y exportado con MCP `diagram-design` (Taste Gate 100%, SVG/PNG), sustituyendo los bloques Mermaid sobredimensionados en `README.md` y `GUIA_USO.md`.
  - [x] Norma canónica *Release Exit Gate* en `AGENTS.md` (Regla 0.8) y `github-automation` (`SKILL.md`).
  - [x] Sincronización continua de hitos en el tablero Kanban [MCP LinkedIn Roadmap](https://github.com/users/solari21/projects/2).

---

## 🔮 Versión 1.2.0 (Próximas Funcionalidades / Backlog)

- [ ] **Encuestas Interactivas (Polls)**:
  - [ ] Herramienta para crear encuestas con opciones múltiples y duración configurable.
  - [ ] Consulta y monitorización de votos y porcentajes en tiempo real.

- [ ] **Publicación Programada Nativa**:
  - [ ] Aprovechamiento del selector nativo de LinkedIn para programar fecha y hora diferida.

- [ ] **Subida Automática de Carruseles PDF**:
  - [ ] Automatización de subida directa de archivos PDF generados al modal de publicación de LinkedIn.

- [ ] **Exportación y Métricas Históricas**:
  - [ ] Exportación periódica de analíticas a bases de datos locales SQLite o archivos CSV/Excel.
