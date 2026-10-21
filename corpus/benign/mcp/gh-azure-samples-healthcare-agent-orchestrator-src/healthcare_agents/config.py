# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import logging
import os

# DirectLine API URL
DEFAULT_DIRECTLINE_URL = "https://directline.botframework.com/v3/directline"
# User ID used for the engagement with the healthcare agent service
DEFAULT_USER_ID = "@agent"
# Used to identify, in the agents_config yaml if the agent is a healthcare agent
DEFAULT_HEALTHCARE_AGENT_SERVICE_YAML_KEY = "healthcare_agent"
# Used to identify the key for the secret in KeyVault
DEFAULT_HEALTHCARE_AGENT_SERVICE_KEYVAULT_SECRET_KEY_NAME = "HealthcareAgentService-{name}-Secret"

# Connection Configuration Defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RECONNECT_ATTEMPTS = 3

# WebSocket Configuration Defaults
DEFAULT_WS_PING_INTERVAL = 20
DEFAULT_WS_PING_TIMEOUT = 10
DEFAULT_WS_CLOSE_TIMEOUT = 5

# Response Configuration Defaults
DEFAULT_RESPONSE_POLL_INTERVAL = 0.1

logger = logging.getLogger(__name__)


class HealthcareAgentConfig:
    """Configuration for Healthcare Agent Service."""

    def __init__(self):
        # API Configuration
        self.directline_url = os.getenv("HEALTHCARE_AGENT_DIRECTLINE_URL", DEFAULT_DIRECTLINE_URL)
        self.default_user_id = os.getenv("HEALTHCARE_AGENT_DEFAULT_USER_ID", DEFAULT_USER_ID)
        self.yaml_key = os.getenv(
            "HEALTHCARE_AGENT_DEFAULT_YAML_KEY", DEFAULT_HEALTHCARE_AGENT_SERVICE_YAML_KEY)
        self.keyvault_secret_key_name = os.getenv(
            "HEALTHCARE_AGENT_SERVICE_KEYVAULT_SECRET_KEY_NAME",
            DEFAULT_HEALTHCARE_AGENT_SERVICE_KEYVAULT_SECRET_KEY_NAME
        )

        # Connection Configuration
        self.max_retries = int(os.getenv("HEALTHCARE_AGENT_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        self.retry_delay = float(os.getenv("HEALTHCARE_AGENT_RETRY_DELAY", str(DEFAULT_RETRY_DELAY)))
        self.timeout = float(os.getenv("HEALTHCARE_AGENT_TIMEOUT", str(DEFAULT_TIMEOUT)))
        self.max_reconnect_attempts = int(
            os.getenv("HEALTHCARE_AGENT_MAX_RECONNECT_ATTEMPTS", str(DEFAULT_MAX_RECONNECT_ATTEMPTS)))

        # WebSocket Configuration
        self.ws_ping_interval = int(os.getenv("HEALTHCARE_AGENT_WS_PING_INTERVAL", str(DEFAULT_WS_PING_INTERVAL)))
        self.ws_ping_timeout = int(os.getenv("HEALTHCARE_AGENT_WS_PING_TIMEOUT", str(DEFAULT_WS_PING_TIMEOUT)))
        self.ws_close_timeout = int(os.getenv("HEALTHCARE_AGENT_WS_CLOSE_TIMEOUT", str(DEFAULT_WS_CLOSE_TIMEOUT)))

        # Response Configuration
        self.response_poll_interval = float(
            os.getenv("HEALTHCARE_AGENT_RESPONSE_POLL_INTERVAL", str(DEFAULT_RESPONSE_POLL_INTERVAL)))


config = HealthcareAgentConfig()
