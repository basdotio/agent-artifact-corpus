/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {isUtf8} from 'node:buffer';
import path from 'node:path';

import type {DebuggerContext} from '../DebuggerContext.js';
import {openLocalFileReadAllowed} from '../LocalFileAccess.js';
import {zod} from '../third_party/index.js';
import type {JSHandle} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';

import {ToolCategory} from './categories.js';
import {createToolOutputSchema, defineTool} from './ToolDefinition.js';

// Default script evaluation timeout in milliseconds (30 seconds)
const DEFAULT_SCRIPT_TIMEOUT = 30000;
const INLINE_EVAL_RESULT_LIMIT = 8192;
const MAX_LOCAL_FILE_BYTES = 10 * 1024 * 1024;
const MAX_PAUSED_LOCAL_FILE_BYTES = 512 * 1024;

interface LocalFileInput {
  path: string;
  name: string;
  size: number;
  base64: string;
  text?: string;
}

async function loadLocalFile(
  filePath: string,
  signal?: AbortSignal,
): Promise<LocalFileInput> {
  signal?.throwIfAborted();
  if (filePath.startsWith('file://')) {
    throw new ToolError(
      'INVALID_ARGUMENT',
      'localFilePath must be an absolute path, not a file:// URL.',
    );
  }

  if (filePath.startsWith('~')) {
    throw new ToolError(
      'INVALID_ARGUMENT',
      'localFilePath must be an absolute path; ~ is not expanded.',
    );
  }

  if (!path.isAbsolute(filePath)) {
    throw new ToolError(
      'INVALID_ARGUMENT',
      'localFilePath must be an absolute path.',
    );
  }

  if (/[{}[\]*?]/.test(filePath)) {
    throw new ToolError(
      'INVALID_ARGUMENT',
      'localFilePath must point to one file; globs are not supported.',
    );
  }

  let opened: Awaited<ReturnType<typeof openLocalFileReadAllowed>>;
  try {
    opened = await openLocalFileReadAllowed(filePath);
  } catch (error) {
    if (error instanceof ToolError) {
      throw error;
    }
    throw new ToolError(
      'IO_ERROR',
      `Could not resolve localFilePath: ${error instanceof Error ? error.message : String(error)}`,
      {cause: error},
    );
  }
  const {handle, resolvedPath, stat} = opened;
  let data: Buffer;
  try {
    signal?.throwIfAborted();

    if (stat.size > MAX_LOCAL_FILE_BYTES) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        `localFilePath is too large (${stat.size} bytes). Maximum supported size is ${MAX_LOCAL_FILE_BYTES} bytes.`,
      );
    }

    const buffer = Buffer.allocUnsafe(MAX_LOCAL_FILE_BYTES + 1);
    let offset = 0;
    while (offset < buffer.length) {
      signal?.throwIfAborted();
      const {bytesRead} = await handle.read(
        buffer,
        offset,
        buffer.length - offset,
        offset,
      );
      if (bytesRead === 0) {
        break;
      }
      offset += bytesRead;
    }
    if (offset > MAX_LOCAL_FILE_BYTES) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        `localFilePath exceeds the maximum supported size of ${MAX_LOCAL_FILE_BYTES} bytes.`,
      );
    }
    data = buffer.subarray(0, offset);
  } catch (error) {
    if (
      error instanceof ToolError ||
      (error instanceof Error && error.name === 'AbortError')
    ) {
      throw error;
    }
    throw new ToolError('IO_ERROR', 'Could not read localFilePath.', {
      cause: error,
    });
  } finally {
    await handle.close();
  }
  const localFile: LocalFileInput = {
    path: resolvedPath,
    name: path.basename(resolvedPath),
    size: data.length,
    base64: data.toString('base64'),
  };

  if (isUtf8(data)) {
    localFile.text = data.toString('utf8');
  }

  return localFile;
}

async function runCancellableEvaluation<T>(
  signal: AbortSignal | undefined,
  debugger_: DebuggerContext,
  operation: () => Promise<T>,
): Promise<T> {
  const terminate = () => {
    void debugger_.terminateExecution().catch(() => undefined);
  };
  signal?.throwIfAborted();
  signal?.addEventListener('abort', terminate, {once: true});
  try {
    return await operation();
  } finally {
    signal?.removeEventListener('abort', terminate);
  }
}

export const evaluateScript = defineTool({
  name: 'evaluate_script',
  description:
    "Evaluates one focused JavaScript function for DOM/page state, web storage, page-defined globals, a paused-frame expression, or browser-side processing of one local file. Use it when those runtime values are the goal and no narrower evidence tool applies. Do not use document.cookie or page evaluation to investigate HttpOnly/Secure cookies, Set-Cookie provenance, or captured HTTP evidence; use list_network_requests with cookieName/reqid, and use search_in_sources/get_script_source for source discovery. While running, evaluation uses the selected frame's isolated world by default or its page main world with mainWorld=true; while paused, it always uses the chosen call frame and ignores mainWorld. Call get_paused_info before paused evaluation, then step or resume when finished. Arbitrary code can change page/external state and requires confirm=true; inline results are bounded, so use outputFile for exact large or binary results.",
  annotations: {
    title: 'Evaluate Script',
    category: ToolCategory.DEBUGGING,
    readOnlyHint: false,
    destructiveHint: true,
    openWorldHint: true,
  },
  capabilities: ['debugger'],
  timeoutMs: DEFAULT_SCRIPT_TIMEOUT,
  outputSchema: createToolOutputSchema({
    resultType: zod.string().optional(),
    value: zod.unknown().optional(),
    filename: zod.string().optional(),
    byteLength: zod.number().int().optional(),
    charLength: zod.number().int().optional(),
    truncated: zod.boolean().optional(),
  }),
  schema: {
    confirm: zod
      .boolean()
      .default(false)
      .describe(
        'Must be true to authorize this exact arbitrary-code evaluation, which may mutate page state, send requests, or cause external side effects. Prefer a read-only expression when inspection is sufficient.',
      ),
    function: zod
      .string()
      .describe(
        'JavaScript function declaration invoked by the tool, for example `() => document.title` or `async () => await Promise.resolve(location.href)`. Return JSON-serializable data; ArrayBuffer/typed arrays require outputFile for exact bytes. With localFilePath, accept `async ({localFile}) => ...` and read localFile.text for UTF-8 or localFile.base64 for exact bytes. Keep the function focused; use mainWorld=true only when page-defined globals are required.',
      ),
    mainWorld: zod
      .boolean()
      .optional()
      .default(false)
      .describe(
        "Running-page mode only: false uses the selected frame's isolated context; true uses that frame's page main world to access application-defined globals. When execution is paused, evaluation always targets frameIndex and this option is ignored.",
      ),
    frameIndex: zod
      .number()
      .int()
      .optional()
      .describe(
        'Paused mode only: zero-based call frame from get_paused_info (default: top frame). The index and its callFrameId expire after any step or resume.',
      ),
    outputFile: zod
      .string()
      .optional()
      .describe(
        'Save the exact result locally instead of returning bounded inline content. JSON-serializable values are written as JSON text and ArrayBuffer/typed arrays as raw bytes; the returned filename is resolved and subject to --allowedRoots.',
      ),
    confirmOverwrite: zod
      .boolean()
      .default(false)
      .describe(
        'Set true only to authorize replacing an existing outputFile. A new file does not require overwrite confirmation.',
      ),
    localFilePath: zod
      .string()
      .optional()
      .describe(
        'Absolute path to one host file passed as localFile; the browser never reads the path directly. Running-page input is limited to 10 MiB, while paused call-frame input remains limited to 512 KiB. Relative paths, file:// URLs, globs, ~, and directories are rejected, access is subject to --allowedRoots, and file contents may expose sensitive host data.',
      ),
  },
  handler: async (request, response, context) => {
    if (!request.params.confirm) {
      throw new ToolError(
        'CONFIRMATION_REQUIRED',
        'evaluate_script requires confirm=true because the supplied function can cause page and external side effects.',
      );
    }
    const {
      function: fnString,
      mainWorld,
      frameIndex,
      outputFile,
      localFilePath,
    } = request.params;
    const localFile = localFilePath
      ? await loadLocalFile(localFilePath, request.signal)
      : undefined;

    if (localFile) {
      response.appendResponseLine(
        `Loaded local file ${localFile.path} (${localFile.size} bytes).`,
      );
    }

    const callExpression = localFile
      ? `(${fnString})(${JSON.stringify({localFile})})`
      : `(${fnString})()`;

    const wrapResultAsync = () => `async () => {
      try {
        const result = await ${callExpression};
        if (result instanceof ArrayBuffer || ArrayBuffer.isView(result)) {
          const buffer = result.buffer || result;
          const bytes = new Uint8Array(buffer, result.byteOffset || 0, result.byteLength || result.length);
          if (typeof FileReader !== 'undefined' && typeof Blob !== 'undefined') {
            const blob = new Blob([bytes]);
            return await new Promise((resolve) => {
              const reader = new FileReader();
              reader.onload = () => resolve(JSON.stringify({ type: 'base64', data: reader.result.split(',')[1] }));
              reader.readAsDataURL(blob);
            });
          } else {
            let binary = '';
            const chunkSize = 8192;
            for (let i = 0; i < bytes.length; i += chunkSize) {
              binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunkSize)));
            }
            return JSON.stringify({ type: 'base64', data: btoa(binary) });
          }
        }
        return JSON.stringify({ type: 'json', data: JSON.stringify(result) });
      } catch (e) {
        return JSON.stringify({ type: 'error', data: e.message || String(e) });
      }
    }`;

    const wrapPausedResult = () => `() => {
      try {
        const result = ${callExpression};
        if (result instanceof Promise) {
          return result;
        }
        if (result instanceof ArrayBuffer || ArrayBuffer.isView(result)) {
          const buffer = result.buffer || result;
          const bytes = new Uint8Array(buffer, result.byteOffset || 0, result.byteLength || result.length);
          let binary = '';
          const chunkSize = 8192;
          for (let i = 0; i < bytes.length; i += chunkSize) {
            binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunkSize)));
          }
          return JSON.stringify({ type: 'base64', data: btoa(binary) });
        }
        return JSON.stringify({ type: 'json', data: JSON.stringify(result) });
      } catch (e) {
        return JSON.stringify({ type: 'error', data: e.message || String(e) });
      }
    }`;

    const handleEvalResult = async (rawString: string) => {
      let parsed: {type: string; data: string};
      try {
        parsed = JSON.parse(rawString);
      } catch {
        parsed = {type: 'json', data: rawString};
      }

      if (parsed.type === 'error') {
        throw new ToolError(
          'CDP_ERROR',
          `Script evaluation error: ${parsed.data}`,
        );
      }

      if (outputFile) {
        if (parsed.type === 'base64') {
          const binaryData = Buffer.from(parsed.data, 'base64');
          const res = await context.saveFile(binaryData, outputFile, {
            confirmOverwrite: request.params.confirmOverwrite,
          });
          response.appendResponseLine(
            `Saved binary memory dump to ${res.filename} (${binaryData.length} bytes).`,
          );
          response.setStructuredContent({
            resultType: 'binary_file',
            filename: res.filename,
            byteLength: binaryData.length,
          });
        } else {
          const textData = new TextEncoder().encode(
            parsed.data === undefined ? 'undefined' : parsed.data,
          );
          const res = await context.saveFile(textData, outputFile, {
            confirmOverwrite: request.params.confirmOverwrite,
          });
          response.appendResponseLine(
            `Saved JSON result to ${res.filename} (${textData.length} bytes).`,
          );
          response.setStructuredContent({
            resultType: 'json_file',
            filename: res.filename,
            byteLength: textData.length,
          });
        }
        return;
      }

      response.appendResponseLine('Script ran on page and returned:');
      if (parsed.type === 'base64') {
        const byteLength = Buffer.from(parsed.data, 'base64').length;
        response.appendResponseLine(
          `[Binary Data: ${byteLength} bytes. Use outputFile to save to disk.]`,
        );
        response.setStructuredContent({resultType: 'binary', byteLength});
      } else {
        const data = parsed.data ?? 'undefined';
        const truncated = data.length > INLINE_EVAL_RESULT_LIMIT;
        if (truncated) {
          response.appendResponseLine(
            `Result is ${data.length} chars; inline output is truncated to ${INLINE_EVAL_RESULT_LIMIT} chars. Re-run with outputFile to save the exact result.`,
          );
        }
        response.appendResponseLine('```json');
        response.appendResponseLine(
          truncated
            ? `${data.slice(0, INLINE_EVAL_RESULT_LIMIT)}... <truncated ${data.length - INLINE_EVAL_RESULT_LIMIT} chars>`
            : data,
        );
        response.appendResponseLine('```');
        let value: unknown = data;
        try {
          value = JSON.parse(data);
        } catch {
          // Keep non-JSON values as their serialized string.
        }
        response.setStructuredContent({
          resultType: 'json',
          value: truncated
            ? `${data.slice(0, INLINE_EVAL_RESULT_LIMIT)}...`
            : value,
          truncated,
          charLength: data.length,
        });
      }
    };

    const debugger_ = context.debuggerContext;
    if (debugger_.isEnabled() && debugger_.isPaused()) {
      if (localFile && localFile.size > MAX_PAUSED_LOCAL_FILE_BYTES) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          `localFilePath is too large for paused call-frame evaluation (${localFile.size} bytes). Maximum supported paused size is ${MAX_PAUSED_LOCAL_FILE_BYTES} bytes.`,
        );
      }

      const pausedState = debugger_.getPausedState();
      const frameIdx = frameIndex ?? 0;
      if (frameIdx < 0 || frameIdx >= pausedState.callFrames.length) {
        throw new Error(
          `frameIndex ${frameIdx} is out of range (0-${pausedState.callFrames.length - 1})`,
        );
      }
      const callFrameId = pausedState.callFrames[frameIdx]?.callFrameId;
      if (callFrameId) {
        const result = await debugger_.evaluateSettledPromiseOnCallFrame(
          callFrameId,
          `(${wrapPausedResult()})()`,
        );

        if (result.exceptionDetails) {
          const errMsg =
            result.exceptionDetails.exception?.description ||
            result.exceptionDetails.text;
          throw new ToolError(
            'CDP_ERROR',
            `Script evaluation error: ${errMsg}`,
          );
        }

        if (
          result.settledPromise &&
          (result.result.subtype === 'arraybuffer' ||
            result.result.subtype === 'typedarray')
        ) {
          throw new ToolError(
            'PRECONDITION_FAILED',
            'Paused async binary results cannot be serialized safely. Resume execution or return JSON-serializable data.',
          );
        }
        const settledValue =
          result.settledPromise && result.result.objectId
            ? await debugger_.materializeRemoteObject(result.result)
            : result.result.value;
        const rawResult = result.settledPromise
          ? JSON.stringify({
              type: 'json',
              data: JSON.stringify(settledValue),
            })
          : (settledValue as string);
        await handleEvalResult(rawResult);
        return;
      }
    }

    if (mainWorld) {
      const frame = context.getSelectedFrame();
      const result = await runCancellableEvaluation(
        request.signal,
        debugger_,
        async () => {
          // Patchright defaults evaluate() to its utility world. Its third
          // parameter selects the frame's main world directly. This preserves
          // the selected iframe execution context and avoids the CSP-blocked
          // inline <script> bridge previously used here.
          return await frame.evaluate(
            `(${wrapResultAsync()})()`,
            undefined,
            false,
          );
        },
      );

      await handleEvalResult(result as string);
      return;
    }

    let fnHandle: JSHandle<unknown> | undefined;
    try {
      const frame = context.getSelectedFrame();
      fnHandle = await runCancellableEvaluation(request.signal, debugger_, () =>
        frame.evaluateHandle(`(${wrapResultAsync()})`),
      );
      await context.waitForEventsAfterAction(async () => {
        const result = await runCancellableEvaluation(
          request.signal,
          debugger_,
          () =>
            frame.evaluate(async fn => {
              // @ts-expect-error no types.
              return await fn();
            }, fnHandle),
        );
        await handleEvalResult(result as string);
      });
    } finally {
      if (fnHandle) {
        await fnHandle.dispose();
      }
    }
  },
});
