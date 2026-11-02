from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.tools import load_mcp_tools
import asyncio
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import render_text_description
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub



model = ChatOllama(model="llama3.2")



server_params = StdioServerParameters(
    command="python",
    args=["math_server.py"]
)

async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools=await load_mcp_tools(session)


            prompt = hub.pull("hwchase17/react-json")
            prompt = prompt.partial(
                tools=render_text_description(tools),
                tool_names=", ".join([t.name for t in tools]),
            )

            agent = create_react_agent(model, tools,prompt)

            print(agent)


            agent_executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, verbose=False, format="json")


            agent_response = agent_executor.invoke({"input":"what's (3 + 5)"})
            return agent_response
        
if __name__ == "__main__":
    result = asyncio.run(run_agent())
    print(result)
        



