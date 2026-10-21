export const config = {
  // Configuração da Evolution API
  evolutionApi: {
    baseUrl: process.env.EVOLUTION_API_URL || "https://seu-servidor-evolution-api.com",
    apiKey: process.env.EVOLUTION_API_KEY || "sua-chave-api",
    instanceId: process.env.EVOLUTION_API_INSTANCE || "instancia-padrao"
  },
  // Configuração do servidor MCP
  mcp: {
    name: "Evolution API Server",
    version: "1.0.0"
  }
}; 