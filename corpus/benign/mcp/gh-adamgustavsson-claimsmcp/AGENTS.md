# AGENTS.md - Project Documentation for AI Agents

## Project Overview

**ClaimsMCP** is a Model Context Protocol (MCP) server that implements the "Claimify" research methodology for extracting verifiable factual claims from text. This is a production-ready implementation using OpenAI's structured outputs API and follows the peer-reviewed approach from "Towards Effective Extraction and Evaluation of Factual Claims" by Metropolitansky & Larson (2025).

**Key Insight**: This is NOT just another text extraction tool. It implements a sophisticated 4-stage academic pipeline that filters out opinions, resolves ambiguities, and produces atomic, self-contained claims.

## Architecture at a Glance

```
User Text → MCP Server → Pipeline → LLM Client → MCP Sampling (primary)
                            ↓                    ↓ (or fallback)
         [Splitting → Selection → Disambiguation → Decomposition]
                            ↓                    ↓
                    Structured Claims        OpenAI API
```

## Core Components

### 1. `claimify_server.py` - MCP Server Entry Point
- **Purpose**: Exposes claim extraction as an MCP tool via stdio
- **Protocol**: Uses Model Context Protocol for client communication
- **Tool**: `extract_claims(text_to_process, question)` - the main interface
- **Important**: Uses stdio (stdin/stdout), NOT HTTP - this is intentional for MCP
- **Async**: Built on asyncio, runs single-threaded event loop

**Key Implementation Details**:
- Returns JSON array of claims as string
- Error handling wraps all exceptions
- Validates API keys on startup
- Logs to stderr (stdout reserved for MCP protocol)

### 2. `pipeline.py` - Core Extraction Logic
- **Purpose**: Orchestrates the 4-stage Claimify methodology
- **Architecture**: Each stage is a separate function with structured I/O

**The 4 Stages**:

1. **Sentence Splitting** (`split_into_sentences`)
   - Uses NLTK's punkt tokenizer
   - Handles paragraphs and list items
   - Maintains sentence boundaries accurately

2. **Selection Stage** (`run_selection_stage`)
   - Filters for sentences with verifiable propositions
   - Removes opinions, speculation, generic statements
   - Uses surrounding context (p=5, f=5 sentences)
   - Returns: `('verifiable', sentence)` or `('unverifiable', None)`

3. **Disambiguation Stage** (`run_disambiguation_stage`)
   - Resolves pronouns, acronyms, partial names
   - Addresses referential and structural ambiguity
   - Only proceeds if ambiguity can be resolved with context
   - Returns: `('resolved', sentence)` or `('unresolvable', None)`

4. **Decomposition Stage** (`run_decomposition_stage`)
   - Breaks sentences into atomic claims
   - Adds clarifying context in [brackets]
   - Ensures each claim is self-contained
   - Returns: `List[str]` of claims

**Flow Control**:
- Each sentence processes through all stages sequentially
- Early exit if any stage filters out the sentence
- Final output is deduplicated list of all claims

**Context Windows**:
- Fixed at p=5, f=5 (preceding/following sentences)
- Based on paper's experimental findings
- Balance between context richness and token cost

### 3. `llm_client.py` - LLM Communication Layer
- **Purpose**: Handles all LLM communication via MCP sampling (primary) or OpenAI API (fallback)
- **Key Feature**: Tries MCP sampling first, falls back to OpenAI's `beta.chat.completions.parse` API
- **Type Safety**: All responses validated against Pydantic models (via JSON parsing for sampling, native for API)
- **Model Support**: MCP sampling works with any model; OpenAI API requires gpt-4o-2024-08-06, gpt-4o-mini, gpt-4o

**Critical Methods**:
- `make_structured_request(system_prompt, user_prompt, response_model, stage)` - Main entry point, tries sampling then API
- `_make_sampling_request()` - Uses MCP `session.create_message()` with retry logic for malformed JSON
- `_make_openai_request()` - Direct OpenAI API call with structured outputs
- `_extract_json_from_text()` - Parses JSON from text responses (handles markdown code blocks)
- Returns parsed Pydantic model or None on failure
- Handles refusals and validation errors explicitly

**Retry Logic**:
- MCP sampling responses are parsed as JSON and validated with Pydantic
- On validation failure, retries up to `SAMPLING_MAX_RETRIES` times with error hints
- Validation errors are included in retry prompts to guide LLM corrections

**Logging Strategy**:
- Controlled by `LOG_LLM_CALLS` env var
- Logs to stderr or file (configurable)
- Captures: method used (sampling/API), prompts, responses, token usage, duration
- Each call numbered for tracing through pipeline

### 4. `structured_models.py` - Pydantic Response Schemas
- **Purpose**: Define strict response formats for structured outputs
- **Type Safety**: Enforced by OpenAI API, not just validation

**Models**:

```python
SelectionResponse:
  - sentence: str
  - thought_process: str  # 4-step CoT
  - final_submission: Literal["Contains...", "Does NOT contain..."]
  - sentence_with_only_verifiable_information: Optional[str]

DisambiguationResponse:
  - incomplete_names_acronyms_abbreviations: str
  - linguistic_ambiguity_analysis: str
  - changes_needed: Optional[str]
  - decontextualized_sentence: Optional[str]

DecompositionResponse:
  - sentence: str
  - referential_terms: Optional[str]
  - max_clarified_sentence: str
  - proposition_range: str  # "3-5"
  - propositions: List[str]
  - final_claims: List[Claim]

Claim:
  - text: str
  - verifiable: bool = True  # Always True, guides LLM thinking
```

**Why Structured Outputs**:
- No regex parsing failures
- Guaranteed schema compliance
- Explicit refusal handling
- Better error messages
- Reduced retry logic needs

### 5. `structured_prompts.py` - Stage Prompts
- **Purpose**: Contains the academic methodology as system prompts
- **Source**: Adapted from Metropolitansky & Larson (2025) paper
- **Modification**: Optimized for both structured outputs (OpenAI) and JSON parsing (MCP sampling)
- **JSON Instructions**: Each prompt includes explicit JSON schema requirements for MCP sampling compatibility

**Multi-Language Support**:
- All prompts include critical language requirement
- Content preserved in original language
- Structural keywords in English
- Examples demonstrate preservation

**Prompt Engineering Notes**:
- Very detailed with many examples (from paper)
- Uses chain-of-thought for selection/disambiguation
- Explicit rules about what to filter
- Examples cover edge cases
- **NEW**: Explicit JSON format instructions at end of each prompt for sampling compatibility

## Data Flow Example

**Input**: "Apple Inc. was founded in 1976 by Steve Jobs. The company is incredibly innovative."

1. **Splitting**: 
   - ["Apple Inc. was founded in 1976 by Steve Jobs.", "The company is incredibly innovative."]

2. **Selection** (Sentence 1):
   - Status: verifiable
   - Output: "Apple Inc. was founded in 1976 by Steve Jobs."

3. **Selection** (Sentence 2):
   - Status: unverifiable (opinion about "innovative")
   - Filtered out

4. **Disambiguation** (Sentence 1):
   - Status: resolved
   - Output: "Apple Inc. was founded in 1976 by Steve Jobs." (no changes needed)

5. **Decomposition** (Sentence 1):
   - Output: ["Apple Inc. was founded in 1976", "Steve Jobs founded Apple Inc."]

**Final Claims**: ["Apple Inc. was founded in 1976", "Steve Jobs founded Apple Inc."]

## Environment Configuration

**Required**:
- None (can run with just MCP sampling)

**Optional**:
- `OPENAI_API_KEY` - For OpenAI API fallback when MCP sampling unavailable
- `LLM_MODEL` - Default: "gpt-4o-2024-08-06" (only used for OpenAI API fallback)

**MCP Sampling Configuration**:
- `SAMPLING_MAX_TOKENS_SELECTION` - Default: "500" (max tokens for selection stage)
- `SAMPLING_MAX_TOKENS_DISAMBIGUATION` - Default: "400" (max tokens for disambiguation stage)
- `SAMPLING_MAX_TOKENS_DECOMPOSITION` - Default: "800" (max tokens for decomposition stage)
- `SAMPLING_MAX_RETRIES` - Default: "2" (max retries for malformed JSON responses)

**Logging**:
- `LOG_LLM_CALLS` - Default: "true" (set to "false" to disable)
- `LOG_OUTPUT` - Default: "stderr" (or "file")
- `LOG_FILE` - Default: "claimify_llm.log" (if LOG_OUTPUT=file)

**Model Compatibility**:
- **MCP Sampling**: Works with any model the client supports
- **OpenAI API Fallback**: Only these models support structured outputs:
  - gpt-4o-2024-08-06 (recommended)
  - gpt-4o-mini (faster/cheaper)
  - gpt-4o (latest)

## Common Agent Tasks

### Adding a New Stage

1. Create Pydantic model in `structured_models.py`
2. Write system prompt in `structured_prompts.py`
3. Add `run_<stage>_stage()` function in `pipeline.py`
4. Add parsing function `parse_structured_<stage>_output()`
5. Insert into pipeline flow in `ClaimifyPipeline.run()`

### Modifying Prompts

**Location**: `structured_prompts.py`

**Guidelines**:
- Keep multi-language requirement
- Maintain example structure
- Test with various languages
- Update Pydantic model if changing fields
- Structured outputs enforce schema, so less format instruction needed

### Debugging Pipeline Issues

**Check logs first**:
```python
# Enable detailed logging
LOG_LLM_CALLS=true
LOG_OUTPUT=stderr  # or file
```

**Log sections**:
- Each LLM call numbered
- Stage identifier
- Full prompts and responses
- Token usage
- Duration

**Common issues**:
- Sentence filtered at selection → check thought_process field
- Can't disambiguate → check linguistic_ambiguity_analysis
- No claims extracted → check all stages in logs
- Model errors → verify model supports structured outputs

### Testing Changes

**Manual testing**:
```python
from llm_client import LLMClient
from pipeline import ClaimifyPipeline

client = LLMClient()
pipeline = ClaimifyPipeline(client, "What is the history of Apple?")
claims = pipeline.run("Apple Inc. was founded in 1976 by Steve Jobs.")
print(claims)
```

**Automated tests**:
```bash
python test_claimify.py
```

### Performance Considerations

**Token costs**:
- Each sentence goes through 3 LLM calls (selection, disambiguation, decomposition)
- Context windows add 10 sentences worth of tokens per call
- Long documents can be expensive

**Optimization strategies**:
- Break large texts into logical chunks
- Use gpt-4o-mini for cost savings (still supports structured outputs)
- Consider pre-filtering obvious non-factual content
- Batch similar sentences if modifying pipeline

**Timing**:
- Expect ~10 seconds per sentence (3 API calls with gpt-4o)
- Faster with gpt-4o-mini
- Network latency is main factor

## Error Handling Patterns

**Pipeline level**:
- Each stage returns status tuple
- Early exit on non-verifiable/unresolvable
- Continues processing remaining sentences on individual failures

**LLM Client level**:
- Returns None on API errors
- Logs all errors to stderr
- Handles refusals explicitly
- No automatic retries (rely on structured outputs reliability)

**Server level**:
- Wraps all tool calls in try/except
- Returns error message to client
- Validates environment on startup
- Fails fast if configuration invalid

## Code Style and Patterns

**Type hints**:
- Use throughout (Python 3.10+)
- Pydantic models for structured data
- TypeVar for generic Pydantic responses

**Async patterns**:
- Server is async (MCP requirement)
- Pipeline is synchronous
- LLM client is synchronous
- No parallelization currently (could be added)

**Logging**:
- Use stderr for logs (stdout is MCP protocol)
- Check `self.logger` before logging
- Structured log messages with stage/call info

**Documentation**:
- Docstrings on all public functions
- References to paper sections where applicable
- Examples in docstrings

## MCP Integration Notes

**Client Configuration** (e.g., Cursor):
```json
{
  "mcpServers": {
    "claimify-local": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/claimify_server.py"]
    }
  }
}
```

**Tool Interface**:
```json
{
  "name": "extract_claims",
  "inputSchema": {
    "text_to_process": "string (required)",
    "question": "string (optional, provides context)"
  }
}
```

**Important**: 
- Server communicates via stdio, not HTTP
- All logs must go to stderr
- Tool returns JSON string (not raw list)
- Client deserializes JSON response

## Dependencies

**Core**:
- `openai>=1.0.0` - API client with structured outputs
- `mcp>=1.0.0` - Model Context Protocol server
- `pydantic>=2.0.0` - Response validation
- `nltk>=3.8.0` - Sentence tokenization
- `python-dotenv>=1.0.0` - Environment config

**NLTK Data**:
- punkt_tab tokenizer (auto-downloaded on first run)
- Fallback to punkt if punkt_tab unavailable

## Research Context

**Paper**: "Towards Effective Extraction and Evaluation of Factual Claims" (Metropolitansky & Larson, 2025)

**Key Methodology**:
- Multi-stage pipeline with context awareness
- Emphasis on decontextualization
- Atomic claim decomposition
- Verifiability as core criterion

**This Implementation**:
- Uses structured outputs (not in original paper)
- Simplified prompt format (structure enforced by API)
- Added comprehensive logging
- Production-ready error handling
- MCP server interface

**Not an official implementation** - prompts modified for structured outputs

## Security Considerations

**API Keys**:
- Loaded from .env file
- Never logged or exposed
- Validated on startup

**Input Validation**:
- Text length not hard-limited (trust MCP client)
- No SQL/command injection risks (only API calls)
- Structured outputs prevent prompt injection in responses

**Output Safety**:
- LLM refusals handled explicitly
- No arbitrary code execution
- Content filtering by OpenAI

## Common Gotchas

1. **"Model does not support structured outputs"**
   - Only specific models work
   - Update LLM_MODEL in .env
   - Check `supports_structured_outputs()` logic

2. **NLTK punkt not found**
   - Auto-downloads on first run
   - May need internet connection
   - Fallback to older punkt version

3. **Empty claims list**
   - Check logs to see which stage filtered
   - Input may be all opinions/generic statements
   - Try simpler factual sentences first

4. **MCP client can't connect**
   - Verify absolute paths in config
   - Check virtual environment activation
   - Ensure python executable is correct

5. **Language not preserved**
   - Prompts have critical language requirement
   - Report if model not following instructions
   - Check logs for actual LLM responses

6. **Logs interfering with MCP**
   - Always log to stderr, never stdout
   - Stdout reserved for MCP protocol
   - Use LOG_OUTPUT=file if needed

## Future Enhancement Ideas

**Performance**:
- Parallel processing of independent sentences
- Caching for identical context windows
- Batching API calls
- Streaming responses for long documents

**Features**:
- Support for other LLM providers (Anthropic, local models)
- Confidence scores for claims
- Claim relationship tracking
- Multi-document claim deduplication

**Quality**:
- Few-shot examples in prompts
- Active learning from user feedback
- A/B testing different prompt variations
- Evaluation metrics against paper's benchmarks

**Developer Experience**:
- Web UI for testing
- Detailed validation reports
- Claim visualization
- Interactive disambiguation

## Getting Help

**For development issues**:
1. Check logs with `LOG_LLM_CALLS=true`
2. Review this AGENTS.md
3. Consult README.md for setup
4. Read the original paper for methodology

**For extending the system**:
1. Start with `pipeline.py` to understand flow
2. Review `structured_models.py` for data structures
3. Study `structured_prompts.py` for prompt engineering
4. Test with `test_claimify.py`

## Quick Reference

**File purposes**:
- `claimify_server.py` - MCP server, entry point
- `pipeline.py` - Core 4-stage extraction logic
- `llm_client.py` - OpenAI API wrapper
- `structured_models.py` - Pydantic response schemas
- `structured_prompts.py` - System prompts for each stage
- `test_claimify.py` - Test suite
- `requirements.txt` - Python dependencies
- `setup.py` - Package installation
- `env.example` - Environment template
- `README.md` - User documentation
- `LICENSE` - Apache 2.0

**Key functions**:
- `ClaimifyPipeline.run(text)` - Main extraction
- `split_into_sentences(text)` - Stage 1
- `run_selection_stage()` - Stage 2
- `run_disambiguation_stage()` - Stage 3
- `run_decomposition_stage()` - Stage 4
- `LLMClient.make_structured_request()` - API calls

**Environment variables**:
- `OPENAI_API_KEY` - Required
- `LLM_MODEL` - Model selection
- `LOG_LLM_CALLS` - Enable/disable logging
- `LOG_OUTPUT` - Where to log
- `LOG_FILE` - Log file path

---

**Last Updated**: October 31, 2025
**Project Status**: Production-ready
**Python Version**: 3.10+
**License**: Apache 2.0
