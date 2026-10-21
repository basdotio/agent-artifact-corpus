import axios, { AxiosError } from 'axios';

/**
 * Evolution API utility for making API calls
 */
export class EvolutionApi {
  private serverUrl: string;
  private apiKey: string;
  private axiosInstance: any;

  constructor() {
    // Get API credentials from environment variables
    this.serverUrl = process.env.EVOLUTION_API_URL || 'https://your-url.xyz';
    // Remove trailing slash if present
    this.serverUrl = this.serverUrl.endsWith('/') ? this.serverUrl.slice(0, -1) : this.serverUrl;
    this.apiKey = process.env.EVOLUTION_API_KEY || 'your-api-key';

    if (!this.serverUrl) {
      throw new Error('EVOLUTION_API_URL environment variable is not set');
    }

    if (!this.apiKey) {
      throw new Error('EVOLUTION_API_KEY environment variable is not set');
    }

    this.axiosInstance = axios.create({
      baseURL: this.serverUrl,
      headers: {
        'Content-Type': 'application/json',
        'apikey': this.apiKey,
      },
    });
  }

  /**
   * Get basic information about the Evolution API
   */
  async getInformation(): Promise<ApiInformation> {
    try {
      const response = await this.axiosInstance.get('/');
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to get API information: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Set presence status for a WhatsApp instance (available or unavailable)
   */
  async setPresence(instanceName: string, presence: PresenceStatus): Promise<void> {
    try {
      await this.axiosInstance.post(`/instance/setPresence/${instanceName}`, { presence });
      
      // This endpoint doesn't return any meaningful data
      return;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to set presence: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Delete a WhatsApp instance permanently
   */
  async deleteInstance(instanceName: string): Promise<DeleteResponse> {
    try {
      const response = await this.axiosInstance.delete(`/instance/delete/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to delete instance: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Logout from a WhatsApp instance (disconnects without deleting the instance)
   */
  async logoutInstance(instanceName: string): Promise<LogoutResponse> {
    try {
      const response = await this.axiosInstance.delete(`/instance/logout/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to logout instance: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Connect to a WhatsApp instance
   */
  async connectInstance(instanceName: string, phoneNumber?: string): Promise<ConnectionResponse> {
    try {
      let path = `/instance/connect/${instanceName}`;
      
      // Add phone number as query parameter if provided
      if (phoneNumber) {
        path += `?number=${encodeURIComponent(phoneNumber)}`;
      }
      
      const response = await this.axiosInstance.get(path);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to connect instance: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Fetch all instances or a specific one by name
   */
  async fetchInstances(instanceName?: string): Promise<InstanceInfo[]> {
    try {
      let path = '/instance/fetchInstances';
      
      // Add instance name as query parameter if provided
      if (instanceName) {
        path += `?instanceName=${encodeURIComponent(instanceName)}`;
      }
      
      const response = await this.axiosInstance.get(path);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to fetch instances: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Create a new WhatsApp instance
   */
  async createInstance(params: CreateInstanceParams): Promise<CreateInstanceResponse> {
    try {
      const response = await this.axiosInstance.post('/instance/create', params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to create instance: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Get connection state of an instance
   */
  async getConnectionState(instanceName: string): Promise<ConnectionStateResponse> {
    try {
      const response = await this.axiosInstance.get(`/instance/connectionState/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to get connection state: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  public async setWebhook(instanceName: string, config: WebhookConfig): Promise<WebhookResponse> {
    try {
      const response = await fetch(`${this.serverUrl}/webhook/set/${instanceName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          apikey: this.apiKey,
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to set webhook: ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Error setting webhook for instance ${instanceName}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  public async getWebhook(instanceName: string): Promise<WebhookResponse> {
    try {
      const response = await this.axiosInstance.get(`/webhook/find/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to get webhook: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  public async setSettings(instanceName: string, settings: InstanceSettings): Promise<SettingsResponse> {
    try {
      const response = await this.axiosInstance.post(`/settings/set/${instanceName}`, settings);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to set settings: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  public async getSettings(instanceName: string): Promise<SettingsResponse> {
    try {
      const response = await this.axiosInstance.get(`/settings/find/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to get settings: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  public async restartInstance(instanceName: string): Promise<RestartResponse> {
    try {
      const response = await this.axiosInstance.put(`/instance/restart/${instanceName}`);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to restart instance: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send a plain text message to a WhatsApp number
   */
  public async sendPlainText(instanceName: string, params: SendPlainTextParams): Promise<SendTextResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendText/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send text message: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Post a WhatsApp status (story)
   */
  public async sendStatus(instanceName: string, params: SendStatusParams): Promise<SendStatusResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendStatus/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to post WhatsApp status: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send a media message (image, video, audio, document) to a WhatsApp number
   */
  public async sendMedia(instanceName: string, params: SendMediaParams): Promise<SendMediaResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendMedia/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send media message: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send a WhatsApp audio message with PTT (push-to-talk) functionality
   */
  public async sendWhatsAppAudio(instanceName: string, params: SendWhatsAppAudioParams): Promise<SendWhatsAppAudioResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendWhatsAppAudio/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send WhatsApp audio message: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send a sticker to a WhatsApp number
   */
  public async sendSticker(instanceName: string, params: SendStickerParams): Promise<SendStickerResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendSticker/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send sticker: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send a location message to a WhatsApp number
   */
  public async sendLocation(instanceName: string, params: SendLocationParams): Promise<SendLocationResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendLocation/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send location: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Send contact information to a WhatsApp number
   */
  public async sendContact(
    instanceName: string, 
    number: string, 
    contact: ContactInfo[], 
    options?: {
      delay?: number;
      quoted?: {
        key: {
          remoteJid: string;
          fromMe: boolean;
          id: string;
          participant?: string;
        };
        message: {
          conversation: string;
        };
      };
      mentionsEveryOne?: boolean;
      mentioned?: string[];
    }
  ): Promise<SendContactResponse> {
    try {
      const params: SendContactParams = {
        number,
        contact,
        ...options
      };

      const response = await this.axiosInstance.post(`/message/sendContact/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send contact: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  public async sendReaction(instanceName: string, params: SendReactionParams): Promise<SendReactionResponse> {
    try {
      const response = await this.axiosInstance.post(`/message/sendReaction/${instanceName}`, params);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to send reaction: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Fetch all WhatsApp groups
   */
  public async fetchAllGroups(instanceName: string, getParticipants?: boolean): Promise<GroupInfo[]> {
    try {
      let path = `/group/fetchAllGroups/${instanceName}`;
      
      // Add getParticipants as query parameter if provided
      if (getParticipants !== undefined) {
        path += `?getParticipants=${getParticipants.toString()}`;
      }
      
      const response = await this.axiosInstance.get(path);
      
      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<{ message?: string }>;
        throw new Error(`Failed to fetch groups: ${axiosError.response?.data?.message || axiosError.message}`);
      }
      throw error;
    }
  }

  /**
   * Finds a WhatsApp group by its JID (Group ID)
   * @param instanceName Name of the Evolution API instance
   * @param params Group parameters including the groupJid
   * @returns Group information including participants
   */
  public async findGroupByJid(
    instanceName: string,
    params: FindGroupByJidParams
  ): Promise<FindGroupByJidResponse> {
    try {
      const response = await this.axiosInstance.get(`/group/findGroupInfos/${instanceName}?groupJid=${params.groupJid}`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error finding group by JID: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  public async findGroupMembers(instanceName: string, params: FindGroupMembersParams): Promise<FindGroupMembersResponse> {
    try {
      const response = await this.axiosInstance.get(`/group/participants/${instanceName}?groupJid=${params.groupJid}`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error finding group members: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  /**
   * Find chats by filter criteria
   * @param instanceName Name of the Evolution API instance
   * @param params Search parameters including optional filters
   * @returns List of chats matching the criteria
   */
  public async findChats(
    instanceName: string,
    params?: FindChatsParams
  ): Promise<FindChatsResponse> {
    try {
      const response = await this.axiosInstance.post(
        `/chat/findChats/${instanceName}`,
        params || {}
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error finding chats: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  /**
   * Find contacts by filter criteria
   * @param instanceName Name of the Evolution API instance
   * @param params Search parameters including optional filters
   * @returns List of contacts matching the criteria
   */
  public async findContacts(
    instanceName: string,
    params?: FindContactsParams
  ): Promise<FindContactsResponse> {
    try {
      const response = await this.axiosInstance.post(
        `/chat/findContacts/${instanceName}`,
        params || {}
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error finding contacts: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  /**
   * Send a poll message to a WhatsApp number
   * @param instanceName Name of the Evolution API instance
   * @param params Poll parameters including number, name, selectableCount, and values
   * @returns Poll send response
   */
  public async sendPoll(
    instanceName: string,
    params: SendPollParams
  ): Promise<SendPollResponse> {
    try {
      const response = await this.axiosInstance.post(
        `/message/sendPoll/${instanceName}`,
        params
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error sending poll: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  /**
   * Send a list message to a WhatsApp number
   */
  async sendList(
    instanceName: string,
    params: SendListParams
  ): Promise<SendListResponse> {
    try {
      const response = await this.axiosInstance.post(
        `/message/sendList/${instanceName}`,
        params
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error sending list: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }

  /**
   * Send a buttons message to a WhatsApp number
   */
  async sendButtons(
    instanceName: string,
    params: SendButtonsParams
  ): Promise<SendButtonsResponse> {
    try {
      const response = await this.axiosInstance.post(
        `/message/sendButtons/${instanceName}`,
        params
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Error sending buttons: ${
            error.response?.data?.message || error.message
          }`
        );
      }
      throw error;
    }
  }
}

// Type definition for presence status
export type PresenceStatus = 'available' | 'unavailable';

// Type definitions for API Information
export interface ApiInformation {
  status: number;
  message: string;
  version: string;
  swagger?: string;
  manager?: string;
  documentation?: string;
}

// Type definitions for Delete Response
export interface DeleteResponse {
  status: string;
  error: boolean;
  response: {
    message: string;
  };
}

// Type definitions for Logout Response
export interface LogoutResponse {
  status: string;
  error: boolean;
  response: {
    message: string;
  };
}

// Type definitions for Connection Response
export interface ConnectionResponse {
  pairingCode?: string;
  code?: string;
  count?: number;
}

// Type definitions for Connection State
export interface ConnectionStateResponse {
  instance: {
    instanceName: string;
    state: string;
  };
}

// Type definitions for Instance Information
export interface InstanceInfo {
  instance: {
    instanceName: string;
    instanceId: string;
    owner?: string;
    profileName?: string;
    profilePictureUrl?: string | null;
    profileStatus?: string;
    status: string;
    serverUrl: string;
    apikey: string;
    integration: {
      integration?: string;
      token?: string;
      webhook_wa_business?: string;
    };
  };
}

// Type definitions for Evolution API
export interface CreateInstanceParams {
  instanceName: string;
  token?: string;
  number?: string;
  qrcode?: boolean;
  integration?: 'WHATSAPP-BAILEYS' | 'WHATSAPP-BUSINESS';
  reject_call?: boolean;
  msgCall?: string;
  groupsIgnore?: boolean;
  alwaysOnline?: boolean;
  readMessages?: boolean;
  readStatus?: boolean;
  syncFullHistory?: boolean;
  webhookUrl?: string;
  webhookByEvents?: boolean;
  webhookEvents?: string[];
  // Add other optional parameters as needed
}

export interface CreateInstanceResponse {
  instance: {
    instanceName: string;
    instanceId: string;
    webhook_wa_business: null | string;
    access_token_wa_business: string;
    status: string;
  };
  hash: {
    apikey: string;
  };
  settings: {
    reject_call: boolean;
    msg_call: string;
    groups_ignore: boolean;
    always_online: boolean;
    read_messages: boolean;
    read_status: boolean;
    sync_full_history: boolean;
  };
}

export interface WebhookConfig {
  enabled: boolean;
  url: string;
  webhookByEvents?: boolean;
  webhookBase64?: boolean;
  events: WebhookEvent[];
}

export type WebhookEvent =
  | 'APPLICATION_STARTUP'
  | 'QRCODE_UPDATED'
  | 'MESSAGES_SET'
  | 'MESSAGES_UPSERT'
  | 'MESSAGES_UPDATE'
  | 'MESSAGES_DELETE'
  | 'SEND_MESSAGE'
  | 'CONTACTS_SET'
  | 'CONTACTS_UPSERT'
  | 'CONTACTS_UPDATE'
  | 'PRESENCE_UPDATE'
  | 'CHATS_SET'
  | 'CHATS_UPSERT'
  | 'CHATS_UPDATE'
  | 'CHATS_DELETE'
  | 'GROUPS_UPSERT'
  | 'GROUP_UPDATE'
  | 'GROUP_PARTICIPANTS_UPDATE'
  | 'CONNECTION_UPDATE'
  | 'LABELS_EDIT'
  | 'LABELS_ASSOCIATION'
  | 'CALL'
  | 'TYPEBOT_START'
  | 'TYPEBOT_CHANGE_STATUS';

interface WebhookResponse {
  webhook: {
    instanceName: string;
    webhook: {
      url: string;
      events: WebhookEvent[];
      enabled: boolean;
    };
  };
}

export interface InstanceSettings {
  rejectCall: boolean;
  msgCall?: string;
  groupsIgnore: boolean;
  alwaysOnline: boolean;
  readMessages: boolean;
  syncFullHistory: boolean;
  readStatus: boolean;
}

export interface SettingsResponse {
  settings: {
    instanceName: string;
    settings: {
      rejectCall: boolean;
      msgCall: string;
      groupsIgnore: boolean;
      alwaysOnline: boolean;
      readMessages: boolean;
      syncFullHistory: boolean;
      readStatus: boolean;
    }
  }
}

export interface RestartResponse {
  restart: {
    message: string;
    success: boolean;
    webhook?: string;
  }
}

export interface SendPlainTextParams {
  number: string;
  text: string;
  delay?: number;
  linkPreview?: boolean;
  mentionsEveryOne?: boolean;
  mentioned?: string[];
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
}

export interface SendStatusParams {
  statusMessage: {
    type: 'text' | 'image' | 'audio';
    content: string;
    caption?: string;
    backgroundColor?: string;
    font?: number;
    allContacts: boolean;
    statusJidList?: string[];
  };
}

export interface SendMediaParams {
  number: string;
  mediatype: 'image' | 'video' | 'audio' | 'document';
  media: string;
  mimetype?: string;
  fileName?: string;
  caption?: string;
  delay?: number;
  mentionsEveryOne?: boolean;
  mentioned?: string[];
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
}

export interface SendMediaResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    imageMessage?: {
      url: string;
      mimetype: string;
      caption?: string;
      fileSha256: string;
      fileLength: string;
      height: number;
      width: number;
      mediaKey: string;
      fileEncSha256: string;
      directPath: string;
      mediaKeyTimestamp: string;
      jpegThumbnail: string;
    };
    videoMessage?: {
      url: string;
      mimetype: string;
      fileSha256: string;
      fileLength: string;
      seconds: number;
      mediaKey: string;
      caption: string;
      height: number;
      width: number;
      fileEncSha256: string;
      directPath: string;
      mediaKeyTimestamp: string;
      jpegThumbnail: string;
    };
    audioMessage?: {
      url: string;
      mimetype: string;
      fileSha256: string;
      fileLength: string;
      seconds: number;
      mediaKey: string;
      fileEncSha256: string;
      directPath: string;
      mediaKeyTimestamp: string;
    };
    documentMessage?: {
      url: string;
      mimetype: string;
      title: string;
      fileSha256: string;
      fileLength: string;
      pageCount: number;
      mediaKey: string;
      fileName: string;
      fileEncSha256: string;
      directPath: string;
      mediaKeyTimestamp: string;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendStatusResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    extendedTextMessage?: {
      text: string;
      backgroundArgb?: number;
      font?: string;
    };
    imageMessage?: {
      url: string;
      mimetype: string;
      caption?: string;
    };
    audioMessage?: {
      url: string;
      mimetype: string;
    };
  };
  messageTimestamp: string;
  status: string;
  participant?: string;
}

export interface SendTextResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    extendedTextMessage: {
      text: string;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendWhatsAppAudioParams {
  number: string;
  audio: string;
  delay?: number;
  encoding?: boolean;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendWhatsAppAudioResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    audioMessage: {
      url: string;
      mimetype: string;
      fileSha256: string;
      fileLength: string;
      seconds: number;
      ptt: boolean;
      mediaKey: string;
      fileEncSha256: string;
      directPath: string;
      mediaKeyTimestamp: string;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendStickerParams {
  number: string;
  sticker: string;
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendStickerResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    stickerMessage: {
      url: string;
      fileSha256: string;
      fileEncSha256: string;
      mediaKey: string;
      mimetype: string;
      directPath: string;
      fileLength: string;
      mediaKeyTimestamp: string;
      isAnimated: boolean;
      firstFrameSidecar?: string;
      stickerSentTs: string;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendLocationParams {
  number: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendLocationResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    locationMessage: {
      degreesLatitude: number;
      degreesLongitude: number;
      name: string;
      address: string;
      contextInfo?: any;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendPollParams {
  number: string;
  name: string;
  selectableCount: number;
  values: string[];
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendPollResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    messageContextInfo: {
      messageSecret: string;
    };
    pollCreationMessage: {
      name: string;
      options: {
        optionName: string;
      }[];
      selectableOptionsCount: number;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendListParams {
  number: string;
  title: string;
  description: string;
  buttonText: string;
  footerText?: string;
  sections: {
    title: string;
    rows: {
      title: string;
      description?: string;
      rowId: string;
    }[];
  }[];
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendListResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    listMessage: {
      title: string;
      description: string;
      buttonText: string;
      listType: string;
      sections: {
        title: string;
        rows: {
          title: string;
          description: string;
          rowId: string;
        }[];
      }[];
      contextInfo: Record<string, unknown>;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendButtonsParams {
  number: string;
  title: string;
  description: string;
  footer?: string;
  buttons: {
    buttonId: string;
    buttonText: string;
  }[];
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendButtonsResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    buttonsMessage: {
      title: string;
      description: string;
      footerText?: string;
      buttons: {
        buttonId: string;
        buttonText: {
          displayText: string;
        };
      }[];
      contextInfo: Record<string, unknown>;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface ContactInfo {
  fullName?: string;
  wuid: string;
  phoneNumber: string;
  organization?: string;
  email?: string;
  url?: string;
}

export interface SendContactParams {
  number: string;
  contact: ContactInfo[];
  delay?: number;
  quoted?: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
      participant?: string;
    };
    message: {
      conversation: string;
    };
  };
  mentionsEveryOne?: boolean;
  mentioned?: string[];
}

export interface SendContactResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    contactMessage: {
      displayName: string;
      vcard: string;
      contextInfo: Record<string, unknown>;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface SendReactionParams {
  reactionMessage: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
    };
    reaction: string;
  };
}

export interface SendReactionResponse {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  message: {
    reactionMessage: {
      key: {
        remoteJid: string;
        fromMe: boolean;
        id: string;
      };
      text: string;
      senderTimestampMs: string;
    };
  };
  messageTimestamp: string;
  status: string;
}

export interface GroupInfo {
  id: string;
  subject: string;
  subjectOwner: string;
  subjectTime: number;
  pictureUrl: string | null;
  size: number;
  creation: number;
  owner: string;
  desc?: string;
  descId?: string;
  restrict: boolean;
  announce: boolean;
  participants?: GroupParticipant[];
}

export interface GroupParticipant {
  id: string;
  admin?: 'admin' | 'superadmin' | null;
}

export interface FindGroupByJidParams {
  groupJid: string;
}

export interface FindGroupByJidResponse {
  id: string;
  subject: string;
  subjectOwner: string;
  subjectTime: number;
  pictureUrl: string | null;
  size: number;
  creation: number;
  owner: string;
  desc?: string;
  descId?: string;
  restrict: boolean;
  announce: boolean;
  participants: {
    id: string;
    admin: string;
  }[];
}

export interface FindGroupMembersParams {
  groupJid: string;
}

export interface FindGroupMembersResponse {
  participants: {
    id: string;
    admin?: string;
  }[];
}

export interface FindChatsParams {
  where?: {
    id?: string;
    name?: string;
    archived?: boolean;
  };
}

export interface FindChatsResponse {
  chats: {
    id: string;
    name?: string;
    pushName?: string;
    isGroup: boolean;
    timestamp: number;
    isReadOnly: boolean;
    unreadCount: number;
    archived: boolean;
    notSpam: boolean;
    ephemeralExpiration?: number;
    ephemeralSettingTimestamp?: number;
    tcToken?: string;
    tcTokenTimestamp?: number;
  }[];
}

export interface FindContactsParams {
  where?: {
    id?: string;
    name?: string;
  };
}

export interface FindContactsResponse {
  contacts: {
    id: string;
    pushName?: string;
    profilePictureUrl?: string;
    statusMessage?: string;
    businessProfile?: {
      description?: string;
      email?: string;
      website?: string;
      address?: string;
    };
    isBusiness: boolean;
    isEnterprise: boolean;
    isUser: boolean;
    isGroup: boolean;
    isWAContact: boolean;
    isMyContact: boolean;
  }[];
}

// Create singleton instance
export const evolutionApi = new EvolutionApi(); 
