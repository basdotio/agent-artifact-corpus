/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * JS Reverse Engineering Tools
 *
 * This module provides tools for JavaScript debugging and reverse engineering:
 * - Script listing and source retrieval
 * - Source code search
 * - Breakpoint management
 * - Request initiator (call stack) analysis
 */

import * as prettier from 'prettier';

import type {CallFrame, DebuggerContext} from '../DebuggerContext.js';
import {zod} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';
import {paginate} from '../utils/pagination.js';

import {ToolCategory} from './categories.js';
import type {Response} from './ToolDefinition.js';
import {
  createToolOutputSchema,
  defineTool,
  PAGINATION_OUTPUT_SCHEMA,
  paginationSchema,
} from './ToolDefinition.js';

function requireDebuggerEnabled(debugger_: DebuggerContext): void {
  if (!debugger_.isEnabled()) {
    throw new ToolError(
      'PRECONDITION_FAILED',
      'Debugger is not enabled. Select a page and retry.',
    );
  }
}

function throwToolFailure(
  code: 'CDP_ERROR' | 'IO_ERROR',
  prefix: string,
  error: unknown,
): never {
  if (error instanceof ToolError) {
    throw error;
  }
  throw new ToolError(
    code,
    `${prefix}: ${error instanceof Error ? error.message : String(error)}`,
    {cause: error, retryable: code === 'CDP_ERROR'},
  );
}

/**
 * After a step command, append a concise summary of where execution stopped.
 * Shows: function name, location, arguments, and a small code snippet.
 */
async function appendStepSummary(
  response: Response,
  debugger_: DebuggerContext,
  action: string,
  frame: CallFrame,
): Promise<void> {
  const line = frame.location.lineNumber + 1; // CDP is 0-based
  const col = frame.location.columnNumber + 1;
  const funcName = frame.functionName || '<anonymous>';
  const url = frame.url || `script:${frame.location.scriptId}`;
  const shortUrl = url.split('/').pop() || url;

  response.appendResponseLine(
    `${action} → ${shortUrl}:${line}:${col}, function ${funcName}`,
  );

  // Show function arguments via evaluateOnCallFrame
  try {
    const argsResult = await debugger_.evaluateOnCallFrame(
      frame.callFrameId,
      `(() => { try { return JSON.stringify(Array.from(arguments)).slice(0, 500); } catch(e) { return String(arguments.length) + ' args'; } })()`,
      {returnByValue: true},
    );
    if (argsResult.result.value && !argsResult.exceptionDetails) {
      response.appendResponseLine(`  args: ${argsResult.result.value}`);
    }
  } catch {
    // arguments not available (e.g. arrow function or global scope)
  }

  // Show a small code snippet around the exact column position
  try {
    const result = await debugger_.getScriptSource(frame.location.scriptId);
    const source = result.scriptSource;
    const lines = source.split('\n');
    const lineContent = lines[frame.location.lineNumber];
    if (lineContent) {
      const snippetLen = 200;
      const half = Math.floor(snippetLen / 2);
      const c = frame.location.columnNumber;
      const s = Math.max(0, c - half);
      const e = Math.min(lineContent.length, s + snippetLen);
      const prefix = s > 0 ? '...' : '';
      const suffix = e < lineContent.length ? '...' : '';
      response.appendResponseLine(
        `  > ${prefix}${lineContent.substring(s, e)}${suffix}`,
      );
    }
  } catch {
    // Source unavailable
  }
}

/**
 * List all loaded JavaScript scripts in the current page.
 */
export const listScripts = defineTool({
  name: 'list_scripts',
  description:
    'Discovers JavaScript currently loaded in the selected debugger context—the main frame by default, or the frame chosen with select_frame. Use select_frame first for iframe-specific source/debugger work. Includes external, inline, and eval scripts in that context; if you already know a function name, endpoint, or code literal, use search_in_sources instead. Each result includes a context-scoped scriptId that expires on reload, navigation, or debugger target change and, for external scripts, a URL that is the preferred selector for get_script_source or save_script_source.',
  annotations: {
    title: 'List Scripts',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['debugger'],
  outputSchema: createToolOutputSchema({
    scripts: zod
      .array(
        zod.object({
          scriptId: zod.string(),
          url: zod.string().nullable(),
          kind: zod.enum(['external', 'inline_or_eval']),
          sourceMapURL: zod.string().nullable(),
          hash: zod.string(),
        }),
      )
      .optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: {
    filter: zod
      .string()
      .optional()
      .describe(
        'Case-insensitive URL substring used to narrow external scripts. It does not search source text or match unnamed inline/eval scripts; use search_in_sources for code-content queries.',
      ),
    ...paginationSchema,
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    let scripts = debugger_.getScripts();

    // Apply filter if provided
    if (request.params.filter) {
      scripts = debugger_.getScriptsByUrlPattern(request.params.filter);
    }

    const paginated = paginate(scripts, {
      pageSize: request.params.pageSize,
      pageIdx: request.params.pageIdx,
    });
    if (paginated.invalidPage) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        `pageIdx ${request.params.pageIdx} is outside 0-${paginated.totalPages - 1}.`,
      );
    }
    const displayScripts = paginated.items;
    const pagination = {
      pageIdx: paginated.currentPage,
      pageSize: request.params.pageSize ?? 20,
      totalItems: scripts.length,
      totalPages: paginated.totalPages,
      hasNextPage: paginated.hasNextPage,
      hasPreviousPage: paginated.hasPreviousPage,
    };

    if (displayScripts.length === 0) {
      response.appendResponseLine('No scripts found.');
      response.setStructuredContent({scripts: [], pagination});
      return;
    }

    response.appendResponseLine(
      `Found ${scripts.length} script(s), showing ${paginated.startIndex + 1}-${paginated.endIndex}:\n`,
    );

    for (const script of displayScripts) {
      response.appendResponseLine(`- ID: ${script.scriptId}`);
      let displayUrl = script.url || '(inline/eval)';
      if (displayUrl.startsWith('data:') && displayUrl.length > 100) {
        displayUrl = displayUrl.substring(0, 100) + '... (truncated)';
      } else if (displayUrl.length > 200) {
        displayUrl = displayUrl.substring(0, 200) + '... (truncated)';
      }
      response.appendResponseLine(`  URL: ${displayUrl}`);
      if (script.sourceMapURL) {
        response.appendResponseLine(`  SourceMap: ${script.sourceMapURL}`);
      }
      response.appendResponseLine('');
    }
    if (paginated.hasNextPage) {
      response.appendResponseLine(
        `Next page: pageIdx=${paginated.currentPage + 1}`,
      );
    }
    response.setStructuredContent({
      scripts: displayScripts.map(script => ({
        scriptId: script.scriptId,
        url: script.url || null,
        kind: script.url ? 'external' : 'inline_or_eval',
        sourceMapURL: script.sourceMapURL ?? null,
        hash: script.hash,
      })),
      pagination,
    });
  },
});

/**
 * Get the source code of a script.
 */
export const getScriptSource = defineTool({
  name: 'get_script_source',
  description:
    'Reads a small source region around a search match, paused location, or known statement without executing or pausing the page. Select by URL when available because URL-backed scripts can be resolved again after navigation; use the debugger-context-scoped scriptId only for current inline/eval scripts. Use line ranges for normal source and offset/length for minified single-line bundles. For a whole, minified, or WASM source, use save_script_source; to observe runtime values next, call set_breakpoint_on_text against the original loaded source.',
  annotations: {
    title: 'Get Script Source',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['debugger'],
  schema: {
    url: zod
      .string()
      .optional()
      .describe(
        'URL from list_scripts, search_in_sources, or a call stack. Preferred stable selector for URL-backed scripts; resolution tries an exact match before a substring match, so provide enough of the URL to avoid ambiguity.',
      ),
    scriptId: zod
      .string()
      .optional()
      .describe(
        'Debugger-context-scoped script ID from list_scripts, search_in_sources, or paused information. Required for unnamed inline/eval scripts, but invalid after reload, navigation, or debugger target/frame change; prefer url for external scripts.',
      ),
    startLine: zod
      .number()
      .int()
      .optional()
      .describe(
        'Inclusive 1-based start line, typically copied from search_in_sources or paused information. Use with endLine for normal multi-line source.',
      ),
    endLine: zod
      .number()
      .int()
      .optional()
      .describe(
        'Inclusive 1-based end line for a bounded multi-line snippet. Omit both line bounds and use offset/length for a minified single-line bundle.',
      ),
    offset: zod
      .number()
      .int()
      .optional()
      .describe(
        'Zero-based character offset into the original source. Use for a bounded read of minified single-line code when line ranges would be too large.',
      ),
    length: zod
      .number()
      .int()
      .optional()
      .default(1000)
      .describe(
        'Maximum characters to return from offset (default: 1000). This is ignored unless offset is provided.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {url, startLine, endLine, offset, length} = request.params;
    let {scriptId} = request.params;

    if (!url && !scriptId) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        'Either url or scriptId must be provided.',
      );
    }

    try {
      let source: string;
      let bytecode: string | undefined;
      if (url) {
        const result = await debugger_.getScriptSourceByUrl(url);
        source = result.source;
        bytecode = result.bytecode;
        scriptId = result.script.scriptId;
        response.appendResponseLine(
          `Resolved URL to script ${scriptId} (${result.script.url}).\n`,
        );
      } else {
        const result = await debugger_.getScriptSource(scriptId!);
        source = result.scriptSource;
        bytecode = result.bytecode;
      }

      if (!source && !bytecode) {
        throw new ToolError(
          'NOT_FOUND',
          `No source found for script ${scriptId}.`,
        );
      }

      if (bytecode) {
        const binaryData = Buffer.from(bytecode, 'base64');
        response.appendResponseLine(
          `Script ${scriptId} is a WebAssembly binary file (${binaryData.length} bytes). Please use save_script_source to download it as a .wasm file.`,
        );
        response.setStructuredContent({
          scriptId,
          sourceType: 'wasm',
          byteLength: binaryData.length,
        });
        return;
      }

      // Character offset mode (for minified files)
      if (offset !== undefined) {
        const start = Math.max(0, offset);
        const end = Math.min(source.length, start + length);
        const extract = source.substring(start, end);

        const prefix = start > 0 ? '...' : '';
        const suffix = end < source.length ? '...' : '';

        response.appendResponseLine(
          `Source for script ${scriptId} (chars ${start}-${end} of ${source.length}):\n`,
        );
        response.appendResponseLine('```javascript');
        response.appendResponseLine(`${prefix}${extract}${suffix}`);
        response.appendResponseLine('```');
        response.setStructuredContent({
          scriptId,
          sourceType: 'javascript',
          startOffset: start,
          endOffset: end,
          totalChars: source.length,
          source: extract,
        });
        return;
      }

      // Line range mode (for normal files)
      if (startLine !== undefined || endLine !== undefined) {
        const lines = source.split('\n');
        const start = (startLine ?? 1) - 1; // Convert to 0-based
        const end = endLine ?? lines.length;
        const selectedLines = lines.slice(start, end);
        const content = selectedLines.join('\n');

        // If the selected range is too large, it's likely minified — suggest offset mode
        if (content.length > 1000) {
          const lineOffset = lines
            .slice(0, start)
            .reduce((sum, l) => sum + l.length + 1, 0);
          response.appendResponseLine(
            `Selected lines ${start + 1}-${Math.min(end, lines.length)} of script ${scriptId} are too large (${content.length} chars). This file is likely minified.`,
          );
          response.appendResponseLine(
            `Recommended: use save_script_source to download the full file — it auto-formats minified code so you can read it normally afterwards.`,
          );
          response.appendResponseLine(
            `Or use offset/length params for a partial read. The character offset for line ${start + 1} is ${lineOffset}.`,
          );
          response.appendResponseLine(`First 1000 characters:\n`);
          response.appendResponseLine('```javascript');
          response.appendResponseLine(content.substring(0, 1000) + '...');
          response.appendResponseLine('```');
          return;
        }

        response.appendResponseLine(
          `Source for script ${scriptId} (lines ${start + 1}-${Math.min(end, lines.length)}):\n`,
        );
        response.appendResponseLine('```javascript');
        for (let i = 0; i < selectedLines.length; i++) {
          response.appendResponseLine(`${start + i + 1}: ${selectedLines[i]}`);
        }
        response.appendResponseLine('```');
        response.setStructuredContent({
          scriptId,
          sourceType: 'javascript',
          startLine: start + 1,
          endLine: Math.min(end, lines.length),
          totalLines: lines.length,
          source: selectedLines.join('\n'),
        });
        return;
      }

      // Full source - but warn if it's too large
      if (source.length > 1000) {
        response.appendResponseLine(
          `Script ${scriptId} is large (${source.length} chars). To view the whole file, use save_script_source (auto-formats minified code). To read a portion inline, use offset/length or startLine/endLine.`,
        );
        response.appendResponseLine(`First 1000 characters:\n`);
        response.appendResponseLine('```javascript');
        response.appendResponseLine(source.substring(0, 1000) + '...');
        response.appendResponseLine('```');
      } else {
        response.appendResponseLine(`Source for script ${scriptId}:\n`);
        response.appendResponseLine('```javascript');
        response.appendResponseLine(source);
        response.appendResponseLine('```');
      }
      response.setStructuredContent({
        scriptId,
        sourceType: 'javascript',
        totalChars: source.length,
        source:
          source.length > 1000 ? `${source.substring(0, 1000)}...` : source,
        truncated: source.length > 1000,
      });
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Failed to get script source', error);
    }
  },
});

/**
 * Save full script source to a local file.
 */
export const saveScriptSource = defineTool({
  name: 'save_script_source',
  description:
    'Saves one complete JavaScript or WASM source for local inspection when an inline snippet is insufficient, especially for large or minified bundles. Prefer get_script_source for a small known region and search_in_sources to locate text across loaded scripts first. With format=true, destinations using a supported JavaScript/TypeScript extension are formatted by default; other extensions preserve raw source, and formatted line numbers may differ from the live page. Use distinctive text plus the original URL with set_breakpoint_on_text for runtime debugging. The returned filename is the resolved local path, while scriptId remains scoped to the current debugger context.',
  annotations: {
    title: 'Save Script Source',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  schema: {
    url: zod
      .string()
      .optional()
      .describe(
        'URL from list_scripts, search_in_sources, or a call stack. Preferred over scriptId because it can be resolved again after navigation; exact match is tried before substring match.',
      ),
    scriptId: zod
      .string()
      .optional()
      .describe(
        'Debugger-context-scoped script ID from list_scripts or search_in_sources. Use for unnamed inline/eval scripts; it becomes invalid after reload, navigation, or debugger target/frame change.',
      ),
    filePath: zod
      .string()
      .describe(
        'Destination path for the complete source, absolute or relative to the server working directory and subject to --allowedRoots. A JavaScript/TypeScript extension enables formatting; use .wasm for bytecode or another extension to preserve raw text.',
      ),
    confirmOverwrite: zod
      .boolean()
      .default(false)
      .describe(
        'Set true only to authorize replacing an existing filePath. A new file does not require overwrite confirmation.',
      ),
    format: zod
      .boolean()
      .optional()
      .default(true)
      .describe(
        'Format supported JavaScript/TypeScript extensions for readability (default: true). Set false when exact source bytes or original line layout matter; formatted line numbers cannot be used as live breakpoint locations.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {url, scriptId, filePath, format} = request.params;

    if (!url && !scriptId) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        'Either url or scriptId must be provided.',
      );
    }

    try {
      let source: string;
      let bytecode: string | undefined;
      let resolvedId = scriptId;
      if (url) {
        const result = await debugger_.getScriptSourceByUrl(url);
        source = result.source;
        bytecode = result.bytecode;
        resolvedId = result.script.scriptId;
        response.appendResponseLine(
          `Resolved URL to script ${resolvedId} (${result.script.url}).`,
        );
      } else {
        const result = await debugger_.getScriptSource(scriptId!);
        source = result.scriptSource;
        bytecode = result.bytecode;
      }

      if (!source && !bytecode) {
        throw new ToolError(
          'NOT_FOUND',
          `No source found for script ${resolvedId}.`,
        );
      }

      if (bytecode) {
        const binaryData = Buffer.from(bytecode, 'base64');
        const result = await context.saveFile(binaryData, filePath, {
          confirmOverwrite: request.params.confirmOverwrite,
        });
        response.appendResponseLine(
          `Saved WASM script source to ${result.filename} (${binaryData.length} bytes).`,
        );
        response.setStructuredContent({
          scriptId: resolvedId,
          filename: result.filename,
          byteLength: binaryData.length,
          sourceType: 'wasm',
        });
      } else {
        let output = source;
        let formatNote = '';
        const ext = filePath.toLowerCase().match(/\.(m?[jt]sx?)$/)?.[1];
        if (format && ext) {
          const parser = ext.startsWith('t') ? 'typescript' : 'babel';
          try {
            output = await prettier.format(source, {
              parser,
              printWidth: 120,
            });
            formatNote = ' (formatted)';
          } catch (err) {
            formatNote = ` (format skipped: ${err instanceof Error ? err.message.split('\n')[0] : String(err)})`;
          }
        }
        const data = new TextEncoder().encode(output);
        const result = await context.saveFile(data, filePath, {
          confirmOverwrite: request.params.confirmOverwrite,
        });
        response.appendResponseLine(
          `Saved script source to ${result.filename} (${output.length} chars${formatNote}).`,
        );
        response.setStructuredContent({
          scriptId: resolvedId,
          filename: result.filename,
          charLength: output.length,
          formatted: formatNote === ' (formatted)',
        });
      }
    } catch (error) {
      throwToolFailure('IO_ERROR', 'Failed to save script source', error);
    }
  },
});

/**
 * Search for a string in all loaded scripts.
 */
export const searchInSources = defineTool({
  name: 'search_in_sources',
  description:
    'Finds a known function name, endpoint, string literal, token, or code pattern in JavaScript loaded by the selected debugger context—the main frame by default, or the frame chosen with select_frame. It searches external, inline/eval, and minified sources in that context without executing or pausing the page, returning 1-based lines plus context-scoped scriptIds; URLs are the preferred selectors for URL-backed matches. Use select_frame first for iframe-specific source work, get_script_source for nearby context, save_script_source for a whole bundle, or set_breakpoint_on_text when runtime values are needed. For a known captured request, prefer get_request_initiator before a broad source search.',
  annotations: {
    title: 'Search in Sources',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['debugger'],
  outputSchema: createToolOutputSchema({
    query: zod.string().optional(),
    totalMatches: zod.number().int().optional(),
    skippedMinified: zod.number().int().optional(),
    matches: zod
      .array(
        zod.object({
          scriptId: zod.string(),
          url: zod.string().nullable(),
          kind: zod.enum(['external', 'inline_or_eval']),
          lineNumber: zod.number().int(),
          lineContent: zod.string(),
        }),
      )
      .optional(),
  }),
  schema: {
    query: zod
      .string()
      .describe(
        'Source text to locate, or a regular-expression pattern when isRegex=true. Prefer a distinctive function name, endpoint, property, or literal that can also anchor set_breakpoint_on_text.',
      ),
    caseSensitive: zod
      .boolean()
      .optional()
      .default(false)
      .describe(
        'Match case exactly when true. Leave false for discovery; set true when choosing exact code text for a breakpoint.',
      ),
    isRegex: zod
      .boolean()
      .optional()
      .default(false)
      .describe(
        'Interpret query as a regular expression when true. Leave false for literal endpoint, token, and code-text searches.',
      ),
    maxResults: zod
      .number()
      .int()
      .optional()
      .default(30)
      .describe(
        'Maximum matches to return (default: 30). Narrow with urlFilter before increasing this for common text.',
      ),
    maxLineLength: zod
      .number()
      .int()
      .optional()
      .default(150)
      .describe(
        'Maximum characters in each matched-line preview (default: 150). Use get_script_source rather than a very large preview when surrounding context is needed.',
      ),
    excludeMinified: zod
      .boolean()
      .optional()
      .default(false)
      .describe(
        'Skip sources with very long lines when true. Keep the default false for reverse engineering because relevant code often exists only in compressed bundles.',
      ),
    urlFilter: zod
      .string()
      .optional()
      .describe(
        'Case-insensitive script-URL substring used to narrow matches to a known bundle or domain. It excludes unnamed inline/eval scripts.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {
      query,
      caseSensitive,
      isRegex,
      maxResults,
      maxLineLength,
      excludeMinified,
      urlFilter,
    } = request.params;

    try {
      const result = await debugger_.searchInScripts(query, {
        caseSensitive,
        isRegex,
      });

      if (result.matches.length === 0) {
        response.appendResponseLine(`No matches found for "${query}".`);
        response.setStructuredContent({query, totalMatches: 0, matches: []});
        return;
      }

      // Filter matches
      let filteredMatches = result.matches;

      // Apply URL filter
      if (urlFilter) {
        const lowerFilter = urlFilter.toLowerCase();
        filteredMatches = filteredMatches.filter(
          m => m.url && m.url.toLowerCase().includes(lowerFilter),
        );
      }

      // Filter out minified files (lines > 10000 chars)
      const minifiedThreshold = 10000;
      let skippedMinified = 0;
      if (excludeMinified) {
        const beforeCount = filteredMatches.length;
        filteredMatches = filteredMatches.filter(m => {
          if (m.lineContent.length > minifiedThreshold) {
            return false;
          }
          return true;
        });
        skippedMinified = beforeCount - filteredMatches.length;
      }

      if (filteredMatches.length === 0) {
        response.appendResponseLine(`No matches found for "${query}".`);
        if (skippedMinified > 0) {
          response.appendResponseLine(
            `(${skippedMinified} matches in minified files were skipped. Set excludeMinified=false to include them.)`,
          );
        }
        response.setStructuredContent({
          query,
          totalMatches: 0,
          skippedMinified,
          matches: [],
        });
        return;
      }

      const displayMatches = filteredMatches.slice(0, maxResults);
      const totalMatches = filteredMatches.length;
      const structuredMatches: Array<{
        scriptId: string;
        url: string | null;
        kind: 'external' | 'inline_or_eval';
        lineNumber: number;
        lineContent: string;
      }> = [];

      response.appendResponseLine(
        `Found ${totalMatches} match(es) for "${query}"${totalMatches > maxResults ? ` (showing first ${maxResults})` : ''}:`,
      );
      if (skippedMinified > 0) {
        response.appendResponseLine(
          `(${skippedMinified} matches in minified files skipped)`,
        );
      }
      response.appendResponseLine('');

      for (const match of displayMatches) {
        const lineNum = match.lineNumber + 1;
        const scriptId = match.scriptId;
        const url = match.url || '(inline)';

        // Truncate line content, centering around the match if possible
        let preview = match.lineContent.trim();
        const effectiveMaxLen = maxLineLength > 0 ? maxLineLength : 500;
        if (preview.length > effectiveMaxLen) {
          // Try to find the query position to center the preview
          const lowerContent = caseSensitive ? preview : preview.toLowerCase();
          const lowerQuery = caseSensitive ? query : query.toLowerCase();
          const matchPos = isRegex ? 0 : lowerContent.indexOf(lowerQuery);

          if (matchPos >= 0) {
            // Center around match position
            const halfLen = Math.floor(effectiveMaxLen / 2);
            let start = Math.max(0, matchPos - halfLen);
            let end = start + effectiveMaxLen;

            if (end > preview.length) {
              end = preview.length;
              start = Math.max(0, end - effectiveMaxLen);
            }

            const prefix = start > 0 ? '...' : '';
            const suffix = end < preview.length ? '...' : '';
            preview = prefix + preview.substring(start, end) + suffix;
          } else {
            // Fallback: truncate from start
            preview = preview.substring(0, effectiveMaxLen) + '...';
          }
        }

        response.appendResponseLine(`[${scriptId}] ${url}:${lineNum}`);
        response.appendResponseLine(`  ${preview}`);
        response.appendResponseLine('');
        structuredMatches.push({
          scriptId,
          url: match.url || null,
          kind: match.url ? 'external' : 'inline_or_eval',
          lineNumber: lineNum,
          lineContent: preview,
        });
      }

      response.appendResponseLine('---');
      response.appendResponseLine(
        'Tip: Use get_script_source(url=..., startLine, endLine) to view full context around a match. Using url is preferred over scriptId as it stays valid across page navigations.',
      );
      response.setStructuredContent({
        query,
        totalMatches,
        skippedMinified,
        matches: structuredMatches,
      });
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Source search failed', error);
    }
  },
});

/**
 * Remove breakpoint(s). Supports removing a single code breakpoint by ID,
 * a single XHR breakpoint by URL, or all breakpoints at once.
 */
export const removeBreakpoint = defineTool({
  name: 'remove_breakpoint',
  description:
    'Removes a known code breakpoint, XHR/Fetch breakpoint, or every MCP-managed breakpoint after explicit confirmation. Use breakpointId from set_breakpoint_on_text/list_breakpoints for remove_code, or reuse the exact URL pattern from break_on_xhr/list_breakpoints for remove_xhr. Removal does not resume an already paused page; call pause_or_resume(action="resume") separately after inspection.',
  annotations: {
    title: 'Remove Breakpoint',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
    destructiveHint: true,
    idempotentHint: true,
  },
  capabilities: ['debugger'],
  schema: {
    action: zod
      .enum(['remove_code', 'remove_xhr', 'remove_all'])
      .describe(
        'Required removal mode: remove_code needs breakpointId, remove_xhr needs url, and remove_all removes both kinds.',
      ),
    breakpointId: zod
      .string()
      .optional()
      .describe(
        'Current breakpoint ID returned by set_breakpoint_on_text or list_breakpoints. Used only with action="remove_code"; list again after a debugger/page-session rebuild because restoration may assign a new ID.',
      ),
    url: zod
      .string()
      .optional()
      .describe(
        'Exact URL substring pattern previously passed to break_on_xhr or returned by list_breakpoints. Used only with action="remove_xhr".',
      ),
    confirm: zod
      .boolean()
      .default(false)
      .describe(
        'Must be true to authorize the selected removal action. This does not authorize or trigger resuming execution.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {action, breakpointId, url, confirm} = request.params;

    if (!confirm) {
      throw new ToolError(
        'CONFIRMATION_REQUIRED',
        'remove_breakpoint requires confirm=true.',
      );
    }

    try {
      if (action === 'remove_code') {
        if (!breakpointId) {
          throw new ToolError(
            'INVALID_ARGUMENT',
            'action=remove_code requires breakpointId.',
          );
        }
        // Remove a single code breakpoint by ID
        await debugger_.removeBreakpoint(breakpointId);
        response.appendResponseLine(`Breakpoint ${breakpointId} removed.`);
        response.setStructuredContent({
          action,
          removed: {kind: 'code', breakpointId},
        });
      } else if (action === 'remove_xhr') {
        if (!url) {
          throw new ToolError(
            'INVALID_ARGUMENT',
            'action=remove_xhr requires url.',
          );
        }
        // Remove a single XHR breakpoint by URL
        await debugger_.removeXHRBreakpoint(url);
        response.appendResponseLine(`XHR breakpoint for "${url}" removed.`);
        response.setStructuredContent({
          action,
          removed: {kind: 'xhr', url},
        });
      } else {
        // Remove all breakpoints (code + XHR)
        const codeCount = debugger_.getBreakpoints().length;
        const xhrCount = debugger_.getXHRBreakpoints().length;
        if (codeCount === 0 && xhrCount === 0) {
          response.appendResponseLine('No active breakpoints to remove.');
          response.setStructuredContent({
            action,
            removed: {codeCount: 0, xhrCount: 0},
          });
          return;
        }
        const result = await debugger_.removeAllBreakpoints();
        if (result.failedCode.length || result.failedXHR.length) {
          throw new ToolError(
            'CDP_ERROR',
            `Breakpoint removal was partial: removed ${result.removedCode} code and ${result.removedXHR} XHR; failed ${result.failedCode.length} code and ${result.failedXHR.length} XHR. List breakpoints to inspect what remains.`,
            {retryable: true},
          );
        }
        const parts: string[] = [];
        if (result.removedCode > 0) parts.push(`${result.removedCode} code`);
        if (result.removedXHR > 0) parts.push(`${result.removedXHR} XHR`);
        response.appendResponseLine(
          `Removed ${parts.join(' + ')} breakpoint(s).`,
        );
        response.setStructuredContent({
          action,
          removed: {
            codeCount: result.removedCode,
            xhrCount: result.removedXHR,
          },
        });
      }

      if (debugger_.isPaused()) {
        response.appendResponseLine(
          'Execution is still paused. Use pause_or_resume(action="resume") when you are ready to continue.',
        );
      }
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Breakpoint removal failed', error);
    }
  },
});

/**
 * List all active breakpoints.
 */
export const listBreakpoints = defineTool({
  name: 'list_breakpoints',
  description:
    'Inspects code and XHR/Fetch breakpoints managed by this MCP session before reproducing an action or cleaning up debugger state. Returns current code breakpointIds and the exact XHR URL patterns needed by remove_breakpoint; URL-backed definitions are restored after navigation when possible, but a rebuilt debugger session may assign new IDs. This does not show why or where execution is currently paused—use get_paused_info for the active call stack.',
  annotations: {
    title: 'List Breakpoints',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['debugger'],
  outputSchema: createToolOutputSchema({
    breakpoints: zod.array(zod.record(zod.string(), zod.unknown())).optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: paginationSchema,
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const breakpoints = debugger_.getBreakpoints();
    const xhrBreakpoints = debugger_.getXHRBreakpoints();
    const entries = [
      ...breakpoints.map(breakpoint => ({
        kind: 'code' as const,
        breakpoint,
      })),
      ...xhrBreakpoints.map(url => ({kind: 'xhr' as const, url})),
    ];

    const paginated = paginate(entries, {
      pageSize: request.params.pageSize,
      pageIdx: request.params.pageIdx,
    });
    if (paginated.invalidPage) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        `pageIdx ${request.params.pageIdx} is outside 0-${paginated.totalPages - 1}.`,
      );
    }
    const pagination = {
      pageIdx: paginated.currentPage,
      pageSize: request.params.pageSize ?? 20,
      totalItems: entries.length,
      totalPages: paginated.totalPages,
      hasNextPage: paginated.hasNextPage,
      hasPreviousPage: paginated.hasPreviousPage,
    };

    if (breakpoints.length === 0 && xhrBreakpoints.length === 0) {
      response.appendResponseLine('No active breakpoints.');
      response.setStructuredContent({breakpoints: [], pagination});
      return;
    }

    response.appendResponseLine(
      `Active breakpoints (${breakpoints.length} code, ${xhrBreakpoints.length} XHR/Fetch):\n`,
    );

    response.appendResponseLine(
      `Showing ${paginated.startIndex + 1}-${paginated.endIndex} of ${entries.length}.`,
    );
    for (const entry of paginated.items) {
      if (entry.kind === 'code') {
        const bp = entry.breakpoint;
        response.appendResponseLine(`- ID: ${bp.breakpointId}`);
        response.appendResponseLine(`  URL: ${bp.url}`);
        response.appendResponseLine(
          `  Line: ${bp.lineNumber + 1}, Column: ${bp.columnNumber}`,
        );
        if (bp.condition) {
          response.appendResponseLine(`  Condition: ${bp.condition}`);
        }
        if (bp.locations.length > 0) {
          response.appendResponseLine(`  Locations: ${bp.locations.length}`);
        }
        response.appendResponseLine('');
      } else {
        response.appendResponseLine(`- XHR URL contains: ${entry.url}`);
      }
    }
    if (paginated.hasNextPage) {
      response.appendResponseLine(
        `Next page: pageIdx=${paginated.currentPage + 1}`,
      );
    }
    response.setStructuredContent({
      breakpoints: paginated.items.map(entry =>
        entry.kind === 'code'
          ? {
              kind: 'code',
              breakpointId: entry.breakpoint.breakpointId,
              url: entry.breakpoint.url,
              lineNumber: entry.breakpoint.lineNumber + 1,
              columnNumber: entry.breakpoint.columnNumber,
              condition: entry.breakpoint.condition ?? null,
            }
          : {kind: 'xhr', url: entry.url},
      ),
      pagination,
    });
  },
});

/**
 * Get the call stack (initiator) for a network request.
 */
export const getRequestInitiator = defineTool({
  name: 'get_request_initiator',
  description:
    'Non-pausing first action for tracing which JavaScript initiated a retained HTTP request when CDP initiator evidence was active. Pass the reqid from list_network_requests; because initiator capture starts lazily and is not retroactive, an older request may have no stack—in that case reproduce the action and inspect the new reqid, or set break_on_xhr before reproduction when runtime values are required. If the captured stack identifies the code, inspect its URL/location with get_script_source. If arguments, locals, or a dynamically built payload are still needed, use break_on_xhr, reproduce, then call get_paused_info or evaluate_script before stepping or resuming. This tool only reads retained evidence and does not pause or reproduce the request.',
  annotations: {
    title: 'Get Request Initiator',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['network'],
  schema: {
    requestId: zod
      .number()
      .int()
      .describe(
        'Numeric reqid returned by list_network_requests, not a raw CDP request ID. It survives navigation while retained, but becomes stale after FIFO eviction or clear_network_requests; list requests again if needed.',
      ),
  },
  handler: async (request, response, context) => {
    const {requestId} = request.params;

    try {
      let httpRequest: ReturnType<typeof context.getNetworkRequestById>;
      try {
        httpRequest = context.getNetworkRequestById(requestId);
      } catch (error) {
        throw new ToolError(
          'NOT_FOUND',
          `Network request ${requestId} is no longer retained. List network requests and use a current reqid.`,
          {cause: error},
        );
      }
      const initiator = context.getRequestInitiator(httpRequest);

      if (!initiator) {
        response.appendResponseLine(
          `No initiator information found for request ${requestId}.`,
        );
        response.appendResponseLine(
          'This might be a navigation request or the initiator was not captured.',
        );
        response.appendResponseLine(
          'Initiator capture is not retroactive. Reproduce the action now and inspect its new reqid; set break_on_xhr before reproduction if runtime values are required.',
        );
        response.setStructuredContent({requestId, initiator: null});
        return;
      }

      response.appendResponseLine(
        `Request initiator for ${httpRequest.url()}:\n`,
      );
      response.appendResponseLine(`Type: ${initiator.type}`);

      if (initiator.url) {
        response.appendResponseLine(`URL: ${initiator.url}`);
      }
      if (initiator.lineNumber !== undefined) {
        response.appendResponseLine(`Line: ${initiator.lineNumber + 1}`);
      }
      if (initiator.columnNumber !== undefined) {
        response.appendResponseLine(`Column: ${initiator.columnNumber}`);
      }

      if (initiator.stack && initiator.stack.callFrames.length > 0) {
        response.appendResponseLine('\nCall Stack:');
        for (let i = 0; i < initiator.stack.callFrames.length; i++) {
          const frame = initiator.stack.callFrames[i];
          const functionName = frame.functionName || '(anonymous)';
          const location = frame.url
            ? `${frame.url}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`
            : `script ${frame.scriptId}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`;
          response.appendResponseLine(
            `  ${i + 1}. ${functionName} @ ${location}`,
          );
        }

        // Include parent stack if available (for async calls)
        if (
          initiator.stack.parent &&
          initiator.stack.parent.callFrames.length > 0
        ) {
          response.appendResponseLine('\nAsync Parent Stack:');
          for (let i = 0; i < initiator.stack.parent.callFrames.length; i++) {
            const frame = initiator.stack.parent.callFrames[i];
            const functionName = frame.functionName || '(anonymous)';
            const location = frame.url
              ? `${frame.url}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`
              : `script ${frame.scriptId}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`;
            response.appendResponseLine(
              `  ${i + 1}. ${functionName} @ ${location}`,
            );
          }
        }
      }
      response.setStructuredContent({
        requestId,
        requestUrl: httpRequest.url(),
        initiator,
      });
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Failed to get request initiator', error);
    }
  },
});

/**
 * Get the current paused state and debug information.
 */
export const getPausedInfo = defineTool({
  name: 'get_paused_info',
  description:
    'Inspects the current call stack, source locations, and selected call-frame scopes after a code/XHR breakpoint or explicit pause has stopped execution. It neither creates a pause nor resumes one. Returned frameIndex values and callFrameIds belong only to the current pause and expire after any step or resume; use evaluate_script with frameIndex for a focused expression, then step or pause_or_resume(action="resume").',
  annotations: {
    title: 'Get Paused Info',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: true,
  },
  capabilities: ['debugger'],
  outputSchema: createToolOutputSchema({
    paused: zod.boolean().optional(),
    reason: zod.string().nullable().optional(),
    hitBreakpoints: zod.array(zod.string()).optional(),
    callFrames: zod.array(zod.record(zod.string(), zod.unknown())).optional(),
  }),
  schema: {
    includeScopes: zod
      .boolean()
      .optional()
      .default(true)
      .describe(
        'Include bounded variables from the selected call frame (default: true). Set false when only the stack and source locations are needed.',
      ),
    maxScopeDepth: zod
      .number()
      .int()
      .optional()
      .default(2)
      .describe(
        'Scope categories to include for frameIndex (default: 2): 1 reads arguments/locals, 2 also reads closures, and 3+ includes other non-global scopes. Increase only when the needed value is absent.',
      ),
    frameIndex: zod
      .number()
      .int()
      .optional()
      .default(0)
      .describe(
        'Zero-based frame from this pause whose scopes should be read (default: top frame). Frame indices change after a step and expire on resume.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const pausedState = debugger_.getPausedState();

    if (!pausedState.isPaused) {
      throw new ToolError(
        'PRECONDITION_FAILED',
        'Execution is not paused. Set a breakpoint and trigger it first.',
      );
    }

    response.appendResponseLine('🔴 Execution Paused\n');

    if (pausedState.reason) {
      response.appendResponseLine(`Reason: ${pausedState.reason}`);
    }

    if (pausedState.hitBreakpoints && pausedState.hitBreakpoints.length > 0) {
      response.appendResponseLine(
        `Hit breakpoints: ${pausedState.hitBreakpoints.join(', ')}`,
      );
    }

    response.appendResponseLine('\n📍 Call Stack:');

    for (let i = 0; i < pausedState.callFrames.length; i++) {
      const frame = pausedState.callFrames[i];
      const script = debugger_.getScriptById(frame.location.scriptId);
      const url =
        script?.url || frame.url || `script:${frame.location.scriptId}`;
      const location = `${url}:${frame.location.lineNumber + 1}:${frame.location.columnNumber + 1}`;
      response.appendResponseLine(
        `  ${i}. ${frame.functionName} @ ${location}`,
      );
    }

    // Include scope variables if requested
    if (request.params.includeScopes && pausedState.callFrames.length > 0) {
      const frameIndex = request.params.frameIndex;
      if (frameIndex < 0 || frameIndex >= pausedState.callFrames.length) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          `frameIndex ${frameIndex} is out of range (0-${pausedState.callFrames.length - 1}).`,
        );
      } else {
        const selectedFrame = pausedState.callFrames[frameIndex];
        response.appendResponseLine(
          `\n🔍 Scope Variables (frame ${frameIndex}: ${selectedFrame.functionName || '<anonymous>'}):`,
        );

        const maxDepth = request.params.maxScopeDepth;
        // Scope priority: local(1) > closure(2) > block/catch/with/etc(3+)
        // Always skip global scope
        const scopePriority: Record<string, number> = {
          local: 1,
          closure: 2,
        };
        let scopeCount = 0;

        for (const scope of selectedFrame.scopeChain) {
          if (scope.type === 'global') {
            continue;
          }

          const priority = scopePriority[scope.type] ?? 3;
          if (priority > maxDepth) {
            continue;
          }
          scopeCount++;

          const scopeName = scope.name || scope.type;
          response.appendResponseLine(`\n  [${scopeName}]:`);

          if (scope.object.objectId) {
            try {
              const variables = await debugger_.getScopeVariables(
                scope.object.objectId,
              );

              if (variables.length === 0) {
                response.appendResponseLine('    (empty)');
              } else {
                for (const variable of variables.slice(0, 20)) {
                  let valueStr =
                    typeof variable.value === 'string'
                      ? `"${variable.value}"`
                      : JSON.stringify(variable.value);
                  if (valueStr && valueStr.length > 200) {
                    valueStr = valueStr.slice(0, 200) + '...(truncated)';
                  }
                  response.appendResponseLine(
                    `    ${variable.name}: ${valueStr}`,
                  );
                }
                if (variables.length > 20) {
                  response.appendResponseLine(
                    `    ... and ${variables.length - 20} more`,
                  );
                }
              }
            } catch {
              response.appendResponseLine('    (unable to retrieve variables)');
            }
          }
        }

        if (scopeCount === 0) {
          response.appendResponseLine(
            '    (no matching scopes — try increasing maxScopeDepth)',
          );
        }
      }
    }

    response.appendResponseLine(
      '\n💡 Use pause_or_resume(action="resume") to resume, or step with direction="over" | "into" | "out" to continue one step.',
    );
    response.setStructuredContent({
      paused: true,
      reason: pausedState.reason ?? null,
      hitBreakpoints: pausedState.hitBreakpoints ?? [],
      callFrames: pausedState.callFrames.map((frame, index) => ({
        frameIndex: index,
        callFrameId: frame.callFrameId,
        functionName: frame.functionName,
        url: frame.url,
        location: frame.location,
      })),
    });
  },
});

/**
 * Resume execution after a breakpoint.
 */
export const pauseOrResume = defineTool({
  name: 'pause_or_resume',
  description:
    'Explicitly requests an immediate pause or resumes an existing paused execution; it never toggles implicitly. Use a code breakpoint or break_on_xhr instead when a specific statement/request should stop, and use get_paused_info before resuming if evidence must be collected. Resuming invalidates current callFrameIds and frame indices.',
  annotations: {
    title: 'Pause / Resume',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  schema: {
    action: zod
      .enum(['pause', 'resume'])
      .describe(
        'Use "pause" only while running, or "resume" only after a breakpoint/manual pause. Resume after get_paused_info/evaluate_script/step inspection is complete.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    try {
      if (request.params.action === 'resume') {
        if (!debugger_.isPaused()) {
          throw new ToolError(
            'CONFLICT',
            'Execution is already running; action=resume is not applicable.',
          );
        }
        await debugger_.resume();
        response.appendResponseLine('▶️ Execution resumed.');
        response.setStructuredContent({action: 'resume', state: 'running'});
      } else {
        if (debugger_.isPaused()) {
          throw new ToolError(
            'CONFLICT',
            'Execution is already paused; action=pause is not applicable.',
          );
        }
        await debugger_.pause();
        response.appendResponseLine(
          '⏸️ Pause requested. Waiting for execution to pause...',
        );
        response.setStructuredContent({
          action: 'pause',
          state: 'pause_requested',
        });
      }
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Execution action failed', error);
    }
  },
});

/**
 * Step execution: over, into, or out.
 */
export const step = defineTool({
  name: 'step',
  description:
    'Advances JavaScript execution by one debugger operation from an existing pause and returns the next stopped call frame with concise source context. Use after get_paused_info or evaluate_script when control flow still needs tracing; it cannot start from running execution. Each advance invalidates prior callFrameIds, so inspect the new pause again as needed, then use pause_or_resume(action="resume") to finish.',
  annotations: {
    title: 'Step',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  schema: {
    direction: zod
      .enum(['over', 'into', 'out'])
      .describe(
        'Choose "over" for the next statement without entering calls, "into" to follow a call, or "out" to continue until the current function returns.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    if (!debugger_.isPaused()) {
      throw new ToolError(
        'PRECONDITION_FAILED',
        'Execution is not paused. Cannot step.',
      );
    }

    const {direction} = request.params;
    const labels = {
      over: '⏭️ Stepped over',
      into: '⬇️ Stepped into',
      out: '⬆️ Stepped out',
    } as const;

    try {
      const frame =
        direction === 'over'
          ? await debugger_.stepOver()
          : direction === 'into'
            ? await debugger_.stepInto()
            : await debugger_.stepOut();
      await appendStepSummary(response, debugger_, labels[direction], frame);
      response.setStructuredContent({
        direction,
        callFrame: {
          callFrameId: frame.callFrameId,
          functionName: frame.functionName,
          url: frame.url,
          location: frame.location,
        },
      });
    } catch (error) {
      throwToolFailure('CDP_ERROR', `Failed to step ${direction}`, error);
    }
  },
});

/**
 * Set a breakpoint on specific code text (function name, statement, etc.)
 * Combines search + locate + set breakpoint in one step.
 */
export const setBreakpointOnText = defineTool({
  name: 'set_breakpoint_on_text',
  description:
    'Sets a restorable URL-backed breakpoint when distinctive code text is known and its runtime values must be observed. Call it directly when the user already supplies precise text plus any URL/occurrence disambiguation; use search_in_sources/get_script_source first only when the location is unknown or ambiguous. For an API with no known code location, start with list_network_requests and get_request_initiator or use break_on_xhr. On a hit, call get_paused_info, optionally evaluate_script, then step or resume. Returns the current breakpointId for remove_breakpoint; list breakpoints again after a rebuilt debugger session, and note that unnamed inline/eval scripts cannot use this URL breakpoint.',
  annotations: {
    title: 'Set Breakpoint on Text',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  schema: {
    text: zod
      .string()
      .describe(
        'Exact case-sensitive source text used to locate the breakpoint, such as a distinctive function declaration, call, or statement. Prefer a snippet confirmed by search_in_sources and avoid common tokens.',
      ),
    urlFilter: zod
      .string()
      .optional()
      .describe(
        'Case-insensitive URL substring that limits candidate scripts. Use the URL from search_in_sources/get_script_source to avoid the same text in unrelated bundles.',
      ),
    occurrence: zod
      .number()
      .int()
      .positive()
      .optional()
      .default(1)
      .describe(
        'One-based occurrence among matching loaded-source results (default: 1). Use only after reviewing multiple search matches; urlFilter is usually the more stable disambiguator.',
      ),
    condition: zod
      .string()
      .optional()
      .describe(
        'Optional simple synchronous expression evaluated in the future call frame; the breakpoint pauses only when it is true. Use it to reduce repeated hits after the location is precise, never for async work, complex discovery, or side effects.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {text, urlFilter, occurrence, condition} = request.params;

    try {
      // Step 1: Search for the text in all scripts
      const searchResult = await debugger_.searchInScripts(text, {
        caseSensitive: true,
        isRegex: false,
      });

      if (searchResult.matches.length === 0) {
        throw new ToolError(
          'NOT_FOUND',
          `"${text}" was not found in any loaded script.`,
        );
      }

      // Apply URL filter if specified
      let matches = searchResult.matches;
      if (urlFilter) {
        const lowerFilter = urlFilter.toLowerCase();
        matches = matches.filter(
          m => m.url && m.url.toLowerCase().includes(lowerFilter),
        );
        if (matches.length === 0) {
          throw new ToolError(
            'NOT_FOUND',
            `"${text}" was not found in scripts matching "${urlFilter}".`,
          );
        }
      }

      // Get the specified occurrence
      if (occurrence > matches.length) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          `Only ${matches.length} occurrence(s) found, but occurrence ${occurrence} was requested.`,
        );
      }

      const match = matches[occurrence - 1];
      const script = debugger_.getScriptById(match.scriptId);
      const url = script?.url || match.url;

      if (!url) {
        throw new ToolError(
          'PRECONDITION_FAILED',
          'Cannot set breakpoint: script has no URL (inline script).',
        );
      }

      // Step 2: Get exact column position by searching in the script source
      const result = await debugger_.getScriptSource(match.scriptId);
      const source = result.scriptSource;
      let columnNumber = 0;

      // For minified files, find exact column
      const lines = source.split('\n');
      if (match.lineNumber < lines.length) {
        const lineContent = lines[match.lineNumber];
        const colPos = lineContent.indexOf(text);
        if (colPos >= 0) {
          columnNumber = colPos;
        }
      }

      // Step 3: Set the breakpoint
      const breakpointInfo = await debugger_.setBreakpoint(
        url,
        match.lineNumber,
        columnNumber,
        condition,
      );

      response.appendResponseLine(`✅ Breakpoint set successfully!`);
      response.appendResponseLine(`- ID: ${breakpointInfo.breakpointId}`);
      response.appendResponseLine(`- URL: ${url}`);
      response.appendResponseLine(
        `- Line: ${match.lineNumber + 1}, Column: ${columnNumber}`,
      );
      if (condition) {
        response.appendResponseLine(`- Condition: ${condition}`);
      }

      // Show context
      const contextStart = Math.max(0, columnNumber - 50);
      const contextEnd = Math.min(
        lines[match.lineNumber].length,
        columnNumber + text.length + 50,
      );
      const preview = lines[match.lineNumber].substring(
        contextStart,
        contextEnd,
      );
      const prefix = contextStart > 0 ? '...' : '';
      const suffix = contextEnd < lines[match.lineNumber].length ? '...' : '';

      response.appendResponseLine('');
      response.appendResponseLine('Context:');
      response.appendResponseLine('```javascript');
      response.appendResponseLine(`${prefix}${preview}${suffix}`);
      response.appendResponseLine('```');
      response.setStructuredContent({
        breakpointId: breakpointInfo.breakpointId,
        url,
        lineNumber: match.lineNumber + 1,
        columnNumber,
        condition: condition ?? null,
      });
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Failed to set breakpoint', error);
    }
  },
});

/**
 * Set XHR/Fetch breakpoint.
 */
export const breakOnXhr = defineTool({
  name: 'break_on_xhr',
  description:
    'Sets a URL-substring breakpoint for a future XHR/Fetch when runtime request arguments, local variables, or payload construction must be inspected. For an already captured request, call get_request_initiator first because it is non-pausing; use this only when that evidence is insufficient. Set it before reproducing the user action—it does not inspect past traffic—then call get_paused_info/evaluate_script and finally step or resume. The URL pattern identifies this breakpoint for list_breakpoints and remove_breakpoint(action="remove_xhr").',
  annotations: {
    title: 'Break on XHR',
    category: ToolCategory.REVERSE_ENGINEERING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  schema: {
    url: zod
      .string()
      .describe(
        'Case-sensitive URL substring matched against future XHR/Fetch requests. Prefer a narrow endpoint path from list_network_requests; retain the exact string to remove the breakpoint later.',
      ),
  },
  handler: async (request, response, context) => {
    const debugger_ = context.debuggerContext;

    requireDebuggerEnabled(debugger_);

    const {url} = request.params;
    const client = debugger_.getClient();

    if (!client) {
      throw new ToolError(
        'PRECONDITION_FAILED',
        'Debugger client not available.',
      );
    }

    try {
      await debugger_.setXHRBreakpoint(url);
      response.appendResponseLine(
        `✅ XHR breakpoint set for URLs containing: "${url}"`,
      );
      response.appendResponseLine(
        'Debugger will pause when a matching XHR/Fetch request is made.',
      );
      response.setStructuredContent({kind: 'xhr', urlPattern: url});
    } catch (error) {
      throwToolFailure('CDP_ERROR', 'Failed to set XHR breakpoint', error);
    }
  },
});
