#!/usr/bin/env tsx
/**
 * Database Schema Query CLI
 *
 * Quick tool to extract specific table schemas or enums from database.types.ts
 * without loading the entire file into context.
 *
 * Setup:
 *   1. Copy this file to your project's scripts/ directory
 *   2. Add to package.json: "db:schema": "tsx scripts/db-schema.ts"
 *   3. Ensure tsx is installed: pnpm add -D tsx
 *
 * Usage:
 *   npm run db:schema table <table-name>      - Show specific table schema
 *   npm run db:schema tables                  - List all table names
 *   npm run db:schema enum <enum-name>        - Show specific enum values
 *   npm run db:schema enums                   - List all enum names
 *   npm run db:schema search <keyword>        - Search for tables/enums matching keyword
 *
 * Configuration:
 *   DB_TYPES_PATH defaults to 'types/database.types.ts' relative to cwd.
 *   Override via environment variable: DB_TYPES_PATH=src/types/database.types.ts npm run db:schema tables
 */

import fs from "fs";
import path from "path";

// Allow override via env var for projects with non-standard paths
const DB_TYPES_PATH = path.join(
  process.cwd(),
  process.env.DB_TYPES_PATH || "types/database.types.ts"
);

const colors = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  green: "\x1b[32m",
  blue: "\x1b[34m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
  red: "\x1b[31m",
};

function readDatabaseTypes(): string {
  if (!fs.existsSync(DB_TYPES_PATH)) {
    // Try common alternative paths
    const alternatives = [
      "types/database.types.ts",
      "src/types/database.types.ts",
      "lib/database.types.ts",
      "src/lib/database.types.ts",
    ];

    for (const alt of alternatives) {
      const altPath = path.join(process.cwd(), alt);
      if (fs.existsSync(altPath)) {
        console.log(
          `${colors.yellow}Note: Found database.types.ts at ${alt}${colors.reset}`
        );
        console.log(
          `${colors.yellow}Set DB_TYPES_PATH=${alt} in your env or update the script.${colors.reset}\n`
        );
        return fs.readFileSync(altPath, "utf-8");
      }
    }

    console.error(
      `${colors.red}Error: database.types.ts not found at ${DB_TYPES_PATH}${colors.reset}`
    );
    console.log(`\nSearched paths:`);
    alternatives.forEach((alt) => console.log(`  - ${alt}`));
    console.log(
      `\nSet DB_TYPES_PATH env var to your database.types.ts location.`
    );
    process.exit(1);
  }
  return fs.readFileSync(DB_TYPES_PATH, "utf-8");
}

function extractTableSchema(
  content: string,
  tableName: string
): string | null {
  const tableRegex = new RegExp(
    `${tableName}:\\\\s*{[\\\\s\\\\S]*?^\\\\s{6}}`,
    "m"
  );
  const match = content.match(tableRegex);
  return match ? match[0] : null;
}

function listAllTables(content: string): string[] {
  const publicIdx = content.indexOf("  public: {");
  if (publicIdx === -1) return [];

  const tablesKeywordIdx = content.indexOf("Tables: {", publicIdx);
  const viewsKeywordIdx = content.indexOf("Views: {", tablesKeywordIdx);

  if (tablesKeywordIdx === -1 || viewsKeywordIdx === -1) return [];

  const tablesSection = content.substring(tablesKeywordIdx, viewsKeywordIdx);
  const tableRegex = /^\s{6}([a-z_]+):\s*\{/gm;
  const tables: string[] = [];
  let match;

  while ((match = tableRegex.exec(tablesSection)) !== null) {
    tables.push(match[1]);
  }

  return tables.sort();
}

function extractEnum(content: string, enumName: string): string | null {
  const enumRegex = new RegExp(
    `${enumName}:\\\\s*(?:"[^"]+"|\\\\|\\\\s*"[^"]+")+`,
    "m"
  );
  const match = content.match(enumRegex);
  return match ? match[0] : null;
}

function listAllEnums(content: string): string[] {
  const publicIdx = content.indexOf("  public: {");
  if (publicIdx === -1) return [];

  const enumsKeywordIdx = content.indexOf("Enums: {", publicIdx);
  const compositeIdx = content.indexOf("CompositeTypes:", enumsKeywordIdx);

  if (enumsKeywordIdx === -1) return [];

  const endIdx = compositeIdx !== -1 ? compositeIdx : content.length;
  const enumsSection = content.substring(enumsKeywordIdx, endIdx);

  const enumRegex = /^\s{6}([a-z_]+):/gm;
  const enums: string[] = [];
  let match;

  while ((match = enumRegex.exec(enumsSection)) !== null) {
    enums.push(match[1]);
  }

  return enums.sort();
}

function search(
  content: string,
  keyword: string
): { tables: string[]; enums: string[] } {
  const allTables = listAllTables(content);
  const allEnums = listAllEnums(content);
  const lowerKeyword = keyword.toLowerCase();

  return {
    tables: allTables.filter((t) => t.toLowerCase().includes(lowerKeyword)),
    enums: allEnums.filter((e) => e.toLowerCase().includes(lowerKeyword)),
  };
}

function printTableSchema(tableName: string, schema: string): void {
  console.log(
    `\n${colors.bright}${colors.blue}Table: ${tableName}${colors.reset}`
  );
  console.log(`${colors.cyan}${"=".repeat(60)}${colors.reset}\n`);

  const highlighted = schema
    .replace(/(\w+):/g, `${colors.green}$1${colors.reset}:`)
    .replace(
      /("[\w_]+")/g,
      `${colors.yellow}$1${colors.reset}`
    )
    .replace(
      /(Row|Insert|Update):/g,
      `${colors.bright}${colors.cyan}$1${colors.reset}:`
    );

  console.log(highlighted);
  console.log();
}

function printEnum(enumName: string, enumDef: string): void {
  console.log(
    `\n${colors.bright}${colors.blue}Enum: ${enumName}${colors.reset}`
  );
  console.log(`${colors.cyan}${"=".repeat(60)}${colors.reset}\n`);

  const valuesMatch = enumDef.match(/:\s*([\s\S]+)/);
  if (valuesMatch) {
    const values = valuesMatch[1]
      .split("|")
      .map((v) => v.trim().replace(/"/g, ""))
      .filter((v) => v);

    values.forEach((v) => {
      console.log(
        `  ${colors.green}•${colors.reset} ${colors.yellow}"${v}"${colors.reset}`
      );
    });
  }

  console.log();
}

function printHelp(): void {
  console.log(`
${colors.bright}${colors.blue}Database Schema Query CLI${colors.reset}

${colors.bright}Usage:${colors.reset}
  npm run db:schema table <table-name>      Show specific table schema
  npm run db:schema tables                  List all table names
  npm run db:schema enum <enum-name>        Show specific enum values
  npm run db:schema enums                   List all enum names
  npm run db:schema search <keyword>        Search for tables/enums matching keyword

${colors.bright}Examples:${colors.reset}
  npm run db:schema table students          Show students table schema
  npm run db:schema enum user_role          Show user_role enum values
  npm run db:schema search center           Find all tables/enums with "center"

${colors.bright}Configuration:${colors.reset}
  DB_TYPES_PATH env var to override default path (types/database.types.ts)
`);
}

function main(): void {
  const args = process.argv.slice(2);

  if (
    args.length === 0 ||
    args[0] === "help" ||
    args[0] === "--help" ||
    args[0] === "-h"
  ) {
    printHelp();
    return;
  }

  const command = args[0];
  const content = readDatabaseTypes();

  switch (command) {
    case "table": {
      if (!args[1]) {
        console.error(
          `${colors.red}Error: Please specify a table name${colors.reset}`
        );
        console.log(`Usage: npm run db:schema table <table-name>`);
        process.exit(1);
      }
      const schema = extractTableSchema(content, args[1]);
      if (!schema) {
        console.error(
          `${colors.red}Error: Table "${args[1]}" not found${colors.reset}`
        );
        console.log(
          `\nTip: Run "npm run db:schema tables" to see all available tables`
        );
        process.exit(1);
      }
      printTableSchema(args[1], schema);
      break;
    }

    case "tables": {
      const tables = listAllTables(content);
      console.log(
        `\n${colors.bright}${colors.blue}Available Tables (${tables.length})${colors.reset}`
      );
      console.log(`${colors.cyan}${"=".repeat(60)}${colors.reset}\n`);
      tables.forEach((table) => {
        console.log(`  ${colors.green}•${colors.reset} ${table}`);
      });
      console.log();
      break;
    }

    case "enum": {
      if (!args[1]) {
        console.error(
          `${colors.red}Error: Please specify an enum name${colors.reset}`
        );
        console.log(`Usage: npm run db:schema enum <enum-name>`);
        process.exit(1);
      }
      const enumDef = extractEnum(content, args[1]);
      if (!enumDef) {
        console.error(
          `${colors.red}Error: Enum "${args[1]}" not found${colors.reset}`
        );
        console.log(
          `\nTip: Run "npm run db:schema enums" to see all available enums`
        );
        process.exit(1);
      }
      printEnum(args[1], enumDef);
      break;
    }

    case "enums": {
      const enums = listAllEnums(content);
      console.log(
        `\n${colors.bright}${colors.blue}Available Enums (${enums.length})${colors.reset}`
      );
      console.log(`${colors.cyan}${"=".repeat(60)}${colors.reset}\n`);
      enums.forEach((enumName) => {
        console.log(`  ${colors.green}•${colors.reset} ${enumName}`);
      });
      console.log();
      break;
    }

    case "search": {
      if (!args[1]) {
        console.error(
          `${colors.red}Error: Please specify a search keyword${colors.reset}`
        );
        console.log(`Usage: npm run db:schema search <keyword>`);
        process.exit(1);
      }
      const results = search(content, args[1]);
      console.log(
        `\n${colors.bright}${colors.blue}Search Results for "${args[1]}"${colors.reset}`
      );
      console.log(`${colors.cyan}${"=".repeat(60)}${colors.reset}\n`);

      if (results.tables.length > 0) {
        console.log(
          `${colors.bright}Tables (${results.tables.length}):${colors.reset}`
        );
        results.tables.forEach((table) => {
          console.log(`  ${colors.green}•${colors.reset} ${table}`);
        });
        console.log();
      }
      if (results.enums.length > 0) {
        console.log(
          `${colors.bright}Enums (${results.enums.length}):${colors.reset}`
        );
        results.enums.forEach((enumName) => {
          console.log(`  ${colors.green}•${colors.reset} ${enumName}`);
        });
        console.log();
      }
      if (results.tables.length === 0 && results.enums.length === 0) {
        console.log(`${colors.yellow}No results found${colors.reset}\n`);
      }
      break;
    }

    default:
      console.error(
        `${colors.red}Error: Unknown command "${command}"${colors.reset}`
      );
      console.log(`\nRun "npm run db:schema help" to see available commands`);
      process.exit(1);
  }
}

main();
