"""
LLM Client for the Claimify system.
Supports both MCP sampling (primary) and OpenAI API (fallback) with structured outputs using Pydantic models.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Type, TypeVar, TYPE_CHECKING
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from mcp.server.session import ServerSession

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class LLMClient:
    """
    A client that communicates with LLMs via MCP sampling (primary) or OpenAI API (fallback).
    Supports structured outputs with Pydantic models through JSON parsing and validation.
    """
    
    def __init__(self, session: Optional['ServerSession'] = None):
        load_dotenv()
        self.provider = "openai"
        self.model = os.getenv("LLM_MODEL", "gpt-4o-2024-08-06")
        self.call_count = 0
        self.session = session
        
        # MCP sampling configuration
        self.max_tokens_selection = int(os.getenv("SAMPLING_MAX_TOKENS_SELECTION", "500"))
        self.max_tokens_disambiguation = int(os.getenv("SAMPLING_MAX_TOKENS_DISAMBIGUATION", "400"))
        self.max_tokens_decomposition = int(os.getenv("SAMPLING_MAX_TOKENS_DECOMPOSITION", "800"))
        self.max_retries = int(os.getenv("SAMPLING_MAX_RETRIES", "2"))
        
        # Set up logging
        self.setup_logging()

        # OpenAI client is optional (only needed for fallback)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            if self.logger:
                self.logger.info("OpenAI API key not provided - will require MCP sampling support from client")

    def setup_logging(self):
        """Set up logging for LLM calls."""
        # Check if logging is enabled
        log_enabled = os.getenv("LOG_LLM_CALLS", "true").lower() in ("true", "1", "yes")
        
        if not log_enabled:
            self.logger = None
            return
        
        # Create logger with unique name to avoid conflicts
        logger_name = f"claimify.llm.{self.provider}.{id(self)}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
        
        # Determine log output - default to file for better visibility
        log_output = os.getenv("LOG_OUTPUT", "file").lower()
        
        if log_output == "file":
            # Log to file
            log_file = os.getenv("LOG_FILE", "claimify_llm.log")
            try:
                # Use absolute path to ensure file is created in project root
                if not os.path.isabs(log_file):
                    log_file = os.path.join(os.getcwd(), log_file)
                handler = logging.FileHandler(log_file, mode='a')
                print(f"Logging LLM calls to: {log_file}", file=sys.stderr)
            except (OSError, PermissionError) as e:
                # Fall back to stderr if file logging fails
                handler = logging.StreamHandler(sys.stderr)
                print(f"Failed to create log file, using stderr: {e}", file=sys.stderr)
        else:
            # Log to stderr - won't interfere with MCP protocol on stdout
            handler = logging.StreamHandler(sys.stderr)
            print(f"Logging LLM calls to: stderr", file=sys.stderr)
        
        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def supports_structured_outputs(self) -> bool:
        """Check if the current model supports structured outputs."""
        # Structured outputs are supported by OpenAI models gpt-4o-mini and gpt-4o-2024-08-06 and later
        supported_models = [
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18", 
            "gpt-4o-2024-08-06",
            "gpt-4o-2024-11-20",
            "gpt-4o-2024-12-17",
            "gpt-4o"  # Latest gpt-4o should support it
        ]
        
        # Check if any supported model name is contained in the current model
        model_lower = self.model.lower()
        
        # Special handling for gpt-4o to avoid false positives with gpt-4o-mini
        if "gpt-4o-mini" in model_lower:
            return True
        elif "gpt-4o-2024" in model_lower:
            return True
        elif model_lower == "gpt-4o":
            return True
        
        return False

    def _get_max_tokens_for_stage(self, stage: str) -> int:
        """Get the max tokens configuration for a given stage."""
        stage_lower = stage.lower()
        if "selection" in stage_lower:
            return self.max_tokens_selection
        elif "disambiguation" in stage_lower:
            return self.max_tokens_disambiguation
        elif "decomposition" in stage_lower:
            return self.max_tokens_decomposition
        else:
            return 1000  # Default

    async def _make_sampling_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        stage: str,
        retry_count: int = 0,
        previous_error: Optional[str] = None
    ) -> Optional[T]:
        """Make a request using MCP sampling with JSON extraction and validation."""
        if not self.session:
            return None

        try:
            # Import here to avoid circular imports
            from mcp.types import SamplingMessage, TextContent, ModelPreferences, ModelHint
            
            # Build the user message, adding error hint if this is a retry
            final_user_prompt = user_prompt
            if previous_error and retry_count > 0:
                final_user_prompt += f"\n\nPREVIOUS ATTEMPT HAD ERROR: {previous_error}\nPlease fix the error and provide a valid JSON response."
            
            # Construct messages array for sampling - just the user message
            messages = [
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=final_user_prompt)
                )
            ]
            
            max_tokens = self._get_max_tokens_for_stage(stage)
            
            # Stage-specific model preferences based on task complexity analysis
            # Selection: Simple binary classification → fast, cheap models
            # Disambiguation: Pronoun/acronym resolution → balanced models
            # Decomposition: Complex semantic extraction → premium reasoning models
            if stage == "selection":
                model_preferences = ModelPreferences(
                    hints=[
                        ModelHint(name="claude-haiku-4-5"),   # Fast & cheap (0.33x rate)
                        ModelHint(name="gpt-5-mini"),         # Cost-efficient GPT-5
                        ModelHint(name="claude-3-5-sonnet")   # Quality fallback
                    ],
                    intelligencePriority=0.4,  # Lower - task is simple
                    speedPriority=0.8,         # High - quick decisions
                    costPriority=0.7           # High - save money on volume
                )
            elif stage == "disambiguation":
                model_preferences = ModelPreferences(
                    hints=[
                        ModelHint(name="claude-3-5-sonnet"),  # Excellent balance
                        ModelHint(name="gpt-4o"),             # Strong alternative
                        ModelHint(name="claude-haiku-4-5")    # Fast fallback
                    ],
                    intelligencePriority=0.6,  # Medium - needs context understanding
                    speedPriority=0.6,         # Medium - moderate urgency
                    costPriority=0.5           # Medium - balanced approach
                )
            else:  # decomposition
                model_preferences = ModelPreferences(
                    hints=[
                        ModelHint(name="gpt-5-mini"),    # Best reasoning (1x rate)
                        ModelHint(name="claude-3-5-sonnet"),  # Proven excellence
                        ModelHint(name="gpt-4-1")             # OpenAI's smartest
                    ],
                    intelligencePriority=0.8,  # High - complex semantic task
                    speedPriority=0.4,         # Lower - quality over speed
                    costPriority=0.3           # Lower - worth paying for quality
                )
            
            # Make the sampling request with system_prompt as a parameter
            result = await self.session.create_message(
                messages=messages,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                temperature=0.0,
                model_preferences=model_preferences
            )
            
            # Extract text from response
            # result is a CreateMessageResult with content field
            if result.content.type != "text":
                if self.logger:
                    self.logger.warning(f"Sampling returned non-text content: {result.content.type}")
                return None
            
            response_text = result.content.text
            
            # Try to extract JSON from the response
            json_data = self._extract_json_from_text(response_text)
            if not json_data:
                error_msg = "No valid JSON found in response"
                if self.logger:
                    self.logger.warning(f"Sampling response has no valid JSON: {response_text[:200]}")
                
                # Retry if we haven't exceeded max retries
                if retry_count < self.max_retries:
                    if self.logger:
                        self.logger.info(f"Retrying sampling request (attempt {retry_count + 2}/{self.max_retries + 1})")
                    return await self._make_sampling_request(
                        system_prompt, user_prompt, response_model, stage,
                        retry_count + 1, error_msg
                    )
                return None
            
            # Validate with Pydantic
            try:
                validated_response = response_model.model_validate(json_data)
                return validated_response
            except ValidationError as e:
                error_msg = f"Pydantic validation error: {str(e)}"
                if self.logger:
                    self.logger.warning(error_msg)
                
                # Retry if we haven't exceeded max retries
                if retry_count < self.max_retries:
                    if self.logger:
                        self.logger.info(f"Retrying sampling request (attempt {retry_count + 2}/{self.max_retries + 1})")
                    return await self._make_sampling_request(
                        system_prompt, user_prompt, response_model, stage,
                        retry_count + 1, error_msg
                    )
                return None
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during sampling request: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[dict]:
        """Extract JSON from text response, handling markdown code blocks."""
        # Try to find JSON in markdown code block
        import re
        
        # Look for ```json ... ``` or ```{...}```
        json_block_match = re.search(r'```(?:json)?\s*\n?({[^`]+})\s*```', text, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON object
        json_match = re.search(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try parsing the whole text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        return None

    async def make_structured_request_async(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        stage: str = "unknown"
    ) -> Optional[T]:
        """
        Async version - makes a structured request to the LLM using MCP sampling (if available) or OpenAI API (fallback).
        
        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            response_model: Pydantic model class for the expected response
            stage: The pipeline stage making this request (for logging)
            
        Returns:
            Parsed response as the specified Pydantic model, or None on failure
        """
        # Try MCP sampling first if session is available
        if self.session:
            if self.logger:
                self.logger.info(f"Attempting MCP sampling for {stage} stage")
            
            try:
                result = await self._make_sampling_request(system_prompt, user_prompt, response_model, stage)
                
                if result:
                    if self.logger:
                        self.logger.info(f"MCP sampling successful for {stage} stage")
                    # Always log to stderr for visibility
                    print(f"[{stage}] ✓ Used MCP sampling", file=sys.stderr)
                    return result
                else:
                    if self.logger:
                        self.logger.warning(f"MCP sampling failed for {stage} stage, falling back to OpenAI API")
                    print(f"[{stage}] → Falling back to OpenAI API (MCP sampling failed)", file=sys.stderr)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"MCP sampling error for {stage} stage: {e}, falling back to OpenAI API")
                print(f"[{stage}] → Falling back to OpenAI API (MCP sampling error: {e})", file=sys.stderr)
        
        # Fall back to OpenAI API
        if not self.client:
            if self.logger:
                self.logger.error("No OpenAI client available and MCP sampling failed/unavailable")
            else:
                print("ERROR: No LLM access available (neither MCP sampling nor OpenAI API)", file=sys.stderr)
            return None
        
        return self._make_openai_request(system_prompt, user_prompt, response_model, stage)

    def make_structured_request(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        stage: str = "unknown"
    ) -> Optional[T]:
        """
        Sync wrapper - makes a structured request to the LLM using MCP sampling (if available) or OpenAI API (fallback).
        
        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            response_model: Pydantic model class for the expected response
            stage: The pipeline stage making this request (for logging)
            
        Returns:
            Parsed response as the specified Pydantic model, or None on failure
        """
        # If no session, just use OpenAI API directly
        if not self.session:
            if not self.client:
                if self.logger:
                    self.logger.error("No OpenAI client available and no MCP session")
                else:
                    print("ERROR: No LLM access available", file=sys.stderr)
                return None
            return self._make_openai_request(system_prompt, user_prompt, response_model, stage)
        
        # We have a session - try to use async
        import asyncio
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            # If we're here, we're in an async context but this is a sync function
            # This shouldn't happen in normal usage
            if self.logger:
                self.logger.warning(f"Sync function called from async context for {stage} stage, using OpenAI API")
            print(f"[{stage}] → Using OpenAI API (sync call from async context)", file=sys.stderr)
            return self._make_openai_request(system_prompt, user_prompt, response_model, stage)
        except RuntimeError:
            # No event loop - we can create one
            return asyncio.run(
                self.make_structured_request_async(system_prompt, user_prompt, response_model, stage)
            )
        
        # Fall back to OpenAI API
        if not self.client:
            if self.logger:
                self.logger.error("No OpenAI client available and MCP sampling failed/unavailable")
            else:
                print("ERROR: No LLM access available (neither MCP sampling nor OpenAI API)", file=sys.stderr)
            return None
        
        return self._make_openai_request(system_prompt, user_prompt, response_model, stage)

    def _make_openai_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        stage: str
    ) -> Optional[T]:
        """
        Makes a request to OpenAI API with structured outputs.
        
        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            response_model: Pydantic model class for the expected response
            stage: The pipeline stage making this request (for logging)
            
        Returns:
            Parsed response as the specified Pydantic model, or None on failure
        """
        if not self.supports_structured_outputs():
            raise ValueError(
                f"Model {self.model} does not support structured outputs. "
                f"Please use a compatible model like gpt-4o-2024-08-06, gpt-4o-mini, or gpt-4o."
            )
        
        if self.logger:
            self.logger.info(f"Using OpenAI API fallback for {stage} stage")
        
        # Always log to stderr for visibility
        print(f"[{stage}] ✓ Using OpenAI API (model: {self.model})", file=sys.stderr)
        
        self.call_count += 1
        start_time = datetime.now()
        
        # Log the request
        if self.logger:
            self.logger.info(f"=== STRUCTURED LLM CALL #{self.call_count} - STAGE: {stage.upper()} ===")
            self.logger.info(f"Provider: {self.provider}, Model: {self.model}")
            self.logger.info(f"Response Model: {response_model.__name__}")
            
            # Log only first sentence of system prompt
            system_first_sentence = system_prompt.split('.')[0] + '.' if '.' in system_prompt else system_prompt[:100] + '...'
            self.logger.info(f"System Prompt ({len(system_prompt)} chars): {system_first_sentence}")
            
            # Log user prompt
            self.logger.info(f"User Prompt ({len(user_prompt)} chars): {user_prompt}")
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Use structured outputs with beta.chat.completions.parse
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=0.0,
                max_tokens=2048,
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Check for refusal
            if response.choices[0].message.refusal:
                if self.logger:
                    self.logger.warning(f"Call #{self.call_count} refused: {response.choices[0].message.refusal}")
                return None
            
            # Get the parsed response
            parsed_response = response.choices[0].message.parsed
            
            # Log the response
            if self.logger:
                self.logger.info(f"Structured response received in {duration:.2f}s:")
                self.logger.info(f"Parsed response: {parsed_response}")
                
                # Log token usage if available
                if hasattr(response, 'usage') and response.usage:
                    usage = response.usage
                    self.logger.info(f"Token usage - Prompt: {usage.prompt_tokens}, "
                                   f"Completion: {usage.completion_tokens}, "
                                   f"Total: {usage.total_tokens}")
                
                self.logger.info(f"=== END STRUCTURED CALL #{self.call_count} ===\n")
            
            return parsed_response
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = f"Error during structured LLM API call: {e}"
            if self.logger:
                self.logger.error(f"Structured call #{self.call_count} failed after {duration:.2f}s: {error_msg}")
                self.logger.error(f"=== END STRUCTURED CALL #{self.call_count} (ERROR) ===\n")
            else:
                print(error_msg, file=sys.stderr)
            
            return None 