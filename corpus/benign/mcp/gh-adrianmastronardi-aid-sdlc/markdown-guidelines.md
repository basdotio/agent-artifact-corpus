# Markdown Guidelines

Estas pautas establecen un formato consistente para escribir y mantener documentos en Markdown
dentro de repositorios de desarrollo de software. Su objetivo es facilitar la lectura por humanos y
la interpretación correcta por herramientas y copilotos, evitando fricciones y asegurando que la
documentación pueda servir como **infraestructura crítica** del AI-Driven SDLC.

---

## Encabezados

- Utiliza siempre encabezados **ATX** (`#`, `##`, `###`), no subrayados (`===` o `---`).
- Un único `#` (H1) por documento, al inicio.
- Deja **una línea en blanco** antes y después de cada encabezado para mejorar el renderizado y el
  diff.
- Usa títulos claros y concisos, evitando signos de puntuación innecesarios.
- En español, utiliza _sentence case_:  
  `## Instalación y configuración` (no “Instalación Y Configuración”).
- No numerar los encabezados de secciones y subsecciones de forma manual, salvo en casos
  excepcionales donde la numeración sea necesaria para referencia cruzada o para seguir un estándar
  técnico específico. En esos casos, justificar su uso en el propio documento.

---

## Párrafos y espaciado

- Separa los párrafos con **una línea en blanco**.
- No insertes espacios al final de línea.
- No uses dobles espacios para forzar salto de línea; si necesitas un salto explícito, usa `<br>`.
- Mantén un ancho máximo de línea de **100 caracteres** para mejorar la legibilidad en CLI y reducir
  diffs ruidosos.

---

## Listas

- Usa `-` para listas no ordenadas.
- Usa `1.` repetido para listas ordenadas (el renderer numerará automáticamente).
- Deja una línea en blanco antes de empezar la lista y después de terminarla.
- Indenta sublistas con 2 espacios.

Ejemplo:

```markdown
- Paso uno
- Paso dos
  - Subpaso
```

---

## Bloques de código

- Usa **fences** (```) y especifica el lenguaje para activar resaltado.
- Mantén el código válido y sin comillas “inteligentes”.
- No mezcles tabs y espacios.
- Abre y cierra correctamente el bloque, con el código en líneas separadas.

Ejemplo:

```bash
touch hello-world.c
vi hello-world.c
```

---

## Tablas

- Usa la primera fila como encabezado y separa columnas con `|`.
- No intentes alinear manualmente con espacios; deja que lo haga un formateador automático si lo
  usas.
- Mantén el contenido breve en cada celda para evitar cortes al visualizar en CLI.

Ejemplo:

```markdown
| ID  | Descripción |
| --- | ----------- |
| 1   | Item 1      |
```

---

## Enlaces e imágenes

- Usa rutas relativas dentro del repo cuando sea posible.
- Proporciona texto alternativo significativo para accesibilidad.
- Evita URLs largas en línea; utiliza enlaces con texto descriptivo.
- Para imágenes SVG (por ejemplo, diagramas Mermaid exportados), preferir SVG si se requiere
  escalabilidad; usar PNG/JPG para capturas de pantalla.

Ejemplo:

```markdown
![Diagrama del flujo de build](docs/build-flow.png)  
[Guía de contribución](CONTRIBUTING.md)
```

---

## Nombres de archivo y estructura

**Convención oficial:**

1. **Archivos raíz convencionales (MAYÚSCULAS)**  
   Usar mayúsculas para los archivos reconocidos por plataformas y herramientas:  
   `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`.

2. **Resto de archivos (minúsculas con guiones)**  
   Para todos los demás `.md` (documentación técnica, guías internas, contextos, specs, etc.):  
   `architecture.md`, `security.md`, `markdown-guidelines.md`.

3. **Documentos de release**  
   Si están bajo `/docs/` u otra carpeta, usar minúsculas con guiones:  
   `docs/release-notes-2025-08.md`, `docs/release-checklist.md`.

**Reglas adicionales:**

- Coloca documentos extensos en `docs/` y deja `README.md` en la raíz.
- Usa front-matter (`---`) solo si es requerido por el generador de sitio, y documenta qué campos se
  permiten.
- Todos los archivos deben guardarse en **UTF-8 sin BOM**.

---

## Estilo general

- Prefiere frases cortas y directas.
- Evita párrafos muy largos (más de 5–6 líneas).
- Usa viñetas o tablas para resumir información técnica.
- Mantén consistencia terminológica y evita mezclar idiomas en un mismo documento.
- Evita caracteres especiales, emojis o símbolos que puedan romper el renderizado o la
  compatibilidad.
- Usa enlaces internos con anclas (`[Texto](#seccion)`) en documentos largos para facilitar la
  navegación.

---

## Herramientas de validación y formateo

Para asegurar que las reglas de este documento se apliquen de forma consistente:

- **Prettier**  
  Usar con la configuración por defecto para Markdown:

  ```bash
  prettier --write "filename.md"
  ```

  Ajustar las reglas necesarias en `.prettierrc` (por ejemplo, `printWidth: 100`).

- **markdownlint**  
  Instalar y configurar en `.markdownlint.json` para validar las reglas definidas aquí.

- **Pre-commit**  
  Configurar un hook de pre-commit para ejecutar tareas de validación y formateo antes de confirmar
  cambios. Esto puede incluir formateo de código, validación de estilo, ejecución de linters,
  pruebas unitarias u otras verificaciones necesarias.

  Ejemplo para formatear y validar archivos Markdown usando Husky:

  ```bash
  npx husky add .husky/pre-commit "npx prettier --write '**/*.md' && npx markdownlint '**/*.md'"
  git add .husky/pre-commit
  ```

  Esto garantiza que todos los archivos `.md` se formateen y validen automáticamente antes de cada
  commit.

- **Integración con VS Code**
  - Instalar las extensiones **Prettier** y **markdownlint**.
  - Activar `"editor.formatOnSave": true` y definir Prettier como formateador por defecto para
    Markdown.
  - Así el formateo se aplica al guardar y Husky lo valida antes del commit.

---

## Validación automática de numeración y unicidad de IDs en backlog

Para asegurar que los archivos del backlog (`task-XXXXX.md` y `epic-XXXXX.md`) cumplan las reglas
definidas en `tasks-guidelines.md`, se recomienda configurar una validación automática mediante
pre-commit hook o CI.

**Reglas a validar:**

- El nombre de archivo debe seguir la convención:
  - `task-00001.md`
  - `epic-00001.md`
- El número (`00001`) debe tener cinco dígitos con ceros a la izquierda.
- No puede existir el mismo número para más de un archivo, sin importar el tipo.
- El campo `id` en `index.yaml` debe coincidir con el número en el nombre de archivo.
- El valor de `type` en `index.yaml` debe ser `task` o `epic`, según corresponda.

**Ejemplo de integración con Husky:**

```bash
npx husky add .husky/pre-commit \
"scripts/validate-backlog-ids.sh && npx prettier --write '**/*.md' && npx markdownlint '**/*.md'"
git add .husky/pre-commit
```
