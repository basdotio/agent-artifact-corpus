import type { ToolRegistration } from "@/types";
import { someFunctionTool } from "./exampleTool";
import { createEvolutionInstanceTool } from "./createEvolutionInstance";
import { getEvolutionInfoTool } from "./getEvolutionInfo";
import { fetchEvolutionInstancesTool } from "./fetchEvolutionInstances";
import { connectEvolutionInstanceTool } from "./connectEvolutionInstance";
import { getConnectionStateTool } from "./getConnectionState";
import { logoutEvolutionInstanceTool } from "./logoutEvolutionInstance";
import { deleteEvolutionInstanceTool } from "./deleteEvolutionInstance";
import { setEvolutionPresenceTool } from "./setEvolutionPresence";
import { setEvolutionWebhookTool } from "./setEvolutionWebhook";
import { setEvolutionSettingsTool } from "./setEvolutionSettings";
import { getEvolutionSettingsTool } from "./getEvolutionSettings";
import { getEvolutionWebhookTool } from "./getEvolutionWebhook";
import { restartEvolutionInstanceTool } from "./restartEvolutionInstance";
import { sendPlainTextTool } from "./sendPlainText";
import { sendStatusTool } from "./sendStatus";
import { sendMediaTool } from "./sendMedia";
import { sendWhatsAppAudioTool } from "./sendWhatsAppAudio";
import { sendStickerTool } from "./sendSticker";
import { sendLocationTool } from "./sendLocation";
import { sendContactTool } from "./sendContact";
import { sendReactionTool } from "./sendReaction";
import { sendPollTool } from "./sendPoll";
import { sendListTool } from "./sendList";
import { sendButtonsTool } from "./sendButtons";
import { fetchAllGroupsTool } from "./fetchAllGroups";
import { findGroupByJidTool } from "./findGroupByJid";
import { findGroupMembersTool } from "./findGroupMembers";
import { findChatsTool } from "./findChats";
import { findContactsTool } from "./findContacts";

// biome-ignore lint/suspicious/noExplicitAny: Any is fine here because all tools validate their input schemas.
export const createTools = (): ToolRegistration<any>[] => {
	return [
		{
			...someFunctionTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => someFunctionTool.handler(args),
		},
		{
			...createEvolutionInstanceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => createEvolutionInstanceTool.handler(args),
		},
		{
			...getEvolutionInfoTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => getEvolutionInfoTool.handler(args),
		},
		{
			...fetchEvolutionInstancesTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => fetchEvolutionInstancesTool.handler(args),
		},
		{
			...connectEvolutionInstanceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => connectEvolutionInstanceTool.handler(args),
		},
		{
			...getConnectionStateTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => getConnectionStateTool.handler(args),
		},
		{
			...logoutEvolutionInstanceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => logoutEvolutionInstanceTool.handler(args),
		},
		{
			...deleteEvolutionInstanceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => deleteEvolutionInstanceTool.handler(args),
		},
		{
			...restartEvolutionInstanceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => restartEvolutionInstanceTool.handler(args),
		},
		{
			...setEvolutionPresenceTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => setEvolutionPresenceTool.handler(args),
		},
		{
			...setEvolutionWebhookTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => setEvolutionWebhookTool.handler(args),
		},
		{
			...getEvolutionWebhookTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => getEvolutionWebhookTool.handler(args),
		},
		{
			...setEvolutionSettingsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => setEvolutionSettingsTool.handler(args),
		},
		{
			...getEvolutionSettingsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => getEvolutionSettingsTool.handler(args),
		},
		{
			...sendPlainTextTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendPlainTextTool.handler(args),
		},
		{
			...sendStatusTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendStatusTool.handler(args),
		},
		{
			...sendMediaTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendMediaTool.handler(args),
		},
		{
			...sendWhatsAppAudioTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendWhatsAppAudioTool.handler(args),
		},
		{
			...sendStickerTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendStickerTool.handler(args),
		},
		{
			...sendLocationTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendLocationTool.handler(args),
		},
		{
			...sendContactTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendContactTool.handler(args),
		},
		{
			...sendReactionTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendReactionTool.handler(args),
		},
		{
			...sendPollTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendPollTool.handler(args),
		},
		{
			...sendListTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendListTool.handler(args),
		},
		{
			...sendButtonsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => sendButtonsTool.handler(args),
		},
		{
			...fetchAllGroupsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => fetchAllGroupsTool.handler(args),
		},
		{
			...findGroupByJidTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => findGroupByJidTool.handler(args),
		},
		{
			...findGroupMembersTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => findGroupMembersTool.handler(args),
		},
		{
			...findChatsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => findChatsTool.handler(args),
		},
		{
			...findContactsTool,
			// biome-ignore lint/suspicious/noExplicitAny: All tools validate their input schemas, so any is fine.
			handler: (args: any) => findContactsTool.handler(args),
		},
	];
};