#!/usr/bin/env node
/**
 * generate-presenter-xml.js - Generates RNA-seq datasetPresenter XML
 *
 * Usage: node generate-presenter-xml.js <bioproject> <project_id> <primary_contact_id> [additional_contact_ids...]
 *
 * This script reads fetched SRA metadata and optionally MINiML data to generate
 * VEuPathDB datasetPresenter XML for RNA-seq datasets.
 */

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
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
 * Derive organismAbbrev from organism name
 * Format: first letter genus + first 3 letters species
 */
function deriveOrganismAbbrev(organismName) {
  const nameParts = organismName.trim().split(/\s+/);
  const genus = nameParts[0] || '';
  const species = nameParts[1] || '';

  const genusPrefix = genus.charAt(0).toLowerCase();
  const speciesPrefix = species.substring(0, 3).toLowerCase();

  return genusPrefix + speciesPrefix;
}

/**
 * Escape text for use in CDATA sections
 */
function escapeForCDATA(text) {
  return text.replace(/\]\]>/g, ']]&gt;');
}

/**
 * Determine if library is likely strand-specific based on library info
 */
function inferStrandSpecificity(runs) {
  // Common strand-specific library selections/protocols
  const strandSpecificSelections = [
    'polya', 'cdna_oligo_dt', 'cdna_randompriming'
  ];

  // Check library selection across runs
  const selections = runs.map(r => (r.library_selection || '').toLowerCase());
  const sources = runs.map(r => (r.library_source || '').toLowerCase());

  // Most modern RNA-seq is strand-specific, default to true
  // unless we see indicators it's not
  return true;
}

/**
 * Extract unique organism name from runs
 */
function getOrganismFromRuns(runs) {
  const organisms = [...new Set(runs.map(r => r.scientific_name).filter(Boolean))];
  return organisms[0] || 'Unknown organism';
}

/**
 * Try to find experiment description from various sources
 */
function findExperimentDescription(sraMetadata, minimlData) {
  // Try MINiML first (usually most descriptive)
  if (minimlData) {
    // Look for Series summary
    const summaryMatch = minimlData.match(/<Summary[^>]*>([\s\S]*?)<\/Summary>/i);
    if (summaryMatch) {
      return summaryMatch[1].trim();
    }
  }

  // Fall back to experiment titles from SRA
  const titles = [...new Set(sraMetadata.runs.map(r => r.experiment_title).filter(Boolean))];
  if (titles.length > 0) {
    return titles[0];
  }

  return 'TODO: Add description';
}

/**
 * Extract methodology info from metadata
 */
function extractMethodology(sraMetadata) {
  const runs = sraMetadata.runs;
  if (runs.length === 0) return '';

  const parts = [];

  // Library strategy
  const strategies = [...new Set(runs.map(r => r.library_strategy).filter(Boolean))];
  if (strategies.length > 0) {
    parts.push(`Library strategy: ${strategies.join(', ')}`);
  }

  // Library layout
  const layouts = [...new Set(runs.map(r => r.library_layout).filter(Boolean))];
  if (layouts.length > 0) {
    parts.push(`Layout: ${layouts.join(', ')}`);
  }

  // Instrument
  const instruments = [...new Set(runs.map(r => r.instrument_model).filter(Boolean))];
  if (instruments.length > 0) {
    parts.push(`Sequencing: ${instruments.join(', ')}`);
  }

  return parts.join('. ');
}

/**
 * Generate the RNA-seq datasetPresenter XML
 */
function generatePresenterXML(data) {
  const {
    presenterName,
    projectId,
    organismName,
    description,
    methodology,
    primaryContactId,
    additionalContactIds,
    bioproject,
    pubmedIds,
    runCount,
    sampleCount,
    isStrandSpecific,
    hasMultipleSamples
  } = data;

  // Format organism name for display
  const organismDisplay = `<i>${organismName}</i>`;

  // Generate contact elements
  const contactElements = additionalContactIds
    .map(id => `    <contactId>${id}</contactId>`)
    .join('\n');

  // Generate pubmed elements
  const pubmedElements = pubmedIds
    .map(id => `    <pubmedId>${id}</pubmedId>`)
    .join('\n');

  return `  <datasetPresenter name="${presenterName}"
                    projectName="${projectId}">
    <displayName><![CDATA[RNA-Seq analysis of ${organismDisplay}]]></displayName>
    <shortDisplayName>TODO: Short name</shortDisplayName>
    <shortAttribution>TODO: Author et al.</shortAttribution>
    <summary><![CDATA[RNA-Seq analysis of ${organismDisplay}]]></summary>
    <description><![CDATA[

<b>General Description:</b> ${escapeForCDATA(description)}
<br><br><b>Methodology used:</b> ${escapeForCDATA(methodology)}

                  ]]></description>
    <protocol></protocol>
    <caveat></caveat>
    <acknowledgement></acknowledgement>
    <releasePolicy></releasePolicy>
    <history buildNumber="TODO"/>
    <primaryContactId>${primaryContactId}</primaryContactId>
${contactElements ? contactElements + '\n' : ''}    <link>
      <text>NCBI Bioproject</text>
      <url>https://www.ncbi.nlm.nih.gov/bioproject/${bioproject}</url>
    </link>
${pubmedElements ? pubmedElements + '\n' : ''}    <templateInjector className="org.apidb.apicommon.model.datasetInjector.RNASeq">
      <prop name="switchStrandsGBrowse">false</prop>
      <prop name="switchStrandsProfiles">false</prop>
      <prop name="graphForceXLabelsHorizontal">false</prop>
      <prop name="hasFishersExactTestData">false</prop>
      <prop name="isEuPathDBSite">true</prop>
      <prop name="jbrowseTracksOnly">false</prop>
      <prop name="graphType">bar</prop>
      <prop name="graphColor">#336699</prop>
      <prop name="graphBottomMarginSize">50</prop>
      <prop name="graphSampleLabels"></prop>
      <prop name="showIntronJunctions">true</prop>
      <prop name="includeInUnifiedJunctions"></prop>
      <prop name="isAlignedToAnnotatedGenome">true</prop>
      <prop name="hasMultipleSamples">${hasMultipleSamples}</prop>
      <prop name="graphXAxisSamplesDescription">TODO: Description of x-axis samples</prop>
      <prop name="graphPriorityOrderGrouping">1000</prop>
      <prop name="optionalQuestionDescription"></prop>
      <prop name="isDESeq">${hasMultipleSamples}</prop>
      <prop name="isDEGseq">false</prop>
      <prop name="includeProfileSimilarity">false</prop>
      <prop name="profileTimeShift"></prop>
    </templateInjector>
  </datasetPresenter>`;
}

function main() {
  const args = process.argv.slice(2);

  if (args.length < 3) {
    console.error('Usage: node generate-presenter-xml.js <bioproject> <project_id> <primary_contact_id> [additional_contact_ids...]');
    console.error('');
    console.error('Arguments:');
    console.error('  bioproject            - BioProject accession (e.g., PRJNA1018599)');
    console.error('  project_id            - VEuPathDB project (e.g., VectorBase, HostDB)');
    console.error('  primary_contact_id    - Primary contact ID from allContacts.xml');
    console.error('  additional_contact_ids - (optional) Additional contact IDs');
    console.error('');
    console.error('Reads from:');
    console.error('  tmp/<bioproject>_sra_metadata.json (required)');
    console.error('  tmp/<GSE>_family.xml (optional, for richer descriptions)');
    console.error('');
    console.error('Example:');
    console.error('  node generate-presenter-xml.js PRJNA1018599 VectorBase john.smith');
    process.exit(1);
  }

  const bioproject = args[0];
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

  // Read SRA metadata
  const sraPath = resolve(`tmp/${bioproject}_sra_metadata.json`);
  if (!existsSync(sraPath)) {
    console.error(`Error: SRA metadata not found at ${sraPath}`);
    console.error('Run fetch-sra-metadata.js first.');
    process.exit(1);
  }

  const sraMetadata = JSON.parse(readFileSync(sraPath, 'utf-8'));

  // Try to read MINiML data (optional)
  let minimlData = null;
  const minimlFiles = readdirSync(resolve('tmp')).filter(f => f.endsWith('_family.xml'));
  if (minimlFiles.length > 0) {
    const minimlPath = resolve(`tmp/${minimlFiles[0]}`);
    try {
      minimlData = readFileSync(minimlPath, 'utf-8');
      console.error(`  Using MINiML data from: ${minimlFiles[0]}`);
    } catch (e) {
      console.error(`  Warning: Could not read MINiML file`);
    }
  }

  // Extract info from metadata
  const runs = sraMetadata.runs || [];
  const organismName = getOrganismFromRuns(runs);
  const uniqueSamples = new Set(runs.map(r => r.sample_accession)).size;

  // Derive presenter name
  const organismAbbrev = deriveOrganismAbbrev(organismName);
  const presenterName = `${organismAbbrev}_${bioproject}_rnaSeq_RSRC`;

  // Find description
  const description = findExperimentDescription(sraMetadata, minimlData);

  // Extract methodology
  const methodology = extractMethodology(sraMetadata);

  // Build data object for template
  const templateData = {
    presenterName,
    projectId,
    organismName,
    description,
    methodology: methodology || 'TODO: Add methodology',
    primaryContactId,
    additionalContactIds,
    bioproject,
    pubmedIds: [], // TODO: Could add PubMed lookup
    runCount: runs.length,
    sampleCount: uniqueSamples,
    isStrandSpecific: inferStrandSpecificity(runs),
    hasMultipleSamples: uniqueSamples > 1 ? 'true' : 'false'
  };

  // Generate XML
  const xml = generatePresenterXML(templateData);

  // Save to tmp file for editing
  const outputPath = resolve(`tmp/${bioproject}_presenter.xml`);
  writeFileSync(outputPath, xml);

  // Save presenter name for downstream scripts (e.g. sample-annotations-to-stf)
  writeFileSync(resolve(`tmp/${bioproject}_presenter_name.txt`), presenterName);

  // Print summary
  console.error('');
  console.error('Generated RNA-seq presenter XML:');
  console.error(`  Output: ${outputPath}`);
  console.error(`  Name: ${presenterName}`);
  console.error(`  Organism: ${organismName}`);
  console.error(`  Runs: ${runs.length}`);
  console.error(`  Unique samples: ${uniqueSamples}`);
  console.error(`  Primary Contact: ${primaryContactId}`);
  if (additionalContactIds.length > 0) {
    console.error(`  Additional Contacts: ${additionalContactIds.join(', ')}`);
  }
  console.error('');
  console.error('Next steps:');
  console.error(`  1. Review and edit: ${outputPath}`);
  console.error('  2. Fill in TODO fields (shortDisplayName, shortAttribution, buildNumber, etc.)');
  console.error('  3. Add pubmedId elements if publications exist');
  console.error('  4. Insert into presenter file when ready');

  // Also output to stdout for reference
  console.log(xml);
}

main();
