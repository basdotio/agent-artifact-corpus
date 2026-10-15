# Deployment guidelines

## Propósito

Proveer a los **desarrolladores** y a sus **copilotos/asistentes de código** un marco claro y
accionable del **proceso de despliegue**: qué etapas ejecuta el CI/CD y cómo interpretar cada
_check_ (**success**, **warning**, **fail**); qué **validaciones** y **reglas** aplicar antes de
promover cambios; qué **herramientas y servicios** intervienen; cómo se **gestionan los ambientes**
(slugs estándar: `dev`, `uat`, `prod`); cuál es el **gitflow** adoptado; y cómo realizar el
**seguimiento post‑despliegue** (monitoreo y verificación) para asegurar releases seguras,
consistentes y auditables.

## Entornos y propósito

> **Estándar de slugs**: usar exactamente `dev`, `uat`, `prod` en **variables** (p. ej., `ENV`),
> **labels** de despliegue y **nombres de environment** del pipeline.

| Entorno (slug)                    | Propósito                                                                                                                                                                                             | Ventana de cambios              | Aprobadores                  |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------- |
| **dev** (desarrollo)              | Trabajo diario de desarrollo y pruebas de _features_; recursos reducidos y mayor libertad operativa. Datos **sintéticos/generados**; puede servir temporalmente a QA si un equipo aún no tiene UAT.   | **Sin restricción configurada** | 1 (equipo o infraestructura) |
| **uat** (user acceptance testing) | Pruebas de aceptación de usuario (QA y negocio). Paridad con producción; datos estadísticamente similares o **anonimizados**. Estabilidad prioritaria; **E2E obligatorios** antes de promover a prod. | **Sin restricción configurada** | 1 (equipo o infraestructura) |
| **prod** (producción)             | Servicio a usuarios finales. **Disponibilidad y estabilidad** son la prioridad; solo cambios vía pipeline auditado.                                                                                   | **Sin restricción configurada** | 1 (equipo o infraestructura) |

**Convenciones por entorno**

- **dev**: permite datos sintéticos; pensada para la iteración en conjunto con pruebas en ambientes
  locales. Equipos y proyectos antiguos sin ambiente UAT pueden usarlo temporalmente para QA (evitar
  datos reales).
- **uat**: paridad de configuración con producción; **datos anonimizados** o muestreados con
  distribución similar; ejecutar **pruebas end‑to‑end** y validaciones de negocio.
- **prod**: cambios solo mediante pipeline; ramas protegidas: no se aceptan pushes directos ni
  _force-push_; auditoría y _change log_ obligatorios.

**Mapa rápido ramas ↔ entornos**

| Rama      | Entorno | Despliegue asociado      |
| --------- | ------- | ------------------------ |
| `develop` | dev     | `deploy:dev`             |
| `uat`     | uat     | `deploy:uat` + `e2e:uat` |
| `master`  | prod    | `deploy:prod`            |

---

## Visión general del proceso

**Punto de partida**: creación del **Merge Request (MR)**.

1.  **Checks iniciales (MR abierto)** Jobs: `unit_test`, `validations`, `project_lint` (incluye
    linters, formateo, configuración, deuda técnica, reglas de usabilidad e infraestructura).
2.  **SAST con SonarQube** Job: `sonarqube` (análisis de código estático y calidad).
3.  **Merge a la rama _default_** (`develop` o `master`, según el repo). Re-ejecución de jobs:
    `unit_test`, `validations`, `project_lint`, `sonarqube`.
4.  **Preparación de despliegue (si aplica)**
    - **Aplicaciones**: job `build` (imagen Docker).
    - **Infraestructura (Terraform)**: jobs `iac:validate` y `iac:plan`.
5.  **Despliegue** Jobs: `deploy:<env>` (aplicación) o `iac:apply` (infraestructura).
6.  **Post‑deploy** Jobs: `e2e:uat` (cuando aplica). Validación funcional del servicio y
    **monitoreo** de aplicaciones y métricas.

**Políticas operativas**

- Entre cada promoción de ramas/entornos (**dev → uat → prod**) se requiere **aprobación**.
- En despliegues a **UAT** se ejecuta un **stage adicional de pruebas de integración**.
- Los stages solo continúan cuando el resultado es **success**.

---

## Flujo de Git (GitFlow)

### Flujo de Desarrollo

Este es el ciclo de trabajo estándar para los desarrolladores.

#### Flujo `feature` (Nueva Funcionalidad)

- **Origen**: `develop`.
- Se crea una rama `feature/nombre-descriptivo`.
- Se desarrolla la funcionalidad.
- **Destino**: Se crea un Merge Request (MR) hacia `develop` para integrar el cambio.

#### Flujo `bugfix` (Corrección en Desarrollo)

- **Origen**: `develop`.
- Se crea una rama `bugfix/nombre-del-bug`.
- Se corrige el bug.
- **Destino**: Se crea un MR hacia `develop`.

### El Camino de `develop` a `uat` (Dos Opciones Flexibles)

Esta es la parte más flexible del flujo. El equipo decide qué camino tomar según el estado de
`develop`.

#### Camino A: Despliegue Selectivo (con `pre-uat`)

- **Cuándo usarlo**: Cuando `develop` contiene cambios a medio terminar que no deben pasar a UAT,
  pero otros cambios sí están listos.
- **Origen**: Se identifica un commit específico en la historia de `develop` que contiene todo lo
  que se desea probar (y nada más).
- Se crea una rama `pre-uat/nombre-paquete` desde ese commit. Esta rama actúa como un "paquete de
  entrega" temporal.
- **Destino**: Se crea un MR desde `pre-uat/nombre-paquete` hacia `uat`.
- Al fusionarse, se despliegan solo esos cambios selectivos a UAT y la rama `pre-uat` puede ser
  eliminada.

#### Camino B: Sincronización Total (Merge Directo)

- **Cuándo usarlo**: Cuando todo el contenido de `develop` es considerado estable y está listo para
  ser probado en conjunto.
- **Acción**: Se crea un MR directamente desde `develop` hacia `uat`.
- Al fusionarse, todos los cambios acumulados en `develop` se despliegan a UAT.

### Flujo de Estabilización en UAT (`uatfix`)

Una vez que el código está en el ambiente de UAT, comienza el ciclo de pruebas y correcciones.

- **Origen**: Un bug es detectado en UAT. El desarrollador crea una rama `uatfix/nombre-del-fix`
  desde la rama `uat`.
- Se implementa la corrección.
- **Destino (Doble y Crítico)**: El `uatfix` debe ir a dos lugares:
  - **MR 1 (hacia `uat`)**: Para redesplegar la corrección en el ambiente de UAT y que QA pueda
    volver a probarla.
  - **MR 2 (hacia `develop`)**: Este paso es obligatorio. Se fusiona el mismo `uatfix` en `develop`
    para asegurar que la corrección no se pierda y prevenir que el bug reaparezca en futuros
    desarrollos.

### Flujo de Lanzamiento a Producción (`release`)

Cuando la rama `uat` se considera estable, aprobada y lista para ser lanzada.

- **Origen**: Se crea una rama `release/vX.Y.Z` desde la rama `uat`.
- Se crea un MR desde `release/vX.Y.Z` hacia `master`.
- **Generación del Candidate**: El pipeline de este MR tiene un job (manual o automático) que crea
  un tag de release candidate (ej. `v1.2.0-rc.1`) sobre el último commit de la rama `release/vX.Y.Z`.
- **Validación en Producción**: Este tag se despliega (usualmente de forma manual) a producción para
  realizar pruebas de humo y validaciones finales.
- **Lanzamiento Final**: Si la validación es exitosa, se aprueba y fusiona el MR en `master`.
- El pipeline de `master` se activa y crea el tag final y limpio (`v1.2.0`), formalizando la nueva
  versión.

### Flujo de Emergencia en Producción (`hotfix`)

Para corregir bugs críticos en producción que no pueden esperar.

- **Origen**: Se crea una rama `hotfix/descripcion-urgente` desde la rama `master`.
- Se implementa la corrección crítica.
- **Destino (Triple y Crítico)**: El `hotfix` debe sincronizarse con todas las ramas base:
  - **MR 1 (hacia `master`)**: Se fusiona con alta prioridad. El pipeline de `master` genera un
    nuevo tag de parche (ej. `v1.2.1`) y lo despliega a producción para resolver la emergencia.
  - **MR 2 (hacia `develop`)**: Se fusiona `master` en `develop` para que el fix no se pierda en el
    futuro.
  - **MR 3 (hacia `uat`)**: Se fusiona `master` en `uat` para que el ambiente de pruebas también
    esté actualizado con la corrección crítica.

[![](https://mermaid.ink/img/pako:eNqVVttO40gQ_ZVWSyOBFBtMQgJ-C0m4rGCIArPaXeWlsStOL3a3t9OOyCA-Zj5gn_ZtXvmxrfYN23GASWQldndVnTp1qtrP1JM-UJdaljUXmusQXHIeJn9L4gO54JqMYcEF13wtyZ4nBdHSlysS4gUrDwRTXK725yK1D7i-UCxezgXBz5cvBJ-SQ5vcgU5iciW4x1lI0q1mgyejCCNw3yVzunZsxz6cU6JZUL_fxIjp8uri8hqv-8z0QTHhLRHjGkIZ154lTGf3NRSOTc7ZCkxWY1gxpWQYyhZIS_AeZaJbPS-A6UTBwbCxt_k8Tes9fxGoAN7McgZu0qfDOW3An6w0INkEQvL6M9Q8kgVz_yRgLgWRKUkIa6YII9-G92QFIXhYNBaB0NBC92jJRIBOF1IZg62ghrMjm4yGN1dfb4njGtbikEOAIe9y5waHINPZxDIhSw7ReqSAGUyxAgvrQcaTu_EEc8BE4kRoSeCJeeZHtBKdmx0UWYAVM--RBdACsmuT4VIq1qk46xhgmoskBWFAIndasQeGujakYUpcvf7IyUJJs_Xrv-wXZXBmCaktzNTf7BDE9o5flEbFQU0kZ2Tvq9RkZhb2Te1qlPRsMlXSQ5mnumBEsYiVtYiZYoVYTBt7LHrAHi4lg38zWrbZ-KAuNYFNs5U3gbU3cum7bNuMgZ2hajwUSgSSh9vi4hj7_vrbb7coQQPj_OoPF61QK16CnYFMJII8JIERj8l5gzRgHkpx9L5NQAnybdYs-NMBXhYXVrla3d-6XiWqskhL6Mf2MMXJsXsDRJnDS2unwDe9CAFT73O4Fb3GHfrDlVrMs2bMXJpZXCzJGgRXCCBQsOKv_4mPlbwLw91GeDkE7D-cLuut0vVx_KRt_PqTmQb23-Z2BdrnehZLXMAYNba3LH2yS6uWNWpHreN0UI7TI-SZC09Jwb8zzxBJ7qXGc8iMqszFmCswE_IdDWYgCh6y-JkZMey6uacCeJPeE5tMQqzlSpuzPiSL9NTfU9hSeFB2yFKayuFY1Z69nw9UUwksgw87BkSzP3JnB3iYH-FhXt_culjtjAsQoBieGSMmfO6bf-PJ9Pr2TzxzbsflRJlNfp_M7iaVFwd0Z6FabaeoQxkzYlxU2atjyONes8SAP-cCSzLLdjQjV2NtVbtZ3KlcaSt39LGsDMZqlxQIWtqkfFO7TIu1M9m8HFlJDxKMIpr6bltr64MmgzW7WhfkmOpkOZ8jqzWfT3CV2VWoeq91dhunBxbt0EBxn7paJdChaIMGeEufjZM51UuI8MAx5j5TjybaC9rETPwlZVSYKZkES-ouWIhNRZPYyHjMGQ7Yty0gfFAjiW9G1D1JPVD3mT5Rt-t07X7vqN89xe9hr9ft0A11nUHP7h2e9nD1pO8Muv2XDv2ehjy0-4PTbr_vOM7g-Lg7cJwOBZ9rqW6y1_z0bf_lf9I82O8?type=png)](Diagrama)

---

### Quality gates por stage (CI/CD)

| Stage          | Checks obligatorios                                                                                                                                                                                                                                              | Fail (bloquea)                                                                                                        |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `unit_test`    | **Cobertura ≥ 80%** y todas las pruebas pasan.                                                                                                                                                                                                                   | Cobertura < **80%** o **cualquier** prueba unitaria falla.                                                            |
| `validations`  | Validaciones orientadas a reglas de Infraestructura y buenas practicas Serverless.                                                                                                                                                                               | Cualquier fallo en alguna de las validaciones bloqueantes.                                                            |
| `project_lint` | Revisión de código estático con **flake8**, **bandit** y **pylint** (configurado vía `.pylintrc`); formateo correcto.                                                                                                                                            | Errores de **flake8** (nivel error), hallazgos **altos** en **bandit**, errores reportados por **pylint**.            |
| `sonarqube`    | **Quality Gate = Passed** con umbrales: **cobertura ≥ 80%**, **duplicación < 5%**, **Security Rating = A**, **Reliability Rating = A**, **0 bugs/0 Security Hotspots en código nuevo** (repos antiguos) y **0 bugs/0 Security Hotspots totales** (repos nuevos). | **Quality Gate = Failed** (incumplimiento de cualquiera de los umbrales o presencia de bugs/Hotspots según política). |

> Cobertura mínima en `unit_test`: **80%**. Linters definidos en los code guidelines (`flake8`,
> `bandit`, `.pylintrc`). En **SonarQube**, el Quality Gate exige: **cobertura ≥ 80%**,
> **duplicación < 5%**, **Security = A**, **Reliability = A**, **0 bugs/0 Security Hotspots en
> código nuevo** (repos antiguos) y **0 bugs/0 Security Hotspots totales** (repos nuevos).

### Stack de herramientas

| Categoría            | Herramientas/Servicios adoptados                                                                                                                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repos & MRs          | **GitLab** (repositorio de código, _merge requests_, _code owners_, ramas protegidas)                                                                                                                                     |
| CI/CD                | **GitLab CI** basado en MR; _runners_ **self-hosted en AWS EC2** (Ubuntu, imagen Docker custom); jobs: `unit_test` → `validations` → `sonarqube` → (`build`) → `iac:validate` → `iac:plan` → `deploy:<env>` / `iac:apply` |
| Contenedores         | **Docker** (Buildx opcional); construcción local/en runners                                                                                                                                                               |
| Runners Gitlab       | **AWS EC2** (self-host), Ubuntu con Docker como _runtime_ de despliegue                                                                                                                                                   |
| Registro de imágenes | **AWS ECR**, **GCP Artifact Registry**                                                                                                                                                                                    |
| IaC                  | **Terraform** (infraestructura general), **Serverless Framework** (servicios/APIs), **Pulumi** (servicios de analítica y MLOps)                                                                                           |
| Seguridad (código)   | **SonarQube** (SAST: cobertura, duplicación, mantenibilidad, confiabilidad, bugs, Security Hotspots)                                                                                                                      |
| Seguridad (IaC)      | **KICS** (escaneo de infraestructura como código)                                                                                                                                                                         |
| Secretos             | **AWS Secrets Manager**, **GCP Secret Manager**                                                                                                                                                                           |
| Observabilidad       | **AWS CloudWatch**, **Sentry**, **Grafana**                                                                                                                                                                               |
| Notificaciones       | **Google Chat** mediante **webhooks**                                                                                                                                                                                     |

### Estados del pipeline (semántica general)

| Estado  | Significado operativo                                                                    | Política por entorno                                                                                                                |
| ------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| success | El _stage_ cumplió todos los checks obligatorios.                                        | Continúa automáticamente.                                                                                                           |
| warning | Hallazgos no bloqueantes (p. ej., _codequality_ menor, _lint_ con reglas suaves).        | **dev**: continúa; **uat**: revisión requerida; **prod**: puede requerir aprobación extra o bloquear si el warning es de seguridad. |
| failed  | Check bloqueante falló (tests, SAST crítica, IaC inválido, _plan_ con diffs prohibidos). | Se detiene; requiere corrección y nuevo pipeline.                                                                                   |
| manual  | Paso requiere aprobación humana (ventana de cambio, `deploy:prod`, _migrations_).        | Solo roles autorizados, con _change window_ vigente.                                                                                |
| skipped | Paso omitido por reglas (cambios no relevantes al servicio/entorno).                     | No afecta el _gate_ si no es obligatorio.                                                                                           |

## Reglas de control

- **Aprobaciones previas**: se requiere **1 aprobación** para cada promoción **dev → uat** y **uat →
  prod** por parte de un integrante del equipo o de infraestructura. Para pasos a **prod** se
  requiere una aprobación adicional por parte del equipo de **QA**.
- **Validaciones automáticas**: jobs **obligatorios**: `unit_test`, `project_lint`, `validations`,
  `sonarqube`, `iac:validate`, `iac:plan`.
- **Restricciones horarias**: actualmente **no hay una ventana de despliegue definida**.
- **Ramas protegidas**: `master`, `uat` y `develop` **no permiten** pushes directos ni _force‑push_.
- **Política de hotfix**: todo MR cuyo **branch origen** sea `hotfix/*` y **destino** `master`
  activa un **stage manual** `hotfix_approval`, que debe ser aprobado por el **Líder de Ingeniería
  de Infraestructura** antes de cualquier `deploy:prod`.
