#!/usr/bin/env bash

# Prepares the environment to execute this script.
function prepareToStart() {
    source .venv/bin/activate
}

# Gets the value of a section key.
function get_config_value() {
    CONFIG_FILE=../etc/config.ini
    SECTION=$1
    KEY=$2
    AWK_CMD=$(which awk)

    $AWK_CMD -F= -v sect="[$SECTION]" -v want_key="$KEY" '
        $0 == sect { in_section = 1; next }
        /^\[.*\]/   { in_section = 0 }

        in_section && $1 ~ "^[[:space:]]*" want_key "[[:space:]]*$" {
            gsub(/[[:space:]]*/, "", $2);
            print $2;

            exit 0
        }
    ' "$CONFIG_FILE"
}

# Starts the MCP server.
function start() {
    prepareToStart

    PYTHON_CMD=$(which python)
    MCPO_CMD=$(which mcpo)
    BEARER_TOKEN=$(get_config_value "server" "bearer_token")

    $MCPO_CMD --host 0.0.0.0 --port 8000 --api-key "$BEARER_TOKEN" -- $PYTHON_CMD server.py
}

start