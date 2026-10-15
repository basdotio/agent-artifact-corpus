import os
from openai import OpenAI
from fastmcp import Client
import pandas as pd
import asyncio
import json


mcp = Client("server.py")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_gpt_for_chart(file_path, user_input):
    """Ask GPT what type of chart to create and which columns to use."""
    df = pd.read_csv(file_path)
    columns = df.columns.tolist()

    prompt = f"""
            You are a data visualization assistant. Given the following user request and the columns in the dataset, suggest the best chart type (bar, scatter, histogram) and which columns to use for x and y axes.
            User Request: "{user_input}"
            Dataset Columns: {columns}
            Respond in JSON format:
                {{
                    "chart_type": "...",
                    "x": "...",
                    "y": "..." (if applicable)
                }}
            """
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a data visualization assistant.."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def generate_visualization(file_path, user_input):

    """Decide chart type via GPT and Generate a visualization using mcp,based on user input."""
    chart_info = ask_gpt_for_chart(file_path, user_input)
    chart_info_json=json.loads(chart_info)
    chart_type = chart_info_json["chart_type"]
    x = chart_info_json["x"]
    y = chart_info_json.get("y", None)

    async with mcp:
        result = await mcp.call_tool("generate_plot", {"file_path": file_path, "chart_type": chart_type,"x":x,"y":y})
    return result.structured_content["chart_path"]


if __name__ == "__main__":
     #For testing purposes
     file_path = "uploaded.csv"
     user_input = "Show sales by date"
     chart_path = asyncio.run(generate_visualization(file_path, user_input))
     print(f"Chart saved at: {chart_path}")