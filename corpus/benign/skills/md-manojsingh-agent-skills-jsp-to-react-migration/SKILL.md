---
name: jsp-to-react-migration
description: "Assess a Java JSP/TagLib app on Tomcat and produce a migration plan to React + Spring Boot APIs. Emphasize evidence-based scoring, strategy selection, roadmap, effort, and risks."
---

# JSP-to-React Migration Assessment Skill (Token-Optimized)

## Output Contract
- Produce a **migration assessment report** (preferred: .docx via docx skill when available).
- Be **evidence-based**. If data is missing, record as **Discovery Needed** (do not assume).
- **Only include sections that apply** (or mark explicitly N/A). Avoid long explanations.

> If generating .docx: read `/mnt/skills/public/docx/SKILL.md` first.

---

## Phase 0 — Inputs (Ask/Extract)
Collect what you can; ask only for missing critical items:

### A) Scope
- App/domain name
- # JSP files, # screens (if different), high-traffic pages
- Age + last major update
- Team size + React/TS experience

### B) Frontend (JSP)
- Tag libs: JSTL / Spring / Struts / custom TLD count
- Scriptlets density: none / light / moderate / heavy
- Includes/fragments patterns
- JS: none / jQuery / mixed / modern
- CSS: Bootstrap / custom / none
- Any existing React/SPA parts?

### C) Backend
- Framework: Spring MVC / Struts / Servlets / other
- Auth: container-managed / Spring Security / SSO (SAML/OIDC) / custom
- Session dependence: low/med/high
- Data: DB type, ORM (JPA/Hibernate/JDBC/MyBatis), queues, batch jobs
- Existing REST APIs? (% coverage, quality)

### D) Ops/Delivery
- Deploy: on-prem VM / cloud VM / containers / K8s
- CI/CD: none/basic/mature
- Testing: unit/integration/e2e coverage level
- Compliance/security constraints

**Minimum required to score + recommend strategy**: A + scriptlets + taglibs + auth/session + REST surface + test coverage + page/screen count.

---

## Phase 1 — Rapid Codebase Signals (If repo access)
Prefer short quantitative signals:
- JSP count, scriptlet count, taglib imports, TLD count
- Session usage hotspots
- Controller/API annotation counts

(Include commands as an appendix only if requested.)

---

## Phase 2 — Complexity Scorecard (1–5 each)
Score, add 1-line justification per row.

| Dimension | Score | Evidence |
|---|---:|---|
| Scriptlets | | |
| Custom tag libs | | |
| View-layer business logic | | |
| Session complexity | | |
| Auth/SSO complexity | | |
| REST API readiness | | |
| UI JS complexity | | |
| Test coverage | | |
| Team React readiness | | |
| Page/screen count | | |

**Total (0–50)** = sum.

### Effort Tier (guideline)
- 10–20: Low (3–6 months)
- 21–33: Medium (6–12 months)
- 34–42: High (12–18 months)
- 43–50: Very high (18+ months)

---

## Phase 3 — Pick Strategy (choose ONE; name alternatives briefly)
### A) Big Bang
Use when: low complexity + small scope + strong team + cutover acceptable.

### B) Strangler Fig (default)
Use when: medium/high scope; coexistence required; incremental screen replacement.

### C) Micro-frontend Bridge
Use when: very large app, continuity critical, need embed React in JSP.

### D) Backend-first (modifier)
Use when: no REST APIs + complex auth/session → build APIs before UI migration.

---

## Phase 4 — Roadmap (phases + milestones)
Keep each phase to: goals, key deliverables, exit criteria.

- Phase 0 Foundation (env, CI, standards, ADRs)
- Phase 1 Backend/API (auth, API layer, OpenAPI, tests baseline)
- Phase 2 Frontend foundation (React/Vite+TS, routing, component library, state)
- Phase 3 Screen migration (ordered backlog + acceptance tests)
- Phase 4 Decommission/cutover (perf, monitoring, remove JSP/Tomcat deps)

Include a simple milestone table:
- Milestone | Duration | Dependencies | Output

---

## Phase 5 — Risks (Top 8–12 max)
Risk register table:

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|

Prefer risks tied to evidence (e.g., “scriptlets in checkout.jsp”).

---

## Report Structure

Generate a Word document (.docx) with the following structure. **Always consult the docx skill before generating**.

```
1. Executive Summary
   - App overview
   - Recommended strategy (1 paragraph)
   - Headline effort estimate
   - Top 3 risks

2. Application Assessment
   - Current Architecture Overview
   - Technology Inventory (table)
   - Complexity Scorecard (table)
   - Key Findings (narrative)

3. Target Architecture
   - Architecture diagram description
   - Frontend stack recommendation with rationale
   - Backend stack recommendation with rationale
   - Infrastructure / deployment target

4. Migration Strategy
   - Chosen strategy with rationale
   - Why alternatives were not chosen

5. Phased Roadmap
   - Phase-by-phase breakdown (table + narrative)
   - Milestone timeline (Gantt-style table)
   - Team composition recommendation

6. Effort Estimate
   - Summary table by phase
   - Assumptions and exclusions

7. Risk Register
   - Full risk table with mitigations

8. Recommendations & Next Steps
   - Immediate actions (next 30 days)
   - Quick wins
   - Key decisions needed from stakeholders

9. Appendix
   - Technology comparison tables (React vs Angular vs Vue, Spring Boot vs Quarkus, etc.)
   - Sample DevContainer configuration
   - Sample monorepo structure
```

---

## Tips for a High-Quality Report

- **Be specific**: If the user gives you page counts, team sizes, or framework names — use them. Avoid vague estimates.
- **Tailor the strategy**: Don't recommend "Big Bang" for a 150-page enterprise app. Match the strategy to the evidence.
- **Flag information gaps**: If the user hasn't provided information about auth or session state, note it as a "discovery item" in the report rather than assuming.
- **Include a quick wins section**: Always identify 2–3 things the team can do in the first 30 days to build confidence and reduce risk.
- **Use tables liberally**: Complexity scorecards, risk registers, and roadmap tables are much more readable than prose.
- **Executive summary first**: The exec summary must stand alone — a non-technical stakeholder should be able to read just that section and understand the situation.

---

## JSP Tag Mapping Patterns

The following patterns fill documented gaps when translating JSP constructs to React/TypeScript. Apply them during Phase 3 (Screen Migration).

---

### Pattern 1: Client-Side Routing (`.jsp` files → React Routes)

> *Each `.jsp` file that represents a separate page should become a separate React component, registered as a `<Route>` in `react-router-dom`. Install `react-router-dom` and wrap the app in `<BrowserRouter>`.*

```
servlet-container URL (/foreach-student.jsp)
        ↓
<Route path="/foreach-student" element={<ForEachStudentTest />} />
```

```tsx
// App.tsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/"                element={<Home />} />
        <Route path="/foreach-student" element={<ForEachStudentTest />} />
        <Route path="/if-student"      element={<IfStudentTest />} />
        {/* one Route per .jsp file */}
      </Routes>
    </Router>
  );
}
```

---

### Pattern 2: Server-Side Initialisation → `useEffect`

> *Any value set server-side at request time should be initialised inside a `useEffect` hook with an empty dependency array `[]`, stored in `useState`. This fires once on component mount, mirroring a single server-side evaluation.*

```jsp
<%-- JSP: evaluated once on the server --%>
<c:set var="stuff" value="<%= new java.util.Date()%>" />
Time on the server is ${stuff}
```

```tsx
// React equivalent
const [stuff, setStuff] = useState<string>("");

useEffect(() => {
  setStuff(new Date().toString()); // runs once on mount
}, []);

return <p>Time on the server is {stuff}</p>;
```

---

### Pattern 3: i18n Locale Switching — State Management

> *Locale selection driven by URL query params (`?theLocale=`) or servlet session scope should be replaced with `useState<Locale>`. Locale-switching anchor tags become `<button onClick>` handlers that update state.*

| JSP / Servlet Concept | React Equivalent |
|---|---|
| `fmt:setLocale` (session-scoped) | `useState<Locale>` |
| `?theLocale=es_ES` query param | `onClick={() => setLocale("es_ES")}` |
| `fmt:setBundle basename="..."` | Import a `translations.ts` object |
| `<fmt:message key="label.greeting" />` | `{translations[locale]["label.greeting"]}` |
| `.properties` files | `Record<Locale, Labels>` TypeScript object |

```tsx
// i18n/translations.ts
export type Locale = "en_US" | "es_ES" | "de_DE";

export const translations: Record<Locale, Record<string, string>> = {
  en_US: { "label.greeting": "Hello",   "label.welcome": "Welcome to the training class." },
  es_ES: { "label.greeting": "Hola",    "label.welcome": "Bienvenidos a la clase de formacion." },
  de_DE: { "label.greeting": "Hallo",   "label.welcome": "Willkomen in der Ausbildung Klasse." },
};

// Component
const [locale, setLocale] = useState<Locale>("en_US");
const t = translations[locale];

return (
  <>
    <button onClick={() => setLocale("en_US")}>English (US)</button>
    <button onClick={() => setLocale("es_ES")}>Spanish (ES)</button>
    <button onClick={() => setLocale("de_DE")}>German (DE)</button>
    <p>{t["label.greeting"]}</p>
  </>
);
```

---

### Pattern 4: Java POJO → TypeScript Interface

> *Every Java model class (POJO) should be translated into a TypeScript `interface`. Getter/setter methods are dropped — use plain properties instead. Place interfaces in a `src/types/` directory and export sample data alongside them.*

| Java Type | TypeScript Type |
|---|---|
| `String` | `string` |
| `boolean` | `boolean` |
| `int` / `long` | `number` |
| `List<T>` | `T[]` |
| `Map<K,V>` | `Record<K, V>` |

```java
// Java POJO
public class Student {
  private String firstName;
  private String lastName;
  private boolean goldCustomer;
  // getters & setters...
}
```

```ts
// src/types/Student.ts
export interface Student {
  firstName: string;
  lastName: string;
  goldCustomer: boolean;
}

// Sample data (replaces in-JSP scriptlet data setup)
export const sampleStudents: Student[] = [
  { firstName: "John",    lastName: "Doe",    goldCustomer: false },
  { firstName: "Maxwell", lastName: "Johson", goldCustomer: false },
  { firstName: "Mary",    lastName: "Public", goldCustomer: true  },
];
```

---

### Pattern 5: `key` Prop Rule for `c:forEach` → `Array.map()`

> *When translating `<c:forEach>` to `Array.map()`, always add a unique `key` prop to the outermost JSX element returned. Prefer a stable, unique field over the array index.*

```jsx
// ✅ Preferred — stable, unique key
{students.map((s) => (
  <tr key={s.firstName + s.lastName}>
    <td>{s.firstName}</td>
  </tr>
))}

// ⚠️ Acceptable fallback when no unique field exists
{students.map((s, i) => (
  <tr key={i}>
    <td>{s.firstName}</td>
  </tr>
))}

// ❌ Missing key — causes React warning
{students.map((s) => (
  <tr>
    <td>{s.firstName}</td>
  </tr>
))}
```

---

### Pattern 6: Shared Navigation Component (JSP Includes → `<Navbar>`)

> *Create a shared `<Navbar>` component using `<NavLink>` from `react-router-dom` (not plain `<a href>`). `NavLink` automatically applies an `active` CSS class to the current page link, replacing any active-state logic in JSP includes.*

```tsx
// src/components/Navbar.tsx
import { NavLink } from "react-router-dom";

const Navbar: React.FC = () => (
  <nav>
    {/* NavLink adds class="active" automatically for the current route */}
    <NavLink to="/foreach-student">forEach Student</NavLink>
    <NavLink to="/if-student">If Student</NavLink>
    <NavLink to="/i18n">i18n Messages</NavLink>
  </nav>
);
```

```css
/* Navbar.css */
a.active {
  background: #3498db;
  color: #fff;
}
```

> Place `<Navbar />` outside `<Routes>` in `App.tsx` so it renders on every page.

---

## Reference Files

- `references/stack-comparison.md` — Detailed technology comparison tables for frontend and backend choices
- `references/sample-monorepo-structure.md` — Example monorepo layout for React + Spring Boot projects
- `references/interview-questions-extended.md` — Extended interview guide for complex enterprise scenarios