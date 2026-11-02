from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from langchain_core.tools import render_text_description
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_community.chat_models import ChatOllama



model = ChatOllama(model="llama3.2")


async def run_agent():
    async with MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["/home/botadmin/New Experiment/MCP/math_server.py"],
                "transport": "stdio",
            },
            "weather": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    ) as client:


        tools= client.get_tools() #await load_mcp_tools(session)


        prompt = hub.pull("hwchase17/react-json")
        prompt = prompt.partial(
            tools=render_text_description(tools),
            tool_names=", ".join([t.name for t in tools]),
        )

        agent = create_react_agent(model, tools,prompt)

        agent_executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, verbose=False, format="json")


        math_response =  agent_executor.invoke({"input":"what's (4+6)"})
        weather_response = agent_executor.invoke({"input":"how is the weather in new york"})

        print("!!!!!!!!!!!!!!")
        print(math_response)
        print(weather_response)
        print("!!!!!!!!!!!!!!!!")

        return math_response,weather_response
    
if __name__ == "__main__":
    maths_result,weather_response = asyncio.run(run_agent())
    print("Math Result: " + str(maths_result))
    print("Weather Response: " + str(weather_response))


