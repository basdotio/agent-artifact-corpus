# python-pip-mcp

Minimal Example Implementation of an Anthropic [MCP](https://modelcontextprotocol.io/introduction) Client and Server in Python with Pip. 

The goal of this repository is to provide a reference implementation of a **mcp client and server** that can be easily debugged in VSCode on Windows using the Python / Python Debugger extension.

Alternative IDEs and OS are not tested but should work with minimal adjustments, too.

## Installation

```powershell
# create venv
python -m venv myenv
myenv\Scripts\activate

# install requirements
pip install -r requirements.txt

# create a .env file and set your anthropic api key
cp .env.sample .env

# run mcp_client.py script
python mcp_client.py

# query for current time
```

