#!/usr/bin/env node

import fs from 'fs';
import path from 'path';

const bioproject = process.argv[2];
const datasetName = process.argv[3];
const outputBase = process.argv[4] || 'outputs';

if (!bioproject || !datasetName) {
  console.error('Usage: sample-annotations-to-stf.js <BIOPROJECT> <datasetName> [outputBase]');
  process.exit(1);
}

const annotationsPath = path.join('tmp', `${bioproject}_sample_annotations.json`);
const outputDir = path.join(outputBase, datasetName);

if (!fs.existsSync(annotationsPath)) {
  console.error('Annotations file not found:', annotationsPath);
  process.exit(1);
}

const annotations = JSON.parse(fs.readFileSync(annotationsPath, 'utf8'));
const { samples, factors } = annotations;

fs.mkdirSync(outputDir, { recursive: true });

function toColName(key) {
  return key.replace(/\s+/g, '.');
}

function inferType(values) {
  const nonNull = values.filter(v => v !== null && v !== undefined && v !== '');
  if (nonNull.length === 0) return { data_type: 'string', data_shape: 'categorical' };

  if (nonNull.every(v => /^-?\d+$/.test(String(v)))) {
    return { data_type: 'integer', data_shape: 'continuous' };
  }
  if (nonNull.every(v => /^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(String(v)))) {
    return { data_type: 'number', data_shape: 'continuous' };
  }
  if (nonNull.every(v => /^\d{4}-\d{2}-\d{2}$/.test(String(v)))) {
    return { data_type: 'date', data_shape: 'continuous' };
  }
  return { data_type: 'string', data_shape: 'categorical' };
}

// factors is an object: { key: { displayName, definition, unit } }
const factorKeys = Object.keys(factors || {});

// --- TSV ---
// Column names use the factor key (spaces → dots)
const factorCols = factorKeys.map(toColName);
const headers = ['sample.ID \\\\ Descriptors', 'SRA.ID.s.', 'label', ...factorCols];

const rows = samples.map(s => {
  const sraIds = (s.runs || []).join(',');
  const factorVals = factorKeys.map(key => {
    const val = s.factors ? s.factors[key] : '';
    return val !== null && val !== undefined ? String(val) : '';
  });
  return [s.sampleId, sraIds, s.label, ...factorVals];
});

const tsv = [headers, ...rows].map(r => r.join('\t')).join('\n') + '\n';
fs.writeFileSync(path.join(outputDir, 'entity-sample.tsv'), tsv);

// --- YAML ---
const factorValues = {};
factorKeys.forEach(key => {
  factorValues[key] = samples.map(s => (s.factors ? s.factors[key] : null));
});

// This script builds YAML by hand (no js-yaml dependency, to keep these
// skill scripts runnable with plain node, no npm install). That means
// scalars have to be quoted/escaped ourselves rather than left to a library.
//
// Quote a scalar for embedding in hand-built YAML if it contains characters
// that are unsafe in a plain (unquoted) scalar. Single-quote style: the only
// escaping rule is doubling any literal single quotes.
function yamlScalar(value) {
  const str = String(value);
  const needsQuoting =
    str === '' ||
    /^\s|\s$/.test(str) ||
    /: |:$/.test(str) ||
    /\s#/.test(str) ||
    /^[-?:,\[\]{}#&*!|>'"%@`]/.test(str) ||
    /^(true|false|null|yes|no|~)$/i.test(str) ||
    /^-?\d+(\.\d+)?$/.test(str);
  if (!needsQuoting) return str;
  return `'${str.replace(/'/g, "''")}'`;
}

function serializeVariable(v) {
  let out = `  - variable: ${yamlScalar(v.variable)}\n`;
  out += `    provider_label:\n`;
  v.provider_label.forEach(l => { out += `      - ${yamlScalar(l)}\n`; });
  out += `    display_name: ${yamlScalar(v.display_name)}\n`;
  if (v.definition) {
    out += `    definition: ${yamlScalar(v.definition)}\n`;
  }
  out += `    data_type: ${v.data_type}\n`;
  out += `    data_shape: ${v.data_shape}\n`;
  if (v.unit) {
    out += `    unit: ${yamlScalar(v.unit)}\n`;
  }
  if (v.is_multi_valued) {
    out += `    is_multi_valued: ${v.is_multi_valued}\n`;
    out += `    multi_value_delimiter: ${yamlScalar(v.multi_value_delimiter)}\n`;
  }
  return out;
}

const variables = [];

variables.push({
  variable: 'SRA.ID.s.',
  provider_label: ['SRA ID(s)'],
  display_name: 'SRA ID(s)',
  data_type: 'string',
  data_shape: 'categorical',
  is_multi_valued: 'yes',
  multi_value_delimiter: ','
});

variables.push({
  variable: 'label',
  provider_label: ['label'],
  display_name: 'label',
  data_type: 'string',
  data_shape: 'categorical'
});

factorKeys.forEach(key => {
  const f = (factors && factors[key]) || {};
  const colName = toColName(key);
  const { data_type, data_shape } = inferType(factorValues[key]);
  const v = {
    variable: colName,
    provider_label: [key],
    display_name: f.displayName || key,
    data_type,
    data_shape
  };
  if (f.definition) v.definition = f.definition;
  if (f.unit) v.unit = f.unit;
  variables.push(v);
});

let yaml = `name: sample
display_name: Sample
display_name_plural: Samples

id_columns:
  - id_column: sample.ID
    entity_name: sample
    provider_label:
      - sample ID

variables:\n`;

variables.forEach(v => { yaml += serializeVariable(v); });
yaml += `\ncategories: []\ncollections: []\n`;

fs.writeFileSync(path.join(outputDir, 'entity-sample.yaml'), yaml);

console.log(`Written to ${outputDir}/entity-sample.{tsv,yaml}`);
