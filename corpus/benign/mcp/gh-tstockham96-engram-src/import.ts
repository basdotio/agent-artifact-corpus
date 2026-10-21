/**
 * engram import — Migrate memory from other AI tools into Engram
 *
 * Supports:
 *   --claude-code    Import from Claude Code (CLAUDE.md + auto memory + session transcripts)
 *   --obsidian       Import from an Obsidian vault (markdown files, wikilinks, tags, frontmatter)
 *
 * Claude Code caps auto memory at 200 lines per project, siloed per repo.
 * Engram has no limit, semantic search across everything, and cross-project intelligence.
 * Import in one command. Keep using Claude Code — Engram just makes it smarter.
 */

import { Vault } from './vault.js';
import type { VaultConfig } from './types.js';
import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join, basename, dirname, resolve } from 'path';
import { homedir } from 'os';

// ── Types ──────────────────────────────────────────────────

interface ImportSource {
  path: string;
  project: string;
  type: 'claude-md' | 'auto-memory' | 'rules' | 'session-transcript' | 'obsidian-note';
  content: string;
  lineCount: number;
}

interface ImportChunk {
  content: string;
  source: ImportSource;
  section?: string;        // markdown section heading
  entities?: string[];
  topics?: string[];
}

interface ImportResult {
  sourcesFound: number;
  sourcesProcessed: number;
  memoriesCreated: number;
  memoriesDeduped: number;
  projectsCovered: string[];
  sessionsParsed: number;
  errors: string[];
  dryRun: boolean;
}

interface ImportOptions {
  dryRun?: boolean;
  includeSessions?: boolean;
  maxSessionsPerProject?: number;
  verbose?: boolean;
  vault: Vault;
}

// ── Formatting helpers ─────────────────────────────────────

function bold(s: string) { return `\x1b[1m${s}\x1b[0m`; }
function dim(s: string) { return `\x1b[2m${s}\x1b[0m`; }
function green(s: string) { return `\x1b[32m${s}\x1b[0m`; }
function yellow(s: string) { return `\x1b[33m${s}\x1b[0m`; }
function cyan(s: string) { return `\x1b[36m${s}\x1b[0m`; }
function red(s: string) { return `\x1b[31m${s}\x1b[0m`; }

// ── Discovery ──────────────────────────────────────────────

function discoverClaudeCodeSources(): ImportSource[] {
  const home = homedir();
  const sources: ImportSource[] = [];
  const claudeDir = join(home, '.claude');

  if (!existsSync(claudeDir)) {
    return sources;
  }

  // 1. User-level CLAUDE.md
  const userClaudeMd = join(claudeDir, 'CLAUDE.md');
  if (existsSync(userClaudeMd)) {
    const content = readFileSync(userClaudeMd, 'utf-8');
    sources.push({
      path: userClaudeMd,
      project: '~global',
      type: 'claude-md',
      content,
      lineCount: content.split('\n').length,
    });
  }

  // 2. User-level rules
  const userRulesDir = join(claudeDir, 'rules');
  if (existsSync(userRulesDir)) {
    for (const file of findMarkdownFiles(userRulesDir)) {
      const content = readFileSync(file, 'utf-8');
      sources.push({
        path: file,
        project: '~global',
        type: 'rules',
        content,
        lineCount: content.split('\n').length,
      });
    }
  }

  // 3. Per-project auto memory and sessions
  const projectsDir = join(claudeDir, 'projects');
  if (existsSync(projectsDir)) {
    for (const projectSlug of readdirSync(projectsDir)) {
      const projectPath = join(projectsDir, projectSlug);
      if (!statSync(projectPath).isDirectory()) continue;

      const projectName = decodeProjectSlug(projectSlug);

      // Auto memory files
      const memoryDir = join(projectPath, 'memory');
      if (existsSync(memoryDir)) {
        for (const file of findMarkdownFiles(memoryDir)) {
          const content = readFileSync(file, 'utf-8');
          if (content.trim().length === 0) continue;
          sources.push({
            path: file,
            project: projectName,
            type: 'auto-memory',
            content,
            lineCount: content.split('\n').length,
          });
        }
      }

      // Session transcripts (JSONL)
      const jsonlFiles = readdirSync(projectPath)
        .filter(f => f.endsWith('.jsonl'))
        .map(f => ({
          name: f,
          path: join(projectPath, f),
          mtime: statSync(join(projectPath, f)).mtimeMs,
          size: statSync(join(projectPath, f)).size,
        }))
        .sort((a, b) => b.mtime - a.mtime); // newest first

      for (const jsonl of jsonlFiles) {
        sources.push({
          path: jsonl.path,
          project: projectName,
          type: 'session-transcript',
          content: '', // loaded on demand (can be huge)
          lineCount: 0,
        });
      }
    }
  }

  // 4. Project-level CLAUDE.md in cwd
  const cwd = process.cwd();
  for (const relPath of ['CLAUDE.md', '.claude/CLAUDE.md', 'CLAUDE.local.md']) {
    const fullPath = join(cwd, relPath);
    if (existsSync(fullPath)) {
      const content = readFileSync(fullPath, 'utf-8');
      sources.push({
        path: fullPath,
        project: basename(cwd),
        type: 'claude-md',
        content,
        lineCount: content.split('\n').length,
      });
    }
  }

  // Project rules in cwd
  const cwdRulesDir = join(cwd, '.claude', 'rules');
  if (existsSync(cwdRulesDir)) {
    for (const file of findMarkdownFiles(cwdRulesDir)) {
      const content = readFileSync(file, 'utf-8');
      sources.push({
        path: file,
        project: basename(cwd),
        type: 'rules',
        content,
        lineCount: content.split('\n').length,
      });
    }
  }

  return sources;
}

function findMarkdownFiles(dir: string): string[] {
  const files: string[] = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...findMarkdownFiles(fullPath));
      } else if (entry.name.endsWith('.md')) {
        files.push(fullPath);
      }
    }
  } catch {
    // Permission denied or similar
  }
  return files;
}

function decodeProjectSlug(slug: string): string {
  // Claude Code encodes paths like: -Users-thomasstockham-Desktop-Scout
  // Decode back to a readable project name
  const parts = slug.split('-').filter(Boolean);

  // Try to find a reasonable project name from the path
  // Skip "Users" and username, take the last meaningful parts
  if (parts.length >= 3 && parts[0] === 'Users') {
    const projectParts = parts.slice(2); // skip "Users" and username
    return projectParts.join('/');
  }
  return slug;
}

// ── Parsing ────────────────────────────────────────────────

function parseMarkdownIntoChunks(source: ImportSource): ImportChunk[] {
  const chunks: ImportChunk[] = [];
  const lines = source.content.split('\n');
  let currentSection = '';
  let currentLines: string[] = [];

  function flush() {
    const text = currentLines.join('\n').trim();
    if (text.length < 10) return; // skip trivially short chunks

    // Extract potential entities (capitalized words, @mentions, paths)
    const entities = extractEntities(text);
    const topics = extractTopics(text, source);

    chunks.push({
      content: text,
      source,
      section: currentSection || undefined,
      entities: entities.length > 0 ? entities : undefined,
      topics: topics.length > 0 ? topics : undefined,
    });
  }

  for (const line of lines) {
    const headerMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headerMatch) {
      flush();
      currentSection = headerMatch[2].trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  flush();

  return chunks;
}

function extractEntities(text: string): string[] {
  const entities = new Set<string>();

  // Extract @mentions
  for (const match of text.matchAll(/@(\w+)/g)) {
    entities.add(match[1]);
  }

  // Extract quoted terms
  for (const match of text.matchAll(/[`"']([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)[`"']/g)) {
    if (match[1].length < 30) entities.add(match[1]);
  }

  return [...entities].slice(0, 10);
}

function extractTopics(text: string, source: ImportSource): string[] {
  const topics = new Set<string>();

  // Add source type as topic
  topics.add(`claude-code`);
  if (source.type === 'auto-memory') topics.add('auto-memory');
  if (source.type === 'rules') topics.add('rules');

  // Extract hashtags
  for (const match of text.matchAll(/#(\w+)/g)) {
    topics.add(match[1]);
  }

  return [...topics].slice(0, 5);
}

// ── Session transcript parsing ────────────────────────────

interface SessionMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

function parseSessionTranscript(source: ImportSource, maxMessages = 200): ImportChunk[] {
  const chunks: ImportChunk[] = [];

  try {
    const raw = readFileSync(source.path, 'utf-8');
    const lines = raw.split('\n').filter(l => l.trim());

    const messages: SessionMessage[] = [];

    for (const line of lines) {
      try {
        const entry = JSON.parse(line);

        // Skip non-message entries (file snapshots, tool results, etc.)
        if (!entry.message?.role) continue;
        if (entry.message.role !== 'user' && entry.message.role !== 'assistant') continue;

        let content = '';
        if (typeof entry.message.content === 'string') {
          content = entry.message.content;
        } else if (Array.isArray(entry.message.content)) {
          // Extract text blocks, skip thinking/tool_use
          content = entry.message.content
            .filter((b: any) => b.type === 'text')
            .map((b: any) => b.text)
            .join('\n');
        }

        if (content.trim().length < 20) continue; // skip trivial messages

        messages.push({
          role: entry.message.role,
          content: content.trim(),
          timestamp: entry.timestamp,
        });

        if (messages.length >= maxMessages) break;
      } catch {
        // Skip unparseable lines
      }
    }

    if (messages.length === 0) return chunks;

    // Strategy: Extract user instructions, decisions, and corrections
    // These are the highest-signal memories from session transcripts
    for (const msg of messages) {
      if (msg.role !== 'user') continue;
      if (msg.content.length < 30) continue;
      if (msg.content.length > 2000) continue; // skip huge pastes

      // Filter for high-signal user messages
      const isHighSignal =
        // Preferences and decisions
        /\b(prefer|always|never|don't|instead|actually|use|switch to|change to)\b/i.test(msg.content) ||
        // Instructions
        /\b(make sure|important|remember|note that|keep in mind|convention|standard|rule)\b/i.test(msg.content) ||
        // Corrections
        /\b(no,|wrong|incorrect|that's not|fix|should be|supposed to)\b/i.test(msg.content) ||
        // Architecture/design
        /\b(architecture|pattern|approach|design|structure|framework|stack|tech)\b/i.test(msg.content);

      if (!isHighSignal) continue;

      chunks.push({
        content: msg.content.slice(0, 1000), // cap length
        source,
        section: `Session transcript`,
        topics: ['claude-code', 'session-transcript'],
      });
    }
  } catch (err) {
    // Can't read file — permission or format issue
  }

  return chunks;
}

// ── Import engine ──────────────────────────────────────────

export async function importClaudeCode(options: ImportOptions): Promise<ImportResult> {
  const result: ImportResult = {
    sourcesFound: 0,
    sourcesProcessed: 0,
    memoriesCreated: 0,
    memoriesDeduped: 0,
    projectsCovered: [],
    sessionsParsed: 0,
    errors: [],
    dryRun: options.dryRun ?? false,
  };

  const projects = new Set<string>();

  console.log(bold('\n🧠 Engram Import — Claude Code\n'));
  console.log(dim('  Scanning for Claude Code memory sources...\n'));

  // Discover all sources
  const sources = discoverClaudeCodeSources();
  result.sourcesFound = sources.length;

  const mdSources = sources.filter(s => s.type !== 'session-transcript');
  const sessionSources = sources.filter(s => s.type === 'session-transcript');

  console.log(`  ${green('✓')} Found ${mdSources.length} memory files across ${new Set(sources.map(s => s.project)).size} projects`);
  console.log(`  ${green('✓')} Found ${sessionSources.length} session transcripts`);

  if (sources.length === 0) {
    console.log(yellow('\n  No Claude Code data found. Is Claude Code installed?\n'));
    return result;
  }

  // Phase 1: Import markdown sources (CLAUDE.md, auto memory, rules)
  if (mdSources.length > 0) {
    console.log(bold('\n  Phase 1: Memory files\n'));

    for (const source of mdSources) {
      const shortPath = source.path.replace(homedir(), '~');
      const chunks = parseMarkdownIntoChunks(source);

      if (chunks.length === 0) {
        if (options.verbose) console.log(dim(`    skip ${shortPath} (empty)`));
        continue;
      }

      console.log(`    ${cyan(shortPath)}`);
      console.log(`      ${source.type} | ${source.lineCount} lines | ${chunks.length} chunks | project: ${source.project}`);

      projects.add(source.project);
      result.sourcesProcessed++;

      for (const chunk of chunks) {
        if (options.dryRun) {
          if (options.verbose) {
            const preview = chunk.content.slice(0, 80).replace(/\n/g, ' ');
            console.log(dim(`      → [dry-run] ${preview}...`));
          }
          result.memoriesCreated++;
          continue;
        }

        try {
          const mem = options.vault.remember({
            content: chunk.content,
            type: 'semantic',
            entities: chunk.entities,
            topics: [...(chunk.topics ?? []), `import:${source.type}`],
            source: { type: 'external' },
            salience: source.type === 'rules' ? 0.8 : 0.6,
            confidence: 0.7,
          });
          result.memoriesCreated++;
        } catch (err) {
          result.errors.push(`Failed to import chunk from ${shortPath}: ${(err as Error).message}`);
        }
      }
    }
  }

  // Phase 2: Import session transcripts (opt-in, higher signal)
  if (options.includeSessions && sessionSources.length > 0) {
    console.log(bold('\n  Phase 2: Session transcripts\n'));

    const maxPerProject = options.maxSessionsPerProject ?? 10;
    const projectSessionCounts: Record<string, number> = {};

    // Sort by modification time (newest first), limit per project
    const sortedSessions = sessionSources
      .map(s => ({ ...s, mtime: statSync(s.path).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);

    for (const source of sortedSessions) {
      const count = projectSessionCounts[source.project] ?? 0;
      if (count >= maxPerProject) continue;
      projectSessionCounts[source.project] = count + 1;

      const shortPath = source.path.replace(homedir(), '~');
      const chunks = parseSessionTranscript(source);

      if (chunks.length === 0) continue;

      result.sessionsParsed++;
      projects.add(source.project);

      if (options.verbose) {
        console.log(`    ${cyan(shortPath)}`);
        console.log(`      ${chunks.length} high-signal messages extracted`);
      }

      for (const chunk of chunks) {
        if (options.dryRun) {
          result.memoriesCreated++;
          continue;
        }

        try {
          options.vault.remember({
            content: chunk.content,
            type: 'episodic',
            topics: [...(chunk.topics ?? []), 'import:session'],
            source: { type: 'external' },
            salience: 0.4,
            confidence: 0.5,
          });
          result.memoriesCreated++;
        } catch (err) {
          result.errors.push(`Failed to import from session: ${(err as Error).message}`);
        }
      }
    }

    if (result.sessionsParsed > 0) {
      console.log(`    Parsed ${result.sessionsParsed} sessions across ${Object.keys(projectSessionCounts).length} projects`);
    }
  } else if (sessionSources.length > 0 && !options.includeSessions) {
    console.log(dim(`\n  Skipping ${sessionSources.length} session transcripts (use --include-sessions to import)`));
  }

  result.projectsCovered = [...projects];

  // Phase 3: Consolidate if we imported enough
  if (!options.dryRun && result.memoriesCreated >= 10) {
    console.log(bold('\n  Phase 3: Consolidation\n'));
    console.log(dim('    Running consolidation to connect and deduplicate imported memories...'));
    try {
      const report = await options.vault.consolidate();
      result.memoriesDeduped = report.contradictionsFound;
      console.log(`    ${green('✓')} ${report.connectionsFormed} connections formed, ${report.contradictionsFound} contradictions resolved`);
    } catch (err) {
      result.errors.push(`Consolidation failed: ${(err as Error).message}`);
    }
  }

  // Summary
  console.log(bold('\n  ─────────────────────────────────────'));
  console.log(bold('  Import Summary\n'));
  console.log(`    Sources found:     ${result.sourcesFound}`);
  console.log(`    Sources processed: ${result.sourcesProcessed}`);
  console.log(`    Sessions parsed:   ${result.sessionsParsed}`);
  console.log(`    Memories created:  ${green(String(result.memoriesCreated))}`);
  console.log(`    Projects covered:  ${result.projectsCovered.length}`);
  if (result.dryRun) {
    console.log(yellow('\n    [DRY RUN] No memories were actually created.'));
    console.log(yellow('    Remove --dry-run to import for real.\n'));
  }
  if (result.errors.length > 0) {
    console.log(red(`\n    ${result.errors.length} errors:`));
    for (const err of result.errors.slice(0, 5)) {
      console.log(red(`      • ${err}`));
    }
  }

  if (!result.dryRun && result.memoriesCreated > 0) {
    const stats = options.vault.stats();
    console.log(bold('\n  🎉 Import complete!\n'));
    console.log(`    Your Engram vault now has ${bold(String(stats.total))} memories.`);
    console.log(`    No 200-line limit. Semantic search across all projects.`);
    console.log(dim(`\n    Try: engram recall "your query here"`));
    console.log(dim(`    Or:  engram stats\n`));
  }

  return result;
}

// ── Obsidian vault import ─────────────────────────────────

interface ObsidianFrontmatter {
  tags?: string[];
  aliases?: string[];
  [key: string]: unknown;
}

function parseFrontmatter(content: string): { frontmatter: ObsidianFrontmatter | null; body: string } {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { frontmatter: null, body: content };

  const yamlBlock = match[1];
  const body = match[2];
  const fm: ObsidianFrontmatter = {};

  // Simple YAML parser for tags and aliases (avoids dependency on yaml lib)
  for (const line of yamlBlock.split('\n')) {
    const tagMatch = line.match(/^tags:\s*\[(.+)\]/);
    if (tagMatch) {
      fm.tags = tagMatch[1].split(',').map(t => t.trim().replace(/^["']|["']$/g, ''));
      continue;
    }
    const aliasMatch = line.match(/^aliases:\s*\[(.+)\]/);
    if (aliasMatch) {
      fm.aliases = aliasMatch[1].split(',').map(a => a.trim().replace(/^["']|["']$/g, ''));
      continue;
    }
    // YAML list format: tags:\n  - foo\n  - bar
    if (line.match(/^tags:\s*$/)) {
      fm.tags = [];
      continue;
    }
    if (line.match(/^aliases:\s*$/)) {
      fm.aliases = [];
      continue;
    }
    if (fm.tags && line.match(/^\s+-\s+/)) {
      fm.tags.push(line.replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, ''));
    }
    if (fm.aliases && line.match(/^\s+-\s+/)) {
      fm.aliases.push(line.replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, ''));
    }
  }

  return { frontmatter: fm, body };
}

function extractWikilinks(text: string): string[] {
  const links = new Set<string>();
  for (const match of text.matchAll(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g)) {
    links.add(match[1].trim());
  }
  return [...links];
}

function extractObsidianTags(text: string): string[] {
  const tags = new Set<string>();
  // Match #tag but not # headings (must not be at start of line or preceded by newline+space)
  for (const match of text.matchAll(/(?:^|\s)#([a-zA-Z][\w/-]*)/gm)) {
    tags.add(match[1]);
  }
  return [...tags];
}

function parseObsidianChunks(source: ImportSource, frontmatter: ObsidianFrontmatter | null): ImportChunk[] {
  const chunks: ImportChunk[] = [];
  const lines = source.content.split('\n');
  let currentSection = '';
  let currentLines: string[] = [];

  function flush() {
    const text = currentLines.join('\n').trim();
    if (text.length < 10) return;

    const wikilinks = extractWikilinks(text);
    const tags = extractObsidianTags(text);

    // Entities: wikilinks + filename entity + @mentions
    const entities = new Set<string>(wikilinks);
    for (const match of text.matchAll(/@(\w+)/g)) {
      entities.add(match[1]);
    }

    // Topics: folder name + tags + frontmatter tags
    const topics = new Set<string>(tags);
    topics.add('obsidian');
    if (frontmatter?.tags) {
      for (const t of frontmatter.tags) topics.add(t);
    }

    chunks.push({
      content: text,
      source,
      section: currentSection || undefined,
      entities: entities.size > 0 ? [...entities].slice(0, 15) : undefined,
      topics: topics.size > 0 ? [...topics].slice(0, 10) : undefined,
    });
  }

  for (const line of lines) {
    const headerMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headerMatch) {
      flush();
      currentSection = headerMatch[2].trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  flush();

  return chunks;
}

/**
 * Build a backlink map: filename -> set of files that link to it via [[wikilinks]]
 */
function buildBacklinkMap(files: { name: string; content: string }[]): Map<string, Set<string>> {
  const backlinks = new Map<string, Set<string>>();
  for (const file of files) {
    const links = extractWikilinks(file.content);
    for (const link of links) {
      const target = link.toLowerCase();
      if (!backlinks.has(target)) backlinks.set(target, new Set());
      backlinks.get(target)!.add(file.name);
    }
  }
  return backlinks;
}

export async function importObsidian(options: ImportOptions & { vaultPath: string }): Promise<ImportResult> {
  const result: ImportResult = {
    sourcesFound: 0,
    sourcesProcessed: 0,
    memoriesCreated: 0,
    memoriesDeduped: 0,
    projectsCovered: [],
    sessionsParsed: 0,
    errors: [],
    dryRun: options.dryRun ?? false,
  };

  const vaultPath = resolve(options.vaultPath.replace(/^~/, homedir()));

  console.log(bold('\n🧠 Engram Import — Obsidian Vault\n'));
  console.log(dim(`  Scanning ${vaultPath}...\n`));

  if (!existsSync(vaultPath)) {
    console.log(red(`  ✗ Vault path not found: ${vaultPath}\n`));
    result.errors.push(`Vault path not found: ${vaultPath}`);
    return result;
  }

  // Discover all .md files, skipping .obsidian/ and .trash/
  const skipDirs = new Set(['.obsidian', '.trash']);
  function findVaultFiles(dir: string): string[] {
    const files: string[] = [];
    try {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) {
          if (skipDirs.has(entry.name)) continue;
          files.push(...findVaultFiles(join(dir, entry.name)));
        } else if (entry.name.endsWith('.md')) {
          files.push(join(dir, entry.name));
        }
      }
    } catch {
      // Permission denied
    }
    return files;
  }

  const allFiles = findVaultFiles(vaultPath);
  result.sourcesFound = allFiles.length;

  console.log(`  ${green('✓')} Found ${allFiles.length} markdown files\n`);

  if (allFiles.length === 0) {
    console.log(yellow('  No markdown files found in vault.\n'));
    return result;
  }

  // Read all files and build backlink map for salience scoring
  const fileData = allFiles.map(filePath => {
    const content = readFileSync(filePath, 'utf-8');
    const name = basename(filePath, '.md');
    return { filePath, name, content };
  });

  const backlinkMap = buildBacklinkMap(fileData.map(f => ({ name: f.name, content: f.content })));

  // Track folders as projects
  const folders = new Set<string>();

  console.log(bold('  Phase 1: Parsing notes\n'));

  let totalChunks = 0;

  for (const file of fileData) {
    const relativePath = file.filePath.replace(vaultPath + '/', '');
    const parentFolder = dirname(relativePath);
    const folderTopic = parentFolder !== '.' ? parentFolder.split('/')[0] : undefined;
    if (folderTopic) folders.add(folderTopic);

    const { frontmatter, body } = parseFrontmatter(file.content);

    const source: ImportSource = {
      path: file.filePath,
      project: folderTopic ?? 'vault-root',
      type: 'obsidian-note',
      content: body,
      lineCount: file.content.split('\n').length,
    };

    const chunks = parseObsidianChunks(source, frontmatter);
    if (chunks.length === 0) {
      if (options.verbose) console.log(dim(`    skip ${relativePath} (empty)`));
      continue;
    }

    result.sourcesProcessed++;
    totalChunks += chunks.length;

    if (options.verbose) {
      console.log(`    ${cyan(relativePath)}`);
      console.log(`      ${source.lineCount} lines | ${chunks.length} chunks | folder: ${folderTopic ?? '(root)'}`);
    }

    // Determine salience: 0.8 if many backlinks, 0.6 default
    const backlinkCount = backlinkMap.get(file.name.toLowerCase())?.size ?? 0;
    const salience = backlinkCount >= 3 ? 0.8 : 0.6;

    // Add filename as entity, frontmatter aliases as entities too
    const fileEntity = file.name;
    const extraEntities = frontmatter?.aliases ?? [];

    for (const chunk of chunks) {
      if (options.dryRun) {
        if (options.verbose) {
          const preview = chunk.content.slice(0, 80).replace(/\n/g, ' ');
          console.log(dim(`      → [dry-run] ${preview}...`));
        }
        result.memoriesCreated++;
        continue;
      }

      try {
        const mergedEntities = [...new Set([fileEntity, ...extraEntities, ...(chunk.entities ?? [])])].slice(0, 15);
        const topicParts = [...(chunk.topics ?? [])];
        if (folderTopic) topicParts.push(folderTopic);
        topicParts.push('import:obsidian');
        const mergedTopics = [...new Set(topicParts)].slice(0, 10);

        options.vault.remember({
          content: chunk.content,
          type: 'semantic',
          entities: mergedEntities,
          topics: mergedTopics,
          source: { type: 'external' },
          salience,
          confidence: 0.7,
        });
        result.memoriesCreated++;
      } catch (err) {
        result.errors.push(`Failed to import chunk from ${relativePath}: ${(err as Error).message}`);
      }
    }
  }

  result.projectsCovered = [...folders];

  console.log(`\n    ${green('✓')} Processed ${result.sourcesProcessed} files → ${totalChunks} chunks`);

  // Phase 2: Consolidate if enough memories imported
  if (!options.dryRun && result.memoriesCreated >= 10) {
    console.log(bold('\n  Phase 2: Consolidation\n'));
    console.log(dim('    Running consolidation to connect and deduplicate imported memories...'));
    try {
      const report = await options.vault.consolidate();
      result.memoriesDeduped = report.contradictionsFound;
      console.log(`    ${green('✓')} ${report.connectionsFormed} connections formed, ${report.contradictionsFound} contradictions resolved`);
    } catch (err) {
      result.errors.push(`Consolidation failed: ${(err as Error).message}`);
    }
  }

  // Summary
  console.log(bold('\n  ─────────────────────────────────────'));
  console.log(bold('  Import Summary\n'));
  console.log(`    Files found:       ${result.sourcesFound}`);
  console.log(`    Files processed:   ${result.sourcesProcessed}`);
  console.log(`    Memories created:  ${green(String(result.memoriesCreated))}`);
  console.log(`    Folders covered:   ${result.projectsCovered.length} (${result.projectsCovered.join(', ') || 'root only'})`);
  if (result.dryRun) {
    console.log(yellow('\n    [DRY RUN] No memories were actually created.'));
    console.log(yellow('    Remove --dry-run to import for real.\n'));
  }
  if (result.errors.length > 0) {
    console.log(red(`\n    ${result.errors.length} errors:`));
    for (const err of result.errors.slice(0, 5)) {
      console.log(red(`      • ${err}`));
    }
  }

  if (!result.dryRun && result.memoriesCreated > 0) {
    const stats = options.vault.stats();
    console.log(bold('\n  🎉 Import complete!\n'));
    console.log(`    Your Engram vault now has ${bold(String(stats.total))} memories.`);
    console.log(`    Obsidian wikilinks and tags preserved as entities and topics.`);
    console.log(dim(`\n    Try: engram recall "your query here"`));
    console.log(dim(`    Or:  engram stats\n`));
  }

  return result;
}
