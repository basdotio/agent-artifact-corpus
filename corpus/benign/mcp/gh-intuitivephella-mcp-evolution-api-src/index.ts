import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { WebSocketServerTransport } from "@modelcontextprotocol/sdk/server/websocket.js";
import { z } from "zod";
import { config } from "./config.js";
import { EvolutionApiService } from "./services/evolutionApiService.js";
import * as http from "http";
import { WebSocketServer } from "ws";
import "dotenv/config";

// Inicializa o serviço da Evolution API
const evolutionService = new EvolutionApiService();

// Cria o servidor MCP
const server = new McpServer({
  name: config.mcp.name,
  version: config.mcp.version
});

// ===== FERRAMENTAS PARA INFORMAÇÕES GERAIS =====

// Adiciona ferramenta para verificar o status da API
server.tool("getApiStatus",
  {},
  async () => {
    try {
      const apiInfo = await evolutionService.getApiInfo();
      return {
        content: [{ 
          type: "text", 
          text: `Evolution API v${apiInfo.version} está rodando. Status: ${apiInfo.status}` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao conectar à Evolution API: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== FERRAMENTAS PARA GESTÃO DE INSTÂNCIAS =====

// Adiciona ferramenta para verificar status da instância
server.tool("getInstanceStatus",
  {},
  async () => {
    try {
      const status = await evolutionService.getInstanceStatus();
      return {
        content: [{ 
          type: "text", 
          text: `Status da instância: ${status.state || "Desconhecido"}` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao verificar status da instância: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para definir presença
server.tool("setPresence",
  { 
    presence: z.enum(["available", "unavailable", "composing", "recording", "paused"])
      .describe("Status de presença para definir")
  },
  async ({ presence }) => {
    try {
      await evolutionService.setPresence(presence);
      return {
        content: [{ 
          type: "text", 
          text: `Presença definida como "${presence}" com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao definir presença: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para logout da instância
server.tool("logoutInstance",
  {},
  async () => {
    try {
      await evolutionService.logout();
      return {
        content: [{ 
          type: "text", 
          text: "Instância desconectada com sucesso." 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao desconectar instância: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para reiniciar a instância
server.tool("restartInstance",
  {},
  async () => {
    try {
      await evolutionService.restartInstance();
      return {
        content: [{ 
          type: "text", 
          text: "Instância reiniciada com sucesso." 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao reiniciar instância: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== FERRAMENTAS PARA MENSAGENS =====

// Adiciona ferramenta para enviar mensagem de texto
server.tool("sendTextMessage",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional (ex: 5511999999999)"),
    text: z.string().min(1).describe("Texto da mensagem a ser enviada"),
    options: z.object({
      delay: z.number().optional().describe("Atraso em milissegundos"),
      presence: z.enum(["composing", "recording", "paused"]).optional().describe("Presença a mostrar"),
      quotedMessageId: z.string().optional().describe("ID da mensagem a ser citada")
    }).optional().describe("Opções adicionais para o envio")
  },
  async ({ number, text, options }) => {
    try {
      const result = await evolutionService.sendTextMessage({ number, text, options });
      return {
        content: [{ 
          type: "text", 
          text: `Mensagem enviada com sucesso: ${result?.key?.id || "ID não disponível"}` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar mensagem: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar mídia
server.tool("sendMedia",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    url: z.string().url().describe("URL da mídia a ser enviada"),
    caption: z.string().optional().describe("Legenda para a mídia"),
    fileName: z.string().optional().describe("Nome do arquivo"),
    mediaType: z.enum(["image", "document", "video", "audio"]).describe("Tipo de mídia")
  },
  async ({ number, url, caption, fileName, mediaType }) => {
    try {
      const result = await evolutionService.sendMedia({
        number,
        media: {
          url,
          caption,
          fileName,
          mediaType
        }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Mídia enviada com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar mídia: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar mensagem de áudio
server.tool("sendAudio",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    url: z.string().url().describe("URL do áudio a ser enviado"),
    ptt: z.boolean().optional().describe("Se é uma mensagem de voz (Push-to-talk)")
  },
  async ({ number, url, ptt }) => {
    try {
      await evolutionService.sendAudio({
        number,
        audio: {
          url,
          ptt
        }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Áudio enviado com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar áudio: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar sticker
server.tool("sendSticker",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    url: z.string().url().describe("URL do sticker a ser enviado")
  },
  async ({ number, url }) => {
    try {
      await evolutionService.sendSticker({
        number,
        sticker: { url }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Sticker enviado com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar sticker: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar localização
server.tool("sendLocation",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    lat: z.number().describe("Latitude"),
    lng: z.number().describe("Longitude"),
    title: z.string().optional().describe("Título da localização"),
    address: z.string().optional().describe("Endereço da localização")
  },
  async ({ number, lat, lng, title, address }) => {
    try {
      await evolutionService.sendLocation({
        number,
        location: { lat, lng, title, address }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Localização enviada com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar localização: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar contato
server.tool("sendContact",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    fullName: z.string().min(1).describe("Nome completo do contato"),
    wuid: z.string().min(1).describe("ID do WhatsApp do contato"),
    phoneNumber: z.string().min(1).describe("Número de telefone do contato")
  },
  async ({ number, fullName, wuid, phoneNumber }) => {
    try {
      await evolutionService.sendContact({
        number,
        contact: { fullName, wuid, phoneNumber }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Contato enviado com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar contato: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para enviar enquete
server.tool("sendPoll",
  { 
    number: z.string().min(1).describe("Número do destinatário no formato internacional"),
    name: z.string().min(1).describe("Pergunta da enquete"),
    options: z.array(z.string()).min(2).describe("Opções de resposta"),
    multipleChoice: z.boolean().optional().describe("Permite múltiplas escolhas")
  },
  async ({ number, name, options, multipleChoice }) => {
    try {
      await evolutionService.sendPoll({
        number,
        poll: { name, options, multipleChoice }
      });
      return {
        content: [{ 
          type: "text", 
          text: `Enquete enviada com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao enviar enquete: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== FERRAMENTAS PARA GESTÃO DE CHAT =====

// Adiciona ferramenta para verificar número de WhatsApp
server.tool("checkWhatsAppNumber",
  { 
    phone: z.string().min(1).describe("Número a ser verificado no formato internacional (ex: 5511999999999)")
  },
  async ({ phone }) => {
    try {
      const result = await evolutionService.checkWhatsAppNumber({ phone });
      const isWhatsApp = result?.numbers?.[0]?.exists || false;
      return {
        content: [{ 
          type: "text", 
          text: isWhatsApp 
            ? `O número ${phone} é um número de WhatsApp válido.` 
            : `O número ${phone} não é um número de WhatsApp válido.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao verificar número: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para marcar mensagem como lida
server.tool("markMessageAsRead",
  { 
    messageId: z.string().min(1).describe("ID da mensagem a ser marcada como lida")
  },
  async ({ messageId }) => {
    try {
      await evolutionService.markMessageAsRead(messageId);
      return {
        content: [{ 
          type: "text", 
          text: `Mensagem marcada como lida com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao marcar mensagem como lida: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para arquivar chat
server.tool("archiveChat",
  { 
    number: z.string().min(1).describe("Número no formato internacional"),
    shouldArchive: z.boolean().default(true).describe("True para arquivar, false para desarquivar")
  },
  async ({ number, shouldArchive }) => {
    try {
      await evolutionService.archiveChat(number);
      return {
        content: [{ 
          type: "text", 
          text: shouldArchive 
            ? `Chat arquivado com sucesso.` 
            : `Chat desarquivado com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao ${shouldArchive ? 'arquivar' : 'desarquivar'} chat: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para excluir mensagem para todos
server.tool("deleteMessageForEveryone",
  { 
    messageId: z.string().min(1).describe("ID da mensagem a ser excluída")
  },
  async ({ messageId }) => {
    try {
      await evolutionService.deleteMessageForEveryone(messageId);
      return {
        content: [{ 
          type: "text", 
          text: `Mensagem excluída para todos com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao excluir mensagem: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== FERRAMENTAS DE PERFIL =====

// Adiciona ferramenta para atualizar nome do perfil
server.tool("updateProfileName",
  { 
    name: z.string().min(1).describe("Novo nome para o perfil")
  },
  async ({ name }) => {
    try {
      await evolutionService.updateProfileName(name);
      return {
        content: [{ 
          type: "text", 
          text: `Nome do perfil atualizado para "${name}" com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao atualizar nome do perfil: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para atualizar status do perfil
server.tool("updateProfileStatus",
  { 
    status: z.string().min(1).describe("Novo status para o perfil")
  },
  async ({ status }) => {
    try {
      await evolutionService.updateProfileStatus(status);
      return {
        content: [{ 
          type: "text", 
          text: `Status do perfil atualizado para "${status}" com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao atualizar status do perfil: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== FERRAMENTAS DE GRUPO =====

// Adiciona ferramenta para criar grupo
server.tool("createGroup",
  { 
    subject: z.string().min(1).describe("Nome do grupo"),
    participants: z.array(z.string()).min(1).describe("Lista de números de participantes"),
    description: z.string().optional().describe("Descrição do grupo")
  },
  async ({ subject, participants, description }) => {
    try {
      const result = await evolutionService.createGroup({
        subject,
        participants,
        description
      });
      return {
        content: [{ 
          type: "text", 
          text: `Grupo "${subject}" criado com sucesso. ID: ${result.groupId}` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao criar grupo: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// Adiciona ferramenta para adicionar participantes ao grupo
server.tool("addGroupParticipants",
  { 
    groupId: z.string().min(1).describe("ID do grupo"),
    participants: z.array(z.string()).min(1).describe("Lista de números de participantes")
  },
  async ({ groupId, participants }) => {
    try {
      await evolutionService.updateGroupMembers({
        groupJid: groupId,
        action: "add",
        participants
      });
      return {
        content: [{ 
          type: "text", 
          text: `${participants.length} participante(s) adicionado(s) ao grupo com sucesso.` 
        }]
      };
    } catch (error) {
      return {
        content: [{ 
          type: "text", 
          text: `Erro ao adicionar participantes: ${(error as Error).message}` 
        }]
      };
    }
  }
);

// ===== RECURSOS PARA CONSULTAR INFORMAÇÕES =====

// Adiciona recurso para visualizar contatos
server.resource(
  "contacts",
  new ResourceTemplate("contacts://list", { list: undefined }),
  async (uri) => {
    try {
      const contactsData = await evolutionService.fetchContacts();
      const contacts = contactsData?.data || [];
      
      return {
        contents: [{
          uri: uri.href,
          text: `Contatos disponíveis (${contacts.length}):\n${contacts
            .map((contact: any) => `- ${contact.name || "Sem nome"}: ${contact.id.replace("@c.us", "")}`)
            .join("\n")}`
        }]
      };
    } catch (error) {
      return {
        contents: [{
          uri: uri.href,
          text: `Erro ao buscar contatos: ${(error as Error).message}`
        }]
      };
    }
  }
);

// Adiciona recurso para visualizar conversas
server.resource(
  "chats",
  new ResourceTemplate("chats://list", { list: undefined }),
  async (uri) => {
    try {
      const chatsData = await evolutionService.fetchChats();
      const chats = chatsData?.data || [];
      
      return {
        contents: [{
          uri: uri.href,
          text: `Conversas disponíveis (${chats.length}):\n${chats
            .map((chat: any) => `- ${chat.name || chat.id || "Chat sem nome"}`)
            .join("\n")}`
        }]
      };
    } catch (error) {
      return {
        contents: [{
          uri: uri.href,
          text: `Erro ao buscar conversas: ${(error as Error).message}`
        }]
      };
    }
  }
);

// Adiciona recurso para visualizar grupos
server.resource(
  "groups",
  new ResourceTemplate("groups://list", { list: undefined }),
  async (uri) => {
    try {
      const groupsData = await evolutionService.fetchAllGroups();
      const groups = groupsData?.data || [];
      
      return {
        contents: [{
          uri: uri.href,
          text: `Grupos disponíveis (${groups.length}):\n${groups
            .map((group: any) => `- ${group.subject || group.id || "Grupo sem nome"} (${group.participants?.length || 0} membros)`)
            .join("\n")}`
        }]
      };
    } catch (error) {
      return {
        contents: [{
          uri: uri.href,
          text: `Erro ao buscar grupos: ${(error as Error).message}`
        }]
      };
    }
  }
);

// Adiciona recurso para visualizar detalhes do perfil
server.resource(
  "profile",
  new ResourceTemplate("profile://info", { list: undefined }),
  async (uri) => {
    try {
      const profile = await evolutionService.fetchProfile();
      
      return {
        contents: [{
          uri: uri.href,
          text: `Informações do perfil:\n- Nome: ${profile.name || "Não definido"}\n- Status: ${profile.status || "Não definido"}`
        }]
      };
    } catch (error) {
      return {
        contents: [{
          uri: uri.href,
          text: `Erro ao buscar informações do perfil: ${(error as Error).message}`
        }]
      };
    }
  }
);

// Adiciona recurso para visualizar configurações de privacidade
server.resource(
  "privacy",
  new ResourceTemplate("privacy://settings", { list: undefined }),
  async (uri) => {
    try {
      const privacy = await evolutionService.fetchPrivacySettings();
      
      return {
        contents: [{
          uri: uri.href,
          text: `Configurações de privacidade:\n- Confirmações de leitura: ${privacy.readreceipts}\n- Perfil: ${privacy.profile}\n- Status: ${privacy.status}\n- Online: ${privacy.online}\n- Último visto: ${privacy.last}\n- Adição a grupos: ${privacy.groupadd}`
        }]
      };
    } catch (error) {
      return {
        contents: [{
          uri: uri.href,
          text: `Erro ao buscar configurações de privacidade: ${(error as Error).message}`
        }]
      };
    }
  }
);

// Inicia o servidor usando stdin/stdout para comunicação
export async function startServer() {
  console.log("Iniciando servidor MCP para Evolution API via STDIO...");
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.log("Servidor MCP STDIO iniciado com sucesso!");
    return server;
  } catch (error) {
    console.error("Erro ao iniciar servidor MCP STDIO:", error);
    throw error;
  }
}

// Inicia o servidor usando WebSocket
export async function startWebSocketServer(port: number = 3000) {
  console.log(`Iniciando servidor MCP para Evolution API via WebSocket na porta ${port}...`);
  try {
    const httpServer = http.createServer();
    const wss = new WebSocketServer({ server: httpServer });
    
    const transport = new WebSocketServerTransport(wss);
    await server.connect(transport);
    
    httpServer.listen(port, () => {
      console.log(`Servidor MCP WebSocket iniciado com sucesso na porta ${port}!`);
    });
    
    return { server, httpServer, wss };
  } catch (error) {
    console.error("Erro ao iniciar servidor MCP WebSocket:", error);
    throw error;
  }
}

// Se este arquivo for executado diretamente, inicia o servidor
if (import.meta.url === `file://${process.argv[1]}`) {
  // Verifica se o WebSocket está habilitado
  const enableWebSocket = process.env.ENABLE_WEBSOCKET === 'true';
  const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
  
  startServer().catch(console.error);
  
  if (enableWebSocket) {
    startWebSocketServer(port).catch(console.error);
  }
} 