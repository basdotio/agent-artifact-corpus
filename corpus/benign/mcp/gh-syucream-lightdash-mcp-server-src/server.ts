import express, { type Request, type Response } from 'express';
import { type StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';

export function startHttpServer(
  httpTransport: StreamableHTTPServerTransport,
  port: number
): void {
  const app = express();
  app.use(express.json());

  app.all('/mcp', async (req: Request, res: Response) => {
    try {
      await httpTransport.handleRequest(req, res, req.body);
    } catch (error: unknown) {
      console.error(`Error handling ${req.method} /mcp request:`, error);
      if (!res.headersSent) {
        const message =
          error instanceof Error ? error.message : 'Internal Server Error';
        res
          .status(500)
          .json({ error: 'Internal Server Error', details: message });
      }
    }
  });

  app
    .listen(port, () => {})
    .on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        console.error(
          `Port ${port} is already in use. Please use a different port.`
        );
      } else {
        console.error('Failed to start Express server:', err);
      }
      process.exit(1);
    });
}
