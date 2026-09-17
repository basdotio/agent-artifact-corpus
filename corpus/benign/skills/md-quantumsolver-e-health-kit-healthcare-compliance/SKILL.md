---
name: healthcare-compliance
description: Engineering-focused guardrails for HIPAA-style privacy, HL7 or FHIR integrations, and safe handling of PHI in e-health systems.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Healthcare Compliance

> This skill provides engineering guardrails for healthcare and e-health projects.
> It is not legal advice; use it to shape technical decisions and checklists.

## How to Use This Skill

Use this skill whenever:
- The system stores or processes Protected Health Information (PHI).
- You touch patient data, clinical notes, lab results, prescriptions, imaging, or billing linked to a person.
- You design integrations with hospital systems (HL7, FHIR, LIS or RIS, PACS).

Combine it with:
- backend-specialist for API and access control decisions.
- database-architect for schema, retention, and indexing choices.
- security-auditor for security scans and secret management.

---

## 1. Regulatory Scope (High-Level)

Focus on common technical expectations across regulations:

- HIPAA (US) – Privacy Rule, Security Rule, audit and breach notification.
- GDPR or local privacy laws – data minimisation, consent, right to access or delete.
- HL7 v2.x – messaging standard used by many legacy hospital systems.
- FHIR (R4 or R5) – modern resource-based REST API standard for clinical data.

Principle: design for least privilege, auditability, and interoperability.

---

## 2. PHI Data Classification

Before coding, identify which fields and tables contain PHI:

- Direct identifiers: name, national ID, phone, email, full address.
- Quasi-identifiers: date of birth, postal code, gender, rare diagnosis combinations.
- Clinical content: encounters, diagnoses, prescriptions, lab results, vitals, imaging reports.
- Billing data tied to a person: invoices, insurance details, claim status.

Rules:
- Do not store PHI in free-text logs, analytics events, or error traces.
- Avoid PHI in URLs or document identifiers such as query strings or path parameters.
- Encrypt backups and exports containing PHI.

---

## 3. Access Control and Roles

Design role-based access control aligned with clinical workflows:

- Receptionist: schedule, basic demographics, no access to detailed clinical notes.
- Nurse: triage data, vitals, limited orders, partial record view.
- Physician: full clinical record, orders, notes, e-prescriptions.
- Lab or Imaging: orders, results entry, no financial data.
- Billing: invoices, payments, insurance, minimal clinical details.

Engineering guidelines:
- Enforce RBAC server-side, not just in the UI.
- Apply row-level access for sensitive records, for example filter by facility or organisation.
- Prefer allowlists, describing who may access, over blocklists.
- Log every access to high-risk objects such as patient, encounter, and medical record.

---

## 4. Audit Trails and Logging

For PHI-bearing objects, the system should answer who did what, when, and to which record.

Minimum requirements:
- Version history for key records, using before or after snapshots or field-level changes.
- Immutable audit log of security-sensitive actions such as login, impersonation, mass exports.
- Record of consent changes, privacy preference updates, and sharing revocations.
- Time-synchronised server clocks (NTP) to make logs reliable.

Logging rules:
- Do not log full payloads of clinical notes, prescriptions, or lab results.
- Prefer identifiers plus minimal context such as record id, action, module, user, timestamp.

---

## 5. Data Protection and Deployment

Checklist for secure-by-default deployments:

- Transport: enforce HTTPS or TLS everywhere, including internal APIs.
- At rest: use database encryption at rest and encrypted volumes or backups.
- Secrets: store credentials in a secret manager or environment variables, never in Git.
- Backups: regular encrypted backups with tested restore procedures.
- Retention: configure retention policies per data category such as clinical, billing, logs.
- Isolation: separate production and test datasets; never use real PHI in development.

For Frappe or ERPNext deployments, ensure:
- Site config (site_config.json) does not commit secrets.
- Background workers and schedulers run under least-privilege OS users.
- Only whitelisted hosts and IPs may reach the database and Redis instances.

---

## 6. HL7 and FHIR Integration Patterns

When integrating with hospital systems:

- HL7 v2:
  - Typically via TCP or file drops, with messages such as ADT, ORM, ORU.
  - Implement a translation layer that validates and maps segments to internal DocTypes.
  - Keep raw HL7 messages for traceability in a secure, access-controlled store.

- FHIR:
  - Prefer RESTful APIs with JSON.
  - Map DocTypes to FHIR resources such as Patient, Encounter, Observation, MedicationRequest, Appointment.
  - Maintain explicit mapping documentation at field level for every integration.

Security rules:
- Authenticate all integration clients using mutual TLS, OAuth2, or signed tokens.
- Throttle and monitor inbound and outbound traffic for abuse and leaks.

---

## 7. Pre-Release Compliance Checklist

Before launching or changing an e-health feature, verify:
- [ ] Data classification completed; PHI locations documented.
- [ ] RBAC implemented and enforced in backend for all health DocTypes.
- [ ] Audit logging enabled for access and modifications of PHI.
- [ ] Transport and at-rest encryption configured and tested.
- [ ] Backup, restore, and retention policies documented and tested.
- [ ] Integrations using HL7 or FHIR authenticated, authorised, and rate-limited.
- [ ] No PHI in logs, analytics, or URLs.
- [ ] Legal or compliance stakeholders have reviewed changes where required.

Use this checklist as a gate before considering an e-health feature done.

