#!/usr/bin/env node

import { startServer, startWebSocketServer } from './index.js';
import { config } from './config.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Exibe informações sobre o MCP Server
console.log(`
╔════════════════════════════════════════════════════╗
║            MCP SERVER PARA EVOLUTION API           ║
╠════════════════════════════════════════════════════╣
║ Versão: ${config.mcp.version}                             ║
║ Instância: ${config.evolutionApi.instanceId}        ║
╚════════════════════════════════════════════════════╝
`);

// Inicia os servidores
const enableWebSocket = process.env.ENABLE_WEBSOCKET === 'true';

async function init() {
  try {
    // Sempre inicia o servidor STDIO
    await startServer();
    
    // Inicia o servidor WebSocket se habilitado
    if (enableWebSocket) {
      const port = process.env.PORT || 3000;
      await startWebSocketServer(Number(port));
    }
  } catch (error) {
    console.error('Erro ao iniciar servidores MCP:', error);
    process.exit(1);
  }
}

init(); 