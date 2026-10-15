import json
from enum import Enum
from typing import Any, Callable, Dict, List

from openai import OpenAI
from pydantic import BaseModel


class VLLMClient:
    """A clean wrapper for interacting with vLLM via OpenAI API"""

    def __init__(
        self,
        base_url: str = "http://host.docker.internal:8000/v1",
        api_key: str = "dummy-key",
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self._model_id = None

    @property
    def model_id(self) -> str:
        """Get the first available model ID"""
        if self._model_id is None:
            self._model_id = self.client.models.list().data[0].id
        return self._model_id

    def get_models(self):
        """List all available models"""
        return self.client.models.list()

    def chat(self, message: str, model: str = None) -> Any:
        """Simple chat completion"""
        model = model or self.model_id
        response = self.client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": message}]
        )
        return response

    def chat_with_tools(
        self,
        message: str,
        tools: List[Dict],
        tool_functions: Dict[str, Callable],
        model: str = None,
    ) -> Dict:
        """Chat with function calling capabilities"""
        model = model or self.model_id
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            tools=tools,
            tool_choice="auto",
        )

        result_dict = {"response": response, "tool_call": None, "result": None}

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0].function
            function_to_call = tool_functions[tool_call.name]
            result = function_to_call(**json.loads(tool_call.arguments))
            result_dict.update({"tool_call": tool_call, "result": result})

        return result_dict

    def structured_chat(self, message: str, schema: Dict, model: str = None) -> Any:
        """Chat with structured JSON output"""
        model = model or self.model_id
        completion = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            extra_body={"guided_json": schema},
        )
        return completion


# Predefined tool functions
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b


def divide(a: int, b: int) -> float:
    """Divide two numbers"""
    if b == 0:
        raise ValueError("b must not be zero")
    return a / b


# Tool definitions
MATH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "divide",
            "description": "Divide two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "Dividend"},
                    "b": {"type": "integer", "description": "Divisor"},
                },
                "required": ["a", "b"],
            },
        },
    },
]

MATH_TOOL_FUNCTIONS = {"add": add, "multiply": multiply, "divide": divide}


# Example Pydantic models for structured output
class CarType(str, Enum):
    sedan = "sedan"
    suv = "SUV"
    truck = "Truck"
    coupe = "Coupe"


class CarDescription(BaseModel):
    brand: str
    model: str
    car_type: CarType
