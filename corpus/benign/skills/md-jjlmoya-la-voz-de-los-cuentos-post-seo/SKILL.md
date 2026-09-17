---
name: post-seo
description: Genero posts de blog SEO en ESPAÑOL E INGLÉS simultáneamente. Creo archivos TypeScript en src/data/posts/, genero contenido en bloques y los importo en index.js. Invócame cuando necesites nuevo contenido multiidioma.
---

# QUÉ HACE
Genero automáticamente posts de blog completos, bilingües y optimizados para SEO:
- Leo posts existentes en AMBOS idiomas
- Identifico temas de alto tráfico no cubiertos todavía
- Elijo dinámicamente un tema nuevo (dormir, edad, beneficios, emociones, etc.)
- Creo contenido en español + traducción al inglés simultáneamente
- Contenido variado: headings, párrafos, listas, tablas, quotes, highlights, stats, gráficas, pasos, comparativas
- **Requisitos SEO Obligatorios**:
    - Mínimo **1500 PALABRAS** por post (en cada idioma). Validado por `npm run test:bilingual`.
    - Al menos **una** recomendación de cuento (`story_recommendation`). **STRICT REQUIREMENTS:**
        1. **NO REPETIR:** No uses siempre los mismos cuentos (ej: "el-finalizador").
        2. **STORY TAGS:** Consulta `src/data/es/storyTags.ts` para encontrar cuentos que encajen REALMENTE con el tema del post.
        3. **RELEVANCIA:** Si el post es sobre "miedo", usa cuentos de la categoría `miedo`. Si es sobre "amistad", usa la categoría `amistad`.
        4. **SLUGS VÁLIDOS:** Usa el campo `key` de `src/data/es/stories.json` (ES) o `src/data/en/stories.json` (EN).
        5. **🔴 POSICIÓN OBLIGATORIA:** La PRIMERA `story_recommendation` DEBE estar **ANTES del 1/3 del post**. Valida con `npm run validate:posts`. Ejemplo: si un post tiene 60 bloques, la primera recomendación debe estar antes del bloque 20.
    - **TÍTULOS POTENTES (Core SEO):** No uses títulos genéricos. La gente busca soluciones a problemas reales.
        - *Mal:* "Cómo mejorar la concentración"
        - *Bien:* "¿Tu hijo no se concentra? 7 técnicas con cuentos para entrenar su atención"
        - *Estructura:* Usa preguntas directas, números (listas) y el beneficio claro.
    - **JUSTIFICACIÓN DE CUENTOS (Obligatorio):** Cada vez que se use un bloque `story_recommendation`, la `description` DEBE explicar explícitamente **por qué** ese cuento soluciona o ayuda al problema tratado en el post. No basta con un resumen; debe haber una conexión terapéutica o educativa clara.
    - **CLIFFHANGER ANTES DE LA CARD (Enganche):** La última frase del bloque de texto inmediatamente anterior a un `story_recommendation` DEBE ser un gancho que invite a la lectura, genere curiosidad o prometa una solución.
    - Fecha actual: **2026-03-14** (Formato: `YYYY-MM-DD`).
- Guardo en archivos `.ts` dentro de `src/data/posts/es/` y `src/data/posts/en/`
- Actualizo `src/data/posts/index.ts` para importar y exportar los nuevos posts.
- **CATEGORÍAS:** Libertad total. Cualquier categoría que elijas (ej: Emociones, Salud, Creatividad) tendrá un color asignado automáticamente en el listado.
- **BRANDING:**
    - Español: "**La Voz de los Cuentos**".
    - Inglés: "**BuboBoo**".
- **NOTA:** Todo manual, sin scripts intermedios

# MI PROCESO

## 1. Leo posts existentes
Abro: `src/data/posts/es/` y `src/data/posts/en/`
Extraigo slugs, títulos, keywords de archivos `.ts` existentes

## 2. Detectar gaps SEO e identificar RECOMENDACIONES
Identifico:
- Qué temas NO están cubiertos
- Palabras clave con alto tráfico pero sin contenido
- **RECOMENDACIÓN:** Busco en `src/data/es/storyTags.ts` qué cuentos coinciden con el tema elegido para la `story_recommendation`.
- **MAPEADO DE LLAVES:** Uso `node scripts/find-story.js <key_es> es` para obtener automáticamente la llave correspondiente en inglés (o viceversa), asegurando que los posts bilingües estén perfectamente sincronizados.

## 3. Elegir tema único
Selecciono un tema nuevo:
- dormir, edad, beneficios, emociones, concentración, creatividad, lectura, conducta, frustración, paciencia, etc.
- Aseguro que no exista en ES ni EN

## 4. Crear archivos TypeScript
Creo dos archivos `.ts`:
- `src/data/posts/es/[slug-tema].ts` (post en español)
- `src/data/posts/en/[slug-tema-en].ts` (post en inglés)

Estructura de cada archivo:
```typescript
export const post = {
  slug: "tema-url",
  slugEs: "tema-url", // Obligatorio
  slugEn: "english-topic", // Obligatorio
  title: "...",
  description: "...",
  date: "2026-03-14",
  category: "Educativo|Consejos|Desarrollo",
  tags: ["keyword1", "keyword2"],
  content: [ bloques ]
}
```

## 5. Actualizar index.ts
Agrego líneas en `src/data/posts/index.ts`:
```typescript
import { post as nuevoNombreEs } from './es/[nuevo-slug]'
import { post as nuevoNombreEn } from './en/[nuevo-slug-en]'
```

Luego agrego a los arrays `postsEs` y `postsEn`.

## 6. Estructura de bloques
Tipos disponibles:
- `heading` (h2/h3)
- `text` (párrafos)
- `list` (items)
- `table` (datos)
- `quote` (citas)
- `highlight` (callouts: info/tip/success/warning)
- `stats` (números)
- `barchart` (gráficas)
- `steps` (procesos)
- `comparison` (vs)

# EJEMPLO DE SALIDA

**Post generado:**
```json
{
  "slug": "cuentos-desarrollar-empatia-ninos",
  "slugEn": "stories-develop-empathy-children",
  "title": "Cómo Usar Cuentos para Desarrollar Empatía en Niños",
  "description": "Descubre técnicas probadas para usar historias infantiles y fortalecer la empatía emocional en tus hijos.",
  "date": "2024-03-12",
  "category": "Educativo",
  "tags": ["empatía", "cuentos", "desarrollo emocional", "niños"],
  "content": [
    { "type": "heading", "level": 2, "text": "¿Por qué la empatía es crucial?" },
    { "type": "text", "body": "La empatía es..." },
    { "type": "list", "style": "unordered", "items": [...] },
    ...más bloques...
  ]
}
```

**Confirmación en consola:**
```
✅ Post generado: "Cómo Usar Cuentos para Desarrollar Empatía en Niños"
📊 Tema: empatía
📁 Palabras: 1847
✅ Guardado en: src/data/es/posts.json
```

# CUÁNDO USARLO
- Necesitas generar nuevo contenido de blog rápidamente
- Quieres posts SEO sin esfuerzo manual
- Buscas cubrir nuevas palabras clave de alto tráfico
- Ya tienes posts base y quieres expandir contenido

# VALIDACIÓN (TÚ EJECUTAS)
Después que genero posts, ejecutas:

**1. Validar contenido de posts (OBLIGATORIO):**
```bash
npm run validate:posts
```

Verifica:
- ✅ **Toda recomendación de cuento está ANTES del 1/3 del post**
- ✅ **Todos los posts tienen al menos una story_recommendation**
- ✅ Coverage porcentaje

**2. Validar estructura bilingüe:**
```bash
npm run test:bilingual
```

Verifica automáticamente:
- ✅ **Mínimo 1500 palabras** por post (en cada idioma)
- ✅ Mismo número ES/EN
- ✅ Slugs pareados correctamente
- ✅ Campos obligatorios
- ✅ Sin posts huérfanos

# RESUMEN
- ✅ Sin scripts intermedios - todo directo
- ✅ Bilingüe automático - ES + EN al mismo tiempo
- ✅ Análisis de gaps - elijo temas que faltan
- ✅ Contenido variado - 8+ tipos de bloques
- ✅ Slugs pareados - slug ↔ slugEn/slugEs
- ✅ Test de paridad - verifica que ES/EN estén sincronizados
- **Solo me invocas, yo genero todo**
