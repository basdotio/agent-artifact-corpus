// Interfaces para a Evolution API

// Informações básicas da API
export interface ApiInfo {
  status: number;
  message: string;
  version: string;
  swagger?: string;
  manager?: string;
  documentation?: string;
}

// Status da instância
export interface InstanceStatus {
  state: string;
  status: string;
  qrcode?: string;
  message?: string;
}

// Mensagens de texto
export interface SendTextMessageRequest {
  number: string;
  text: string;
  options?: MessageOptions;
}

export interface MessageOptions {
  delay?: number;
  presence?: "composing" | "recording" | "paused";
  quotedMessageId?: string;
  mentionedList?: string[];
}

export interface SendTextMessageResponse {
  key: {
    id: string;
    remoteJid: string;
    fromMe: boolean;
  };
  message: {
    conversation: string;
  };
  messageTimestamp: number;
  status: string;
}

// Verificação de números
export interface CheckNumberRequest {
  phone: string;
}

export interface CheckNumberResponse {
  numbers: Array<{
    jid: string;
    exists: boolean;
    phone: string;
  }>;
}

// Contatos e chats
export interface Contact {
  id: string;
  name?: string;
  pushname?: string;
  shortName?: string;
  isMe?: boolean;
  isGroup?: boolean;
}

export interface Chat {
  id: string;
  name?: string;
  lastMessage?: {
    text?: string;
    timestamp?: number;
  };
  unreadCount?: number;
  isGroup?: boolean;
}

// Templates de mensagem
export interface SendTemplateRequest {
  number: string;
  template: {
    namespace: string;
    name: string;
    language: {
      code: string;
    };
    components: TemplateComponent[];
  };
  options?: MessageOptions;
}

export interface TemplateComponent {
  type: "header" | "body" | "button" | "footer";
  parameters?: TemplateParameter[];
}

export interface TemplateParameter {
  type: "text" | "image" | "document" | "video";
  text?: string;
  image?: { link: string };
  document?: { link: string; filename: string };
  video?: { link: string };
}

// Mídia
export interface SendMediaRequest {
  number: string;
  media: {
    url: string;
    caption?: string;
    fileName?: string;
    mediaType?: "image" | "document" | "video" | "audio";
  };
  options?: MessageOptions;
}

// Áudios
export interface SendAudioRequest {
  number: string;
  audio: {
    url: string;
    ptt?: boolean; // Push to talk (mensagem de voz)
  };
  options?: MessageOptions;
}

// Stickers
export interface SendStickerRequest {
  number: string;
  sticker: {
    url: string;
  };
  options?: MessageOptions;
}

// Localização
export interface SendLocationRequest {
  number: string;
  location: {
    lat: number;
    lng: number;
    title?: string;
    address?: string;
  };
  options?: MessageOptions;
}

// Contatos
export interface SendContactRequest {
  number: string;
  contact: {
    fullName: string;
    wuid: string;
    phoneNumber: string;
  };
  options?: MessageOptions;
}

// Reações
export interface SendReactionRequest {
  reactionMessage: {
    key: {
      id: string;
      remoteJid: string;
    };
    reaction: string;
  };
}

// Enquetes
export interface SendPollRequest {
  number: string;
  poll: {
    name: string;
    options: string[];
    multipleChoice?: boolean;
  };
  options?: MessageOptions;
}

// Listas
export interface SendListRequest {
  number: string;
  list: {
    title: string;
    description: string;
    buttonText: string;
    sections: ListSection[];
  };
  options?: MessageOptions;
}

export interface ListSection {
  title: string;
  rows: ListRow[];
}

export interface ListRow {
  id: string;
  title: string;
  description?: string;
}

// Status
export interface SendStatusRequest {
  status: {
    type: "text" | "image" | "video" | "audio";
    content: string; // Texto ou URL
    caption?: string;
    options?: {
      backgroundColor?: string;
      font?: number;
    };
  };
}

// Perfil
export interface ProfileInfo {
  name?: string;
  status?: string;
  picUrl?: string;
  business?: {
    description?: string;
    email?: string;
    websites?: string[];
    categories?: string[];
  };
}

export interface UpdateProfileRequest {
  name?: string;
  status?: string;
}

// Privacidade
export interface PrivacySettings {
  readreceipts: "all" | "contacts" | "none";
  profile: "all" | "contacts" | "none";
  status: "all" | "contacts" | "none";
  online: "all" | "contacts" | "none";
  last: "all" | "contacts" | "none";
  groupadd: "all" | "contacts" | "none";
}

// Grupos
export interface CreateGroupRequest {
  subject: string;
  participants: string[];
  description?: string;
  picture?: string;
}

export interface GroupInfo {
  id: string;
  subject: string;
  description?: string;
  owner?: string;
  participants: GroupParticipant[];
  creation?: number;
  ephemeralDuration?: number;
}

export interface GroupParticipant {
  id: string;
  admin?: "admin" | "superadmin" | null;
  isSuperAdmin?: boolean;
}

export interface GroupUpdateRequest {
  groupJid: string;
  action: "add" | "remove" | "promote" | "demote";
  participants: string[];
}

export interface GroupSettingRequest {
  groupJid: string;
  setting: "announcement" | "locked" | "unlocked";
}

// Webhook
export interface WebhookConfig {
  url: string;
  enabled: boolean;
  events?: WebhookEvent[];
}

export type WebhookEvent = 
  | "message" 
  | "message.ack" 
  | "qr" 
  | "connection.update" 
  | "group.update" 
  | "presence.update";

// Chatwoot
export interface ChatwootConfig {
  enabled: boolean;
  account_id: string;
  token: string;
  endpoint: string;
  instance_name?: string;
  sign_msg?: boolean;
  name_inbox?: string;
}

// Typebot
export interface TypebotConfig {
  enabled: boolean;
  url: string;
  typebot: string;
  expire?: number;
  keyword_finish?: string[];
  delay_message?: number;
  unknown_message?: string;
  listening_from_me?: boolean;
}

// Instância
export interface InstanceConfig {
  instanceName: string;
  webhook?: WebhookConfig;
  settings?: {
    reject_call?: boolean;
    msg_call?: string;
    groups_ignore?: boolean;
    always_online?: boolean;
    read_messages?: boolean;
    read_status?: boolean;
  };
}