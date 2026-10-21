---
name: landing-page
description: Genera landing pages para clientes nuevos — pide nombre/marca, rubro y tono, recomienda el stack según el cliente, define la dirección visual con la skill frontend-design, escribe el copy en español, construye la landing (responsive, SEO y accesibilidad básicos), la verifica con capturas y ofrece deploy. Usar cuando el usuario pide "crear una landing", "armar una landing", "landing para un cliente nuevo", "hacer la página web de un negocio", una web de una sola página para un negocio, o invoca /landing-page. También cuando dice "esta quedó aprobada" sobre una landing.
---

# Landing page para cliente nuevo

Cada landing es para un cliente real distinto. El objetivo es entregar algo con identidad propia (no una plantilla), listo para publicar, con todo lo pendiente señalado claramente. Hablá en español rioplatense.

Archivos de referencia en la carpeta de esta skill (leelos cuando el flujo lo indique):
- `stacks.md` — catálogo de stacks, costos, hosting y formularios
- `rubros.md` — secciones, CTA y estilo típicos por rubro
- `tonos.md` — cómo suena el copy en cada tono
- `aprobadas.md` — landings que gustaron (punto de partida para clientes parecidos)

No construyas nada antes de que el usuario elija stack y dirección visual: rehacer una landing entera porque se eligió mal el enfoque es mucho más caro que una pregunta.

## Paso 0 — frontend-design (obligatorio)

Toda decisión visual sale de la skill `frontend-design`, no de criterio propio.

1. Verificá si está instalada: `ls ~/.claude/skills/frontend-design/SKILL.md .claude/skills/frontend-design/SKILL.md 2>/dev/null`
2. Si no está, instalala global:
   ```bash
   npx skills add https://github.com/anthropics/skills --skill frontend-design -g --agent claude-code -y
   ```
   (`--agent` y `-y` evitan que el instalador quede esperando respuestas interactivas.) Verificá que exista `~/.claude/skills/frontend-design/SKILL.md`. **Si el comando falla o el archivo no aparece, mostrale el error al usuario y frená.** No sigas sin la skill.
3. Leé su `SKILL.md` completo (con el Skill tool si aparece disponible; si se acaba de instalar, leé el archivo directamente) y aplicá sus lineamientos en los pasos 4 y 6.

## Paso 1 — Inputs y brief

Si existe `brief.md` en la carpeta actual, leelo primero y preguntá solo lo que falte o lo que el usuario quiera cambiar.

**Obligatorios** (si falta alguno, preguntá y no avances; nunca inventes datos del cliente):
1. Nombre de la página / marca
2. Rubro
3. Tono

**Opcionales** — preguntalos en el mismo mensaje, aclarando que se pueden saltear: colores o logo, WhatsApp (y mensaje precargado), email, redes, servicios/productos principales, ciudad, ID de Google Analytics y/o Meta Pixel.

Guardá todo en `brief.md` (carpeta actual) con esta forma, y actualizalo a medida que se definen cosas:

```markdown
# Brief — <Marca>
- Rubro: · Tono: · Ciudad:
- Colores/logo: · WhatsApp: (mensaje: "") · Email: · Redes:
- Servicios/productos:
- Analytics: GA= · Meta Pixel=
## Stack
<elegido + por qué>
## Dirección visual
<concepto, paleta, tipografías>
## Pendientes / placeholders
```

Lo que el usuario no dio queda como `—` (no lo completes con datos inventados).

## Paso 2 — Stack

Saltealo si el usuario ya indicó el stack o si `brief.md` ya lo tiene (salvo que pida cambiarlo).

Hacé en **un solo mensaje** las preguntas que falten:
- ¿Una sola página o varias secciones/páginas?
- ¿El cliente va a editar contenido solo (textos, fotos, precios)?
- ¿Necesita extras (blog, tienda, turnos, formularios complejos, multi-idioma)?
- ¿Dónde se hostea y hay presupuesto para hosting/servicios pagos?
- ¿Qué tan rápido hay que entregarla?

Con las respuestas, leé `stacks.md` y recomendá **2-3 stacks factibles**, cada uno con: para qué caso conviene, pros, contras, costo aproximado de hosting y dificultad de mantenimiento. Marcá uno como **recomendado** con el porqué en una línea. Esperá la elección y guardala en el brief.

## Paso 3 — Punto de partida

Leé `aprobadas.md` (¿hay alguna del mismo rubro o tono?) y la sección del rubro en `rubros.md`. Son punto de partida, no plantilla: el cliente nuevo tiene que verse distinto.

## Paso 4 — Dirección visual

Aplicando `frontend-design` sobre el rubro + tono (+ colores/logo si los hay), proponé **2-3 direcciones** cortas, cada una con:
- Concepto en una línea
- Paleta (3-5 colores con hex)
- Tipografías (títulos + texto, de Google Fonts o similares)

Que sean realmente distintas entre sí. Esperá a que elija y registrala en el brief.

## Paso 5 — Copy

Leé `tonos.md`. Escribí todo el copy en español, adaptado al tono (voseo argentino si el tono es cercano o juvenil). Concreto y específico del cliente; nada de frases que sirvan para cualquier negocio. Lo que no sepas (precios, años de trayectoria, cantidad de clientes) va como placeholder visible, no inventado.

## Paso 6 — Construcción

Antes de escribir: si la carpeta actual tiene archivos además de `brief.md`, listalos y preguntá antes de sobrescribir.

Secciones base (ajustalas al rubro según `rubros.md`):
1. Hero — titular, subtítulo, CTA principal
2. Servicios / productos
3. Beneficios / por qué elegirnos
4. Testimonios — placeholders marcados como tales (ej. "[Testimonio de ejemplo — reemplazar]")
5. FAQ
6. Contacto / CTA final — botón de WhatsApp `https://wa.me/<número sin + ni espacios>?text=<mensaje URL-encoded>` si hay número
7. Footer

Requisitos técnicos:
- **Responsive, mobile first.**
- **SEO básico**: `title`, meta description, Open Graph + Twitter card con imagen OG (si no hay, generá una simple 1200×630 con la marca y marcala como pendiente de reemplazo), `lang="es"`, favicon, HTML semántico, un solo `h1`.
- **Accesibilidad básica**: `alt` en imágenes, contraste AA, jerarquía de headings sin saltos, foco visible, labels en el formulario.
- Analytics: si hay IDs, snippet activo; si no, snippet comentado con `TODO`.
- Formulario de contacto con la solución que indica `stacks.md` para el stack elegido.

Incluí un `README.md` corto: cómo correrla localmente, cómo editar textos/imágenes/colores, y la lista de placeholders.

## Paso 7 — Checklist de entrega

Verificá y reportá cada punto como **OK** o **pendiente** (con el motivo):
- [ ] Favicon
- [ ] Title, meta description y Open Graph completos (con imagen OG)
- [ ] Formulario de contacto funcional (sin datos/cuenta → listo para conectar y pendiente)
- [ ] Link de WhatsApp con mensaje precargado
- [ ] Google Analytics y/o Meta Pixel (sin IDs → snippet comentado y pendiente)
- [ ] Todos los links y botones apuntan a algo real o están marcados como placeholder (`grep -n 'href="#"'` y similares)
- [ ] Build sin errores (si el stack tiene build)

## Paso 8 — Auto-verificación con capturas

1. Levantá la landing: con un HTML suelto, `python3 -m http.server <puerto>` en la carpeta; con framework, su dev server o preview. Corré el servidor en segundo plano.
2. Capturas con Playwright (si falta el navegador, `npx -y playwright install chromium` primero), guardadas en el directorio temporal de la sesión, **no** en el proyecto:
   ```bash
   npx -y playwright screenshot --full-page --wait-for-timeout 1500 --viewport-size=390,844 http://localhost:<puerto> <tmp>/mobile.png
   npx -y playwright screenshot --full-page --wait-for-timeout 1500 --viewport-size=1440,900 http://localhost:<puerto> <tmp>/desktop.png
   ```
3. Mirá las capturas buscando: desborde horizontal, textos cortados o superpuestos, contraste bajo, secciones rotas, imágenes que no cargan, fuentes que no cargaron.
4. Corregí y volvé a capturar hasta que esté limpio.
5. Al final: borrá las capturas y apagá el servidor.

## Paso 9 — Deploy (opcional)

Preguntá si quiere publicarla. **Nunca deployes sin confirmación explícita.** Recomendá la plataforma que mejor encaje con el stack (ver `stacks.md`; ojo con planes gratuitos que no permiten uso comercial). Si confirma, deployá y devolvé el link público. Si falta login o CLI, explicá el paso exacto que tiene que hacer el usuario y esperá.

## Paso 10 — Resumen final

Corto:
- Stack usado
- Archivos generados
- Dirección visual elegida
- Resultado del checklist (OK / pendiente)
- Placeholders a reemplazar con info real

## "Esta quedó aprobada"

Cuando el usuario diga que una landing quedó aprobada, agregá una entrada a `aprobadas.md` (en la carpeta de esta skill, ej. `~/.claude/skills/landing-page/aprobadas.md`) con la plantilla que tiene ese archivo, usando los datos del `brief.md` del proyecto. Preguntá en una línea qué fue lo que más le gustó al cliente si no lo dijo; es el dato más valioso para las próximas.
