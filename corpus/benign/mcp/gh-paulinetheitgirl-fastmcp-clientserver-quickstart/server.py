# fastmcp run server.py:mcp --transport http --port 8000 OR python server.py
import os
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("My MCP Server")
load_dotenv(override=False)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

@mcp.tool
def greet(name: str = "Jane Doe") -> str:
    """
    Greet the user by their name
    """
    client = OpenAI(
                    base_url=OPENAI_BASE_URL,
                    api_key=OPENAI_API_KEY  # Docker Model Runner doesn't require an API key!
                )
        
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", "content": f"Hi, my name is {name}"}
        ]
    )

    first_response = response.choices[0].message.content
    logging.info(first_response)

    return first_response

@mcp.tool
def compose_haiku(topic: str = "the sun") -> str:
    """
    Returns a haiku about the given topic
    """
    client = OpenAI(
                    base_url=OPENAI_BASE_URL,
                    api_key=OPENAI_API_KEY
                )
        
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", "content": f"Write a haiku about {topic}"}
        ],
        max_completion_tokens=50
    )

    haiku = response.choices[0].message.content
    logging.info(haiku)

    return haiku

if __name__ == "__main__":
    mcp.run(transport="http", host=os.getenv("MCP_SERVER_HOST"), port=int(os.getenv("MCP_SERVER_PORT")))

    