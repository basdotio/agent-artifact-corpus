/**
 * Minimal ambient type for the DSH web server service (dsh-host-webserver).
 *
 * The bridge package does not depend on dsh-host-webserver; in the web
 * profile the service is injected by the DSH bundle. This declaration keeps
 * the management-route integration type-checked without adding a dependency.
 */
import type { IncomingMessage, ServerResponse } from 'node:http';

declare module '@deepseek-ai/cordis' {
  interface Context {
    /** DSH web server (web profile only). */
    webServer?: {
      register(route: {
        kind: 'exact' | 'prefix';
        path: string;
        handler: (req: IncomingMessage, res: ServerResponse) => void | Promise<void>;
      }): () => void;
    };
  }
}
