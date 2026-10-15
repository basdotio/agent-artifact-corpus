import ollama
import json

class Gemma:
    def __init__(self, model: str):
        self.client = ollama
        self.model = model

    def add_user_message(self, messages: list, message):
        if isinstance(message, list):
            for item in message:
                if isinstance(item, dict):
                    messages.append(item)
                else:
                    messages.append({"role": "user", "content": str(item)})
        elif isinstance(message, dict):
            messages.append(message)
        elif hasattr(message, 'content'):
            messages.append({"role": "user", "content": message.content})
        else:
            messages.append({"role": "user", "content": str(message)})

    def add_assistant_message(self, messages: list, message):
        if hasattr(message, 'message'):
            msg_obj = message.message
            assistant_msg = {
                "role": "assistant",
                "content": msg_obj.content or "",
            }
            if getattr(msg_obj, "tool_calls", None):
                assistant_msg["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in msg_obj.tool_calls
                ]
            messages.append(assistant_msg)
        elif hasattr(message, 'choices'):
            content = message.choices[0].message.content
            assistant_msg = {
                "role": "assistant",
                "content": content or "",
            }
            if message.choices[0].message.tool_calls:
                assistant_msg["tool_calls"] = message.choices[0].message.tool_calls
            messages.append(assistant_msg)
        elif isinstance(message, dict):
            messages.append(message)

    def text_from_message(self, message):
        if hasattr(message, 'message'):
            return message.message.content or ""
        if hasattr(message, 'choices'):
            return message.choices[0].message.content or ""
        if isinstance(message, dict):
            return message.get("content", "")
        return str(message)

    def has_tool_calls(self, message):
        if hasattr(message, 'message'):
            return bool(getattr(message.message, 'tool_calls', None))
        if hasattr(message, 'choices'):
            return bool(message.choices[0].message.tool_calls)
        return False

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=[],
        tools=None,
        thinking=False,
        thinking_budget=1024,
    ):
        formatted_tools = []
        if tools:
            for t in tools:
                if isinstance(t, dict) and "type" in t and "function" in t:
                    formatted_tools.append(t)
                elif isinstance(t, dict) and "name" in t:
                    formatted_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema", {}),
                        }
                    })

        msgs = list(messages)
        if system and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": system})

        response = self.client.chat(
            model=self.model,
            messages=msgs,
            tools=formatted_tools if formatted_tools else None,
            options={"temperature": temperature} if temperature is not None else None,
        )
        return response
