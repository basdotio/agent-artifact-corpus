# Step 4: Curate Contacts

## Overview

This step identifies and curates contact entries for the genome submission. Contacts are stored in a shared file and referenced by ID in the presenter XML.

## Contacts File

All contacts are stored in:

```
veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml
```

## Contact Identification Priority

1. **Named submitter from assembly metadata**: Check `submitter` field in assembly report
2. **Senior/last author from PubMed**: The `lastAuthor` from fetch-pubmed results
3. **Other PubMed authors**: If the paper is clearly a genome-sequencing paper (not incidental)
4. **Curator judgment**: For ambiguous cases, ask curator to decide using the `AskUserQuestion` tool

## Searching for Existing Contacts

The allContacts.xml file is large. Use grep to search for potential matches:

```bash
# Search by surname (case-insensitive, handles some diacritics)
grep -i "skerker" veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml

# Search with context to see full contact record
grep -i -A5 "skerker" veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml
```

### Diacritic-Aware Searching

For names with diacritics (é, ö, ñ, etc.), search for the base form:

```bash
# For "Müller", try:
grep -i "muller\|müller" allContacts.xml
```

## Contact XML Structure

```xml
<contact>
  <contactId>firstname.lastname</contactId>
  <name>First M. Last</name>
  <institution>University Name</institution>
  <email>email@example.com</email>
  <address></address>
  <city></city>
  <state/>
  <zip></zip>
  <country></country>
</contact>
```

### Contact ID Format

- Typically: `firstname.lastname` (lowercase, periods as separators)
- Examples: `jeffrey.m.skerker`, `jorge.dubcovsky`, `robert.h.proctor`
- For common names, may include middle initial to disambiguate

## Creating New Contacts

**CRITICAL**: The allContacts.xml file is ~40,000 lines. You MUST follow this procedure:

1. **Ask the curator** with the `AskUserQuestion` tool whether they prefer new contacts at the beginning or end of the file
2. **Get line count first**: `wc -l .../allContacts.xml`
3. **Use Read with offset** to read only the relevant section (e.g., last 50 lines for end insertion)
4. **Never read the entire file** - multiple 100-line reads wastes context

See [Editing Large XML Files](editing-large-xml.md) for detailed patterns.

### Required fields for new contacts:
   - **contactId**: Unique identifier (e.g., `firstname.lastname`, lowercase)
   - **name**: Full name as it appears in publications
   - **institution**: Current affiliation (from paper or assembly metadata)
   - **email**: Optional but helpful if available
   - Empty tags for: address, city, state, zip, country

### Finding full first names

The fetch-pubmed results may only have initials (e.g., "D. F. Smith"). To find full first names, fetch the PubMed article page directly:

```
WebFetch(url="https://pubmed.ncbi.nlm.nih.gov/<PMID>/", prompt="What are the full author names?")
```

Full first names make contact IDs more unique and less prone to collision. This is optional but helpful.

## Presenter XML References

The presenter XML uses two contact elements:

```xml
<primaryContactId>firstname.lastname</primaryContactId>
<contactId>another.person</contactId>  <!-- optional, for additional contacts -->
```

- **primaryContactId**: Required. The main contact for the dataset.
- **contactId**: Optional. Can have multiple for additional contributors.

## Decision Guidelines

### When to include all paper authors:
- Paper is specifically about genome sequencing/annotation
- Authors are clearly genome project contributors

### When to be selective:
- Genome is incidental to a larger study
- Paper has many authors from a consortium
- Focus on those who led the sequencing work

### Present choices to curator:
Always show the curator your findings and recommendations before finalizing contact selections.

## Next Step

Proceed to [Step 5 - Update Presenter Files](step-5-update-presenter.md) to generate and insert the presenter XML.
