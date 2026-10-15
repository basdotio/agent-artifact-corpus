# Checklist Maestro de Tareas: MCP Linkedin (LinkedIn Automation Server)

## 📌 Histórico Acumulativo de Fases

### Fase 1: Arquitectura y Diseño del Servidor MCP
- [x] Validación empírica de selectores y flujo de publicación (Login, File Chooser, Contenteditable, Publicar, Comentarios)
- [x] Implementación de `linkedin_server.py` con FastMCP 2.2+ y Playwright headless

### Fase 2: Herramientas Básicas del Núcleo
- [x] `linkedin_create_post`: Publicación de texto enriquecido con emojis, imágenes y primer comentario
- [x] `linkedin_get_recent_posts`: Extracción de publicaciones recientes y métricas de impresiones
- [x] `linkedin_check_session`: Verificación de salud y estado de la sesión activa

### Fase 3: Suite Completa del Menú de 3 Puntitos
- [x] `linkedin_toggle_feature_post`: Destacar / Quitar de destacados en la parte superior del perfil
- [x] `linkedin_toggle_save_post`: Guardar / Quitar de guardados en elementos personales
- [x] `linkedin_get_post_embed_code`: Extracción del snippet HTML `<iframe>` para incrustar en webs
- [x] `linkedin_get_post_link`: Obtención y copia del enlace canónico directo
- [x] `linkedin_edit_post`: Edición del texto de publicaciones existentes
- [x] `linkedin_delete_post`: Eliminación definitiva con salvaguarda obligatoria `confirm=True`
- [x] `linkedin_get_comment_settings_url`: Control y acceso a opciones de privacidad de comentarios

### Fase 4: Motores de Búsqueda y Prospección Profesional
- [x] `linkedin_search_people`: Búsqueda de personas y profesionales con filtros geográficos y de cargo
- [x] `linkedin_search_jobs`: Búsqueda de ofertas de trabajo activas (Madrid, remoto, etc.)
- [x] `linkedin_search_companies`: Búsqueda de organizaciones, instituciones y empresas

### Fase 5: Verificación y Pruebas Iniciales
- [x] Validación de introspección de esquemas FastMCP
- [x] Verificación empírica de selectores DOM en vivo
- [x] Documentación inicial de pruebas en `walkthrough.md`

### Fase 6: Registro en Entorno Antigravity
- [x] Configuración del servidor en `mcp_config.json` (`"linkedin"`)
- [x] Registro en catálogo de proyectos de Antigravity (`af5d9fbb-585e-431c-8a0a-64cd55a8e0e3.json`)

### Fase 7: Gobernanza y Skill Global
- [x] Creación de Skill Global `linkedin-automation` en `~/.gemini/config/skills/linkedin-automation/SKILL.md`
- [x] Registro como Entrada #21 en Sección V de `AGENTS.md`

### Fase 8: Plan B de Resiliencia: Ventana Interactiva Brave (/IT)
- [x] Implementación de `renew_session_interactive()` con proyección asistida `schtasks /IT`
- [x] Integración de fallback automático ante expiración, captchas o 2FA
- [x] Cero robo de foco garantizado (`SW_SHOWNOACTIVATE`)

### Fase 9: Benchmark Open-Source (`stickerdaniel` & `eliasbiondo`)
- [x] Análisis forense e ingeniería inversa de ambos proyectos de referencia
- [x] Módulo desacoplado `linkedin_extended.py` con parsers resilientes y jitter gaussiano
- [x] Integración de 7 herramientas adicionales para alcanzar el catálogo completo de 21 herramientas:
  - [x] `linkedin_get_inbox_messages`: Consulta de conversaciones recientes con no leídos y timestamps
  - [x] `linkedin_get_conversation_thread`: Lectura del historial completo de chats
  - [x] `linkedin_send_message`: Envío seguro con salvaguarda HITL en dos fases (`confirm=True`)
  - [x] `linkedin_get_profile_details`: Extracción profunda del perfil (Acerca de, Experiencias, Habilidades)
  - [x] `linkedin_get_feed_posts`: Extracción de publicaciones del timeline global por botones semánticos
  - [x] `linkedin_get_job_details`: Detalle íntegro de ofertas laborales y modalidades
  - [x] `linkedin_get_company_details`: Detalle corporativo de instituciones y empresas

### Fase 10: Validación Empírica Integral (Zero Mocks)
- [x] Verificación end-to-end contra datos reales de LinkedIn de las 21 herramientas
- [x] Corrección de falsos positivos de timeout (`wait_until="commit"`)
- [x] Sanitización estricta de cookies para evitar errores `HTTP 999`
- [x] Empaquetado oficial en Wheel (`.whl`) y Source Distribution (`.tar.gz`) en `dist/`

### Fase 11: Despliegue de Arquitectura Paso Cero CDP y Motor Tiptap
- [x] Implementación de conexión pasiva en caliente vía WebSocket al puerto 9222 de Brave Browser
- [x] Protección anti-revocación multi-sesión (eliminación del login redundante por formulario)
- [x] Adaptación del editor de comentarios a componentes ricos `div.tiptap.ProseMirror` con tipeo simulado y saltos `Shift+Enter`
- [x] Sincronización de tableros Kanban en GitHub Projects V2 (#2)

### Fase 12: Primera Publicación, Auditoría de Calidad y Retirada
- [x] Publicación inicial de prueba (`urn:li:activity:7515912088733515776`)
- [x] Auditoría de calidad visual: la infografía generada tenía estética de cómic/infantil no alineada con el estándar profesional
- [x] Eliminación limpia y definitiva de la publicación mediante `linkedin_delete_post(confirm=True)`

### Fase 13: Renovación de Fuentes en Gemini NotebookLM y Generación Blueprint v2
- [x] Conexión al cuaderno `bad774e8-adeb-458a-8632-cff7ca06c94e` con credenciales de `solari21@gmail.com`
- [x] Purga permanente de fuentes obsoletas en el cuaderno
- [x] Ingesta de las versiones actuales de la documentación:
  - `README.md`
  - `SKILL.md`
  - `TODO.md`
  - `walkthrough.md`
  - Repositorio GitHub (`https://github.com/solari21/mcp-linkedin`)
- [x] Creación de nuevo artefacto Studio de tipo Infografía (`12c8df74-bf0d-47e8-857e-4aced02915da`) con prompt técnico especializado:
  - Estilo: Arquitectura de software / Blueprint técnico de ingeniería de sistemas
  - Esquema modular: Núcleo de navegación dual, seguridad gaussiana, selectores DOM y catálogo de 21 herramientas
- [x] Descarga de la infografía en alta resolución: [infografia_mcp_linkedin.png](file:///c:/Users/solari21.SOLARI21PC/Antigravity%20Projects/MCP%20Linkedin/assets/infografia_mcp_linkedin.png) (2752×1536 px, 5.03 MB)
- [x] Commit y push oficial a la rama `main` en GitHub (`commit d293fb2`)

### Fase 14: Diagnóstico Forense del Reto de Seguridad LinkedIn y Checkpoints
- [x] Descubrimiento de inputs fantasma en `/login`: LinkedIn inyecta campos invisibles (`visible: false`) para autocompletado y WebAuthn
- [x] Análisis forense del checkpoint de seguridad: los intentos de login automatizados desde IP/huella nueva invalidaron temporalmente `li_at`, levantando el reCAPTCHA ("Vamos a hacer una comprobación rápida de seguridad")
- [x] Detección de bucle de ventanas emergentes por invocación automática de `schtasks /IT` ante fallos de sesión

### Fase 15: Erradicación Radical del Bucle de Popups y Blindaje de Persistencia a 1 Año
- [x] Supresión definitiva de la invocación automática de `trigger_interactive_session_renewal` en `ensure_authenticated` (cero ventanas no solicitadas)
- [x] Normalización estricta del dominio de cookies a `.linkedin.com` (erradicando omisiones por subdominio `www`)
- [x] Configuración de expiración persistente de 1 año (`now + 365 días`) para cookies críticas (`li_at`, `JSESSIONID`, `li_rm`)
- [x] Creación de copia de seguridad atómica `linkedin_storage_state.json.bak` blindada contra sobreescrituras vacías
- [x] Prohibición absoluta de tecleo automatizado de credenciales en `/login` para evitar reCAPTCHA y revocación de sesión
- [x] Extracción comprehensiva dual en CDP: WebSocket directo a nivel navegador (`Storage.getCookies`) y nivel pestaña activa (`Network.getCookies`)

### Fase 16: Captura Pasiva de Sesión en Brave y Verificación Headless
- [x] Monitorización pasiva vía CDP de la sesión autenticada en Brave Browser (puerto 9222)
- [x] Guardado atómico de `li_at` con vigencia de 1 año (`expires` en 2027) y sincronización a `.bak`
- [x] Verificación de acceso al feed en modo 100% headless y anónimo con cookies normalizadas a `.linkedin.com`

### Fase 17: Publicación Oficial Definitiva del Post y Primer Comentario
- [x] Publicación del post oficial en LinkedIn con texto enriquecido completo y nueva infografía Blueprint v2 (`infografia_mcp_linkedin.png`)
- [x] Atribución íntegra: Daniel Sticker (@stickerdaniel en GitHub) y Elias Biondo en LinkedIn
- [x] Publicación del primer comentario verificado en DOM con enlace directo al repositorio GitHub (`https://github.com/solari21/mcp-linkedin`)
- [x] Captura de URL canónica de la actividad: `https://www.linkedin.com/feed/update/urn:li:activity:7515951568215588864/`
- [x] Sincronización de documentación (`README.md`, `walkthrough.md`, `task.md`) y push final a GitHub

### Fase 18: Blindaje Documental, Lecciones de Producción y Sincronización Global
- [x] Documentación exhaustiva en `TODO.md` de la erradicación del bucle de popups y salvaguardas de sesión
- [x] Inclusión de alerta técnica en `README.md` sobre prohibición de subprocesos concurrentes y captura pasiva CDP
- [x] Matriz forense completa de incidencias y causas raíz en `walkthrough.md` (Sección 11)
- [x] Actualización de gobernanza global en `AGENTS.md` (Regla II.32 y Sección V.21) y `SKILL.md`
- [x] Verificación de integridad con `agents_guardian.py` y `py_compile` (0 NameError, sintaxis limpia)
- [x] Sincronización íntegra con GitHub (commit y push a `main`)
