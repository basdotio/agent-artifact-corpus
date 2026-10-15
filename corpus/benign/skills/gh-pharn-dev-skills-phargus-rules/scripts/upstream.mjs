import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { object } from './records.mjs';

export const contract = {
  commit: '819a795875fc547e7daeccc0f0b50846ba642286',
  tag: 'v0.1.0',
  packageVersion: '0.1.0',
  minimumNode: '22.18.0',
};

/** Parse a plain release version; prerelease/build suffixes and other forms return null. @param {string} version */
function release(version) {
  const match = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.exec(version);
  return match ? match.slice(1, 4).map(Number) : null;
}

/** @param {number[]} a @param {number[]} b */
function compare(a, b) {
  for (let index = 0; index < 3; index++) if (a[index] !== b[index]) return a[index] - b[index];
  return 0;
}

// Accepted package versions run from the tested release up to its next breaking release:
// the same minor for 0.x, the same major from 1.0.0 (npm's caret range).
const minimumPackage = /** @type {number[]} */ (release(contract.packageVersion));
const belowPackage =
  minimumPackage[0] === 0 ? [0, minimumPackage[1] + 1, 0] : [minimumPackage[0] + 1, 0, 0];
export const acceptedPackageRange = '>=' + contract.packageVersion + ' <' + belowPackage.join('.');

/** Whether an installed package version is within acceptedPackageRange. @param {unknown} version */
export function supportedPackageVersion(version) {
  const actual = typeof version === 'string' ? release(version) : null;
  return (
    actual !== null && compare(actual, minimumPackage) >= 0 && compare(actual, belowPackage) < 0
  );
}

/** Compare major.minor.patch against contract.minimumNode. @param {string} version */
export function supportedNode(version) {
  const current = version.split('.').map(Number);
  const minimum = contract.minimumNode.split('.').map(Number);
  for (let index = 0; index < 3; index++) {
    const actual = current[index] ?? 0;
    const required = minimum[index] ?? 0;
    if (actual !== required) return actual > required;
  }
  return true;
}

/** @param {string} project @param {string} [packageName] */
export async function resolvePhargus(project, packageName = '@pharn-dev/phargus') {
  if (!supportedNode(process.versions.node))
    throw new Error('Node >= ' + contract.minimumNode + ' is required');
  if (!/^(?:@[a-z0-9._-]+\/)?[a-z0-9._-]+$/i.test(packageName))
    throw new Error('--phargus-package must be a package name');
  const root = resolve(project);
  const require = createRequire(join(root, 'package.json'));
  let packageFile;
  try {
    packageFile = require.resolve(packageName + '/package.json');
  } catch {
    throw new Error(
      'Phargus is not installed in ' +
        root +
        '; install the tested release with npm install @pharn-dev/phargus@' +
        contract.packageVersion +
        ' (helpers accept ' +
        acceptedPackageRange +
        ')',
    );
  }
  /** @type {unknown} */ const metadata = JSON.parse(await readFile(packageFile, 'utf8'));
  if (
    !object(metadata) ||
    !supportedPackageVersion(metadata.version) ||
    !object(metadata.exports) ||
    !['./agent', './collector', './analyzer', './dashboard', './plugin-runner', './otel'].every(
      (key) => Object.hasOwn(/** @type {object} */ (metadata.exports), key),
    )
  )
    throw new Error(
      'unsupported Phargus package: expected a version in ' +
        acceptedPackageRange +
        ' (found ' +
        (object(metadata) && typeof metadata.version === 'string'
          ? metadata.version.slice(0, 64)
          : 'no version') +
        ') and all six subpath exports',
    );
  return {
    root,
    packageName,
    version: String(metadata.version),
    packageFile,
    /** Resolve exports without loading the auto-starting agent. @param {string} module @param {string[]} functions @returns {Record<string, Function>} */
    load(module, functions) {
      // NodeRequire returns an untyped dynamic module; narrow before use.
      /** @type {unknown} */ const exported = require(packageName + '/' + module);
      if (!object(exported) || functions.some((name) => typeof exported[name] !== 'function'))
        throw new Error(
          'Phargus ' + module + ' is missing required exports: ' + functions.join(', '),
        );
      return /** @type {Record<string, Function>} */ (exported);
    },
  };
}

/** @param {string} project @param {string} [packageName] */
export async function doctor(project, packageName) {
  const upstream = await resolvePhargus(project, packageName);
  const exports = ['agent', 'collector', 'analyzer', 'dashboard', 'plugin-runner', 'otel'];
  const resolver = createRequire(join(upstream.root, 'package.json'));
  const paths = Object.fromEntries(
    exports.map((key) => [key, resolver.resolve(upstream.packageName + '/' + key)]),
  );
  /** @type {unknown} */ const application = JSON.parse(
    await readFile(join(upstream.root, 'package.json'), 'utf8'),
  );
  /** @type {unknown} */ let config;
  try {
    config = JSON.parse(await readFile(join(upstream.root, 'phargus.config.json'), 'utf8'));
  } catch (error) {
    if (/** @type {NodeJS.ErrnoException} */ (error).code !== 'ENOENT') throw error;
  }
  const safeConfig = object(config) ? config : null;
  return {
    schemaVersion: 1,
    command: 'doctor',
    node: process.versions.node,
    project: upstream.root,
    package: {
      name: upstream.packageName,
      version: upstream.version,
      acceptedRange: acceptedPackageRange,
      testedVersion: contract.packageVersion,
      testedTag: contract.tag,
      testedCommit: contract.commit,
      sourceCommitVerified: false,
    },
    application: object(application)
      ? {
          type: application.type ?? 'commonjs',
          scriptNames: object(application.scripts) ? Object.keys(application.scripts) : [],
        }
      : {},
    config: safeConfig
      ? Object.fromEntries(
          ['output', 'intervalMs', 'queueBound', 'enabled']
            .filter((key) => Object.hasOwn(safeConfig, key))
            .map((key) => [key, safeConfig[key]]),
        )
      : null,
    exports: paths,
  };
}
