import { randomUUID } from 'node:crypto';
import { WebSocket, WebSocketServer } from 'ws';
import type { AddressInfo } from 'node:net';
import type { PageHelloMessage, PageInfo, RPCRequestMessage } from './protocol.js';
import { isPageHello, isRPCResponse } from './protocol.js';

interface PageSession {
  pageId: string;
  info: PageInfo;
  connectedAt: number;
  lastSeen: number;
  socket: WebSocket;
}

interface PendingRequest {
  pageId: string;
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: NodeJS.Timeout;
}

export interface PageSummary extends PageInfo {
  pageId: string;
  connectedAt: number;
  lastSeen: number;
}

export class VConsoleBridge {
  private readonly server: WebSocketServer;
  private readonly token: string;
  private readonly pages = new Map<string, PageSession>();
  private readonly pending = new Map<string, PendingRequest>();

  constructor(host: string, port: number, token = '') {
    this.token = token;
    this.server = new WebSocketServer({
      host,
      port,
      maxPayload: 4 * 1024 * 1024,
      perMessageDeflate: false,
    });
    this.server.on('connection', (socket) => this.handleConnection(socket));
  }

  public get port(): number {
    const address = this.server.address() as AddressInfo | null;
    return address?.port || 0;
  }

  public waitUntilListening(): Promise<void> {
    if (this.server.address()) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      this.server.once('listening', resolve);
      this.server.once('error', reject);
    });
  }

  public listPages(): PageSummary[] {
    return Array.from(this.pages.values()).map((page) => ({
      pageId: page.pageId,
      ...page.info,
      connectedAt: page.connectedAt,
      lastSeen: page.lastSeen,
    }));
  }

  public request(
    pageId: string | undefined,
    method: RPCRequestMessage['method'],
    params: Record<string, unknown>,
    timeout = 8000,
  ): Promise<unknown> {
    const page = this.resolvePage(pageId);
    const id = randomUUID();
    const message: RPCRequestMessage = {
      v: 1,
      id,
      type: 'rpc.request',
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('The mobile page did not respond before the timeout.'));
      }, timeout);
      this.pending.set(id, { pageId: page.pageId, resolve, reject, timer });
      page.socket.send(JSON.stringify(message), (error) => {
        if (!error) {
          return;
        }
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error);
      });
    });
  }

  public close(): Promise<void> {
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(new Error('The vConsole MCP server is shutting down.'));
    }
    this.pending.clear();
    for (const page of this.pages.values()) {
      page.socket.terminate();
    }
    this.pages.clear();

    return new Promise((resolve) => {
      this.server.close(() => resolve());
    });
  }

  private handleConnection(socket: WebSocket) {
    let pageId = '';

    socket.on('message', (raw) => {
      let message: unknown;
      try {
        message = JSON.parse(raw.toString());
      } catch {
        return;
      }

      if (isPageHello(message)) {
        if (this.token && message.token !== this.token) {
          socket.close(1008, 'Invalid pairing token.');
          return;
        }
        if (pageId && pageId !== message.pageId) {
          socket.close(1008, 'A socket can register only one page.');
          return;
        }
        pageId = message.pageId;
        this.registerPage(socket, message);
        return;
      }
      if (pageId && isRPCResponse(message)) {
        this.resolveRequest(pageId, message);
      }
    });

    socket.on('close', () => {
      const page = this.pages.get(pageId);
      if (page?.socket === socket) {
        this.pages.delete(pageId);
        this.rejectPageRequests(pageId);
      }
    });
  }

  private registerPage(socket: WebSocket, message: PageHelloMessage) {
    const previous = this.pages.get(message.pageId);
    if (previous && previous.socket !== socket) {
      previous.socket.close();
    }
    const now = Date.now();
    this.pages.set(message.pageId, {
      pageId: message.pageId,
      info: message.payload,
      connectedAt: now,
      lastSeen: now,
      socket,
    });
  }

  private resolveRequest(pageId: string, message: { id: string; result?: unknown; error?: string }) {
    const request = this.pending.get(message.id);
    if (!request || request.pageId !== pageId) {
      return;
    }
    clearTimeout(request.timer);
    this.pending.delete(message.id);
    const page = this.pages.get(pageId);
    if (page) {
      page.lastSeen = Date.now();
    }
    if (message.error) {
      request.reject(new Error(message.error));
    } else {
      request.resolve(message.result);
    }
  }

  private resolvePage(pageId?: string): PageSession {
    if (pageId) {
      const page = this.pages.get(pageId);
      if (!page) {
        throw new Error(`No connected page found for pageId ${pageId}.`);
      }
      return page;
    }
    if (this.pages.size === 0) {
      throw new Error('No mobile page is connected. Open the test page and connect vConsole first.');
    }
    if (this.pages.size > 1) {
      throw new Error('Multiple pages are connected. Call list_pages and provide pageId.');
    }
    return this.pages.values().next().value as PageSession;
  }

  private rejectPageRequests(pageId: string) {
    if (!pageId) {
      return;
    }
    for (const [id, request] of this.pending.entries()) {
      if (request.pageId !== pageId) {
        continue;
      }
      clearTimeout(request.timer);
      request.reject(new Error('The mobile page disconnected.'));
      this.pending.delete(id);
    }
  }
}
