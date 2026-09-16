#!/usr/bin/env node
/**
 * generate-analysis-config.js - Generates analysisConfig.xml for RNA-seq pipeline
 *
 * Usage: node generate-analysis-config.js <bioproject> [--strand-specific]
 *
 * This script reads SRA metadata and sample annotations to generate
 * the analysisConfig.xml file needed for pipeline processing.
 *
 * Reads from:
 *   tmp/<bioproject>_sra_metadata.json
 *   tmp/<bioproject>_sample_annotations.json (Claude-generated)
 *
 * Writes to:
 *   delivery/bulk-rnaseq/<bioproject>/analysisConfig.xml
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';

/**
 * Generate the analysisConfig.xml content
 */
function generateAnalysisConfig(data) {
  const {
    profileSetName,
    samples,
    isStrandSpecific
  } = data;

  // Generate sample value elements
  const sampleValues = samples
    .map(s => `        <value>${s.label}|${s.sampleId}</value>`)
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<xml>
  <step class="ApiCommonData::Load::RnaSeqAnalysisEbi">
    <property name="profileSetName" value="${profileSetName}"/>
    <property name="samples">
${sampleValues}
    </property>
    <property name="isStrandSpecific" value="${isStrandSpecific ? '1' : '0'}"/>
  </step>
</xml>`;
}

function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('Usage: node generate-analysis-config.js <bioproject> [--strand-specific]');
    console.error('');
    console.error('Arguments:');
    console.error('  bioproject         - BioProject accession (e.g., PRJNA1018599)');
    console.error('  --strand-specific  - Mark as strand-specific (default: false)');
    console.error('');
    console.error('Reads from:');
    console.error('  tmp/<bioproject>_sra_metadata.json');
    console.error('  tmp/<bioproject>_sample_annotations.json');
    console.error('');
    console.error('Writes to:');
    console.error('  delivery/bulk-rnaseq/<bioproject>/analysisConfig.xml');
    process.exit(1);
  }

  const bioproject = args[0];
  const isStrandSpecific = args.includes('--strand-specific');

  // Read SRA metadata
  const sraPath = resolve(`tmp/${bioproject}_sra_metadata.json`);
  if (!existsSync(sraPath)) {
    console.error(`Error: SRA metadata not found at ${sraPath}`);
    console.error('Run fetch-sra-metadata.js first.');
    process.exit(1);
  }

  const sraMetadata = JSON.parse(readFileSync(sraPath, 'utf-8'));

  // Try to read sample annotations (Claude-generated)
  const annotationsPath = resolve(`tmp/${bioproject}_sample_annotations.json`);
  let sampleAnnotations = null;

  if (existsSync(annotationsPath)) {
    sampleAnnotations = JSON.parse(readFileSync(annotationsPath, 'utf-8'));
    console.error(`  Using sample annotations from: ${annotationsPath}`);
  } else {
    console.error(`  Warning: Sample annotations not found at ${annotationsPath}`);
    console.error('  Generating basic annotations from SRA metadata...');

    // Generate basic annotations from SRA metadata
    const runs = sraMetadata.runs || [];
    const sampleMap = new Map();

    for (const run of runs) {
      const sampleId = run.sample_accession || run.sample_alias || run.run_accession;
      if (!sampleMap.has(sampleId)) {
        sampleMap.set(sampleId, {
          sampleId: sampleId,
          label: sampleId, // Default label is just the sample ID
          runs: []
        });
      }
      sampleMap.get(sampleId).runs.push(run.run_accession);
    }

    sampleAnnotations = {
      bioproject: bioproject,
      samples: Array.from(sampleMap.values())
    };
  }

  // Extract profile set name (use short display name or bioproject)
  const profileSetName = sampleAnnotations.profileSetName || `${bioproject} RNA-Seq`;

  // Build data object
  const configData = {
    profileSetName,
    samples: sampleAnnotations.samples || [],
    isStrandSpecific
  };

  // Ensure output directory exists
  const outputDir = resolve(`delivery/bulk-rnaseq/${bioproject}`);
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
    console.error(`  Created directory: ${outputDir}`);
  }

  // Generate and write config
  const xml = generateAnalysisConfig(configData);
  const outputPath = resolve(outputDir, 'analysisConfig.xml');
  writeFileSync(outputPath, xml);

  console.error('');
  console.error('Generated analysisConfig.xml:');
  console.error(`  Output: ${outputPath}`);
  console.error(`  Profile set: ${profileSetName}`);
  console.error(`  Samples: ${configData.samples.length}`);
  console.error(`  Strand-specific: ${isStrandSpecific}`);

  // Also print to stdout
  console.log(xml);
}

main();
