/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

interface RunAbortableOperationOptions {
  timeoutMs: number;
  timeoutMessage: string;
  signal?: AbortSignal;
}

type SettledResult<T> =
  | {status: 'fulfilled'; value: T}
  | {status: 'rejected'; reason: unknown};

function abortError(signal: AbortSignal): Error {
  if (signal.reason instanceof Error) {
    return signal.reason;
  }
  return new Error(
    signal.reason === undefined
      ? 'Tool call was cancelled'
      : String(signal.reason),
  );
}

/**
 * Runs a tool operation with a linked cancellation signal.
 *
 * Cancellation is observable immediately by the operation, but this function
 * does not settle until the underlying promise has settled. Callers can
 * therefore release exclusivity locks in a finally block without allowing a
 * timed-out operation to continue concurrently with the next tool call.
 */
export async function runAbortableOperation<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  options: RunAbortableOperationOptions,
): Promise<T> {
  const controller = new AbortController();
  const externalSignal = options.signal;

  const abortFromExternalSignal = () => {
    controller.abort(abortError(externalSignal!));
  };
  if (externalSignal?.aborted) {
    abortFromExternalSignal();
  } else {
    externalSignal?.addEventListener('abort', abortFromExternalSignal, {
      once: true,
    });
  }

  const timeoutId = setTimeout(() => {
    controller.abort(new Error(options.timeoutMessage));
  }, options.timeoutMs);

  const settled: Promise<SettledResult<T>> = Promise.resolve()
    .then(() => {
      controller.signal.throwIfAborted();
      return operation(controller.signal);
    })
    .then(
      value => ({status: 'fulfilled', value}) as const,
      reason => ({status: 'rejected', reason}) as const,
    );

  const aborted = new Promise<'aborted'>(resolve => {
    if (controller.signal.aborted) {
      resolve('aborted');
      return;
    }
    controller.signal.addEventListener('abort', () => resolve('aborted'), {
      once: true,
    });
  });

  try {
    const first = await Promise.race([settled, aborted]);
    if (first === 'aborted' || controller.signal.aborted) {
      // Drain the operation before returning so the caller can safely release
      // its mutex. Cancellable operations should react to the linked signal.
      if (first === 'aborted') {
        await settled;
      }
      throw abortError(controller.signal);
    }

    if (first.status === 'rejected') {
      throw first.reason;
    }
    return first.value;
  } finally {
    clearTimeout(timeoutId);
    externalSignal?.removeEventListener('abort', abortFromExternalSignal);
  }
}
