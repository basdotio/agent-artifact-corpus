/**
 * Telegram tools for the AI agent
 * Calls the Python HTTP bridge to interact with Telegram
 */

import { tool } from "ai";
import { z } from "zod";
import { config } from "../config";

const API = config.telegramApiUrl;

// Helper for API calls
async function telegramFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Telegram API error: ${error}`);
  }

  return response.json();
}

// Types
interface Chat {
  id: number;
  type: string;
  first_name?: string;
  last_name?: string;
  title?: string;
  username?: string;
  unread_count?: number;
  last_message?: string;
}

interface Message {
  id: number;
  date: string;
  text: string;
  out: boolean;
  sender_name: string;
  sender_id: number;
  reply_to_msg_id?: number;
  has_media: boolean;
  media_type?: string;
}

// Tools

export const getChats = tool({
  description: `List all Telegram chats (conversations). Returns chat ID, name, type, and last message preview. Use this to find someone's chat ID before reading or sending messages.`,
  inputSchema: z.object({
    limit: z.number().min(1).max(100).default(30).describe("Number of chats to return"),
    chat_type: z
      .enum(["user", "chat", "channel"])
      .optional()
      .describe("Filter by type: 'user' for DMs, 'chat' for groups, 'channel' for channels"),
  }),
  execute: async ({ limit, chat_type }) => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (chat_type) params.set("chat_type", chat_type);

    const data = await telegramFetch<{ chats: Chat[]; count: number }>(
      `/chats?${params.toString()}`
    );

    // Format for better readability
    const formatted = data.chats.map((chat) => {
      const name = chat.title || `${chat.first_name || ""} ${chat.last_name || ""}`.trim() || "Unknown";
      return {
        id: chat.id,
        name,
        type: chat.type,
        username: chat.username,
        unread: chat.unread_count || 0,
        preview: chat.last_message?.slice(0, 50),
      };
    });

    return { chats: formatted, total: data.count };
  },
});

export const getMessages = tool({
  description: `Read messages from a specific Telegram chat. Returns message ID, text, sender, date. Use after getChats to get the chat_id.`,
  inputSchema: z.object({
    chat_id: z
      .union([z.number(), z.string()])
      .describe("Chat ID (number) or username (string like '@username')"),
    limit: z.number().min(1).max(50).default(10).describe("Number of messages to fetch"),
    offset_id: z.number().optional().describe("Get messages before this message ID (for pagination)"),
  }),
  execute: async ({ chat_id, limit, offset_id }) => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (offset_id) params.set("offset_id", String(offset_id));

    const data = await telegramFetch<{ messages: Message[]; count: number }>(
      `/chats/${chat_id}/messages?${params.toString()}`
    );

    // Format messages for readability
    const formatted = data.messages.map((msg) => ({
      id: msg.id,
      from: msg.sender_name,
      text: msg.text,
      date: msg.date,
      isFromMe: msg.out,
      hasMedia: msg.has_media,
      mediaType: msg.media_type,
      replyTo: msg.reply_to_msg_id,
    }));

    return { messages: formatted, count: data.count };
  },
});

export const sendMessage = tool({
  description: `Send a text message to a Telegram chat. Returns success status and message ID.`,
  inputSchema: z.object({
    chat_id: z
      .union([z.number(), z.string()])
      .describe("Chat ID (number) or username (string like '@username')"),
    message: z.string().min(1).max(4096).describe("Message text to send"),
    reply_to: z.number().optional().describe("Message ID to reply to (optional)"),
  }),
  execute: async ({ chat_id, message, reply_to }) => {
    const data = await telegramFetch<{ success: boolean; message_id: number; date: string }>(
      `/chats/${chat_id}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ message, reply_to }),
      }
    );

    return {
      success: data.success,
      messageId: data.message_id,
      sentAt: data.date,
    };
  },
});

export const scheduleMessage = tool({
  description: `Schedule a message to be sent at a future time. Perfect for sending good morning/night messages.`,
  inputSchema: z.object({
    chat_id: z
      .union([z.number(), z.string()])
      .describe("Chat ID (number) or username (string like '@username')"),
    message: z.string().min(1).max(4096).describe("Message text to send"),
    minutes_from_now: z.number().min(1).max(525600).describe("Minutes from now to send (1-525600, max 1 year)"),
  }),
  execute: async ({ chat_id, message, minutes_from_now }) => {
    const data = await telegramFetch<{ success: boolean; message_id: number; scheduled_for: string }>(
      `/chats/${chat_id}/schedule`,
      {
        method: "POST",
        body: JSON.stringify({ message, minutes_from_now }),
      }
    );

    return {
      success: data.success,
      messageId: data.message_id,
      scheduledFor: data.scheduled_for,
    };
  },
});

export const getChat = tool({
  description: `Get detailed information about a specific chat by ID or username.`,
  inputSchema: z.object({
    chat_id: z
      .union([z.number(), z.string()])
      .describe("Chat ID (number) or username (string like '@username')"),
  }),
  execute: async ({ chat_id }) => {
    const data = await telegramFetch<Chat>(`/chats/${chat_id}`);
    return data;
  },
});

export const searchContacts = tool({
  description: `Search for contacts by name, username, or phone number.`,
  inputSchema: z.object({
    query: z.string().min(1).describe("Search query (name, username, or phone)"),
  }),
  execute: async ({ query }) => {
    const params = new URLSearchParams({ query });
    const data = await telegramFetch<{ contacts: any[]; count: number }>(
      `/contacts/search?${params.toString()}`
    );
    return data;
  },
});

// ============= NEW TOOLS =============

export const getHistory = tool({
  description: `Get full chat history (up to 500 messages). Use for getting more context about the conversation.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    limit: z.number().min(1).max(500).default(100).describe("Number of messages"),
  }),
  execute: async ({ chat_id, limit }) => {
    const params = new URLSearchParams({ limit: String(limit) });
    const data = await telegramFetch<{ messages: Message[]; count: number }>(
      `/chats/${chat_id}/history?${params.toString()}`
    );
    return {
      messages: data.messages.map((msg) => ({
        id: msg.id,
        from: msg.sender_name,
        text: msg.text,
        date: msg.date,
        isFromMe: msg.out,
      })),
      count: data.count,
    };
  },
});

export const sendReaction = tool({
  description: `Send a reaction emoji to a message. Perfect for reacting to her messages with ❤️ 🔥 😂 😮 😢 🎉 👍 👎`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    message_id: z.number().describe("Message ID to react to"),
    emoji: z.string().describe("Emoji to react with (e.g., '❤️', '🔥', '😂')"),
    big: z.boolean().default(false).describe("Show big animation"),
  }),
  execute: async ({ chat_id, message_id, emoji, big }) => {
    const data = await telegramFetch<{ success: boolean; emoji: string }>(
      `/chats/${chat_id}/messages/${message_id}/reaction`,
      {
        method: "POST",
        body: JSON.stringify({ emoji, big }),
      }
    );
    return data;
  },
});

export const replyToMessage = tool({
  description: `Reply directly to a specific message. Creates a reply thread.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    message_id: z.number().describe("Message ID to reply to"),
    message: z.string().min(1).describe("Reply text"),
  }),
  execute: async ({ chat_id, message_id, message }) => {
    const data = await telegramFetch<{ success: boolean; message_id: number }>(
      `/chats/${chat_id}/messages/${message_id}/reply`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      }
    );
    return data;
  },
});

export const editMessage = tool({
  description: `Edit a message you sent. Fix typos or update content.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    message_id: z.number().describe("Message ID to edit"),
    new_text: z.string().min(1).describe("New message text"),
  }),
  execute: async ({ chat_id, message_id, new_text }) => {
    const data = await telegramFetch<{ success: boolean }>(
      `/chats/${chat_id}/messages/${message_id}`,
      {
        method: "PUT",
        body: JSON.stringify({ new_text }),
      }
    );
    return data;
  },
});

export const deleteMessage = tool({
  description: `Delete a message. Use to remove embarrassing messages.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    message_id: z.number().describe("Message ID to delete"),
  }),
  execute: async ({ chat_id, message_id }) => {
    const data = await telegramFetch<{ success: boolean }>(
      `/chats/${chat_id}/messages/${message_id}`,
      { method: "DELETE" }
    );
    return data;
  },
});

export const forwardMessage = tool({
  description: `Forward a message to another chat. Great for sharing memes or content.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Source chat ID"),
    message_id: z.number().describe("Message ID to forward"),
    to_chat_id: z.union([z.number(), z.string()]).describe("Destination chat ID"),
  }),
  execute: async ({ chat_id, message_id, to_chat_id }) => {
    const params = new URLSearchParams({ to_chat_id: String(to_chat_id) });
    const data = await telegramFetch<{ success: boolean }>(
      `/chats/${chat_id}/messages/${message_id}/forward?${params.toString()}`,
      { method: "POST" }
    );
    return data;
  },
});

export const markAsRead = tool({
  description: `Mark all messages in a chat as read.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
  }),
  execute: async ({ chat_id }) => {
    const data = await telegramFetch<{ success: boolean }>(
      `/chats/${chat_id}/read`,
      { method: "POST" }
    );
    return data;
  },
});

export const pinMessage = tool({
  description: `Pin an important message in the chat.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    message_id: z.number().describe("Message ID to pin"),
  }),
  execute: async ({ chat_id, message_id }) => {
    const data = await telegramFetch<{ success: boolean }>(
      `/chats/${chat_id}/messages/${message_id}/pin`,
      { method: "POST" }
    );
    return data;
  },
});

export const searchMessages = tool({
  description: `Search for messages in a chat by text. Find specific conversations.`,
  inputSchema: z.object({
    chat_id: z.union([z.number(), z.string()]).describe("Chat ID or username"),
    query: z.string().min(1).describe("Search text"),
    limit: z.number().min(1).max(100).default(20).describe("Max results"),
  }),
  execute: async ({ chat_id, query, limit }) => {
    const params = new URLSearchParams({ query, limit: String(limit) });
    const data = await telegramFetch<{ messages: Message[]; count: number }>(
      `/chats/${chat_id}/search?${params.toString()}`
    );
    return {
      messages: data.messages.map((msg) => ({
        id: msg.id,
        from: msg.sender_name,
        text: msg.text,
        date: msg.date,
      })),
      count: data.count,
    };
  },
});

export const getUserStatus = tool({
  description: `Check if a user is online. See when she was last active.`,
  inputSchema: z.object({
    user_id: z.union([z.number(), z.string()]).describe("User ID or username"),
  }),
  execute: async ({ user_id }) => {
    const data = await telegramFetch<{ user_id: number; status: string; raw_status: string }>(
      `/users/${user_id}/status`
    );
    return data;
  },
});

export const getUserPhotos = tool({
  description: `Get a user's profile photos.`,
  inputSchema: z.object({
    user_id: z.union([z.number(), z.string()]).describe("User ID or username"),
    limit: z.number().min(1).max(50).default(10).describe("Max photos"),
  }),
  execute: async ({ user_id, limit }) => {
    const params = new URLSearchParams({ limit: String(limit) });
    const data = await telegramFetch<{ photos: any[]; count: number }>(
      `/users/${user_id}/photos?${params.toString()}`
    );
    return data;
  },
});

export const searchGifs = tool({
  description: `Search for GIFs to send. Returns a list of available GIFs.`,
  inputSchema: z.object({
    query: z.string().min(1).describe("GIF search query (e.g., 'love', 'funny', 'cute')"),
    limit: z.number().min(1).max(50).default(10).describe("Max results"),
  }),
  execute: async ({ query, limit }) => {
    const params = new URLSearchParams({ query, limit: String(limit) });
    const data = await telegramFetch<{ gifs: any[]; count: number }>(
      `/gifs/search?${params.toString()}`
    );
    return data;
  },
});

// Export all telegram tools
export const telegramTools = {
  // Core
  getChats,
  getMessages,
  sendMessage,
  scheduleMessage,
  getChat,
  searchContacts,
  // History & Search
  getHistory,
  searchMessages,
  // Reactions & Replies
  sendReaction,
  replyToMessage,
  // Edit & Delete
  editMessage,
  deleteMessage,
  // Forward & Pin
  forwardMessage,
  pinMessage,
  markAsRead,
  // User Info
  getUserStatus,
  getUserPhotos,
  // Media
  searchGifs,
};
