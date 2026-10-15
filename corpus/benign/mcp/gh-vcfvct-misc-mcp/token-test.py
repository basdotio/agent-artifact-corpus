import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv  # type: ignore

from openai import OpenAI, AzureOpenAI
from azure.identity import DefaultAzureCredential

# Load .env if present (no error if missing)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from openai import OpenAI

# Create a client configured for Azure OpenAI
client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
)

# Send a chat completion request
response = client.chat.completions.create(
    model="gpt-5-nano",  # This is your deployment name in Azure
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "what is the capital of Japan"},
    ],
    max_completion_tokens=16384,
)

# Print the model's reply
print(response.choices[0].message.content)
# print token usage
if response.usage:
    print(
        f"Prompt tokens: {response.usage.prompt_tokens}, Completion tokens: {response.usage.completion_tokens}, Total tokens: {response.usage.total_tokens}"
    )
