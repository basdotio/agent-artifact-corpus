export interface PageInfo {
  url: string;
  title: string;
  userAgent: string;
}

export interface PageHelloMessage {
  v: 1;
  type: 'page.hello';
  pageId: string;
  ts: number;
  payload: PageInfo;
  token?: string;
}

export interface RPCResponseMessage {
  v: 1;
  id: string;
  type: 'rpc.response';
  result?: unknown;
  error?: string;
}

export interface RPCRequestMessage {
  v: 1;
  id: string;
  type: 'rpc.request';
  method: 'console.list' | 'network.list' | 'runtime.evaluate';
  params: Record<string, unknown>;
}

export function isPageHello(value: unknown): value is PageHelloMessage {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const message = value as Partial<PageHelloMessage>;
  return message.v === 1
    && message.type === 'page.hello'
    && typeof message.pageId === 'string'
    && !!message.pageId
    && !!message.payload
    && typeof message.payload.url === 'string';
}

export function isRPCResponse(value: unknown): value is RPCResponseMessage {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const message = value as Partial<RPCResponseMessage>;
  return message.v === 1
    && message.type === 'rpc.response'
    && typeof message.id === 'string';
}
