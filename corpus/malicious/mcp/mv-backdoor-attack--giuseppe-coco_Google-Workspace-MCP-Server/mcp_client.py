import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
   load_dotenv()
   config = {
      "mcpServers": {
         "gsuite": {
            "command": "python",
            "args": [f"{os.getenv("MCP_SERVER_ABS_PATH")}"],
         }
      }
   }

   client = MCPClient.from_dict(config)

   llm = ChatOpenAI(model="gpt-4o")

   # Create agent with the client
   agent = MCPAgent(llm=llm, client=client, max_steps=30)

   result = await agent.run(
      """
      Create a Google Calendar Event based on the content of the last mail being sent to my inbox.
      If you cannot create an event, create a sort of "reminder event" in order to remind me to check that email. 
      """,
   )
   print(f"\nResult: {result}")

if __name__ == "__main__":
   asyncio.run(main())