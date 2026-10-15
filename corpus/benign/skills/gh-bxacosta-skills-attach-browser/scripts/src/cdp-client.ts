/**
 * Minimal Chrome DevTools Protocol client over ONE browser-level WebSocket.
 *
 * Design rules (each one avoids a real bug seen in existing tools):
 * - One socket for everything. Page sessions are multiplexed on it with
 *   `Target.attachToTarget({ flatten: true })` + `sessionId`. Every extra
 *   socket to an approval-mode browser means another "Allow?" dialog.
 * - The connect wait is unbounded by default: while the dialog is on screen the
 *   WebSocket handshake simply does not complete. Aborting and retrying pops a
 *   NEW dialog, so waiting is the correct behaviour.
 * - Per-command timeouts are separate from the connect wait.
 * - When the socket dies, every pending call is rejected (no hanging promises).
 *
 * Types come from the `devtools-protocol` package (types only, zero runtime).
 */

import type { ProtocolMapping } from "devtools-protocol/types/protocol-mapping.js";

type Commands = ProtocolMapping.Commands;
type Events = ProtocolMapping.Events;
export type CommandName = keyof Commands;
export type EventName = keyof Events;
export type CommandParams<M extends CommandName> = Commands[M]["paramsType"][0];
export type CommandResult<M extends CommandName> = Commands[M]["returnType"];
export type EventParams<E extends EventName> = Events[E][0];

export class CdpError extends Error {
  constructor(
    readonly method: string,
    readonly code: number,
    message: string,
  ) {
    super(`${method}: ${message} (CDP ${code})`);
    this.name = "CdpError";
  }
}

export class CdpClosedError extends Error {
  constructor(
    readonly code: number,
    readonly reason: string,
  ) {
    super(`CDP connection closed (code ${code}${reason ? `: ${reason}` : ""})`);
    this.name = "CdpClosedError";
  }
}

export interface ConnectOptions {
  /**
   * Max time to wait for the handshake, i.e. for the user to click "Allow".
   * 0 = wait forever (recommended for interactive use). Default: 0.
   */
  connectTimeoutMs?: number;
  /** Called once the socket is being opened, so the UI can say "click Allow". */
  onWaitingForApproval?: () => void;
}

export interface SendOptions {
  /** Route the command to an attached target (flatten mode). */
  sessionId?: string;
  /** Per-command timeout. Default 30 s. 0 = none. */
  timeoutMs?: number;
}

interface Pending {
  method: string;
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer?: ReturnType<typeof setTimeout>;
}

type Listener = (params: any, sessionId?: string) => void;

export class CdpClient {
  #ws: WebSocket;
  #nextId = 0;
  #pending = new Map<number, Pending>();
  #listeners = new Map<string, Set<Listener>>();
  #closed: CdpClosedError | null = null;
  #closeHandlers = new Set<(error: CdpClosedError) => void>();

  private constructor(ws: WebSocket) {
    this.#ws = ws;
    ws.onmessage = (ev) => this.#onMessage(String(ev.data));
    ws.onclose = (ev) => this.#onClose(ev.code, ev.reason);
  }

  /** Open the browser-level WebSocket. Resolves once the user has approved. */
  static connect(endpoint: string, opts: ConnectOptions = {}): Promise<CdpClient> {
    const { connectTimeoutMs = 0, onWaitingForApproval } = opts;
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(endpoint);
      onWaitingForApproval?.();

      const timer =
        connectTimeoutMs > 0
          ? setTimeout(() => {
              ws.close();
              reject(new Error(`Timed out after ${connectTimeoutMs} ms waiting for the connection to be approved.`));
            }, connectTimeoutMs)
          : undefined;

      ws.onopen = () => {
        clearTimeout(timer);
        resolve(new CdpClient(ws));
      };
      // Before open, an error/close means refused: Deny clicked, browser gone,
      // wrong path, or the port belongs to something else.
      ws.onerror = () => {};
      ws.onclose = (ev) => {
        clearTimeout(timer);
        reject(new CdpClosedError(ev.code, ev.reason || "connection refused or denied"));
      };
    });
  }

  get isOpen(): boolean {
    return this.#closed === null && this.#ws.readyState === WebSocket.OPEN;
  }

  send<M extends CommandName>(
    method: M,
    // Params are optional when the command takes none or all its fields are optional.
    ...args: [CommandParams<M>] extends [undefined]
      ? [params?: undefined, opts?: SendOptions]
      : {} extends NonNullable<CommandParams<M>>
      ? [params?: CommandParams<M>, opts?: SendOptions]
      : [params: CommandParams<M>, opts?: SendOptions]
  ): Promise<CommandResult<M>> {
    const [params, opts = {}] = args;
    if (this.#closed) return Promise.reject(this.#closed);

    const id = ++this.#nextId;
    const { sessionId, timeoutMs = 30_000 } = opts;

    return new Promise<CommandResult<M>>((resolve, reject) => {
      const entry: Pending = { method, resolve: resolve as (v: unknown) => void, reject };
      if (timeoutMs > 0) {
        entry.timer = setTimeout(() => {
          this.#pending.delete(id);
          reject(new Error(`${method}: no response after ${timeoutMs} ms`));
        }, timeoutMs);
      }
      this.#pending.set(id, entry);
      this.#ws.send(JSON.stringify({ id, method, params: params ?? {}, ...(sessionId && { sessionId }) }));
    });
  }

  /**
   * Subscribe to an event. Pass `sessionId` to only receive events from that
   * target; omit it to receive the event from every session. Returns unsubscribe.
   */
  on<E extends EventName>(
    event: E,
    handler: (params: EventParams<E>, sessionId?: string) => void,
    sessionId?: string,
  ): () => void {
    const key = sessionId ? `${event}\u0000${sessionId}` : event;
    let set = this.#listeners.get(key);
    if (!set) this.#listeners.set(key, (set = new Set()));
    set.add(handler as Listener);
    return () => set!.delete(handler as Listener);
  }

  /** Resolve with the first matching event (optionally filtered by predicate). */
  waitFor<E extends EventName>(
    event: E,
    opts: { sessionId?: string; timeoutMs?: number; filter?: (p: EventParams<E>) => boolean } = {},
  ): Promise<EventParams<E>> {
    const { sessionId, timeoutMs = 30_000, filter } = opts;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        off();
        reject(new Error(`Timed out waiting for ${event}`));
      }, timeoutMs);
      const off = this.on(
        event,
        (params) => {
          if (filter && !filter(params)) return;
          clearTimeout(timer);
          off();
          resolve(params);
        },
        sessionId,
      );
    });
  }

  /** Called when the connection drops for any reason (user closed browser, revoked, etc). */
  onClose(handler: (error: CdpClosedError) => void): () => void {
    this.#closeHandlers.add(handler);
    return () => this.#closeHandlers.delete(handler);
  }

  /**
   * Close OUR connection. This never closes the user's browser — that would be
   * `Browser.close`, which you must never send to a browser you did not launch.
   */
  close(): void {
    this.#ws.close();
  }

  #onMessage(raw: string): void {
    let msg: any;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }

    if (typeof msg.id === "number") {
      const entry = this.#pending.get(msg.id);
      if (!entry) return;
      this.#pending.delete(msg.id);
      clearTimeout(entry.timer);
      // Responses do not echo `method`; that is why it is kept in the pending entry.
      if (msg.error) entry.reject(new CdpError(entry.method, msg.error.code, msg.error.message));
      else entry.resolve(msg.result);
      return;
    }

    if (typeof msg.method === "string") {
      this.#emit(msg.method, msg.params, msg.sessionId);
      if (msg.sessionId) this.#emit(`${msg.method}\u0000${msg.sessionId}`, msg.params, msg.sessionId);
    }
  }

  #emit(key: string, params: unknown, sessionId?: string): void {
    for (const listener of this.#listeners.get(key) ?? []) {
      try {
        listener(params, sessionId);
      } catch (error) {
        console.error(`CDP listener for ${key} threw:`, error);
      }
    }
  }

  #onClose(code: number, reason: string): void {
    if (this.#closed) return;
    this.#closed = new CdpClosedError(code, reason);
    for (const entry of this.#pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(this.#closed);
    }
    this.#pending.clear();
    for (const handler of this.#closeHandlers) handler(this.#closed);
  }
}
