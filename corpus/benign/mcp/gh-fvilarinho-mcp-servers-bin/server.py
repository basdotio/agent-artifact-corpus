from os import name

import requests
import json
from configparser import ConfigParser
from mcp.server.fastmcp import FastMCP

# Starts the MCP server.
print("Staring server...")
mcp = FastMCP("cameras-automation")

# Loads configuration from file.
print("Loading settings...")

config = ConfigParser()
config.read("../etc/config.ini")

print("Settings loaded!")

print("Server started!")

# Gets the value of a section key.
def get_config_value(section, key):
    """Helper function to retrieve a configuration value or raise an error"""
    if not config.has_section(section):
        raise ValueError(f"Section '{section}' not found!")

    if not config.has_option(section, key):
        raise ValueError(f"Configuration key '{key}' not found in the section '{section}'!")

    return config.get(section, key)

# Gets the required headers used to do the API calls.
def get_headers(camera: str) -> dict:
    bearer_token = get_config_value(camera, "bearer_token")

    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }

@mcp.tool()
def available_cameras() -> dict:
    """
    List all available cameras defined in the configuration file.
    """
    cameras = config.sections()
    available_cameras = []

    for camera in cameras:
        if camera != "server":
            available_cameras.append(camera)

    return { "cameras": available_cameras }

@mcp.tool()
def describe_camera(name: str) -> dict:
    """
    Give the details about a camera by name (not by model). The name must be in the configuration file.
    """
    name = name.replace(" camera", "")
    url = get_config_value(name, "url")
    url += "/stats"

    headers = get_headers(name)
    timeout = int(get_config_value(name, "timeout"))

    response = requests.get(
        url,
        headers = headers,
        timeout = timeout
    )

    data = json.loads(response.text)
    data["name"] = name

    return data

@mcp.tool()
def turn_on_camera(name: str = "") -> dict:
    """
    Turn on a camera by name. The name must be in the configuration file.
    """
    name = name.replace(" camera", "")
    url = get_config_value(name, "url")
    url += "/on"

    headers = get_headers(name)
    timeout = int(get_config_value(name, "timeout"))

    response = requests.post(
        url,
        headers = headers,
        timeout = timeout
    )

    return json.loads(response.text)

@mcp.tool()
def turn_off_camera(name: str = "") -> dict:
    """
    Turn off a camera by name. The name must be in the configuration file.
    """
    name = name.replace(" camera", "")
    url = get_config_value(name, "url")
    url += "/off"

    headers = get_headers(name)
    timeout = int(get_config_value(name, "timeout"))

    response = requests.post(
        url,
        json={},
        headers = headers,
        timeout = timeout
    )

    return json.loads(response.text)

if __name__ == "__main__":
    mcp.run()
