#!/usr/bin/env node
/**
 * fetch-miniml.js - Finds and downloads MINiML XML for GEO-linked BioProjects
 *
 * Usage: node fetch-miniml.js <bioproject_accession>
 *
 * This script:
 * 1. Queries NCBI GDS database for BioProject
 * 2. Extracts GEO series accession (GSE...)
 * 3. Downloads MINiML XML from NCBI FTP
 * 4. Saves to tmp/
 *
 * Output:
 *   - Success: Prints GSE accession to stdout, writes XML to tmp/{GSE}_family.xml
 *   - No GEO link: Prints "NO_GEO_LINK" to stdout
 */

import { writeFileSync } from 'fs';
import { resolve } from 'path';
import { gunzipSync } from 'zlib';

const EUTILS_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';

/**
 * Search GEO DataSets for a BioProject
 */
async function searchGeoForBioProject(bioproject) {
  const url = `${EUTILS_BASE}/esearch.fcgi?db=gds&term=${bioproject}[BioProject]&retmode=json`;

  console.error(`  Searching GEO for BioProject ${bioproject}...`);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`NCBI esearch error: HTTP ${response.status}`);
  }

  const data = await response.json();
  const ids = data.esearchresult?.idlist || [];

  if (ids.length === 0) {
    return null;
  }

  console.error(`  Found ${ids.length} GEO DataSet ID(s)`);
  return ids;
}

/**
 * Get GEO DataSet summary to extract GSE accession
 */
async function getGdsSummary(ids) {
  const url = `${EUTILS_BASE}/esummary.fcgi?db=gds&id=${ids.join(',')}&retmode=json`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`NCBI esummary error: HTTP ${response.status}`);
  }

  const data = await response.json();

  // Look for GSE accessions in results
  for (const id of ids) {
    const result = data.result?.[id];
    if (result?.accession?.startsWith('GSE')) {
      return result.accession;
    }
  }

  // Sometimes the accession is in a different format, check entrytype
  for (const id of ids) {
    const result = data.result?.[id];
    if (result?.entrytype === 'GSE') {
      // The accession might be the GDS ID, need to extract GSE from gse field
      if (result.gse) {
        return `GSE${result.gse}`;
      }
    }
  }

  return null;
}

/**
 * Download and extract MINiML XML
 */
async function downloadMiniml(gseAccession) {
  // GSE accessions are organized in directories by thousands
  // e.g., GSE245678 is in GSE245nnn/
  const gseNumber = gseAccession.replace('GSE', '');
  const dirSuffix = gseNumber.slice(0, -3) + 'nnn';
  const gseDir = `GSE${dirSuffix}`;

  // Try gzipped first
  const gzUrl = `https://ftp.ncbi.nlm.nih.gov/geo/series/${gseDir}/${gseAccession}/miniml/${gseAccession}_family.xml.tgz`;

  console.error(`  Downloading MINiML from: ${gzUrl}`);

  try {
    const response = await fetch(gzUrl);

    if (!response.ok) {
      // Try direct XML (some older series)
      const xmlUrl = `https://ftp.ncbi.nlm.nih.gov/geo/series/${gseDir}/${gseAccession}/miniml/${gseAccession}_family.xml`;
      console.error(`  Trying uncompressed: ${xmlUrl}`);

      const xmlResponse = await fetch(xmlUrl);
      if (!xmlResponse.ok) {
        throw new Error(`MINiML not found at NCBI FTP (tried .tgz and .xml)`);
      }

      return await xmlResponse.text();
    }

    // It's a .tgz file - need to decompress
    const buffer = await response.arrayBuffer();
    const tgzData = new Uint8Array(buffer);

    // The .tgz is gzipped tar - we need to gunzip first
    // For simplicity, we'll use zlib to gunzip then manually extract tar
    const tarData = gunzipSync(Buffer.from(tgzData));

    // Parse tar format to extract the XML file
    // Tar files have 512-byte headers followed by file content
    let offset = 0;
    while (offset < tarData.length) {
      // Read filename from header (first 100 bytes)
      const filename = tarData.slice(offset, offset + 100).toString('utf-8').replace(/\0/g, '').trim();

      if (!filename) break; // End of archive

      // Read file size from header (bytes 124-136, octal)
      const sizeStr = tarData.slice(offset + 124, offset + 136).toString('utf-8').replace(/\0/g, '').trim();
      const fileSize = parseInt(sizeStr, 8) || 0;

      // Skip header (512 bytes)
      offset += 512;

      // If this is the XML file, extract it
      if (filename.endsWith('.xml')) {
        const content = tarData.slice(offset, offset + fileSize).toString('utf-8');
        return content;
      }

      // Skip to next file (padded to 512-byte boundary)
      offset += Math.ceil(fileSize / 512) * 512;
    }

    throw new Error('XML file not found in tar archive');

  } catch (err) {
    throw new Error(`Failed to download MINiML: ${err.message}`);
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('Usage: node fetch-miniml.js <bioproject_accession>');
    console.error('');
    console.error('Arguments:');
    console.error('  bioproject_accession - BioProject accession (e.g., PRJNA1018599)');
    console.error('');
    console.error('Example:');
    console.error('  node fetch-miniml.js PRJNA1018599');
    console.error('');
    console.error('Output:');
    console.error('  - Success: Prints GSE accession, saves tmp/{GSE}_family.xml');
    console.error('  - No GEO link: Prints "NO_GEO_LINK"');
    process.exit(1);
  }

  const bioproject = args[0];

  // Validate accession format
  if (!/^PRJ[A-Z]{1,2}\d+$/.test(bioproject)) {
    console.error(`Error: Invalid BioProject accession format: ${bioproject}`);
    process.exit(1);
  }

  console.error(`Looking for GEO series linked to: ${bioproject}`);

  try {
    // Step 1: Search GEO for BioProject
    const gdsIds = await searchGeoForBioProject(bioproject);

    if (!gdsIds) {
      console.error('  No GEO DataSets found for this BioProject');
      console.log('NO_GEO_LINK');
      process.exit(0);
    }

    // Step 2: Get GSE accession from GDS summary
    const gseAccession = await getGdsSummary(gdsIds);

    if (!gseAccession) {
      console.error('  Could not find GSE accession in GDS results');
      console.log('NO_GEO_LINK');
      process.exit(0);
    }

    console.error(`  Found GEO Series: ${gseAccession}`);

    // Step 3: Download MINiML
    const xml = await downloadMiniml(gseAccession);

    // Step 4: Save to file
    const outputPath = resolve(`tmp/${gseAccession}_family.xml`);
    writeFileSync(outputPath, xml);
    console.error(`  Saved to: ${outputPath}`);

    // Output GSE accession to stdout
    console.log(gseAccession);

  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
