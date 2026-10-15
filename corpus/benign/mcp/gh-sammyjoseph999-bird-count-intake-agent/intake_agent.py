"""Agent for the Marrow Creek bird count intake.

Reads three messy sources, works through them with the tools in
intake_server.py, and writes two files:

    clean_roster.json   one validated record per sighting
    review_queue.json   everything that needs a person to look at it

Usage:
    python intake_agent.py
"""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from intake_server import DATA_DIR, ROSTER, mcp

load_dotenv()

MODEL = os.environ.get("INTAKE_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = 40
OUTPUT_DIR = Path(__file__).resolve().parent

# Order matters: when two sources report the same sighting, the first one
# committed is kept and the later one goes to review as a possible duplicate.
SOURCE_FILES = [
    ("logbook", "source1_logbook.txt", "2026-09-19 (the date written at the top of the logbook)"),
    ("email", "source2_email.txt", "2026-09-21 (the day the email was sent, a Monday)"),
    ("spreadsheet", "source3_spreadsheet.json", "year 2026 (rows give month/day only)"),
]

SYSTEM_PROMPT = """You are the intake clerk for the Marrow Creek autumn bird count.
You receive one source of sightings at a time, written by volunteers. Turn every
sighting in it into either a committed record or a review item, using the tools.

Work through the source one sighting at a time:

1. Call resolve_species with the bird's name as the observer wrote it (singular,
   without counts or filler words, typos left as they are). You never decide what
   species a bird is. Only the tool's answer counts.
2. If the tool returns no_match, call flag_for_review with reason unknown_species.
   If it returns a category other than "species", flag with reason species_group.
3. Work out the count, the date and the location from the note.
   - A count must be a definite number. "pair" is 2 and "half a dozen" is 6, and
     a stated estimate such as "about 20" or "12 (est)" is 20 or 12. Words like
     "a handful", "a flock", "a few" or "lots" are not a number: flag vague_count.
   - Dates must be YYYY-MM-DD. Use the reference date to work out "yesterday",
     a weekday name or a month/day. If the day cannot be pinned down, flag
     unclear_date. If the date is clear but outside the count week, flag
     outside_count_window.
   - If the species, count or location is missing or blank, flag missing_field.
     Never fill a gap with a guess, and never borrow a value from another sighting
     unless the source clearly applies it (a logbook section heading gives the
     location for the lines under it).
4. Otherwise call commit_observation. It is the final authority: it re-checks the
   record and detects duplicates on its own. If it reports a duplicate, do
   nothing more for that sighting. If it rejects the record, flag the note with
   the matching reason, or invalid_record if none of the others fits.

When several reasons apply, use the first that matches in this order:
unknown_species, species_group, missing_field, vague_count, unclear_date,
outside_count_window, invalid_record.

Always pass the original wording of the note as raw_input. Handle every sighting
exactly once. When the whole source is done, reply with a one-line summary and
no tool call."""


def load_mcp_tools(mcp_server):
    """Read the server's tools and return them in the shape the OpenAI API expects.

    Returns (openai_tools, tool_functions): the tool definitions to send to the
    model, and a map from tool name to the Python function behind it.
    """
    # FastMCP renamed get_tools() to list_tools(); support both
    if hasattr(mcp_server, "list_tools"):
        tools = asyncio.run(mcp_server.list_tools())
    else:
        tools = asyncio.run(mcp_server.get_tools())
    if isinstance(tools, dict):
        tools = list(tools.values())

    openai_tools, tool_functions = [], {}
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        })
        tool_functions[tool.name] = tool.fn
    return openai_tools, tool_functions


def execute_tool(function_name, arguments, tool_functions):
    """Run one tool call and return its result as a JSON string for the model."""
    if function_name not in tool_functions:
        return json.dumps({"error": f"Unknown tool: {function_name}"})
    try:
        return json.dumps(tool_functions[function_name](**arguments))
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


class IntakeAgent:
    def __init__(self, client, mcp_server, model=MODEL):
        self.client = client
        self.model = model
        self.tools, self.tool_functions = load_mcp_tools(mcp_server)

    def run_source(self, source_name, content, reference_date):
        """Run the tool loop over one source and return the model's closing summary."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Source: {source_name}\n"
                f"Reference date: {reference_date}\n\n"
                f"{content}"
            )},
        ]

        for _ in range(MAX_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.2,
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content

            messages.append(message)
            for call in message.tool_calls:
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    result = execute_tool(call.function.name, arguments, self.tool_functions)
                except json.JSONDecodeError as e:
                    result = json.dumps({"error": f"Arguments were not valid JSON: {e}"})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        return "Max iterations reached"


def print_summary(summary):
    print(f"\nCommitted {summary['committed']} records, flagged {summary['flagged']} for review.")
    print("\nBirds counted, by species:")
    for name, total in summary["birds_by_species"].items():
        print(f"  {total:>4}  {name}")
    print("\nReview queue, by reason:")
    for reason, total in summary["flags_by_reason"].items():
        print(f"  {total:>4}  {reason}")


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Add it to a .env file in this folder.")

    agent = IntakeAgent(OpenAI(api_key=api_key), mcp)
    ROSTER.reset()

    for source_name, filename, reference_date in SOURCE_FILES:
        content = (DATA_DIR / filename).read_text(encoding="utf-8")
        print(f"[{source_name}] processing...")
        print(f"[{source_name}] {agent.run_source(source_name, content, reference_date)}")

    (OUTPUT_DIR / "clean_roster.json").write_text(json.dumps(ROSTER.clean, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "review_queue.json").write_text(json.dumps(ROSTER.review, indent=2), encoding="utf-8")
    print_summary(ROSTER.summary())


if __name__ == "__main__":
    main()
