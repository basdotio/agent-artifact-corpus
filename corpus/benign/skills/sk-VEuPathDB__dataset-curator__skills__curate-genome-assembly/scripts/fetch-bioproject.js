#!/usr/bin/env node
/**
 * fetch-bioproject.js - Fetches BioProject metadata from NCBI
 *
 * Usage: node fetch-bioproject.js <bioproject_accession>
 *
 * This script:
 * 1. Uses NCBI esearch to get the BioProject ID from accession
 * 2. Uses NCBI esummary to get BioProject details (title, description)
 * 3. Saves results to tmp/<bioproject_accession>_bioproject.json
 */

import { writeFileSync } from 'fs';
import { resolve } from 'path';

const EUTILS_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';

/**
 * Fetch JSON from NCBI E-utilities
 */
async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Search for BioProject ID by accession
 */
async function searchBioProject(accession) {
  // The [PRJA] field tag searches for project accessions
  const url = `${EUTILS_BASE}/esearch.fcgi?db=bioproject&term=${accession}[PRJA]&retmode=json`;
  const result = await fetchJson(url);

  if (!result.esearchresult?.idlist?.length) {
    throw new Error(`No BioProject found for accession: ${accession}`);
  }

  return result.esearchresult.idlist[0];
}

/**
 * Get BioProject summary by ID
 */
async function getBioProjectSummary(id) {
  const url = `${EUTILS_BASE}/esummary.fcgi?db=bioproject&id=${id}&retmode=json`;
  const result = await fetchJson(url);

  if (!result.result?.[id]) {
    throw new Error(`No summary found for BioProject ID: ${id}`);
  }

  return result.result[id];
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('Usage: node fetch-bioproject.js <bioproject_accession>');
    console.error('');
    console.error('Arguments:');
    console.error('  bioproject_accession - BioProject accession (e.g., PRJNA282568)');
    console.error('');
    console.error('Example:');
    console.error('  node fetch-bioproject.js PRJNA282568');
    process.exit(1);
  }

  const accession = args[0];

  // Validate accession format (PRJNA, PRJEA, PRJDA, etc.)
  if (!/^PRJ[A-Z]{1,2}\d+$/.test(accession)) {
    console.error(`Error: Invalid BioProject accession format: ${accession}`);
    console.error('Expected format: PRJNA123456, PRJEA123456, PRJDA123456, etc.');
    process.exit(1);
  }

  console.error(`Fetching BioProject: ${accession}`);

  try {
    // Step 1: Search for BioProject ID
    console.error('  Searching for BioProject ID...');
    const bioProjectId = await searchBioProject(accession);
    console.error(`  Found BioProject ID: ${bioProjectId}`);

    // Step 2: Get BioProject summary
    console.error('  Fetching BioProject summary...');
    const summary = await getBioProjectSummary(bioProjectId);

    // Extract relevant fields
    const output = {
      accession: accession,
      id: bioProjectId,
      title: summary.project_title || '',
      description: summary.project_description || '',
      organism: summary.organism_name || '',
      submitterOrganization: summary.organization || '',
      registrationDate: summary.registration_date || '',
      // Keep raw summary for reference
      _raw: summary
    };

    // Save to file
    const outputPath = resolve(`tmp/${accession}_bioproject.json`);
    writeFileSync(outputPath, JSON.stringify(output, null, 2));
    console.error(`  Saved to: ${outputPath}`);

    // Also output to stdout for piping
    console.log(JSON.stringify(output, null, 2));

  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

main();
