from contextlib import AsyncExitStack
from pathlib import Path
from mcp.client.stdio import stdio_client
import asyncio
from util.config import settings

from openai import AsyncAzureOpenAI

class OpenAIClient:
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        self.openai_client = AsyncAzureOpenAI(
            api_key= settings.MODEL_API_KEY,
            api_version=settings.MODEL_API_VERSION,
            azure_endpoint= settings.MODEL_URL
            )
        
    async def generate_sql_from_nl(self,schema:str,user_query: str):
        """Process a query using OpenAI and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from OpenAI.
        """
        try:
            # Construct messages with schema context
            system_prompt = (
                "You are an expert PostgreSQL assistant. "
                "Use the following schema metadata to generate SQL:\n\n"
                f"{schema}\n\n"
                "Use fully qualified names like 'schema.table' also consider end_date columns for calculation unless the user query mentioned about inactive status. Only return the SQL query, no comments or extra text."
            )
            response = await self.openai_client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    { "role": "system", "content": system_prompt },
                    { "role": "user", "content": user_query }
                ],
                temperature=0.7,
                top_p=1.0
            )
    
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error: {str(e)}")
    
