import gradio as gr
import time
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from utils import llm, AiGenerator, elevenlabs_client, synth_llm, Synthesizer, GenerationInput, BaseModel, ChatMessage, List
import requests as rq

SYSTEM_PROMPT = """\
You are an AI assistant with deep expertise in the programming language TypeScript.

Before you help a user, make sure that you know the context in which the user is working, the situation in which they are, so that you have all the relevant information to provide precise and on-point answers for their questions.

Available to you are two tools:
- 'deepsearch_tool' tool: it takes a query (str) as an input and returns an answer. It is useful to search for precise information in the depths of the web when you need to answer advanced and/or complicated questions by the user about Typescript (especially debugging and errors).
- 'documentation_search_tool' tool: it takes a query (str) as an input and returns an answer. It is useful to search for specific information within a database containing TypeScript documentation.

IMPORTANT INSTRUCTIONS:
1. If the questions are easy and basic, you don't have to use tools, you can base yourself off the knowledge you have of TypeScript
2. You must politely dismiss all the requests that do not concern TypeScript
"""

app = FastAPI(default_response_class=ORJSONResponse)
mcp_client = BasicMCPClient("http://localhost:8000/sse")
mcp_tools = McpToolSpec(mcp_client)
CHAT_HISTORY: List[ChatMessage] = []

class ApiOutput(BaseModel):
    response: str
    process: str
    audio_file: str | None

@app.post("/chat")
async def chat(inpt: GenerationInput) -> ApiOutput:
    tools = await mcp_tools.to_tool_list_async()
    agent = FunctionAgent(
        name="Agent",
        description="An agent that can review pull requests and send messages on Discord",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    workflow = AgentWorkflow(agents=[agent], root_agent="Agent")
    summarizer = Synthesizer(llm=synth_llm)
    ai_gen = AiGenerator(elevenlabs_client=elevenlabs_client, agent=workflow, synthesizer=summarizer)
    response, process, audio_file = await ai_gen.generate(inpt)
    return ApiOutput(response=response, process=process, audio_file=audio_file)

def route_to_api(files: List[str], messages: List[str], voice_enabled: bool):
    if len(messages) > 0 and len(files) >= 0:
        inpt = GenerationInput(file=None, prompt=messages[0], voice_enabled=voice_enabled, chat_history=CHAT_HISTORY)
        response = rq.post("http://localhost:7999/chat", json=inpt.model_dump())
        res_json = response.json()
        CHAT_HISTORY.append(ChatMessage.from_str(content=messages[0], role="user"))
        CHAT_HISTORY.append(ChatMessage.from_str(content=res_json["process"], role="assistant"))
        CHAT_HISTORY.append(ChatMessage.from_str(content=res_json["response"], role="assistant"))
        return res_json["response"], res_json["process"], res_json["audio_file"]
    else:
        inpt = GenerationInput(file=files[0], prompt=None, voice_enabled=voice_enabled, chat_history=CHAT_HISTORY)
        response = rq.post("http://localhost:7999/chat", json=inpt.model_dump())
        res_json = response.json()
        CHAT_HISTORY.append(ChatMessage.from_str(content=f"My prompt is contained in this audio file: {files[0]}", role="user"))
        CHAT_HISTORY.append(ChatMessage.from_str(content=res_json["process"], role="assistant"))
        CHAT_HISTORY.append(ChatMessage.from_str(content=res_json["response"], role="assistant"))
        return res_json["response"], res_json["process"], res_json["audio_file"]

def add_message(history, message):
    for x in message["files"]:
        history.append({"role": "user", "content": {"path": x}})
    if message["text"] is not None:
        history.append({"role": "user", "content": message["text"]})
    return history, gr.MultimodalTextbox(value=None, interactive=False)

def bot(history: list, voice_enabled: bool):
    messages = history.copy()
    messages.reverse()
    sliced_messages = []
    print(voice_enabled)
    for message in messages:
        if message["role"] == "assistant":
            break
        else:
            sliced_messages.append(message)
    files_only = [d["content"][0] for d in sliced_messages if type(d["content"]) == tuple]
    messages_only = [d["content"] for d in sliced_messages if type(d["content"]) == str and d["content"]!='']
    response, process, audio_file = route_to_api(files=files_only, messages=messages_only, voice_enabled=voice_enabled)
    if audio_file is not None:
        history.append({"role": "assistant", "content": f"<details>\n\t<summary><b>Agentic Process</b></summary>\n\n{process}\n\n</details>\n\n{response}"})
        history.append({"role": "assistant", "content": {"path": audio_file}})
    else:
        history.append({"role": "assistant", "content": f"<details>\n\t<summary><b>Agentic Process</b></summary>\n\n{process}\n\n</details>\n\n{response}"})
    return history

with gr.Blocks(theme=gr.themes.Ocean(), title="TySVA") as demo:
    title = gr.HTML("<h1 align='center'>TySVA</h1>\n<h2 align='center'>Learn TypeScript chatting effortlessly with AI</h2>")
    chatbot = gr.Chatbot(elem_id="chatbot", bubble_full_width=False, type="messages", min_height=700, min_width=700, label="TySVA", show_copy_all_button=True)
    chat_input = gr.MultimodalTextbox(
        interactive=True,
        placeholder="Enter message or say something...",
        show_label=False,
        sources=["microphone"],
    )

    voice_enabled = gr.Checkbox(value=True, label="Enable Voice Response")

    chat_msg = chat_input.submit(
        add_message, [chatbot, chat_input], [chatbot, chat_input]
    )
    bot_msg = chat_msg.then(bot, [chatbot, voice_enabled], chatbot, api_name="bot_response")
    bot_msg.then(lambda: gr.MultimodalTextbox(interactive=True), None, [chat_input])

app = gr.mount_gradio_app(app, demo, path="/app")