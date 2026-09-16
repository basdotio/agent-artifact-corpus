# Step 3: Curate Contacts

## Overview

This step identifies and curates contact entries for the RNA-seq dataset. Contacts are stored in a shared file and referenced by ID in the presenter XML.

## Contacts File

All contacts are stored in:

```
veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml
```

## Contact Identification Sources

### For GEO-linked datasets (MINiML available)
1. **GEO contributors**: Listed in the MINiML `<Contributor>` elements
2. **Contact email**: Listed in `<Contact>` or submitter info

### For non-GEO datasets
1. **BioProject submitter**: Organization from BioProject metadata
2. **PubMed authors**: If a linked publication exists

### General priority
1. Principal investigator or lab head
2. Data submitter / first author
3. Senior author from associated publications

### For datasets with PDF data
If `tmp/<BIOPROJECT>_pdf_extracted.json` exists, it provides rich author information:

```json
{
  "extracted": {
    "authors": [
      {
        "name": "Full Name",
        "affiliation": "University/Institute",
        "roles": ["corresponding author", "conceived project", "performed experiments"],
        "isLikelyDataSubmitter": true
      }
    ]
  },
  "textChunks": {
    "authorAffiliations": "Full author list with affiliations..."
  }
}
```

**Using PDF author data:**
- **Positional roles**: Look for `"corresponding author"`, `"first author"`, `"last author"` in the `roles` array to identify primaryContactId
- **Contribution details**: Additional roles like `"performed experiments"`, `"analyzed data"` help identify secondary contacts who were specifically involved in the transcriptomics work
- **Data submitter**: The `isLikelyDataSubmitter` flag identifies who likely submitted the SRA data
- **Full affiliations**: The `authorAffiliations` text chunk has complete institution details
- **Cross-reference**: Match PDF authors with GEO contributors or BioProject submitters

**Primary contact selection:**
1. Corresponding author (usually the PI)
2. Author marked as `isLikelyDataSubmitter`
3. Last author (if different from above)

**Secondary contacts** (if adding additional contacts):
- Authors with roles indicating direct involvement in transcriptomics: `"performed experiments"`, `"analyzed data"`, `"supervised"`

## Searching for Existing Contacts

The allContacts.xml file is large. Use grep to search for potential matches:

```bash
# Search by surname (case-insensitive)
grep -i "smith" veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml

# Search with context to see full contact record
grep -i -A5 "smith" veupathdb-repos/EbrcModelCommon/Model/lib/xml/datasetPresenters/contacts/allContacts.xml
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
- Examples: `john.smith`, `maria.garcia`, `wei.zhang`
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
   - **institution**: Current affiliation
   - **email**: Optional but helpful if available
   - Empty tags for: address, city, state, zip, country

### Extracting Contact Info from MINiML

If you have MINiML data, look for contributor information:

```xml
<Contributor iid="contrib1">
  <Person>
    <First>John</First>
    <Last>Smith</Last>
  </Person>
  <Laboratory>Smith Lab</Laboratory>
  <Department>Biology</Department>
  <Organization>University</Organization>
  <Email>john.smith@univ.edu</Email>
</Contributor>
```

## Presenter XML References

The presenter XML uses two contact elements:

```xml
<primaryContactId>firstname.lastname</primaryContactId>
<contactId>another.person</contactId>  <!-- optional, for additional contacts -->
```

- **primaryContactId**: Required. The main contact for the dataset.
- **contactId**: Optional. Can have multiple for additional contributors.

## Decision Guidelines

### When to include additional contacts:
- Multiple PIs contributed to the study
- Clearly identified lab heads in submission metadata
- Paper has clear lead authors

### When to be selective:
- Large consortium papers
- Unknown relationship between authors and data generation
- Focus on corresponding author or data submitter

### Present choices to curator:
Always show the curator your findings and recommendations before finalizing contact selections.

## Next Step

Proceed to [Step 4 - Generate Presenter](step-4-generate-presenter.md) to generate and insert the presenter XML.
