---
name: DTV Marketing Manager
description: Automatiza la creación y programación de contenido diario para Meta Business Suite siguiendo la estrategia de Despierta tu Voz
version: 1.0.0
author: Despierta tu Voz Team
tags: [marketing, automation, meta, instagram, facebook, content-generation]
---

# DTV Marketing Manager Skill

## 📋 Descripción

Esta Skill automatiza el proceso completo de marketing diario para "Despierta tu Voz", generando contenido estratégico (Post + Story) optimizado para Meta Business Suite, manteniendo coherencia visual y utilizando tracking de Bitly.

## 🎯 Objetivo

Generar y programar contenido coherente con la identidad de marca siguiendo un calendario estratégico semanal y basándose PRIMORDIALMENTE en los artículos de la base de conocimiento (Blog). Incluye piezas específicas para nichos (Directores de Coro, Profesores de Canto y Cantantes), evitando frases competitivas con profesores de canto y manteniendo un tono cálido, humano y profesional.

## 🛡️ Reglas de Calidad y Salvaguardas (¡CRÍTICO!)

1.  **Anti-Fallback:** Está ESTRICTAMENTE PROHIBIDO publicar o subir como borrador a Meta cualquier contenido que contenga la cadena `[FALLBACK]`. Si la IA falla en la generación del copy, el sistema debe abortar la publicación inmediatamente para proteger la imagen de marca. 
2.  **Validación de Nichos:** Asegurar que los posts de nicho (Directores/Profesores) no usen términos prohibidos como "batuta" o "competencia técnica".
3.  **Detección de Errores:** Cualquier error en la generación de imágenes o acortamiento de links detendrá el proceso de publicación.
4.  **Contenido Basado en Blog (Obligatorio):** Todo copy debe nacer de la esencia de un artículo real del blog (`resources/blog_knowledge.json`). Está PROHIBIDO usar `EXAMPLES.md` o crear teorías genéricas. Si no hay un artículo relacionado, se debe usar la filosofía general de la marca pero manteniendo siempre el tono del blog.

## 🔧 Configuración Requerida

### Variables de Entorno (.env)

```env
# Meta Graph API
META_ACCESS_TOKEN=your_meta_access_token_here
META_PAGE_ID=your_facebook_page_id
META_INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id

# Bitly API
BITLY_ACCESS_TOKEN=your_bitly_token_here

# Configuración
DTV_BASE_URL=https://despiertatuvoz.vercel.app
DTV_PUBLISH_MODE=draft  # draft | publish | assets_only
```

### Permisos Requeridos Meta Graph API

- `instagram_content_publish`
- `pages_manage_posts`
- `pages_show_list`
- `instagram_basic`
- `pages_read_engagement`

## 📅 Plan Estratégico Semanal

| Día | Tipo | Enfoque | CTA |
|-----|------|---------|-----|
| Lunes | Filosófico | Reflexión basada en artículos de Amor/Creatividad | Descubre más |
| Martes | Coaching | Tip técnico basado en artículos de Psicología/Paz | Prueba el ejercicio |
| Miércoles | Nicho: Coros | Basado en "Carta al solista corista" | Empieza gratis |
| Jueves | Coaching | Basado en artículos de Bloqueos/Patrones | Únete al reto |
| Viernes | Filosófico | Inspiración basada en artículos de Naturaleza/Ego | Reflexiona |
| Sábado | Promoción | Caso de éxito o Amor/Dar (Blog) | Descubre tu voz |
| Domingo | Coaching | Preparación basada en artículos de Mente/Naturaleza | Planifica tu práctica |

## 🧠 Base de Conocimiento (Blog)

La Skill utiliza un motor de conocimiento (`resources/blog_knowledge.json`) que contiene la esencia de los artículos de `despiertatuvoz.com`. El generador de contenido DEBE:
1. Identificar el artículo más relevante para el tema del día.
2. Extraer el mensaje central o las metáforas clave del artículo.
3. Redactar el post de forma que sea una extensión del blog, invitando siempre a profundizar en el post completo o con el Mentor en la App.

## 🎨 Estética Visual

Beige tones, warm studio, vocal coaching aesthetic, high-end photography, 
minimalist design, professional lighting, soft shadows, elegant composition
```

**Temáticas Visuales por Nicho:**
- **General:** Estudio de canto, micrófonos elegantes, personas cantando.
- **Directores de Coro:** Manos expresivas en movimiento, gestos de dirección, grupos de personas ensayando, partituras corales (Sin batuta).
- **Profesores:** Pianos de cola, primer plano de laringe (estilizado), partituras clásicas, entorno pedagógico.
- **Cantantes/Coralistas:** Micrófono de estudio, partitura en atril, expresión de confianza, primer plano vocal.

**Formatos:**
- **Feed Post:** 1080x1080 (1:1)
- **Story:** 1080x1920 (9:16)

## 🚀 Modos de Operación

### 1. **DRAFT Mode** (Recomendado)
Publica el contenido en Meta Business Suite como borrador para revisión humana final.

### 2. **PUBLISH Mode**
Publica directamente el contenido programado para las 18:00 CET del mismo día.

### 3. **ASSETS_ONLY Mode**
Genera únicamente los assets (imagen + copy + link) y los guarda localmente sin publicar.

## 📝 Uso

### Ejecución Manual

```bash
node .agent/skills/dtv_marketing_manager/scripts/run.js
```

### Ejecución con Parámetros

```bash
# Ejecutar contenido según el plan semanal (Día actual)
node .agent/skills/dtv_marketing_manager/scripts/run.js

# Ejecutar un nicho específico (Se programará para su día recomendado)
node .agent/skills/dtv_marketing_manager/scripts/run.js --niche=choral_directors

# Ejecutar todos los nichos para la semana (Cada uno se programará en su día)
node .agent/skills/dtv_marketing_manager/scripts/run.js --niche=choral_directors
node .agent/skills/dtv_marketing_manager/scripts/run.js --niche=vocal_teachers
node .agent/skills/dtv_marketing_manager/scripts/run.js --niche=singers_choristers
```

### 📅 Distribución Semanal de Nichos
Para evitar la saturación y los posts repetidos, cada nicho tiene un día asignado:
- **Miércoles:** Directores de Coro
- **Jueves:** Profesores de Canto
- **Viernes:** Cantantes y Coralistas

El sistema detecta automáticamente estos días al usar el flag `--niche`.

### Automatización con Cron (Opcional)

```bash
# Ejecutar todos los días a las 08:00 CET
0 8 * * * cd /path/to/despierta-tu-voz-app && node .agent/skills/dtv_marketing_manager/scripts/run.js
```

## 🔄 Workflow de Ejecución

### Step 1: Análisis del Contexto
- Detecta el día de la semana actual
- Consulta el plan estratégico semanal
- Determina el tipo de contenido (Filosófico, Promoción, Coaching)

### Step 2: Generación de Copy (Basada en Blog)
- Consulta el "Almacén de Sabiduría" (`blog_knowledge.json`)
- Selecciona un artículo que resuene con el tipo de contenido y día
- Extrae la esencia, metáforas y tono del autor original
- Genera copy unificado para Feed y Story que actúe como "gancho" hacia el artículo completo
- Evita frases competitivas con profesores de canto
- Incluye CTA apropiado que conecte el Blog con la App

### Step 3: Generación de Visuales
- Crea imagen 1:1 para Feed Post usando el prompt dinámico
- Crea imagen 9:16 para Story usando el mismo estilo
- Mantiene coherencia visual con la identidad de marca

### Step 4: Acortamiento de URL
- Genera link corto con Bitly
- Incluye parámetros UTM para tracking:
  - `utm_source=instagram`
  - `utm_medium=social`
  - `utm_campaign=daily_content`
  - `utm_content={day}_{type}`

### Step 5: Publicación/Guardado
Según el modo configurado:
- **DRAFT:** Envía a Meta Graph API en modo borrador
- **PUBLISH:** Programa publicación para las 18:00 CET
- **ASSETS_ONLY:** Guarda en `output/{date}/`

## 👥 Segmentación de Audiencias (Nuevos Targets)

Además del contenido general, se generan tres piezas semanales para nichos específicos:

### 1. Directores de Coro (Enfoque: Rendimiento Grupal)
- **Foco:** Psicología del grupo, empaste vocal y estado emocional colectivo.
- **Argumento:** La tensión en un coro a menudo es emocional (estrés/miedo).
- **Solución DTV:** Herramienta para que el coralista llegue preparado individualmente, mejorando el grupo.

### 2. Profesores de Técnica Vocal (Enfoque: Aliado Pedagógico)
- **Foco:** Pedagogía y gestión del bloqueo emocional del alumno.
- **Argumento:** El profesor se centra en la técnica (laringe, apoyo); la app gestiona la frustración entre clases.
- **Solución DTV:** Mentor IA como asistente para el alumno fuera del aula.

### 3. Cantantes y Coralistas (Enfoque: Confianza)
- **Foco:** Confianza individual, miedo a destacar o tensión emocional.
- **Argumento:** El miedo aprieta la emisión.
- **Solución DTV:** Espacio privado para ganar confianza antes del ensayo.

## ✍️ Directrices de Redacción

- **Tono:** Técnico y profesional pero cálido.
- **Léxico Clave:** Resonancia, aducción, pasaje, empaste, gestión del aire.
- **Estructura:** Empezar con reflexión o pregunta de valor. SIN SPAM DIRECTO. El enlace de la App se ofrece como recurso gratuito de apoyo al final.

## 📂 Estructura de Archivos

```
.agent/skills/dtv_marketing_manager/
├── SKILL.md                          # Este archivo
├── scripts/
│   ├── run.js                        # Script principal de ejecución
│   ├── content_generator.js          # Generación de copy
│   ├── image_generator.js            # Generación de imágenes
│   ├── meta_publisher.js             # Publicación en Meta
│   ├── bitly_shortener.js            # Acortamiento de URLs
│   └── calendar_logic.js             # Lógica del calendario
├── resources/
│   ├── weekly_plan.json              # Plan estratégico detallado
│   ├── prompts.json                  # Prompts para generación
│   ├── hashtags.json                 # Banco de hashtags
│   └── copy_templates.json           # Templates de copy
├── output/                           # Assets generados (git-ignored)
└── .env.example                      # Template de variables

```

## 🛡️ Seguridad

- **Nunca** commitees el archivo `.env` con tokens reales
- Usa `.env.example` como template
- Los tokens deben tener permisos mínimos necesarios
- Revisa los borradores antes de publicar en modo PUBLISH

## 📊 Logs y Monitoreo

Los logs se guardan en:
```
.agent/skills/dtv_marketing_manager/logs/{date}.log
```

Incluyen:
- Timestamp de ejecución
- Tipo de contenido generado
- URLs de publicación
- Errores y warnings

## 🔍 Troubleshooting

### Error: "Invalid OAuth Token"
- Verifica que `META_ACCESS_TOKEN` sea válido
- Regenera el token en Meta for Developers
- Confirma que los permisos estén activos

### Error: "Bitly API Error"
- Verifica `BITLY_ACCESS_TOKEN`
- Confirma que la URL base sea accesible

### Error: "Image Generation Failed"
- Verifica la conexión a internet
- Revisa los prompts en `resources/prompts.json`

## 📈 Métricas y Análisis

La Skill genera un reporte semanal con:
- Posts publicados vs programados
- Engagement estimado
- Links más clickeados (vía Bitly)
- Sugerencias de optimización

## 🎯 Roadmap

- [ ] Integración con Analytics para A/B testing
- [ ] Generación de Reels automáticos
- [ ] Respuestas automáticas a comentarios
- [ ] Integración con LinkedIn y Twitter
- [ ] Dashboard de métricas en tiempo real

## 📞 Soporte

Para dudas o mejoras, contacta al equipo de Despierta tu Voz.
