from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chat_models import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# Define prompt + model
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a smart web + PDF assistant."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad")
])
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3, google_api_key=os.getenv("GEMINI_API_KEY"))
agent = create_tool_calling_agent(llm=llm.bind_tools([your_tools]), tools=[your_tools], prompt=prompt)
executor = AgentExecutor(agent=agent, tools=[your_tools], verbose=True)
