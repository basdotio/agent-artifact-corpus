#!/usr/bin/env python3
"""
Claimify MCP Server

A Model Context Protocol server that exposes the Claimify claim extraction tool.
This implements the multi-stage claim extraction methodology from the paper
"Towards Effective Extraction and Evaluation of Factual Claims".
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Any, Dict
import re
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.session import ServerSession
from mcp.types import Tool, TextContent, Resource, AnyUrl, Prompt, PromptArgument, PromptMessage, GetPromptResult
from pydantic import AnyUrl as PydanticAnyUrl
from dotenv import load_dotenv

# Set working directory to the script's directory
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

# Load environment variables from the script directory
load_dotenv(SCRIPT_DIR / ".env")

# Import our custom modules
from llm_client import LLMClient
from pipeline import ClaimifyPipeline

# Initialize the MCP server
server = Server("claimify-extraction-server")

# Store extracted claims
# Key: extraction ID, Value: dict with metadata and claims
claims_store: Dict[str, Dict[str, Any]] = {}
# Additionally index individual claim resources for fast lookup
# Key: slug (unique per claim) -> claim text
claim_index: Dict[str, str] = {}

# --- Prompt Templates ---

CLAIM_STATUS_DEFINITIONS = """Status Definitions:
- VERIFIED: Claim is clearly supported by reliable sources
- UNCERTAIN: Claim may be correct but lacks precision, has ambiguity, or limited evidence
- DISPUTED: Claim is demonstrably false or contradicted by sources"""

VERIFICATION_GUIDELINES = """Verification Guidelines:
- Only use authoritative and reliable sources (academic journals, reputable news, official institutions)
- Do NOT fabricate sources or URLs - only include sources you can actually access and verify
- Provide specific justification for each source
- Use UNCERTAIN for claims that are ambiguous, lack specificity (dates, scope, etc.), or have limited evidence
- Use DISPUTED only for claims that are clearly false or contradicted by reliable sources"""

CLAIM_FORMAT_TEMPLATES = """Format for VERIFIED claims:
**Status:** VERIFIED

**Evidence:**
- Source 1: [Title](URL) - Brief justification
- Source 2: [Title](URL) - Brief justification
- Source 3: [Title](URL) - Brief justification

Format for UNCERTAIN claims:
**Status:** UNCERTAIN

**Evidence:** (if available)
- Source 1: [Title](URL) - Partial support or context

**Analysis:**
Explain the ambiguity, missing details, or why full verification is not possible

Format for DISPUTED claims:
**Status:** DISPUTED

**Analysis:**
Explain why the claim is false, including contradictory evidence"""

CLAIMS_MD_STRUCTURE = """```markdown
# Claims Report

**Generated:** <current_date>
**Total Claims:** <count>
**TODO:** <count>
**In Progress:** 0
**Verified:** 0
**Uncertain:** 0
**Disputed:** 0

---

## Claims

### Claim 1
**Text:** <claim_text>

**Status:** TODO

---

### Claim 2
**Text:** <claim_text>

**Status:** TODO

---

...
```"""

def _slugify_claim(text: str) -> str:
    """Create a filesystem/URI safe slug from claim text.

    Rules:
    - Lowercase
    - Replace non-alphanumeric with hyphen
    - Collapse multiple hyphens
    - Trim leading/trailing hyphens
    - Limit length to 80 chars to avoid huge URIs
    - Ensure uniqueness by appending an increment if collision
    """
    base = text.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-+", "-", base).strip('-')
    if len(base) > 80:
        base = base[:80].rstrip('-')
    original = base
    counter = 2
    while base in claim_index:  # ensure uniqueness
        base = f"{original}-{counter}"
        counter += 1
    return base


# Define the extract_claims tool
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="extract_claims",
            description="""Extracts verifiable, decontextualized factual claims from a given text string.
Claims are decontextualized (self-contained) and verifiable. Each sentence is parsed with surrounding sentences as context. Do not call the tool with long texts as it will timeout (expect roughly 10 seconds per sentence).
If needed, break the text into smaller chunks and call the tool multiple times. Make sure to break in sections with enough context.

Example:
Input: "Apple INC did a fine result last quarter of 2024. The company's revenue increased by 15% due to strong sales."
Output: ["Apple INC's revenue increased by 15% last quarter of 2024"]""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text_to_process": {
                        "type": "string",
                        "description": "The input text string from which to extract claims."
                    },
                    "question": {
                        "type": "string",
                        "description": "An optional question that provides context for the text. This can help in resolving ambiguities during the disambiguation stage.",
                        "default": "The user did not provide a question."
                    }
                },
                "required": ["text_to_process"]
            }
        )
    ]


# --- Prompts ---
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """Expose verification prompt templates."""
    return [
        Prompt(
            name="verify_claim",
            description="Verify a single factual claim using reliable sources. Updates claim status from TODO → IN_PROGRESS → VERIFIED/UNCERTAIN/DISPUTED. Attach the claim as a resource in the context.",
            arguments=[]
        ),
        Prompt(
            name="create_claims_report",
            description="Create initial CLAIMS.md file with all claims marked as TODO. The file can then be updated incrementally as claims are verified (VERIFIED/UNCERTAIN/DISPUTED). Attach the extraction resource to the context.",
            arguments=[]
        ),
        Prompt(
            name="complete_claim_workflow",
            description="Complete end-to-end claim extraction and verification workflow: extract claims from text, create CLAIMS.md, and verify all claims.",
            arguments=[
                PromptArgument(
                    name="text_to_extract",
                    description="The text from which to extract and verify factual claims",
                    required=True
                )
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Return a rendered prompt for verification flow."""
    
    if name == "verify_claim":
        full_prompt = (
            "You are a fact-checker verifying claims from extracted text.\n\n"
            "Task: Verify a single claim by researching reliable sources.\n\n"
            "Workflow: All claims start with TODO status, move to IN_PROGRESS during verification, then become VERIFIED, UNCERTAIN, or DISPUTED.\n\n"
            "Instructions:\n"
            "1. Parse the claim text from the resource attached in the context\n"
            "2. Mark the claim as IN_PROGRESS in your response\n"
            "3. Search for evidence from reliable sources (academic journals, reputable news, official institutions)\n"
            "4. Determine the final status:\n"
            "   - VERIFIED: Claim is clearly supported by reliable sources\n"
            "   - UNCERTAIN: Claim may be correct but lacks precision, has ambiguity, or has limited/conflicting evidence\n"
            "   - DISPUTED: Claim is demonstrably false or contradicted by reliable sources\n"
            "5. Provide evidence and analysis based on the status\n\n"
            f"{VERIFICATION_GUIDELINES}\n\n"
            "Output Format:\n"
            "**Claim:** <claim_text>\n\n"
            "**Status:** VERIFIED / UNCERTAIN / DISPUTED\n\n"
            "**Evidence:** (for VERIFIED and UNCERTAIN)\n"
            "- Source 1: [Title](URL) - Justification\n"
            "- Source 2: [Title](URL) - Justification\n"
            "- Source 3: [Title](URL) - Justification (if available)\n\n"
            "**Analysis:**\n"
            "For UNCERTAIN: Explain the ambiguity, missing context, or why verification is incomplete\n"
            "For DISPUTED: Explain why the claim is false, including contradictory evidence\n\n"
            "The claim should be attached as a resource in your context.\n\n"
            "Begin verification now."
        )

        messages = [
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=full_prompt)
            )
        ]

        return GetPromptResult(
            description="Claim verification prompt",
            messages=messages
        )
    
    elif name == "create_claims_report":
        full_prompt = (
            "Task: Create a comprehensive CLAIMS.md file documenting all extracted claims with their verification status.\n\n"
            "Workflow: All claims start with TODO status, move to IN_PROGRESS during verification, then become VERIFIED, UNCERTAIN, or DISPUTED.\n\n"
            "Instructions:\n"
            "1. Parse the extraction data (JSON) attached in the context to get all claims\n"
            f"2. Create a CLAIMS.md file with the following structure:\n\n{CLAIMS_MD_STRUCTURE}\n\n"
            "3. Save the file as CLAIMS.md in the current directory\n"
            "4. IMPORTANT: Initially, ALL claims must have status TODO\n"
            "5. The file serves as a template that will be updated incrementally:\n"
            "   - Start: All claims marked TODO\n"
            "   - During verification: Update individual claims to IN_PROGRESS\n"
            "   - After verification: Update to VERIFIED, UNCERTAIN, or DISPUTED with evidence\n\n"
            f"{CLAIM_STATUS_DEFINITIONS}\n\n"
            f"{CLAIM_FORMAT_TEMPLATES}\n\n"
            f"Verification Guidelines (for later updates):\n{VERIFICATION_GUIDELINES}\n\n"
            "The extraction data should be attached as a resource in your context.\n\n"
            "Create the initial CLAIMS.md with all claims marked as TODO."
        )
        
        messages = [
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=full_prompt)
            )
        ]
        
        return GetPromptResult(
            description="Create CLAIMS.md report with verification status for all claims",
            messages=messages
        )
    
    elif name == "complete_claim_workflow":
        args = arguments or {}
        text_to_extract = args.get("text_to_extract", "")
        
        full_prompt = (
            "TASK: Extract factual claims from text and create a complete CLAIMS.md file with full verification for each claim.\n\n"
            "INSTRUCTIONS:\n\n"
            "Step 1: Call the extract_claims Tool\n"
            "- Use the extract_claims tool with the text provided below\n"
            "- The tool will return a JSON array of decontextualized, verifiable factual claims\n"
            "- Use this output for the next steps\n\n"
            "Step 2: Create and Populate CLAIMS.md File\n"
            f"- Using the claims from Step 1, IMMEDIATELY create a CLAIMS.md file with ALL claims marked as TODO:\n\n{CLAIMS_MD_STRUCTURE}\n\n"
            "Save this file immediately. It serves as a project status board.\n\n"
            "Step 3: Verify Each Claim (Update File Incrementally)\n"
            "For EACH claim in the file, verify it one by one and update the file after each verification:\n\n"
            "Verification Process:\n"
            "1. Search for evidence from reliable sources (academic journals, reputable news, official institutions)\n"
            "2. Determine status:\n"
            "   - VERIFIED: Claim is clearly supported by reliable sources (provide 3+ sources with URLs)\n"
            "   - UNCERTAIN: Claim may be correct but lacks precision, has ambiguity, or limited evidence\n"
            "   - DISPUTED: Claim is demonstrably false or contradicted by reliable sources\n"
            "3. Add verification results to the CLAIMS.md structure\n\n"
            f"{VERIFICATION_GUIDELINES}\n\n"
            f"{CLAIM_FORMAT_TEMPLATES}\n\n"
            "EXECUTION:\n"
            "1. First, call the extract_claims tool with the text below\n"
            "2. Immediately create and save CLAIMS.md with ALL claims marked as TODO (use the header structure above with counts)\n"
            "3. Then, research and verify EACH claim one by one:\n"
            "   - Update the specific claim's status in CLAIMS.md to IN_PROGRESS\n"
            "   - Research and determine final status (VERIFIED/UNCERTAIN/DISPUTED)\n"
            "   - Update the claim with evidence/analysis\n"
            "   - Update the header counts\n"
            "   - Save the file\n"
            "   - Move to next claim\n"
            "4. Continue until all claims are verified\n\n"
            "IMPORTANT: Create the CLAIMS.md file IMMEDIATELY after extraction (Step 2) so it serves as a status board.\n"
            "Update it incrementally as you verify each claim. This way, if interrupted, progress is saved.\n\n"
            "TEXT TO EXTRACT AND VERIFY:\n"
            "---\n"
            f"{text_to_extract}\n"
            "---\n\n"
            "Begin now by calling the extract_claims tool."
        )
        
        messages = [
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=full_prompt)
            )
        ]
        
        return GetPromptResult(
            description="Complete claim extraction and verification workflow",
            messages=messages
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "extract_claims":
        try:
            text_to_process = arguments.get("text_to_process", "")
            question = arguments.get("question", "The user did not provide a question.")
            
            # Get the session from the request context for MCP sampling support
            session = server.request_context.session if server.request_context else None
            
            # Initialize the LLM client with session for MCP sampling
            llm_client = LLMClient(session=session)
            pipeline = ClaimifyPipeline(llm_client, question)
            
            # Run the extraction pipeline asynchronously
            claims = await pipeline.run_async(text_to_process)
            
            # Store the claims and create per-claim indexed resources
            extraction_id = f"extraction_{len(claims_store) + 1}_{int(datetime.now().timestamp())}"
            timestamp = datetime.now().isoformat()
            text_preview = text_to_process[:100] + "..." if len(text_to_process) > 100 else text_to_process
            extraction_slug = _slugify_claim(text_preview)
            extraction_record = {
                "id": extraction_id,
                "slug": extraction_slug,
                "timestamp": timestamp,
                "question": question,
                "text_preview": text_preview,
                "claims": claims,
                "claim_count": len(claims)
            }
            claims_store[extraction_id] = extraction_record
            # Also index by slug for easy lookup
            claims_store[extraction_slug] = extraction_record

            # Populate individual claim entries with slug URIs
            for claim_text in claims:
                slug = _slugify_claim(claim_text)
                claim_index[slug] = claim_text
            
            # Return the claims as actual structured data
            result = json.dumps(claims, indent=2)
            
            # Notify that the resource list has changed
            # Note: We'll do this via the stored extraction
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            error_msg = f"Error during claim extraction: {str(e)}"
            return [TextContent(type="text", text=error_msg)]
    else:
        raise ValueError(f"Unknown tool: {name}")


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all claim resources (each individual claim plus aggregate extraction root)."""
    resources: list[Resource] = []

    # Root extraction resources (aggregate)
    seen_extractions = set()
    for extraction_id, extraction_data in claims_store.items():
        # Skip if we've already added this extraction (since we store by both ID and slug)
        if extraction_data['id'] in seen_extractions:
            continue
        seen_extractions.add(extraction_data['id'])
        
        resources.append(Resource(
            uri=AnyUrl(f"claim://{extraction_data['slug']}"),
            name=f"Extraction: {extraction_data['text_preview'][:50]}...",
            description=f"Extraction with {extraction_data['claim_count']} claims at {extraction_data['timestamp']}: {extraction_data['text_preview']}",
            mimeType="application/json"
        ))

    # Individual claim resources (slug based)
    for slug, claim_text in claim_index.items():
        resources.append(Resource(
            uri=AnyUrl(f"claim://{slug}"),
            name=slug,
            description=claim_text[:100] + ("..." if len(claim_text) > 100 else ""),
            mimeType="text/plain"
        ))

    return resources


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str | bytes:
    """Read an extraction (aggregate) or individual claim resource.

    URI patterns:
    - claim://<slug-from-text-preview>  (aggregate extraction - JSON)
    - claim://<slug-from-claim-text>    (individual claim - plain text)
    """
    target = str(uri).replace("claim://", "")

    # Individual claim (slug only returns raw text)
    if target in claim_index:
        return claim_index[target]

    # Aggregate extraction (JSON) - lookup by slug or extraction_id
    if target in claims_store:
        record = claims_store[target]
        # Return only the extraction data, not duplicates
        return json.dumps({
            "id": record['id'],
            "timestamp": record['timestamp'],
            "question": record['question'],
            "text_preview": record['text_preview'],
            "claims": record['claims'],
            "claim_count": record['claim_count']
        }, indent=2)

    raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Main entry point for the server."""
    # Check for configuration
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    
    # Log configuration to stderr (so it doesn't interfere with MCP protocol on stdout)
    print(f"Starting Claimify MCP Server...", file=sys.stderr)
    
    if has_api_key:
        print(f"OpenAI API key found - will use as fallback if MCP sampling unavailable", file=sys.stderr)
        print(f"LLM Provider: {provider}", file=sys.stderr)
        print(f"Model: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}", file=sys.stderr)
    else:
        print("No OpenAI API key found - will require MCP sampling support from client", file=sys.stderr)
    
    print("Server is ready to accept connections via stdio.", file=sys.stderr)
    
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, 
                        server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main()) 