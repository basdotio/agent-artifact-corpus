# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import json
import logging
from typing import Annotated, Optional

import aiohttp
import websockets
from azure.keyvault.secrets.aio import SecretClient

from data_models.chat_context import ChatContext

from .config import config

logger = logging.getLogger(__name__)


class HealthcareAgentError(Exception):
    """Base exception for Healthcare Agent errors."""
    pass


class ConnectionError(HealthcareAgentError):
    """Raised when there are connection issues."""
    pass


class AuthenticationError(HealthcareAgentError):
    """Raised when there are authentication issues."""
    pass


class TimeoutError(HealthcareAgentError):
    """Raised when operations timeout."""
    pass


class HealthcareAgentServiceClient:
    """
    Healthcare Agent Service Client
    Manages a conversation lifecycle with the Healthcare agent service, and communicate with the agent using Direct Line API.
    KeyVault is used to store the Direct Line secret key.
    """

    def __init__(self,
                 agent_name: Annotated[str, "The name of the healthcare agent."],
                 chat_ctx: Annotated[ChatContext, "The shared chat context."],
                 url: Annotated[str, "The URL for the Direct Line API."],
                 keyvault_client: Annotated[SecretClient, "The Azure Key Vault client."],
                 directline_secret_key: Annotated[str, "The name of the secret in Azure Key Vault."],
                 # Optional parameters
                 max_retries: Annotated[int, "Maximum number of retries for failed operations."] = config.max_retries,
                 retry_delay: Annotated[float, "Delay when retrying."] = config.retry_delay,
                 timeout: Annotated[float, "Request timeout."] = config.timeout):
        """
        Initializes the Healthcare Agent Service Client.

        Args:
            agent_name (str): The name of the healthcare agent.
            chat_ctx (ChatContext): The chat context containing patient information.
            url (str): The URL for the Direct Line API.
            keyvault_client (SecretClient): The Azure Key Vault client for retrieving secrets.
            directline_secret_key (str): The name of the secret in Azure Key Vault.
            max_retries (int): Maximum number of retries for failed operations.
            retry_delay (float): Delay between retries in seconds.
            timeout (float): Timeout for API operations in seconds.
        """
        self.name = agent_name
        self.chat_ctx = chat_ctx
        self.keyvault: SecretClient = keyvault_client
        self.url = url
        self.directline_secret_key = directline_secret_key
        self.token = None
        self.stream_url = None
        self._conversation_id = None
        self._ws_task = None
        self._latest_agent_response = None
        self._latest_agent_response_raw = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._ws_connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = config.max_reconnect_attempts

    async def _retry_operation(self, operation, *args, **kwargs):
        """Helper method to retry operations with exponential backoff."""
        last_exception = None
        for attempt in range(self._max_retries):
            try:
                return await operation(*args, **kwargs)
            except aiohttp.ClientResponseError as e:
                if e.status == 401:
                    # Refresh token on authentication error
                    self.token = None
                    last_exception = AuthenticationError(f"Authentication failed: {str(e)}")
                else:
                    last_exception = ConnectionError(f"HTTP error: {str(e)}")
            except asyncio.TimeoutError:
                last_exception = TimeoutError("Operation timed out")
            except Exception as e:
                last_exception = HealthcareAgentError(f"Operation failed: {str(e)}")

            if attempt < self._max_retries - 1:
                delay = self._retry_delay * (2 ** attempt)
                logger.warning(
                    f"[{self.name}] Operation failed, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self._max_retries}): {str(last_exception)}"
                )
                await asyncio.sleep(delay)

        raise last_exception

    async def _listen_to_ws(self):
        """WebSocket listener with reconnection logic."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                if not self.stream_url:
                    raise ValueError("No stream URL available to listen for messages.")

                async with websockets.connect(
                    self.stream_url,
                    ping_interval=config.ws_ping_interval,
                    ping_timeout=config.ws_ping_timeout,
                    close_timeout=config.ws_close_timeout,
                    max_size=1024 * 1024,  # 1MB max message size
                    compression=None  # Disable compression for better control
                ) as websocket:
                    logger.debug(f"[{self.name}] WebSocket connection established")
                    self._ws_connected = True
                    self._reconnect_attempts = 0

                    while True:
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=self._timeout
                            )

                            # Process the message
                            if message:
                                await self._process_ws_message(message)

                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            try:
                                await websocket.ping()
                                logger.debug(f"[{self.name}] Sent ping to keep connection alive")
                            except Exception as e:
                                logger.warning(f"[{self.name}] Failed to send ping: {e}")
                                break
                            continue

                        except websockets.exceptions.ConnectionClosed as e:
                            logger.warning(f"[{self.name}] WebSocket connection closed: {e}")
                            if e.code == 1000:  # Normal closure
                                logger.info(f"[{self.name}] WebSocket closed normally")
                                return
                            break

                        except websockets.exceptions.WebSocketException as e:
                            logger.error(f"[{self.name}] WebSocket error: {e}")
                            break

                        except Exception as e:
                            logger.error(f"[{self.name}] Unexpected error in WebSocket loop: {e}")
                            break

            except websockets.exceptions.InvalidStatus as e:
                logger.error(f"[{self.name}] Invalid WebSocket status code: {e}")
                if e.response.status_code == 401:
                    # Authentication error, try to refresh token
                    self.token = None
                    await self._get_headers(self.directline_secret_key)
                self._reconnect_attempts += 1

            except Exception as e:
                logger.error(f"[{self.name}] WebSocket connection error: {str(e)}")
                self._ws_connected = False
                self._reconnect_attempts += 1

            # Exponential backoff for reconnection
            if self._reconnect_attempts < self._max_reconnect_attempts:
                delay = self._retry_delay * (2 ** self._reconnect_attempts)
                logger.info(f"[{self.name}] Attempting to reconnect in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"[{self.name}] Maximum reconnection attempts reached")
                break

        # If we get here, we've exhausted all reconnection attempts
        self._ws_connected = False
        logger.error(f"[{self.name}] WebSocket connection permanently lost")

    async def _process_ws_message(self, message: str):
        """Process WebSocket messages with proper error handling."""
        try:
            data = json.loads(message)
            activities = data.get("activities", [])

            for activity in activities:
                activity_type = activity.get("type")
                if activity_type == "message":
                    await self._process_message_activity(activity)
                elif activity_type == "typing":
                    logger.debug(f"[{self.name}] Agent is typing...")
                else:
                    logger.warning(f"[{self.name}] Unhandled activity type: {activity_type}")

        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"[{self.name}] Error processing WebSocket message: {e}")

    async def _process_message_activity(self, activity: dict):
        """Process message activities from the agent."""
        if activity.get("from", {}).get("id", "") == config.default_user_id:
            return

        attachments = activity.get('attachments', [])
        if not attachments:
            text = activity.get('text')
            if text:
                self._latest_agent_response = text
        else:
            for attachment in attachments:
                if attachment.get('contentType') == 'application/vnd.microsoft.card.adaptive':
                    items = attachment.get('content', {}).get('body', [{}])[0].get('items', [])
                    text_blocks = [x['text'].strip() for x in items if x.get('type') == 'TextBlock']
                    self._latest_agent_response = " ".join(text_blocks)
                    self._latest_agent_response_raw = attachment

    async def send_message(self, message: str, attachments: list[dict] = None) -> dict:
        """Send a message to the healthcare agent service with retry logic."""
        async def _send():
            if not self._conversation_id:
                await self.start_conversation()
            await self._ensure_ws_connection()
            url = f"{self.url}/conversations/{self._conversation_id}/activities"
            payload = {
                "type": "message",
                "from": {"id": config.default_user_id},
                "text": message,
            }
            if attachments:
                payload["attachments"] = attachments
            if self.chat_ctx.chat_history.messages:
                sk_chat_history = self.chat_ctx.chat_history.serialize()
                payload["channelData"] = {
                    "skChatHistory": sk_chat_history,
                    "patientId": self.chat_ctx.patient_id,
                }
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers(self.directline_secret_key)
                async with session.post(url, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    if resp.status not in [200, 201]:
                        raise Exception(f"Error sending message: {resp.text} ({resp.status})")
                    return await resp.json()

        return await self._retry_operation(_send)

    async def _get_headers(self, directline_secret_key: str) -> dict:
        """
        Retrieves the headers for the Direct Line API requests.
        Args:
            directline_secret_key (str): The name of the secret in Azure Key Vault.
        Returns:
            dict: The headers for the Direct Line API requests.
        """
        if not self.token:
            self.token = await self._get_directline_secret(directline_secret_key)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        return headers

    async def _get_directline_secret(self, directline_secret_key: str) -> str:
        """
        Retrieves the Direct Line token from Azure Key Vault.
        Args:
            directline_secret_key (str): The name of the secret in Azure Key Vault.
        Returns:
            str: The Direct Line token.
        """
        secret = await self.keyvault.get_secret(
            name=directline_secret_key,
        )
        if not secret:
            raise ValueError(f"Secret {directline_secret_key} not found in Key Vault.")
        if not secret.value:
            raise ValueError(f"Secret {directline_secret_key} is empty.")
        return secret.value

    async def start_conversation(self) -> str:
        """
        Starts a new conversation with the healthcare agent service.

        Returns:
            str: The conversation ID.
        Raises:
            Exception: If there is an error starting the conversation.
        """
        response_json = None
        async with aiohttp.ClientSession() as session:
            url = f"{self.url}/conversations"
            headers = await self._get_headers(self.directline_secret_key)
            async with session.post(url, headers=headers) as resp:
                resp.raise_for_status()
                response_json = await resp.json()
                if resp.status not in [200, 201]:
                    logger.error("Error starting conversation: %s (%s)", resp.text, resp.status)
                    raise Exception("Error starting conversation")

        self.stream_url = response_json["streamUrl"]
        self.set_conversation_id(response_json["conversationId"])
        self._ws_task = asyncio.create_task(self._listen_to_ws())
        logger.info("[%s] conversation started: %s", self.name, self._conversation_id)
        return self._conversation_id

    async def end_conversation(self) -> None:
        """
        Ends the current conversation with the healthcare agent service.
        """
        if self._conversation_id:
            url = f"{self.url}/conversations/{self._conversation_id}"
            async with aiohttp.ClientSession() as session:
                headers = await self._get_headers(self.directline_secret_key)
                async with session.delete(url, headers=headers) as resp:
                    resp.raise_for_status()
                    if resp.status not in [200, 204]:
                        logger.error("Error ending conversation: %s (%s)", resp.text, resp.status)
                        raise Exception("Error ending conversation")
            self.set_conversation_id(None)
            logger.info("[%s] conversation ended", self.name)
        else:
            logger.warning("[%s] No conversation to end", self.name)
        self.token = None
        self.stream_url = None
        self._ws_task = None
        self._latest_agent_response = None
        self._latest_agent_response_raw = None

    async def close(self) -> None:
        """
        Cleanup. Cancels the websocket task and ends the conversation if it exists.
        """
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._conversation_id:
            await self.end_conversation()

    async def process(
        self,
        message: Annotated[str, "Text to be processed by the Healthcare Agent Service."],
        attachments: Annotated[Optional[list[dict]],
                               "Attachments (eg images) to be processed by the Healthcare Agent Service."] = None
    ) -> dict:
        try:
            await self.send_message(message, attachments)

            # Wait for the response with timeout
            start_time = asyncio.get_event_loop().time()
            while self._latest_agent_response is None:
                if asyncio.get_event_loop().time() - start_time > self._timeout:
                    raise TimeoutError("Timeout waiting for agent response")
                await asyncio.sleep(config.response_poll_interval)

            response = self._latest_agent_response
            adaptive_card = self._latest_agent_response_raw.get(
                'content', {}) if self._latest_agent_response_raw else {}
            self._latest_agent_response = None
            self._latest_agent_response_raw = None

            # Format the response
            if isinstance(response, str):
                response = {
                    "text": response,
                    "card": str(adaptive_card) if adaptive_card else None
                }
            elif isinstance(response, dict):
                if "text" not in response:
                    response = {"text": str(response),
                                'card': str(adaptive_card) if adaptive_card else None}
            else:
                response = {"text": str(response),
                            'card': str(adaptive_card) if adaptive_card else None}

            return response

        except aiohttp.ClientResponseError as e:
            logger.error(f"[{self.name}] HTTP error sending message: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[{self.name}] Error in process: {str(e)}")
            raise

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        logger.info(f"[{self.name}] Exiting context manager.")
        try:
            if self._ws_task and not self._ws_task.done():
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"[{self.name}] Error during WebSocket task cleanup: {e}")

            if self._conversation_id:
                try:
                    await self.end_conversation()
                except Exception as e:
                    logger.error(f"[{self.name}] Error ending conversation: {e}")

            # Clean up resources
            self.token = None
            self.stream_url = None
            self._ws_task = None
            self._latest_agent_response = None
            self._ws_connected = False
            self._reconnect_attempts = 0

        except Exception as e:
            logger.error(f"[{self.name}] Error during cleanup: {e}")
            raise

    async def _reconnect(self):
        """Handle WebSocket reconnection with exponential backoff."""
        backoff = 1
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                # Reset the WebSocket task
                if self._ws_task and not self._ws_task.done():
                    self._ws_task.cancel()
                    try:
                        await self._ws_task
                    except asyncio.CancelledError:
                        pass

                # Create new WebSocket connection task
                self._ws_task = asyncio.create_task(self._listen_to_ws())
                logger.info(f"[{self.name}] WebSocket reconnection initiated")
                return

            except Exception as e:
                logger.error(f"[{self.name}] Reconnection attempt failed: {e}")
                self._reconnect_attempts += 1
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    # Exponential backoff with a cap
                    backoff = min(backoff * 2, 60)  # Cap at 60 seconds
                    logger.info(f"[{self.name}] Next reconnection attempt in {backoff} seconds")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"[{self.name}] Maximum reconnection attempts reached")
                    break

    async def check_health(self) -> bool:
        """Check the health of the Healthcare Agent Service."""
        try:
            if not self._conversation_id:
                await self.start_conversation()

            # Send a ping message
            await self.send_message("ping")

            # Wait for response with timeout
            start_time = asyncio.get_event_loop().time()
            while self._latest_agent_response is None:
                if asyncio.get_event_loop().time() - start_time > self._timeout:
                    return False
                await asyncio.sleep(0.1)

            return True
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return False

    async def _ensure_ws_connection(self) -> None:
        if not self._conversation_id:
            return
        if self._ws_task and not self._ws_task.done():
            return
        async with aiohttp.ClientSession() as session:
            headers = await self._get_headers(self.directline_secret_key)
            url = f"{self.url}/conversations/{self._conversation_id}"
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                info = await resp.json()
                self.stream_url = info.get("streamUrl")
        if not self.stream_url:
            raise ConnectionError(
                f"[{self.name}] Unable to obtain streamUrl for reconnection."
            )
        self._ws_task = asyncio.create_task(self._listen_to_ws())
        logger.debug(
            f"[{self.name}] WebSocket listener (re)started for "
            f"conversation {self._conversation_id}"
        )

    def get_conversation_id(self) -> str:
        """Get the conversation ID."""
        return self._conversation_id

    def set_conversation_id(self, conversation_id: str) -> None:
        """Set the conversation ID."""
        self._conversation_id = conversation_id
        if self.name not in self.chat_ctx.healthcare_agents:
            self.chat_ctx.healthcare_agents[self.name] = {}
        if conversation_id is None:
            del self.chat_ctx.healthcare_agents[self.name]["conversation_id"]
        else:
            self.chat_ctx.healthcare_agents[self.name]["conversation_id"] = conversation_id
