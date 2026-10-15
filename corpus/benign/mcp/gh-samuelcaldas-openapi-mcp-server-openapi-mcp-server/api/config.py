# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Configuration module for the OpenAPI MCP Server."""

import os
from awslabs.openapi_mcp_server import get_caller_info, logger
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    """Configuration for the OpenAPI MCP Server."""

    # API information
    api_name: str = 'awslabs-openapi-mcp-server'
    api_base_url: str = 'https://localhost:8000'
    api_spec_url: str = ''
    api_spec_path: str = ''

    # Authentication
    auth_type: str = 'none'  # none, basic, bearer, api_key, cognito
    auth_username: str = ''
    auth_password: str = ''
    auth_token: str = ''
    auth_api_key: str = ''
    auth_api_key_name: str = 'api_key'
    auth_api_key_in: str = 'header'  # header, query, cookie

    # Cognito authentication
    auth_cognito_client_id: str = ''
    auth_cognito_username: str = ''
    auth_cognito_password: str = ''
    auth_cognito_client_secret: str = ''
    auth_cognito_domain: str = ''  # Required for client credentials flow
    auth_cognito_scopes: str = ''  # Optional, comma-separated list of scopes
    auth_cognito_user_pool_id: str = ''
    auth_cognito_region: str = 'us-east-1'

    # Server configuration
    # Default to localhost for security; use SERVER_HOST env var to override when needed (e.g. in Docker)
    host: str = '127.0.0.1'
    port: int = 8000
    debug: bool = False
    transport: str = 'stdio'
    http_path: str = '/mcp'
    allow_remote_bind: bool = False
    allowed_origins: list[str] = field(default_factory=list)
    message_timeout: int = 60
    version: str = ''

    def __post_init__(self):
        """Set version from package metadata if not provided."""
        if not self.version:
            from awslabs.openapi_mcp_server import __version__

            self.version = __version__

    # Tag filtering
    include_tags: str = ''  # comma-separated list of OpenAPI tags to include
    exclude_tags: str = ''  # comma-separated list of OpenAPI tags to exclude

    # HTTP method filtering (feature flag; no-op when empty)
    # Comma-separated HTTP methods to suppress from MCP tools, e.g. POST,PUT,DELETE,PATCH
    # for a read-only MCP connection.  GET is always ignored (GET ops become resources).
    disable_http_methods: str = ''

    # Operation count limiting (feature flag; 0 = unlimited)
    # Cap on the number of MCP tools exposed.  GET-type tools survive the cap first.
    # Useful for large specs that exceed SSE frame limits or bloat LLM context.
    max_tools: int = 0

    # Output validation
    validate_output: bool = True  # validate API responses against OpenAPI response schemas

    # Additional API specs for multi-spec composition
    # JSON array: [{"name": "...", "spec_url": "...", "base_url": "..."}]
    additional_specs: str = ''

    # Security settings for URL/path validation
    allow_insecure_http: bool = False  # permit http:// URLs (default: HTTPS only)
    allow_private_networks: bool = False  # permit private/loopback/link-local IPs
    allowed_spec_dirs: str = ''  # colon-separated list of allowed directories for spec_path


def load_config(args: Any = None) -> Config:
    """Load configuration from arguments and environment variables.

    Args:
        args: Command line arguments

    Returns:
        Config: Configuration object

    """
    logger.debug('Loading configuration')

    # Get caller information for debugging
    caller_info = get_caller_info()
    logger.debug(f'Called from {caller_info}')

    # Create default config
    config = Config()

    # Load from environment variables
    env_vars = {
        # API information
        'API_NAME': (lambda v: setattr(config, 'api_name', v)),
        'API_BASE_URL': (lambda v: setattr(config, 'api_base_url', v)),
        'API_SPEC_URL': (lambda v: setattr(config, 'api_spec_url', v)),
        'API_SPEC_PATH': (lambda v: setattr(config, 'api_spec_path', v)),
        # Authentication
        'AUTH_TYPE': (lambda v: setattr(config, 'auth_type', v)),
        'AUTH_USERNAME': (lambda v: setattr(config, 'auth_username', v)),
        'AUTH_PASSWORD': (lambda v: setattr(config, 'auth_password', v)),
        'AUTH_TOKEN': (lambda v: setattr(config, 'auth_token', v)),
        'AUTH_API_KEY': (lambda v: setattr(config, 'auth_api_key', v)),
        'AUTH_API_KEY_NAME': (lambda v: setattr(config, 'auth_api_key_name', v)),
        'AUTH_API_KEY_IN': (lambda v: setattr(config, 'auth_api_key_in', v)),
        # Cognito authentication environment variables
        'AUTH_COGNITO_CLIENT_ID': (lambda v: setattr(config, 'auth_cognito_client_id', v)),
        'AUTH_COGNITO_USERNAME': (lambda v: setattr(config, 'auth_cognito_username', v)),
        'AUTH_COGNITO_PASSWORD': (lambda v: setattr(config, 'auth_cognito_password', v)),
        'AUTH_COGNITO_CLIENT_SECRET': (lambda v: setattr(config, 'auth_cognito_client_secret', v)),
        'AUTH_COGNITO_DOMAIN': (lambda v: setattr(config, 'auth_cognito_domain', v)),
        'AUTH_COGNITO_SCOPES': (lambda v: setattr(config, 'auth_cognito_scopes', v)),
        'AUTH_COGNITO_USER_POOL_ID': (lambda v: setattr(config, 'auth_cognito_user_pool_id', v)),
        'AUTH_COGNITO_REGION': (lambda v: setattr(config, 'auth_cognito_region', v)),
        # Server configuration
        'SERVER_HOST': (lambda v: setattr(config, 'host', v)),
        'SERVER_PORT': (lambda v: setattr(config, 'port', int(v))),
        'SERVER_DEBUG': (lambda v: setattr(config, 'debug', v.lower() == 'true')),
        'SERVER_TRANSPORT': (lambda v: setattr(config, 'transport', v)),
        'SERVER_HTTP_PATH': (lambda v: setattr(config, 'http_path', v)),
        'ALLOW_REMOTE_BIND': (
            lambda v: setattr(config, 'allow_remote_bind', v.lower() in ('true', '1', 'yes'))
        ),
        'ALLOWED_ORIGINS': (
            lambda v: setattr(
                config,
                'allowed_origins',
                [origin.strip() for origin in v.split(',') if origin.strip()],
            )
        ),
        'SERVER_MESSAGE_TIMEOUT': (lambda v: setattr(config, 'message_timeout', int(v))),
        # Tag filtering
        'INCLUDE_TAGS': (lambda v: setattr(config, 'include_tags', v)),
        'EXCLUDE_TAGS': (lambda v: setattr(config, 'exclude_tags', v)),
        # HTTP method filtering
        'DISABLE_HTTP_METHODS': (lambda v: setattr(config, 'disable_http_methods', v)),
        # Operation count limiting
        'MAX_TOOLS': (lambda v: setattr(config, 'max_tools', int(v))),
        # Output validation
        'VALIDATE_OUTPUT': (lambda v: setattr(config, 'validate_output', v.lower() != 'false')),
        # Additional specs
        'ADDITIONAL_SPECS': (lambda v: setattr(config, 'additional_specs', v)),
        # Security settings
        'ALLOW_INSECURE_HTTP': (
            lambda v: setattr(config, 'allow_insecure_http', v.lower() in ('true', '1', 'yes'))
        ),
        'ALLOW_PRIVATE_NETWORKS': (
            lambda v: setattr(config, 'allow_private_networks', v.lower() in ('true', '1', 'yes'))
        ),
        'ALLOWED_SPEC_DIRS': (lambda v: setattr(config, 'allowed_spec_dirs', v)),
    }

    # Load environment variables
    env_loaded = {}
    for key, setter in env_vars.items():
        if key in os.environ:
            env_value = os.environ[key]
            setter(env_value)
            env_loaded[key] = env_value

    if env_loaded:
        logger.debug(
            f'Loaded {len(env_loaded)} environment variables: {", ".join(env_loaded.keys())}'
        )

    # Load from arguments
    if args:
        arg_values = vars(args)
        if hasattr(args, 'api_name') and args.api_name:
            logger.debug(f'Setting API name from arguments: {args.api_name}')
            config.api_name = args.api_name

        if hasattr(args, 'api_url') and args.api_url:
            logger.debug(f'Setting API base URL from arguments: {args.api_url}')
            config.api_base_url = args.api_url

        if hasattr(args, 'spec_url') and args.spec_url:
            logger.debug(f'Setting API spec URL from arguments: {args.spec_url}')
            config.api_spec_url = args.spec_url

        if hasattr(args, 'spec_path') and args.spec_path:
            logger.debug(f'Setting API spec path from arguments: {args.spec_path}')
            config.api_spec_path = args.spec_path

        if arg_values.get('port') is not None:
            logger.debug(f'Setting port from arguments: {args.port}')
            config.port = args.port

        for argument, attribute in (
            ('transport', 'transport'),
            ('host', 'host'),
            ('http_path', 'http_path'),
            ('allow_remote_bind', 'allow_remote_bind'),
        ):
            value = arg_values.get(argument)
            if value is not None:
                setattr(config, attribute, value)

        allowed_origins = arg_values.get('allowed_origins')
        if allowed_origins is not None:
            config.allowed_origins = (
                [origin.strip() for origin in allowed_origins.split(',') if origin.strip()]
                if isinstance(allowed_origins, str)
                else list(allowed_origins)
            )

        if hasattr(args, 'debug') and args.debug:
            logger.debug('Setting debug mode from arguments')
            config.debug = True

        # Authentication arguments
        if hasattr(args, 'auth_type') and args.auth_type:
            logger.debug(f'Setting auth type from arguments: {args.auth_type}')
            config.auth_type = args.auth_type

        if hasattr(args, 'auth_username') and args.auth_username:
            logger.debug('Setting auth username from arguments')
            config.auth_username = args.auth_username

        if hasattr(args, 'auth_password') and args.auth_password:
            logger.debug('Setting auth password from arguments')
            config.auth_password = args.auth_password

        if hasattr(args, 'auth_token') and args.auth_token:
            logger.debug('Setting auth token from arguments')
            config.auth_token = args.auth_token

        if hasattr(args, 'auth_api_key') and args.auth_api_key:
            logger.debug('Setting auth API key from arguments')
            config.auth_api_key = args.auth_api_key

        if hasattr(args, 'auth_api_key_name') and args.auth_api_key_name:
            logger.debug(f'Setting auth API key name from arguments: {args.auth_api_key_name}')
            config.auth_api_key_name = args.auth_api_key_name

        if hasattr(args, 'auth_api_key_in') and args.auth_api_key_in:
            logger.debug(f'Setting auth API key location from arguments: {args.auth_api_key_in}')
            config.auth_api_key_in = args.auth_api_key_in

        # Cognito authentication arguments
        if hasattr(args, 'auth_cognito_client_id') and args.auth_cognito_client_id:
            logger.debug('Setting Cognito client ID from arguments')
            config.auth_cognito_client_id = args.auth_cognito_client_id

        if hasattr(args, 'auth_cognito_username') and args.auth_cognito_username:
            logger.debug('Setting Cognito username from arguments')
            config.auth_cognito_username = args.auth_cognito_username

        if hasattr(args, 'auth_cognito_password') and args.auth_cognito_password:
            logger.debug('Setting Cognito password from arguments')
            config.auth_cognito_password = args.auth_cognito_password

        if hasattr(args, 'auth_cognito_client_secret') and args.auth_cognito_client_secret:
            logger.debug('Setting Cognito client secret from arguments')
            config.auth_cognito_client_secret = args.auth_cognito_client_secret

        if hasattr(args, 'auth_cognito_domain') and args.auth_cognito_domain:
            logger.debug('Setting Cognito domain from arguments')
            config.auth_cognito_domain = args.auth_cognito_domain

        if hasattr(args, 'auth_cognito_scopes') and args.auth_cognito_scopes:
            logger.debug('Setting Cognito scopes from arguments')
            config.auth_cognito_scopes = args.auth_cognito_scopes

        if hasattr(args, 'auth_cognito_user_pool_id') and args.auth_cognito_user_pool_id:
            logger.debug('Setting Cognito user pool ID from arguments')
            config.auth_cognito_user_pool_id = args.auth_cognito_user_pool_id

        if hasattr(args, 'auth_cognito_region') and args.auth_cognito_region:
            logger.debug(f'Setting Cognito region from arguments: {args.auth_cognito_region}')
            config.auth_cognito_region = args.auth_cognito_region

        # Tag filtering arguments
        if hasattr(args, 'include_tags') and args.include_tags:
            config.include_tags = args.include_tags

        if hasattr(args, 'exclude_tags') and args.exclude_tags:
            config.exclude_tags = args.exclude_tags

        # HTTP method filtering arguments
        if hasattr(args, 'disable_http_methods') and args.disable_http_methods:
            config.disable_http_methods = args.disable_http_methods

        # Operation count limiting arguments
        if hasattr(args, 'max_tools') and args.max_tools is not None:
            config.max_tools = args.max_tools

        # Output validation
        if hasattr(args, 'no_validate_output') and args.no_validate_output:
            config.validate_output = False

        # Additional specs
        if hasattr(args, 'additional_specs') and args.additional_specs:
            config.additional_specs = args.additional_specs

        # Security settings
        if hasattr(args, 'allow_insecure_http') and args.allow_insecure_http:
            config.allow_insecure_http = True

        if hasattr(args, 'allow_private_networks') and args.allow_private_networks:
            config.allow_private_networks = True

        if hasattr(args, 'allowed_spec_dirs') and args.allowed_spec_dirs:
            config.allowed_spec_dirs = args.allowed_spec_dirs

    from awslabs.openapi_mcp_server.transport import validate_transport_config

    config.transport = validate_transport_config(config).value

    # Log final configuration details
    logger.info(f'Configuration loaded: API name={config.api_name}, transport={config.transport}')

    return config
