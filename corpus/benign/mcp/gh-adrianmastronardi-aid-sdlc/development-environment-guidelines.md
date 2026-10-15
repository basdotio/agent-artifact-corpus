# Guía de Configuración: Ambiente de Desarrollo con Cursor

Este documento detalla los lineamientos de configuración para el ambiente de desarrollo usando Cursor IDE como la principal herramienta. El objetivo es estandarizar el entorno de trabajo para maximizar la productividad, la calidad del código y la colaboración en equipo.

## 📋 Tabla de Contenidos

- [1. IDE y Compatibilidad](#1-ide-y-compatibilidad)
- [2. Extensiones de Backend](#2-extensiones-de-backend)
- [3. Extensiones de Frontend](#3-extensiones-de-frontend)

---

## 1. IDE y Compatibilidad

### **IDE Principal**
- **Cursor** - Versión mínima: 1.4

### **Sistemas Operativos Soportados**

| Sistema Operativo | Estado | Recomendación |
|------------------|---------|---------------|
| **macOS** | ✅ Estable | **Recomendado** |
| **Windows** | ✅ Estable | **Recomendado** |
| **Linux** | ⚠️ Limitado | No recomendado (genera fricción) |

---

## 2. Extensiones de Backend

### **AWS y Nube**
- **AWS Toolkit** (`amazonwebservices.aws-toolkit-vscode`)
  - Integración directa con servicios AWS (Lambda, SAM, CloudFormation)
  - Gestión de credenciales

### **Python**
- **Python** (`ms-python.python`)
  - Soporte completo para el lenguaje
  - Incluye depuración, pruebas y gestión de entornos
- **Pylance** (`ms-python.vscode-pylance`)
  - Motor de análisis estático e IntelliSense
  - Mejora velocidad y precisión
- **Python Debugger** (`ms-python.debugpy`)
  - Herramienta de depuración esencial

### **Calidad de Código y Análisis**
- **SonarLint** (`sonarsource.sonarlint-vscode`)
  - Análisis estático en tiempo real
  - Detecta bugs, "code smells" y vulnerabilidades
- **SonarLint On‑Demand Analyzers** (`sonarsource.sonarlint_ondemand-analyzers`)
  - Analizadores complementarios para mejorar detección

### **Git y Control de Versiones**
- **GitLens** (`eamodio.gitlens`)
  - Información avanzada de Git
  - Blame enriquecido, historiales detallados y comparaciones
- **Git History** (`donjayamanne.githistory`)
  - Visualización y búsqueda en historial de commits
- **Git Blame** (`waderyan.gitblame`)
  - Muestra quién y cuándo modificó cada línea
- **Git Extension Pack** (`donjayamanne.git-extension-pack`)
  - Paquete de utilidades de Git
- **Conventional Commits**
  - Genera commits con estructura estandarizada
- **.gitignore Generator** (`codezombiech.gitignore`)
  - Genera plantillas de .gitignore rápidamente

### **DMN**
- **Red Hat DMN Editor** (`redhat.vscode-extension-dmn-editor`)
  - Editor para archivos DMN (Decision Model and Notation)

### **Esquemas y Formatos**
- **YAML** (`redhat.vscode-yaml`)
  - Soporte completo para archivos YAML
  - Validación, autocompletado y esquemas
- **XML** (`redhat.vscode-xml`)
  - Soporte avanzado con validación XSD y formateo
- **OpenAPI Preview** (`zoellner.openapi-preview`)
  - Visualización de especificaciones OpenAPI/Swagger

### **Productividad y Navegación**
- **Project Manager** (`alefragnani.project-manager`)
  - Gestión y cambio rápido entre proyectos
- **Open in GitHub** (`ziyasal.vscode-open-in-github`)
  - Abre archivos, líneas o repositorios directamente en GitHub

### **Visualización y UX**
- **CodeViz** (`codeviz.codeviz`)
  - Visualización de estructura y dependencias del código
- **Material Theme** (`equinusocio.vsc-material-theme`)
  - Tema visual basado en Material Design
- **Material Theme Icons** (`equinusocio.vsc-material-theme-icons`)
  - Iconos a juego con el tema visual
- **Material Icon Theme** (`pkief.material-icon-theme`)
  - Set alternativo de iconos para el explorador

---

## 3. Extensiones de Frontend

### **Automatización de Código**
- **Auto Import**
  - Corrige errores de componentes no importados
  - Atajo: `Cmd + Enter`
- **Auto Rename Tag**
  - Modifica automáticamente etiquetas de cierre al cambiar apertura
- **Better Comments**
  - Estilos diferenciados para comentarios (bloques, líneas, TODO)
  - Definición por colores y resaltado

### **Identificación de Errores y Formato**
- **Error Lens**
  - Resalta errores de sintaxis directamente en la línea
- **ESLint**
  - Linter para análisis y corrección de código JavaScript
- **Prettier ESLint**
  - Integra Prettier y ESLint para formateo consistente
- **Prettier VSCode**
  - Formateador de código universal

### **Snippets y Atajos**
- **JavaScript Snippets**
  - Atajos para bloques de código JavaScript
- **React Snippets**
  - Plantillas de componentes React
  - Ejemplo: `rafce` (React Arrow Function Component Export)

### **Herramientas de Depuración**
- **Redux Dev Tools**
  - Depuración de Redux
- **Jest**
  - Pruebas unitarias
- **Jest Runner**
  - Ejecuta pruebas de Jest desde el editor
- **Playwright**
  - Pruebas de integración y end-to-end

### **Productividad Adicional**
- **Turbo Console.log**
  - Genera `console.log()` automáticamente
  - Atajo: `Ctrl + Cmd + Option + L`
- **Wakatime**
  - Medición de tiempo de programación por proyecto
- **Git History y Git Graph**
  - Visualización gráfica del historial de commits

---

## 📝 Notas Importantes

- Todas las extensiones listadas son **obligatorias** para el desarrollo
- Mantener las extensiones actualizadas para evitar conflictos
- Configurar preferencias según estándares del equipo
- Reportar problemas de compatibilidad al equipo de desarrollo

---

## 🔄 Mantenimiento

- Revisar mensualmente nuevas versiones de extensiones
- Validar compatibilidad con nuevas versiones de Cursor
- Actualizar esta guía cuando se agreguen o modifiquen extensiones