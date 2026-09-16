#!/usr/bin/env node
/**
 * fetch-sra-metadata.js - Fetches and merges SRA run metadata with BioSample attributes
 *
 * Usage: node fetch-sra-metadata.js <bioproject_accession>
 *
 * This script:
 * 1. Queries ENA Portal API for run-level metadata
 * 2. Extracts unique sample accessions (SAMN...)
 * 3. Queries NCBI BioSample API for custom attributes (batched)
 * 4. Merges run data with sample attributes
 * 5. Writes combined JSON to tmp/
 *
 * Falls back to manual CSV if API fetching fails.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const ENA_PORTAL_API = 'https://www.ebi.ac.uk/ena/portal/api/search';
const NCBI_EFETCH = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi';

// ENA fields to request
const ENA_FIELDS = [
  'run_accession',
  'sample_accession',
  'sample_alias',
  'sample_title',
  'experiment_title',
  'library_layout',
  'library_strategy',
  'library_source',
  'library_selection',
  'instrument_platform',
  'instrument_model',
  'read_count',
  'base_count',
  'scientific_name',
  'tax_id'
].join(',');

/**
 * Fetch JSON from ENA Portal API
 */
async function fetchEnaRuns(bioproject) {
  const url = `${ENA_PORTAL_API}?result=read_run&query=study_accession=${bioproject}&fields=${ENA_FIELDS}&format=json`;

  console.error(`  Querying ENA Portal API...`);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`ENA API error: HTTP ${response.status}`);
  }

  const data = await response.json();

  if (!Array.isArray(data) || data.length === 0) {
    throw new Error(`No runs found in ENA for BioProject: ${bioproject}`);
  }

  console.error(`  Found ${data.length} runs`);
  return data;
}

/**
 * Parse BioSample XML and extract attributes
 */
function parseBioSampleXml(xml) {
  const samples = {};

  // Match each BioSample element
  const sampleRegex = /<BioSample[^>]*accession="([^"]+)"[^>]*>([\s\S]*?)<\/BioSample>/g;
  let match;

  while ((match = sampleRegex.exec(xml)) !== null) {
    const accession = match[1];
    const content = match[2];

    const attributes = {};

    // Extract attributes
    const attrRegex = /<Attribute[^>]*attribute_name="([^"]+)"[^>]*>([^<]*)<\/Attribute>/g;
    let attrMatch;

    while ((attrMatch = attrRegex.exec(content)) !== null) {
      const name = attrMatch[1].toLowerCase().replace(/\s+/g, '_');
      const value = attrMatch[2].trim();
      if (value) {
        attributes[name] = value;
      }
    }

    samples[accession] = attributes;
  }

  return samples;
}

/**
 * Fetch BioSample attributes from NCBI (batched)
 */
async function fetchBioSampleAttributes(sampleAccessions) {
  const allAttributes = {};
  const batchSize = 100;

  console.error(`  Fetching BioSample attributes for ${sampleAccessions.length} samples...`);

  for (let i = 0; i < sampleAccessions.length; i += batchSize) {
    const batch = sampleAccessions.slice(i, i + batchSize);
    const ids = batch.join(',');

    const url = `${NCBI_EFETCH}?db=biosample&id=${ids}&retmode=xml`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        console.error(`    Warning: BioSample batch ${i / batchSize + 1} failed: HTTP ${response.status}`);
        continue;
      }

      const xml = await response.text();
      const batchAttributes = parseBioSampleXml(xml);
      Object.assign(allAttributes, batchAttributes);

      console.error(`    Fetched batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(sampleAccessions.length / batchSize)}`);

      // Rate limiting - be nice to NCBI
      if (i + batchSize < sampleAccessions.length) {
        await new Promise(resolve => setTimeout(resolve, 350));
      }
    } catch (err) {
      console.error(`    Warning: BioSample batch ${i / batchSize + 1} failed: ${err.message}`);
    }
  }

  return allAttributes;
}

/**
 * Parse CSV manually (no dependencies)
 */
function parseCsv(content) {
  const lines = content.split(/\r?\n/).filter(line => line.trim());
  if (lines.length < 2) return [];

  // Parse header - handle quoted fields
  const parseRow = (line) => {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  };

  const headers = parseRow(lines[0]);
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseRow(lines[i]);
    const row = {};
    headers.forEach((header, idx) => {
      row[header] = values[idx] || '';
    });
    rows.push(row);
  }

  return rows;
}

/**
 * Convert CSV rows to our JSON format
 */
function csvToRuns(rows) {
  return rows.map(row => {
    // Map common CSV column names to our format
    const run = {
      run_accession: row['Run'] || row['run_accession'] || '',
      sample_accession: row['BioSample'] || row['sample_accession'] || '',
      sample_alias: row['Sample Name'] || row['sample_alias'] || '',
      sample_title: row['sample_title'] || '',
      experiment_title: row['Experiment'] || row['experiment_title'] || '',
      library_layout: row['LibraryLayout'] || row['library_layout'] || '',
      library_strategy: row['LibraryStrategy'] || row['library_strategy'] || '',
      library_source: row['LibrarySource'] || row['library_source'] || '',
      library_selection: row['LibrarySelection'] || row['library_selection'] || '',
      instrument_platform: row['Platform'] || row['instrument_platform'] || '',
      instrument_model: row['Model'] || row['instrument_model'] || '',
      read_count: parseInt(row['spots'] || row['read_count'] || '0', 10) || null,
      base_count: parseInt(row['bases'] || row['base_count'] || '0', 10) || null,
      scientific_name: row['Organism'] || row['scientific_name'] || '',
      tax_id: row['TaxID'] || row['tax_id'] || ''
    };

    // Collect remaining columns as sample_attributes
    const knownKeys = new Set([
      'Run', 'run_accession', 'BioSample', 'sample_accession', 'Sample Name', 'sample_alias',
      'sample_title', 'Experiment', 'experiment_title', 'LibraryLayout', 'library_layout',
      'LibraryStrategy', 'library_strategy', 'LibrarySource', 'library_source',
      'LibrarySelection', 'library_selection', 'Platform', 'instrument_platform',
      'Model', 'instrument_model', 'spots', 'read_count', 'bases', 'base_count',
      'Organism', 'scientific_name', 'TaxID', 'tax_id', 'Bytes', 'AvgSpotLen',
      'Consent', 'DATASTORE_filetype', 'DATASTORE_provider', 'DATASTORE_region',
      'Assay Type', 'BioProject', 'Center Name', 'SRA Study', 'ReleaseDate'
    ]);

    const attributes = {};
    for (const [key, value] of Object.entries(row)) {
      if (!knownKeys.has(key) && value) {
        const normalizedKey = key.toLowerCase().replace(/\s+/g, '_');
        attributes[normalizedKey] = value;
      }
    }

    if (Object.keys(attributes).length > 0) {
      run.sample_attributes = attributes;
    }

    return run;
  });
}

/**
 * Try to load manual CSV fallback
 */
function tryLoadManualCsv(bioproject) {
  const paths = [
    resolve(`tmp/${bioproject}_SraRunTable.csv`),
    resolve('tmp/SraRunTable.csv')
  ];

  for (const csvPath of paths) {
    if (existsSync(csvPath)) {
      console.error(`  Found manual CSV: ${csvPath}`);
      const content = readFileSync(csvPath, 'utf-8');
      const rows = parseCsv(content);
      console.error(`  Parsed ${rows.length} rows from CSV`);
      return csvToRuns(rows);
    }
  }

  return null;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('Usage: node fetch-sra-metadata.js <bioproject_accession>');
    console.error('');
    console.error('Arguments:');
    console.error('  bioproject_accession - BioProject accession (e.g., PRJNA1018599)');
    console.error('');
    console.error('Example:');
    console.error('  node fetch-sra-metadata.js PRJNA1018599');
    console.error('');
    console.error('Output: tmp/<bioproject>_sra_metadata.json');
    console.error('');
    console.error('Fallback: If API fails, place SraRunTable.csv in tmp/ directory');
    process.exit(1);
  }

  const bioproject = args[0];

  // Validate accession format
  if (!/^PRJ[A-Z]{1,2}\d+$/.test(bioproject)) {
    console.error(`Error: Invalid BioProject accession format: ${bioproject}`);
    console.error('Expected format: PRJNA123456, PRJEA123456, PRJDA123456, etc.');
    process.exit(1);
  }

  console.error(`Fetching SRA metadata for: ${bioproject}`);

  let runs;
  let source = 'ENA+BioSample';

  try {
    // Step 1: Fetch runs from ENA
    runs = await fetchEnaRuns(bioproject);

    // Step 2: Extract unique sample accessions
    const sampleAccessions = [...new Set(runs.map(r => r.sample_accession).filter(Boolean))];

    // Step 3: Fetch BioSample attributes
    const sampleAttributes = await fetchBioSampleAttributes(sampleAccessions);

    // Step 4: Merge attributes into runs
    for (const run of runs) {
      if (run.sample_accession && sampleAttributes[run.sample_accession]) {
        run.sample_attributes = sampleAttributes[run.sample_accession];
      }
    }

  } catch (err) {
    console.error(`  API fetch failed: ${err.message}`);
    console.error('  Checking for manual CSV fallback...');

    runs = tryLoadManualCsv(bioproject);

    if (!runs) {
      console.error('');
      console.error('No data available. To use manual fallback:');
      console.error(`  1. Go to: https://www.ncbi.nlm.nih.gov/Traces/study/?acc=${bioproject}`);
      console.error('  2. Click "Metadata" button to download SraRunTable.csv');
      console.error(`  3. Save as: tmp/${bioproject}_SraRunTable.csv`);
      console.error('  4. Re-run this script');
      process.exit(1);
    }

    source = 'manual_csv';
  }

  // Build output
  const output = {
    bioproject: bioproject,
    fetchDate: new Date().toISOString(),
    source: source,
    runCount: runs.length,
    runs: runs
  };

  // Save to file
  const outputPath = resolve(`tmp/${bioproject}_sra_metadata.json`);
  writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.error(`  Saved to: ${outputPath}`);

  // Summary
  console.error('');
  console.error(`Summary:`);
  console.error(`  Runs: ${runs.length}`);
  console.error(`  Unique samples: ${new Set(runs.map(r => r.sample_accession)).size}`);

  const withAttrs = runs.filter(r => r.sample_attributes && Object.keys(r.sample_attributes).length > 0).length;
  console.error(`  Runs with custom attributes: ${withAttrs}`);

  // Also output to stdout
  console.log(JSON.stringify(output, null, 2));
}

main();
