#!/usr/bin/env node
/**
 * fetch-pubmed.js - Fetches PubMed records for a genome assembly
 *
 * Usage: node fetch-pubmed.js <assembly_accession>
 *
 * This script:
 * 1. Uses NCBI Datasets publications API to find papers (formal links + text-mined)
 * 2. Falls back to BioProject elink if needed
 * 3. Uses NCBI esummary to get PubMed details (title, authors)
 * 4. Saves results to tmp/<assembly_accession>_pubmed.json
 */

import { writeFileSync, readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const EUTILS_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const DATASETS_PUBLICATIONS_BASE = 'https://www.ncbi.nlm.nih.gov/datasets/api/publications/genome';

/**
 * Fetch JSON from a URL
 */
async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Find publications via NCBI Datasets publications API
 * This endpoint returns both formally linked and text-mined publications
 */
async function findPublicationsViaDatasets(assemblyAccession) {
  const url = `${DATASETS_PUBLICATIONS_BASE}/${assemblyAccession}/`;
  try {
    const result = await fetchJson(url);
    const publications = result.publications || [];
    return publications.map(pub => ({
      pmid: pub.pmid,
      source: pub.labels || []
    }));
  } catch (error) {
    // API may return 404 for assemblies with no data
    return [];
  }
}

/**
 * Find linked PubMed records for a BioProject via elink
 */
async function findLinkedPubMedViaBioProject(bioProjectId) {
  const url = `${EUTILS_BASE}/elink.fcgi?dbfrom=bioproject&db=pubmed&id=${bioProjectId}&retmode=json`;
  try {
    const result = await fetchJson(url);
    const linkSets = result.linksets || [];
    const pubmedIds = [];

    for (const linkSet of linkSets) {
      const linkSetDbs = linkSet.linksetdbs || [];
      for (const linkSetDb of linkSetDbs) {
        if (linkSetDb.dbto === 'pubmed' && linkSetDb.links) {
          pubmedIds.push(...linkSetDb.links.map(id => ({
            pmid: String(id),
            source: ['bioproject_elink']
          })));
        }
      }
    }
    return pubmedIds;
  } catch (error) {
    return [];
  }
}

/**
 * Get PubMed summaries for multiple IDs
 */
async function getPubMedSummaries(pubsWithSource) {
  if (pubsWithSource.length === 0) return [];

  const ids = pubsWithSource.map(p => p.pmid);
  const sourceMap = Object.fromEntries(pubsWithSource.map(p => [p.pmid, p.source]));

  const url = `${EUTILS_BASE}/esummary.fcgi?db=pubmed&id=${ids.join(',')}&retmode=json`;
  const result = await fetchJson(url);

  const summaries = [];
  for (const id of ids) {
    const summary = result.result?.[id];
    if (summary) {
      summaries.push({
        pmid: id,
        title: summary.title || '',
        authors: (summary.authors || []).map(a => ({
          name: a.name,
          authtype: a.authtype
        })),
        source: summary.source || '',
        pubdate: summary.pubdate || '',
        volume: summary.volume || '',
        issue: summary.issue || '',
        pages: summary.pages || '',
        doi: summary.elocationid || '',
        lastAuthor: summary.lastauthor || '',
        // How this publication was found
        discoverySource: sourceMap[id] || [],
        _raw: summary
      });
    }
  }

  return summaries;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('Usage: node fetch-pubmed.js <assembly_accession>');
    console.error('');
    console.error('Arguments:');
    console.error('  assembly_accession - GenBank assembly accession (e.g., GCA_000988875.2)');
    console.error('');
    console.error('Example:');
    console.error('  node fetch-pubmed.js GCA_000988875.2');
    process.exit(1);
  }

  const assemblyAccession = args[0];

  // Validate assembly accession format
  if (!/^GC[AF]_\d+\.\d+$/.test(assemblyAccession)) {
    console.error(`Error: Invalid assembly accession format: ${assemblyAccession}`);
    console.error('Expected format: GCA_000988875.2 or GCF_000988875.2');
    process.exit(1);
  }

  console.error(`Fetching PubMed records for assembly: ${assemblyAccession}`);

  // Try to get BioProject accession from assembly report
  let bioProjectAccession = '';
  let bioProjectId = '';
  const assemblyReportPath = resolve(`tmp/${assemblyAccession}_dataset_report.json`);
  if (existsSync(assemblyReportPath)) {
    const assemblyData = JSON.parse(readFileSync(assemblyReportPath, 'utf-8'));
    bioProjectAccession = assemblyData.reports?.[0]?.assembly_info?.bioproject_accession || '';
    if (bioProjectAccession) {
      const bioProjectPath = resolve(`tmp/${bioProjectAccession}_bioproject.json`);
      if (existsSync(bioProjectPath)) {
        const bioProjectData = JSON.parse(readFileSync(bioProjectPath, 'utf-8'));
        bioProjectId = bioProjectData.id || '';
      }
    }
  }

  try {
    const allPubs = new Map(); // pmid -> {pmid, source[]}

    // Method 1: NCBI Datasets publications API (includes text-mined results)
    console.error('  Checking NCBI Datasets publications API...');
    const datasetsPubs = await findPublicationsViaDatasets(assemblyAccession);
    if (datasetsPubs.length > 0) {
      console.error(`    Found ${datasetsPubs.length} publication(s) via Datasets API`);
      for (const pub of datasetsPubs) {
        if (allPubs.has(pub.pmid)) {
          allPubs.get(pub.pmid).source.push(...pub.source);
        } else {
          allPubs.set(pub.pmid, { pmid: pub.pmid, source: [...pub.source] });
        }
      }
    } else {
      console.error('    No publications found via Datasets API');
    }

    // Method 2: BioProject elink (if we have the BioProject ID)
    if (bioProjectId) {
      console.error(`  Checking BioProject elink (${bioProjectAccession})...`);
      const elinkPubs = await findLinkedPubMedViaBioProject(bioProjectId);
      if (elinkPubs.length > 0) {
        console.error(`    Found ${elinkPubs.length} publication(s) via BioProject elink`);
        for (const pub of elinkPubs) {
          if (allPubs.has(pub.pmid)) {
            allPubs.get(pub.pmid).source.push(...pub.source);
          } else {
            allPubs.set(pub.pmid, { pmid: pub.pmid, source: [...pub.source] });
          }
        }
      } else {
        console.error('    No publications found via BioProject elink');
      }
    }

    const pubsWithSource = Array.from(allPubs.values());

    if (pubsWithSource.length === 0) {
      console.error('  No publications found from any source.');
      const output = {
        assemblyAccession,
        bioProjectAccession,
        pubmedCount: 0,
        papers: []
      };
      const outputPath = resolve(`tmp/${assemblyAccession}_pubmed.json`);
      writeFileSync(outputPath, JSON.stringify(output, null, 2));
      console.error(`  Saved (empty) to: ${outputPath}`);
      console.log(JSON.stringify(output, null, 2));
      return;
    }

    // Deduplicate sources
    for (const pub of pubsWithSource) {
      pub.source = [...new Set(pub.source)];
    }

    console.error(`  Total unique publications: ${pubsWithSource.length}`);
    console.error('  Fetching PubMed summaries...');
    const papers = await getPubMedSummaries(pubsWithSource);

    const output = {
      assemblyAccession,
      bioProjectAccession,
      pubmedCount: papers.length,
      papers
    };

    // Save to file
    const outputPath = resolve(`tmp/${assemblyAccession}_pubmed.json`);
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
