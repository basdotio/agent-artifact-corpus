---
name: lead_gen
description: "Pipeline de génération de leads B2B : scrape Google Maps via Serper, qualifie les sites web via deep crawl + analyse keywords (email de contact), enrichit les contacts via OSINT (nom/titre/LinkedIn), et synchronise vers HubSpot CRM. USE WHEN: l'utilisateur demande des leads, du scraping, de l'enrichissement, des prospects, une sync HubSpot, des entreprises Google Maps, une recherche par industrie ou de la découverte de contacts."
---

# Skill: Lead_gen — Lead Generation B2B

## Inputs requis (3 elements uniquement)
- `max_leads` — nombre de leads (ex: 5, 50)
- `industry` — industrie cible (ex: "Saunas", "Cuisinistes", "Jacuzzis")
- `country` — pays (ex: "France", "Belgique")

La requete Google Maps est auto-reformulee pour cibler les **fabricants/constructeurs qui vendent des produits**. Le mot "fabricant" est automatiquement prepend a l'industrie. L'utilisateur n'a pas besoin de le preciser.

Si l'utilisateur ne fournit pas tous les inputs, les lui demander avant de commencer.

---

## Pipeline séquentiel

### Etapes 1+1b : Scraping + Dedup + Expansion automatique
- **Scripts :** `execution/scrape_google_maps.py` + `execution/dedup.py`
- **Orchestre par :** `run_pipeline.py` (boucle d'expansion)
- **Output :** `.tmp/google_maps_results.json` (leads uniques, prets pour qualification)
- **Comportement :**
  1. Scrape initial avec requete "fabricant {industry} {country}"
  2. Dedup intra-batch (fuzzy nom 82% + domaine exact) + dedup vs HubSpot (bulk fetch)
  3. Si moins de leads que demande → **expansion automatique** : essaie des queries alternatives (synonymes, termes individuels, regions)
  4. Boucle jusqu'a atteindre le nombre de leads demande ou avoir epuise toutes les variantes
- **Queries d'expansion (2 sources) :**
  - **Google Maps** (`/maps`) : constructeur/fournisseur/vendeur + termes individuels + regions (Ile-de-France, PACA, etc.)
  - **Google Web** (`/search`) : recherche organique pour capter les grands fabricants multi-produits absents de Maps (ex: Novellini, Grohe). Filtre auto les reseaux sociaux, annuaires et marketplaces.
- **Rate limit :** Si Serper renvoie un 429, le pipeline se met en **pause** (state sauvegarde dans `.tmp/pipeline_state.json`)
- **Resume :** `python run_pipeline.py --resume --industry "..." --country "..." --max_leads N`

### Etape 2 : Qualification des sites (Deep Crawl + Keywords)
- **Script :** `execution/qualify_site.py`
- **Input :** `.tmp/google_maps_results.json`
- **Output :** `.tmp/qualified_leads.json`
- **Action :** Deep crawl (homepage + pages contact/mentions légales), extraction email de contact du site, classification par keywords (Manufacturer/Service/Unknown), détection e-commerce
- **Email :** L'email de contact trouvé sur le site est stocké dans `Email_Generique` — c'est l'email principal utilisé pour HubSpot
- **Filtre :** Garde uniquement Business_Type=Manufacturer (e-commerce non requis)

### Etape 3 : Enrichissement (OSINT) + Push HubSpot
- **Script :** `execution/enrich.py`
- **Input :** `.tmp/qualified_leads.json`
- **Action :** Recherche OSINT via Serper pour trouver le nom du décideur, son poste et son profil LinkedIn
- **Note :** L'email de contact provient du site web (étape 2). L'enrichissement ne cherche PAS d'email.
- **Push HubSpot :** Chaque lead est poussé vers HubSpot immédiatement après enrichissement (données complètes : nom, site, email, type, décideur, LinkedIn, tel)
- **Sauvegarde incrémentale :** `enriched_leads.json` est sauvegardé après chaque lead enrichi (protection anti-crash)

### Etape 4 : Sync HubSpot (filet de sécurité)
- **Script :** `execution/sync_hubspot.py`
- **Logique Upsert :**
  1. Chercher contact par email (anti-duplication primaire)
  2. Si pas d'email → fallback recherche par nom d'entreprise / domaine web (anti-duplication secondaire)
  3. Si existe -> Mettre à jour champs manquants
  4. Si n'existe pas -> Créer contact + entreprise associée
- **Email synced :** `Email_Generique` (email de contact du site web)
- **Log :** `.tmp/sync_log_YYYYMMDD_HHMMSS.json`
- **Triple anti-doublon :** dedup batch (etape 1b) + dedup HubSpot (etape 1b) + upsert email/company (etape 4)

### Etape 5 : Backup Excel (automatique apres sync)
- **Script :** `execution/save_to_excel.py --backup-mode`
- **Output :** `Generate_leads.xlsx` avec Statut_Sync=Synced
- **Email vide :** Affiché comme "Non renseigné" dans l'Excel
- **IMPORTANT :** Demander à l'utilisateur de fermer le fichier Excel avant exécution
- Desactivable avec `--no-backup`

### Pause / Resume automatique (rate limit)
- Si une API atteint son quota (429), le pipeline **se met en pause** automatiquement
- L'etat complet est sauvegarde dans `.tmp/pipeline_state.json` (etapes completees, leads accumules, queries essayees)
- Resume manuel : `python run_pipeline.py --resume --industry "..." --country "..." --max_leads N`
- Resume automatique : `pipeline_watcher.py` sur VPS (voir ci-dessous)

### VPS Watcher (resume automatique)
- **Script :** `execution/pipeline_watcher.py`
- **Deploiement :** Cron sur VPS, verifie 1x/jour si une pipeline est en pause
- **Logique :** Teste l'API bloquee → si disponible, relance `run_pipeline.py --resume`
- **Cron :** `0 6 * * * cd /path/to/agents_ia && python execution/pipeline_watcher.py --mode once >> /var/log/pipeline_watcher.log 2>&1`
- **Mode continu :** `python pipeline_watcher.py --mode poll --interval 86400`

### Mode alternatif : Excel d'abord (ancien workflow)
- Ajouter `--use-excel` au pipeline pour utiliser l'ancien flow : Excel -> HubSpot

---

## Commandes utiles

```bash
# Pipeline complet (defaut, 3 workers paralleles)
python execution/run_pipeline.py --industry "Saunas" --country "France" --max_leads 50

# Pipeline sequentiel (1 worker, safe pour free tier Firecrawl)
python execution/run_pipeline.py --industry "Cuisinistes" --country "France" --max_leads 50 --workers 1

# Resume apres pause rate limit
python execution/run_pipeline.py --resume --industry "Saunas" --country "France" --max_leads 5

# VPS watcher (single check)
python execution/pipeline_watcher.py --mode once

# Scripts individuels
python execution/scrape_google_maps.py --industry "Saunas" --location "France"
python execution/dedup.py --input .tmp/google_maps_results.json
python execution/qualify_site.py --input .tmp/google_maps_results.json --workers 3
python execution/enrich.py --input .tmp/qualified_leads.json
python execution/sync_hubspot.py --input .tmp/enriched_leads.json --write-log
```

---

## Clés API requises / optionnelles

| Clé | Requis | Usage |
|-----|--------|-------|
| `SERPER_API_KEY` | Oui | Scraping Google Maps + OSINT LinkedIn |
| `FIRECRAWL_API_KEY` | Oui | Deep crawl sites web (qualification + extraction email) |
| `HUBSPOT_API_KEY` | Oui | Sync CRM |

---

## Scripts utilisés

| Script | Function | Input → Output |
|--------|----------|----------------|
| `execution/scrape_google_maps.py` | Search businesses via Serper | Query → `.tmp/google_maps_results.json` |
| `execution/dedup.py` | Dedup intra-batch + vs HubSpot (bulk fetch) | JSON → JSON (doublons retires) |
| `execution/qualify_site.py` | Deep crawl + keyword classification + email extraction | URL → `.tmp/qualified_leads.json` |
| `execution/enrich.py` | OSINT via Serper (nom décideur, titre, LinkedIn) | Company → `.tmp/enriched_leads.json` |
| `execution/sync_hubspot.py` | Push leads to HubSpot (upsert, default) | JSON → HubSpot CRM + sync log |
| `execution/save_to_excel.py` | Save leads to Excel (backup or `--use-excel`) | Data → `Generate_leads.xlsx` |
| `execution/sync_from_hubspot.py` | Pull updates from HubSpot (Excel mode only) | HubSpot → Excel |
| `execution/watch_lead_status.py` | Two-phase prospection watcher (re-trigger si subtask closed) | HubSpot ↔ ClickUp ↔ R2 |
| `execution/pipeline_watcher.py` | VPS cron: resume paused pipelines | State → API test → Resume |
| `execution/run_pipeline.py` | Master pipeline orchestrator (expansion + pause/resume) | Args → Full pipeline |
| `execution/dashboard_server.py` | Web dashboard: launch, monitor, API usage (port 8080) | Browser → FastAPI → `.tmp/` |

---

## Dashboard (monitoring & lancement)

- **Script :** `execution/dashboard_server.py`
- **Port :** 8080 (`http://<VPS_IP>:8080`)
- **Fonctions :** Lancer une prospection, suivre la progression en temps reel, monitorer les quotas API
- **Deploiement VPS :**
  ```bash
  # Lancement direct
  nohup python execution/dashboard_server.py > .tmp/dashboard.log 2>&1 &

  # Ou via systemd (demarrage auto)
  # Creer /etc/systemd/system/lead-dashboard.service puis:
  # systemctl enable lead-dashboard && systemctl start lead-dashboard
  ```
- **Endpoints API :**
  - `GET /` — Dashboard HTML
  - `GET /api/status` — Statut pipeline + compteurs leads
  - `GET /api/usage` — Utilisation API vs quotas mensuels
  - `GET /api/logs` — Dernieres lignes du log pipeline
  - `POST /api/launch` — Lancer un pipeline `{industry, countries[], max_leads}`
  - `POST /api/stop` — Arreter le pipeline en cours

---

## Prospection Watcher — Re-trigger

Si une subtask ClickUp est terminée par erreur (résultat incomplet), l'utilisateur peut **remettre `hs_lead_status=OPEN`** sur le contact HubSpot. Le watcher :
1. Détecte que l'ancienne subtask est closed/complete
2. Efface `clickup_prospection_task_id` sur le contact
3. Crée une nouvelle subtask (retour en Phase 1)

Pas besoin de supprimer manuellement l'ancienne subtask ni de vider des champs.

---

## Garde-fous
- Ne jamais scraper sans input `industry` + `location`
- Ne jamais push vers HubSpot sans vérification Upsert
- Le pipeline fonctionne avec 3 clés API (Serper + Firecrawl + HubSpot)
- Si un script échoue, lire l'erreur, corriger, réessayer (self-anneal)
- Les fichiers `.tmp/` sont temporaires — les supprimer après usage
