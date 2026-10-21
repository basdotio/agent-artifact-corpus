#!/usr/bin/env node
/**
 * Thin CLI over the public library API. Parses argv, calls `generate`, prints.
 * Depends only on ./index.js — no reach into generator/corpus internals — so the
 * library stays the single source of truth for behavior.
 */
import { generate, type Unit } from "./index.js";

const UNITS: readonly Unit[] = ["words", "sentences", "paragraphs"];

const HELP = `claudem-ipsum — filler text in Claude's voice

Usage:
  claudem-ipsum [count] [options]

Arguments:
  count                 how many units to generate (default: 50)

Options:
  -u, --unit <unit>     words | sentences | paragraphs (default: words)
  -s, --seed <seed>     seed for reproducible output
  -j, --json            print { text, stats } as JSON
      --stats           print a stats summary to stderr
  -h, --help            show this help

Examples:
  claudem-ipsum 40
  claudem-ipsum 3 --unit sentences
  claudem-ipsum 2 -u paragraphs -s demo
  claudem-ipsum 25 --json
`;

interface Args {
  count: number;
  unit: Unit;
  seed?: string;
  json: boolean;
  stats: boolean;
}

class UsageError extends Error {}

function parse(argv: readonly string[]): Args {
  const out: Args = { count: 50, unit: "words", json: false, stats: false };
  let sawCount = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    switch (arg) {
      case "-h":
      case "--help":
        console.log(HELP);
        process.exit(0);
        break;
      case "-j":
      case "--json":
        out.json = true;
        break;
      case "--stats":
        out.stats = true;
        break;
      case "-u":
      case "--unit": {
        const v = argv[++i];
        if (v === undefined) throw new UsageError(`${arg} needs a value`);
        if (!UNITS.includes(v as Unit)) {
          throw new UsageError(`unknown unit '${v}' (expected ${UNITS.join(", ")})`);
        }
        out.unit = v as Unit;
        break;
      }
      case "-s":
      case "--seed": {
        const v = argv[++i];
        if (v === undefined) throw new UsageError(`${arg} needs a value`);
        out.seed = v;
        break;
      }
      default: {
        if (arg.startsWith("-")) throw new UsageError(`unknown option '${arg}'`);
        if (sawCount) throw new UsageError(`unexpected argument '${arg}'`);
        const n = Number(arg);
        if (!Number.isInteger(n) || n < 0) {
          throw new UsageError(`count must be a non-negative integer, got '${arg}'`);
        }
        out.count = n;
        sawCount = true;
      }
    }
  }
  return out;
}

function main(argv: readonly string[]): void {
  let args: Args;
  try {
    args = parse(argv);
  } catch (err) {
    if (err instanceof UsageError) {
      console.error(`error: ${err.message}\n`);
      console.error(HELP);
      process.exit(2);
    }
    throw err;
  }

  const result = generate({ count: args.count, unit: args.unit, seed: args.seed });

  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  console.log(result.text);
  if (args.stats) {
    const { words, sentences, paragraphs } = result.stats;
    console.error(`${words} words · ${sentences} sentences · ${paragraphs} paragraphs`);
  }
}

main(process.argv.slice(2));
