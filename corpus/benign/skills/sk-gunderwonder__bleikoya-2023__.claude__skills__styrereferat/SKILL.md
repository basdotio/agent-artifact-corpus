---
name: styrereferat
description: Importer et Google Doc fra Shared Drive som en draft-post på bleikoya.net (typisk styremøtereferat). Bruk når brukeren ber om å publisere referat, hente inn et styremøte-dokument, eller "lage utkast fra Google Doc".
---

# Styrereferat-import

Importerer et Google Doc som en draft WordPress-post på bleikoya.net. Gjenbruker `import_google_doc_to_post()` i `includes/google/docs-import.php` — alt fra henting, formatering (headings, lister, tabeller, bold/italic/lenker), bildeimport til draft-opprettelse er allerede implementert.

Posten opprettes som **draft** med `_visibility = private`. Brukeren publiserer manuelt fra WP admin.

## Argumenter

```
/styrereferat [url-eller-id] [--prod]
```

- `url-eller-id` — Google Docs URL eller doc-ID. Hvis utelatt, vis liste over nyeste docs i "Styremøter"-mappa og la bruker velge. `list-docs.php` godtar både mappenavn og folder-ID som første argument.
- `--prod` — kjør mot produksjon (ssh.bleikoya.net) i stedet for lokal (bleikoya.test). Default er lokal.

## Flyt

### 1. Parse argumenter

- Hvis `--prod` finnes: sett `$WP_CMD="ssh bleikoya.net@ssh.bleikoya.net 'wp --path=/www"`-prefiks og remote sti til scripts (`/www/wp-content/themes/bleikoya-2023/.claude/skills/styrereferat/`).
- Ellers: lokal `wp --path=$(pwd)` fra theme-katalog (sjekk `wp config path` finnes; fallback til standard WP-rot).

### 2. Velg dokument

**Hvis URL/ID gitt**: bruk direkte.

**Hvis ingen**: kjør list-scriptet og vis nummerert valg. Første argument er enten et mappenavn eller en folder-ID (lang alfanumerisk streng, f.eks. fra en Drive-URL `drive.google.com/drive/folders/<ID>`):

```bash
# Lokalt, etter navn:
wp eval-file .claude/skills/styrereferat/list-docs.php "Styremøter" 15

# Lokalt, etter folder-ID:
wp eval-file .claude/skills/styrereferat/list-docs.php "1lKm65DfCQqhk6ZkjjzHzetiympUlrAq4" 15

# Prod:
ssh bleikoya.net@ssh.bleikoya.net "wp --path=/www eval-file /www/wp-content/themes/bleikoya-2023/.claude/skills/styrereferat/list-docs.php 'Styremøter' 15"
```

Output er TSV: `<doc_id>\t<title>\t<modified>` per linje. Parse og vis som nummerert liste. Hvis "Styremøter"-mappa ikke finnes (ERROR i output), prøv på nytt uten mappefilter — be evt. brukeren om en Drive-URL til riktig mappe og bruk folder-ID-en derfra.

Merk: Styremøter-mappa har historisk én undermappe per møte (ikke per år), så det er ofte ingen direkte docs i selve "Styremøter" — referatene ligger ett nivå ned. Trenger du å finne alle referater på tvers, søk i hele Shared Drive med `name contains 'styremøte'` via Drive API.

Bruk `AskUserQuestion` med opp til 4 nyeste docs. Hvis brukeren vil ha flere, falback til å spørre etter URL.

**Multi-import**: Hvis brukeren ber om å importere alle docs som "mangler" på nettsidene, hent eksisterende poster med `wp post list --category_name=styret --fields=ID,post_title,post_date` og match mot Drive-listen før du spør hvilke som skal importeres.

### 3. Velg kategori

Hent gjeldende kategorier ved kjøretid (ikke hardkod) og spør hvilken som skal brukes. Hent fra REST:

```bash
curl -s "https://bleikoya.net/wp-json/wp/v2/categories?per_page=100&_fields=id,name,slug" | jq '.'
```

Spør med `AskUserQuestion`. Foreslå disse (sjekk at de finnes i respons først, ellers hopp over):

- `styret` (ID 47) — default for styremøtereferat
- `generalforsamling` (ID 48)
- `bleikoya-velforening` (ID 19)
- Ingen kategori

### 4. Kjør import

```bash
# Lokalt:
wp eval-file .claude/skills/styrereferat/import.php "<doc_url_eller_id>" <category_id>

# Prod:
ssh bleikoya.net@ssh.bleikoya.net "wp --path=/www eval-file /www/wp-content/themes/bleikoya-2023/.claude/skills/styrereferat/import.php '<doc_url_eller_id>' <category_id>"
```

Hvis ingen kategori er valgt, utelat siste argument.

### 5. Bekreft til bruker

Parse output:
```
POST_ID: 1234
TITLE: Referat fra Styremøte ...
EDIT_URL: https://.../wp-admin/post.php?post=1234&action=edit
```

Returner til bruker:
- Tittelen på posten
- En klikkbar edit-URL slik at de kan åpne draften
- Påminnelse om at status er **draft** og må publiseres manuelt

## Feilhåndtering

- `ERROR: doc URL/ID required` → be om URL
- `ERROR: GOOGLE_SHARED_DRIVE_ID not configured` → sjekk at `.env` har `GOOGLE_SHARED_DRIVE_ID` satt
- Andre Google API-feil (fra `get_google_client()`) → vis meldingen, foreslå å sjekke `GOOGLE_APPLICATION_CREDENTIALS` og at Service Account har tilgang til Shared Drive
- `wp eval-file` exit code ikke 0 → vis stderr/stdout

## Eksempler

**Lim inn URL**:
```
/styrereferat https://docs.google.com/document/d/1abc.../edit
```

**Bla i nyeste docs lokalt**:
```
/styrereferat
```

**Importer direkte til prod**:
```
/styrereferat https://docs.google.com/document/d/1abc.../edit --prod
```
