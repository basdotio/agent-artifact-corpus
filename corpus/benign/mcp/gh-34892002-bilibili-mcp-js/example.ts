import { MCPToolkit } from "./mcp-langchain-ts-client/index.js";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { ChatOpenAI } from "@langchain/openai";
import { MemorySaver } from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";

import path from "path";

const isBun = typeof process.versions.bun !== 'undefined';
const serverParams = {
  command: isBun ? "bun" : "node",
  args: [path.join(process.cwd(), "dist", "index.js")]
};

const memory = new MemorySaver();

// Initialize the toolkit
const toolkit = new MCPToolkit(serverParams);
await toolkit.initialize();

// Extract LangChain.js compatible tools
const tools = toolkit.tools;
console.log('可用工具列表:');
tools.forEach(tool => {
  console.log(`- 工具名称: ${tool.name}`);
  console.log(`  描述: ${tool.description}`);
  console.log('---');
});

const llm = new ChatOpenAI({
  modelName: "gpt-4o-mini",
  temperature: 0,
  openAIApiKey: "your_api_key", // 替换成你模型的密钥
  configuration: {
    baseURL: "https://www.api.com/v1", // 替换成你模型的API地址
  },
});

const agent = createReactAgent({ 
  llm, 
  tools,
  checkpointSaver: memory,
});

const result = await agent.invoke(
  { messages: [new HumanMessage("搜索b站'蓝色战衣',输出作者排行榜")] },
  { configurable: { thread_id: "42" } }
);
console.log("Agent response:", result.messages[result.messages.length - 1].content);
