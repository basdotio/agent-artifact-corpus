import dotenv from 'dotenv'
dotenv.config()

export const SERVER_CONFIG = {
  name: 'promptopia-mcp',
  version: '1.1.0',
  capabilities: {
    tools: {},
    prompts: {
      listChanged: true  // Added listChanged capability
    }
  }
}

export const PROMPTS_CONFIG = {
  promptsDir: process.env.PROMPTS_DIR ?? './prompts'
}
