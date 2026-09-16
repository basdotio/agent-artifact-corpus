#!/usr/bin/env node
/**
 * generate-presenter-xml.js - Generates datasetPresenter XML from NCBI metadata
 *
 * Usage: node generate-presenter-xml.js <genbank_accession> <project_id> <primary_contact_id> [additional_contact_ids...]
 *
 * This script reads fetched NCBI metadata and generates VEuPathDB datasetPresenter XML
 * for ApiCommonPresenters. All templates are inlined - no external dependencies required.
 */

import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

// Load valid project IDs from resources
const validProjectsPath = new URL('../resources/valid-projects.json', import.meta.url);
const VALID_PROJECT_IDS = JSON.parse(readFileSync(validProjectsPath, 'utf-8'));

/**
 * Remove special characters, keeping only alphanumeric
 */
function removeSpecialChars(str) {
  return str.replace(/[^a-zA-Z0-9]/g, '');
}

/**
 * Derive organismAbbrev from organism name and strain
 * Format: first letter genus + first 3 letters species + strain (no special chars, max 30)
 */
function deriveOrganismAbbrev(organismName, strain) {
  const nameParts = organismName.split(' ');
  const genus = nameParts[0] || '';
  const species = nameParts.slice(1).join(' ') || '';

  const genusPrefix = genus.charAt(0).toLowerCase();
  const speciesPrefix = species.substring(0, 3).toLowerCase();
  const strainSuffix = removeSpecialChars(strain);

  return (genusPrefix + speciesPrefix + strainSuffix).substring(0, 30);
}

/**
 * Format date from YYYY-MM-DD to Mon DD, YYYY
 */
function formatDate(isoDate) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const [year, month, day] = isoDate.split('-');
  return `${months[parseInt(month) - 1]} ${parseInt(day)}, ${year}`;
}

/**
 * Escape text for use in CDATA sections (mainly for display purposes)
 */
function escapeForCDATA(text) {
  // CDATA cannot contain ]]> sequence
  return text.replace(/\]\]>/g, ']]&gt;');
}

/**
 * Generate methodology text from assembly info
 */
function generateMethodology(assemblyInfo, wgsInfo) {
  const parts = [];

  if (wgsInfo?.wgs_project_accession) {
    parts.push(`WGS Project: ${wgsInfo.wgs_project_accession}`);
  }

  if (assemblyInfo?.assembly_method) {
    parts.push(`Assembly method: ${assemblyInfo.assembly_method}`);
  }

  if (assemblyInfo?.genome_coverage) {
    parts.push(`Genome coverage: ${assemblyInfo.genome_coverage}x`);
  }

  if (assemblyInfo?.sequencing_tech) {
    parts.push(`Sequencing technology: ${assemblyInfo.sequencing_tech}`);
  }

  return parts.join('. ');
}

/**
 * Generate the datasetPresenter XML
 */
function generatePresenterXML(data) {
  const {
    presenterName,
    organismName,
    strain,
    description,
    methodology,
    buildNumber,
    genomeSource,
    genomeVersion,
    annotationSource,
    annotationVersion,
    primaryContactId,
    additionalContactIds,
    bioProjectAccession,
    pubmedIds,
    projectId
  } = data;

  // Format organism name with strain for summary
  const organismForSummary = strain
    ? `<i>${organismName}</i> ${strain}`
    : `<i>${organismName}</i>`;

  // Generate contact elements
  const contactElements = additionalContactIds
    .map(id => `    <contactId>${id}</contactId>`)
    .join('\n');

  // Generate pubmed elements
  const pubmedElements = pubmedIds
    .map(id => `    <pubmedId>${id}</pubmedId>`)
    .join('\n');

  return `  <datasetPresenter name="${presenterName}"
                    >
    <displayName><![CDATA[Genome Sequence and Annotation]]></displayName>
    <shortDisplayName></shortDisplayName>
    <shortAttribution></shortAttribution>
    <summary><![CDATA[Genome Sequence and Annotation of ${organismForSummary}
                  ]]></summary>
    <description><![CDATA[

<b>General Description:</b> ${escapeForCDATA(description)}
<br><br><b>Methodology used:</b> ${escapeForCDATA(methodology)}

                  ]]></description>
    <protocol></protocol>
    <caveat></caveat>
    <acknowledgement></acknowledgement>
    <releasePolicy></releasePolicy>
    <history buildNumber="${buildNumber}"
             genomeSource="${genomeSource}" genomeVersion="${genomeVersion}"
             annotationSource="${annotationSource}" annotationVersion="${annotationVersion}"/>
    <primaryContactId>${primaryContactId}</primaryContactId>
${contactElements ? contactElements + '\n' : ''}    <link>
      <text>NCBI Bioproject</text>
      <url>https://www.ncbi.nlm.nih.gov/bioproject/${bioProjectAccession}</url>
    </link>
    <link>
      <text>GenBank Assembly</text>
      <url>https://www.ncbi.nlm.nih.gov/assembly/${genomeVersion}</url>
    </link>
${pubmedElements ? pubmedElements + '\n' : ''}    <templateInjector projectName="${projectId}" className="org.apidb.apicommon.model.datasetInjector.AnnotatedGenome">
      <prop name="isEuPathDBSite">true</prop>
      <prop name="optionalSpecies"></prop>
      <prop name="specialLinkDisplayText"></prop>
      <prop name="updatedAnnotationText"></prop>
      <prop name="isCurated">false</prop>
      <prop name="specialLinkExternalDbName"></prop>
      <prop name="showReferenceTranscriptomics">false</prop>
    </templateInjector>
  </datasetPresenter>`;
}

function main() {
  const args = process.argv.slice(2);

  if (args.length < 3) {
    console.error('Usage: node generate-presenter-xml.js <genbank_accession> <project_id> <primary_contact_id> [additional_contact_ids...]');
    console.error('');
    console.error('Arguments:');
    console.error('  genbank_accession     - GenBank assembly accession (e.g., GCA_000988875.2)');
    console.error('  project_id            - VEuPathDB project (e.g., FungiDB, PlasmoDB)');
    console.error('  primary_contact_id    - Primary contact ID from allContacts.xml');
    console.error('  additional_contact_ids - (optional) Additional contact IDs');
    console.error('');
    console.error('Example:');
    console.error('  node generate-presenter-xml.js GCA_000988875.2 FungiDB jeffrey.m.skerker');
    process.exit(1);
  }

  const genbankAccession = args[0];
  const projectId = args[1];
  const primaryContactId = args[2];
  const additionalContactIds = args.slice(3);

  // Validate project ID
  if (!VALID_PROJECT_IDS.includes(projectId)) {
    const projectIdLower = projectId.toLowerCase();
    const match = VALID_PROJECT_IDS.find(id => id.toLowerCase() === projectIdLower);

    if (match) {
      console.error(`Error: PROJECT_ID "${projectId}" appears to be a typo. Did you mean "${match}"?`);
    } else {
      console.error(`Error: PROJECT_ID "${projectId}" is not valid.`);
      console.error(`Valid PROJECT_IDs: ${VALID_PROJECT_IDS.join(', ')}`);
    }
    process.exit(1);
  }

  // Read assembly dataset report
  const assemblyPath = resolve(`tmp/${genbankAccession}_dataset_report.json`);
  if (!existsSync(assemblyPath)) {
    console.error(`Error: Assembly report not found at ${assemblyPath}`);
    console.error('Run Step 1 (fetch assembly metadata) first.');
    process.exit(1);
  }

  const assemblyData = JSON.parse(readFileSync(assemblyPath, 'utf-8'));
  const report = assemblyData.reports[0];

  // Extract bioproject accession
  const bioProjectAccession = report.assembly_info?.bioproject_accession;
  if (!bioProjectAccession) {
    console.error('Error: BioProject accession not found in assembly report');
    process.exit(1);
  }

  // Try to read bioproject data (optional - for description)
  const bioProjectPath = resolve(`tmp/${bioProjectAccession}_bioproject.json`);
  let bioProjectDescription = '';
  if (existsSync(bioProjectPath)) {
    const bioProjectData = JSON.parse(readFileSync(bioProjectPath, 'utf-8'));
    bioProjectDescription = bioProjectData.description || bioProjectData.title || '';
  } else {
    console.error(`Warning: BioProject data not found at ${bioProjectPath}`);
    console.error('Run fetch-bioproject.js to get BioProject description.');
    // Fall back to bioproject title from assembly report
    const bioProjectLineage = report.assembly_info?.bioproject_lineage?.[0]?.bioprojects?.[0];
    bioProjectDescription = bioProjectLineage?.title || 'TODO: Add description';
  }

  // Try to read pubmed data (optional)
  const pubmedPath = resolve(`tmp/${genbankAccession}_pubmed.json`);
  let pubmedIds = [];
  if (existsSync(pubmedPath)) {
    const pubmedData = JSON.parse(readFileSync(pubmedPath, 'utf-8'));
    pubmedIds = pubmedData.papers?.map(p => p.pmid) || [];
  } else {
    console.error(`Note: PubMed data not found at ${pubmedPath}`);
    console.error('Run fetch-pubmed.js to find linked publications.');
  }

  // Extract organism info
  const organismName = report.organism?.organism_name || '';
  const strain = report.organism?.infraspecific_names?.strain || '';

  // Derive presenter name
  const organismAbbrev = deriveOrganismAbbrev(organismName, strain);
  const presenterName = `${organismAbbrev}_primary_genome_RSRC`;

  // Determine genome/annotation source
  const sourceDb = report.source_database || '';
  const isRefSeq = sourceDb.includes('REFSEQ');
  const genomeSource = 'INSDC'; // Always INSDC for both GenBank and RefSeq
  const annotationSource = isRefSeq ? 'RefSeq' : 'GenBank';

  // Format annotation version date
  const annotationDate = report.annotation_info?.release_date || report.assembly_info?.release_date || '';
  const annotationVersion = annotationDate ? formatDate(annotationDate) : 'TODO';

  // Generate methodology
  const methodology = generateMethodology(
    {
      assembly_method: report.assembly_info?.assembly_method,
      genome_coverage: report.assembly_stats?.genome_coverage,
      sequencing_tech: report.assembly_info?.sequencing_tech
    },
    report.wgs_info
  );

  // Build data object for template
  const templateData = {
    presenterName,
    organismName,
    strain,
    description: bioProjectDescription,
    methodology: methodology || 'TODO: Add methodology',
    buildNumber: 'TODO', // Curator needs to determine this
    genomeSource,
    genomeVersion: genbankAccession,
    annotationSource,
    annotationVersion,
    primaryContactId,
    additionalContactIds,
    bioProjectAccession,
    pubmedIds,
    projectId
  };

  // Generate and output XML
  const xml = generatePresenterXML(templateData);
  console.log(xml);

  // Print summary to stderr
  console.error('');
  console.error('Generated presenter XML:');
  console.error(`  Name: ${presenterName}`);
  console.error(`  Organism: ${organismName}${strain ? ' ' + strain : ''}`);
  console.error(`  Primary Contact: ${primaryContactId}`);
  if (additionalContactIds.length > 0) {
    console.error(`  Additional Contacts: ${additionalContactIds.join(', ')}`);
  }
  console.error(`  BioProject: ${bioProjectAccession}`);
  console.error(`  PubMed IDs: ${pubmedIds.length > 0 ? pubmedIds.join(', ') : 'none found'}`);
  console.error('');
  console.error('TODO items to complete:');
  console.error('  - Set buildNumber in history element');
  console.error('  - Review/edit description text');
  if (pubmedIds.length === 0) {
    console.error('  - Add pubmedId elements if publications exist');
  }
}

main();
