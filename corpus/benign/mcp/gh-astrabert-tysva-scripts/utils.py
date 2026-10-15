from llama_index.llms.groq import Groq
from llama_index.core.agent.workflow import AgentWorkflow, ToolCall, ToolCallResult
from llama_index.core.llms.structured_llm import StructuredLLM
from llama_index.core.llms import ChatMessage
from elevenlabs import AsyncElevenLabs
import uuid
import json
from typing import List
from pydantic import BaseModel, field_validator, Field, model_validator
from pathlib import Path
from dotenv import load_dotenv
from os import environ as ENV

load_dotenv()

elevenlabs_client = AsyncElevenLabs(api_key=ENV["elevenlabs_api_key"])
llm = Groq(model="llama-3.3-70b-versatile", api_key=ENV["groq_api_key"])

class Synthesis(BaseModel):
    process_synthesis: str = Field(description="Synthesis of the agentic process")
    response_synthesis: str = Field(description="Synthesis of the final response")

synth_llm = llm.as_structured_llm(Synthesis)

class Synthesizer:
    def __init__(self, llm: StructuredLLM):
        self.llm = llm
    def generate(self, agentic_process: str, final_response: str):
        if agentic_process != "":
            messages = [ChatMessage.from_str(role="system", content="You are an AI assistant that performs summarization of text contents regarding AI agentic processes and response, for people who are not able to read. Keep in mind, then, that you summarization must be suitable for a spoken conversation. Your only focus is providing summaries of what the user tells you to summarize."), ChatMessage.from_str(role="assistant", content=agentic_process), ChatMessage.from_str(role="assistant", content=final_response), ChatMessage.from_str(role="user", content="Could please summarize your process agentic process (the first message you sent me) and the final response (second message)?")]
            response = self.llm.chat(messages)
            text = response.message.blocks[0].text
            json_res = json.loads(text)
            return json_res["process_synthesis"], json_res["response_synthesis"]
    async def agenerate(self, agentic_process: str, final_response: str):
        messages = [ChatMessage.from_str(role="system", content="You are an AI assistant that performs summarization of text contents regarding AI agentic processes and response, for people who are not able to read. Keep in mind, then, that you summarization must be suitable for a spoken conversation. Your only focus is providing summaries of what the user tells you to summarize."), ChatMessage.from_str(role="assistant", content=agentic_process), ChatMessage.from_str(role="assistant", content=final_response), ChatMessage.from_str(role="user", content="Could please summarize your agentic process (the first message you sent me) and the final response (second message)?")]
        response = await self.llm.achat(messages)
        text = response.message.blocks[0].text
        json_res = json.loads(text)
        return json_res["process_synthesis"], json_res["response_synthesis"]

class GenerationInput(BaseModel):
    file: None | str
    prompt: None | str
    voice_enabled: bool
    chat_history: List[ChatMessage]
    @field_validator("file", mode="after")
    def is_valid_file(cls, file: None | str, mode="after"):
        if file is None:
            return file
        else:
            fl = Path(file)
            if fl.is_file():
                return file
            else:
                raise ValueError(f"{file} is not a file!")
    @model_validator(mode="after")
    def is_valid_input(self):
        if self.file is None and self.prompt is None:
            raise ValueError("'prompt' and 'file' fields are both set to None. Please set one of the two to a non-null value.")
        elif self.file is not None and self.prompt is not None:
            raise ValueError("'prompt' and 'file' fields are both set to a non-null value. Please set one of the two to a null value.")
        else:
            return self

class AiGenerator:
    def __init__(self, elevenlabs_client: AsyncElevenLabs, agent: AgentWorkflow, synthesizer: Synthesizer):
        self.elevenlabs_client = elevenlabs_client
        self.agent = agent
        self.synthesizer = synthesizer
    async def generate(self, inpt: GenerationInput):
        if (inpt.prompt is not None and inpt.file is None) or (inpt.prompt is not None and inpt.file is not None):
            process = ""
            handler = self.agent.run(user_msg=inpt.prompt, chat_history=inpt.chat_history)
            async for event in handler.stream_events():
                if isinstance(event, ToolCall):
                    process += "Calling tool **" + event.tool_name + "**" + " with arguments:\n```json\n" + json.dumps(event.tool_kwargs, indent=4) + "\n```\n"
                if isinstance(event, ToolCallResult):
                    process += f"Tool call result for **{event.tool_name}**: {event.tool_output}"
            response = await handler
            response = str(response)
            if inpt.voice_enabled:
                agentic_synth, res_synth = await self.synthesizer.agenerate(process, response)
                if process != "":
                    fin_synth = f"The agentic process that we followed was:\n\n{agentic_synth}\n\nThis brought to the following final result:\n\n{res_synth}"
                else:
                    fin_synth = res_synth
                r = self.elevenlabs_client.text_to_speech.convert(voice_id="NHRgOEwqx5WZNClv5sat",text=fin_synth, output_format="mp3_22050_32",model_id="eleven_turbo_v2_5")
                fl = str(uuid.uuid4())+".mp3"
                with open(fl,"wb") as f:
                    async for chunk in r:
                        if chunk:
                            f.write(chunk)
                f.close()
                return response, process, fl
            return response, process, None
        elif inpt.file is not None and inpt.prompt is None:
            with open(inpt.file, "rb") as fd:
                b = fd.read()
            fd.close()
            transcription = await self.elevenlabs_client.speech_to_text.convert(model_id="scribe_v1", file=b, tag_audio_events=True, diarize=True, language_code="eng")
            prompt = transcription.text
            process = ""
            handler = self.agent.run(user_msg=prompt, chat_history=inpt.chat_history)
            async for event in handler.stream_events():
                if isinstance(event, ToolCall):
                    process += "Calling tool **" + event.tool_name + "**" + " with arguments:\n```json\n" + json.dumps(event.tool_kwargs, indent=4) + "\n```\n"
                if isinstance(event, ToolCallResult):
                    process += f"Tool call result for **{event.tool_name}**: {event.tool_output}"
            response = await handler
            response = str(response)
            if inpt.voice_enabled:
                agentic_synth, res_synth = await self.synthesizer.agenerate(process, response)
                fin_synth = f"The agentic process that we followed was:\n\n{agentic_synth}\n\nThis brought to the following final result:\n\n{res_synth}"
                r = self.elevenlabs_client.text_to_speech.convert(voice_id="NHRgOEwqx5WZNClv5sat",text=fin_synth, output_format="mp3_22050_32",model_id="eleven_turbo_v2_5")
                fl = str(uuid.uuid4())+".mp3"
                with open(fl,"wb") as f:
                    async for chunk in r:
                        if chunk:
                            f.write(chunk)
                f.close()
                return response, process, fl
            return response, process, None
        else:
            return "There is no input provided", "There is no input provided", None
            