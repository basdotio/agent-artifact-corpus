#!/usr/bin/env node
// @ts-check
// Check the repo's diagrams and link each one into Diagrammo.
//
//   node check-diagrams.mjs [repo-dir] [--no-links]
//
// Reads every .dgmo file in <repo-dir>/docs/diagrams. If any has an error, it
// prints every error with its file and line, writes nothing and exits 1, so the
// agent fixes them and runs it again. If all are clean, it gets a share link for
// each and writes docs/diagrams/README.md, an index of the diagrams.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

/** Where the agent writes the diagrams, relative to the repo. */
export const OUTPUT_DIR = 'docs/diagrams';

export const INDEX_FILE = 'README.md';

/** The index's first line. An index without it is someone else's file, never overwritten. */
export const INDEX_MARKER = '<!-- Written by the dgmo-repo-diagrams skill; rewritten on every run. -->';

/** The CLI, run with npx so the user installs nothing. */
export const DGMO_CLI = ['npx', '-y', '@diagrammo/dgmo-cli'];

export const LINK_NOTICE =
  'Note: each link carries its diagram\'s full source in the URL. Run with --no-links to leave them out.';

/**
 * @typedef {{ file: string, title: string, url: string | null, tooLarge: boolean }} Checked
 * @typedef {{ links?: boolean, dgmo?: string[] }} CheckOptions
 */

export class DiagramError extends Error {}

/**
 * Check every diagram, then link each one and write the index.
 * Returns the index's path.
 * @param {string} repoDir
 * @param {CheckOptions} [options]
 */
export function checkDiagrams(repoDir, options = {}) {
  const { links = true, dgmo = DGMO_CLI } = options;
  const dir = resolve(repoDir, OUTPUT_DIR);
  if (!existsSync(dir)) throw new DiagramError(`No ${OUTPUT_DIR} directory in ${resolve(repoDir)}. Write the diagrams there first.`);
  const files = readdirSync(dir)
    .filter((f) => f.endsWith('.dgmo'))
    .sort();
  if (files.length === 0) throw new DiagramError(`No .dgmo files in ${dir}. Write the diagrams there first.`);
  const out = join(dir, INDEX_FILE);
  if (existsSync(out) && !readFileSync(out, 'utf8').startsWith(INDEX_MARKER)) {
    throw new DiagramError(`${OUTPUT_DIR}/${INDEX_FILE} exists and was not written by this skill. Move it, then run this again.`);
  }

  const scratch = mkdtempSync(join(tmpdir(), 'dgmo-repo-diagrams-'));
  try {
    const errors = files.flatMap((file) => {
      const error = validate(dgmo, join(dir, file), scratch);
      return error === null ? [] : [`${OUTPUT_DIR}/${file}: ${error}`];
    });
    if (errors.length > 0) {
      throw new DiagramError(`${errors.length} of ${files.length} diagrams have errors — fix them and run this again:\n${errors.join('\n')}`);
    }
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }

  const checked = files.map((file) => {
    const path = join(dir, file);
    const title = titleOf(readFileSync(path, 'utf8'), file);
    if (!links) return { file, title, url: null, tooLarge: false };
    return { file, title, ...share(dgmo, path) };
  });
  writeFileSync(out, index(checked, links));
  return out;
}

/**
 * The CLI's error for this diagram, or null when it renders clean.
 * --json, because without it the CLI draws a diagram with errors as an error
 * card and still exits 0; with it, errors are success: false.
 * @param {string[]} dgmo
 * @param {string} file
 * @param {string} scratch
 */
function validate(dgmo, file, scratch) {
  const out = join(scratch, `${basename(file, '.dgmo')}.svg`);
  const run = runDgmo(dgmo, [file, '-o', out, '--theme', 'light', '--json']);
  const reply = parseJson(run.stdout);
  if (run.status === 0 && isRecord(reply) && reply['success'] === true) return null;
  if (isRecord(reply) && typeof reply['error'] === 'string') return reply['error'];
  return `${run.stderr}${run.stdout}`.trim() || `dgmo exited ${run.status}`;
}

/**
 * The diagram's share link. Past the URL limit there is none, and the index says so.
 * @param {string[]} dgmo
 * @param {string} file
 * @returns {{ url: string | null, tooLarge: boolean }}
 */
function share(dgmo, file) {
  const run = runDgmo(dgmo, ['share', file, '--no-copy', '--json']);
  const reply = parseJson(run.stdout);
  if (run.status === 0 && isRecord(reply) && typeof reply['url'] === 'string') return { url: reply['url'], tooLarge: false };
  const message = isRecord(reply) && typeof reply['error'] === 'string' ? reply['error'] : `${run.stderr}${run.stdout}`;
  if (/too large/i.test(message)) return { url: null, tooLarge: true };
  throw new DiagramError(`dgmo share failed for ${basename(file)}:\n${message.trim()}`);
}

/**
 * The title on the diagram's first line (`sequence Checkout` → `Checkout`),
 * else the file name.
 * @param {string} source
 * @param {string} file
 */
function titleOf(source, file) {
  const first = source
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line !== '' && !line.startsWith('//'));
  const title = first?.replace(/^\S+\s*/, '').trim();
  return title || basename(file, '.dgmo');
}

/**
 * @param {Checked[]} checked
 * @param {boolean} links
 */
function index(checked, links) {
  const cell = (/** @type {string} */ s) => s.replace(/\|/g, '\\|');
  const head = links ? '| Diagram | Source | Open |\n|---|---|---|' : '| Diagram | Source |\n|---|---|';
  const rows = checked.map((c) => {
    const row = `| ${cell(c.title)} | [${cell(c.file)}](${encodeURI(c.file)})`;
    if (!links) return `${row} |`;
    const open = c.url ? `[Open in Diagrammo](${c.url})` : 'Too large for a link — open the file in Diagrammo';
    return `${row} | ${open} |`;
  });
  const lead = links
    ? 'Each link opens the diagram in Diagrammo, where it can be edited. The link carries the diagram\'s full source.'
    : 'Open a file in Diagrammo, or render it with `npx -y @diagrammo/dgmo-cli <file> -o <file>.svg`.';
  return `${INDEX_MARKER}\n\n# Diagrams\n\n${lead}\n\n${head}\n${rows.join('\n')}\n`;
}

/**
 * @param {string[]} dgmo
 * @param {string[]} args
 */
function runDgmo(dgmo, args) {
  const [cmd, ...pre] = dgmo;
  if (!cmd) throw new DiagramError('No dgmo command given.');
  const run = spawnSync(cmd, [...pre, ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (run.error) throw new DiagramError(`Could not run ${dgmo.join(' ')}: ${run.error.message}`);
  return { status: run.status, stdout: run.stdout ?? '', stderr: run.stderr ?? '' };
}

/** @param {string} stdout */
function parseJson(stdout) {
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

/**
 * @param {unknown} v
 * @returns {v is Record<string, unknown>}
 */
function isRecord(v) {
  return typeof v === 'object' && v !== null;
}

/**
 * The command line. Returns the exit code.
 * @param {string[]} argv the arguments after the script name
 * @param {CheckOptions} [options]
 */
export function main(argv, options = {}) {
  const flags = argv.filter((a) => a.startsWith('--'));
  const unknown = flags.filter((f) => f !== '--no-links');
  const dirs = argv.filter((a) => !a.startsWith('--'));
  if (unknown.length > 0 || dirs.length > 1) {
    console.error('Usage: node check-diagrams.mjs [repo-dir] [--no-links]');
    return 2;
  }
  const links = !flags.includes('--no-links');
  try {
    const out = checkDiagrams(dirs[0] ?? '.', { ...options, links });
    if (links) console.error(LINK_NOTICE);
    console.log(out);
    return 0;
  } catch (err) {
    if (!(err instanceof DiagramError)) throw err;
    console.error(`Error: ${err.message}`);
    return 1;
  }
}

// realpath, because import.meta.url has symlinks resolved and argv[1] does not:
// a skill installed as a symlink would otherwise run nothing and exit 0.
if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  process.exitCode = main(process.argv.slice(2));
}
