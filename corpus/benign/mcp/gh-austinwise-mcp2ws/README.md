# mcp2ws

Did you just wake up from a 20 year coma? Did you build a bunch of buzzword compliant web services
back in the early 2000s and want all your [SOAP](https://en.wikipedia.org/wiki/SOAP) and
[WSDL](https://en.wikipedia.org/wiki/Web_Services_Description_Language)
to be relevant again?

Now you can put the smooth sheen of AI on your pile of angle brackets by exposing your
SOAP-based web service as a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server.
It's time to wake from that coma and start hallucinating.

## What?

To explain the joke: back in the early 2000s
[web services](https://en.wikipedia.org/wiki/Web_service)
were promoted heavily by several companies as the future of how organizations interoperate with each
other. The specific vision included a plethora of XML-based communication formats that never caught
on broadly. Instead REST-ful web apis became the norm. But now 20 years later, MCP arrives claiming
it too is the future of how companies interoperate, at least for AI-related applications. And unlike
SOAP, there are a lot of very useful MCP servers and client delivering on that promise. So the
conceit of this repos is to give SOAP-based web services a second chance at the limelight.

## Prerequisites

* Have a web service described by a WSDL file.
* Have a compatible version of Python (tested with 3.13) or [`uv`](https://docs.astral.sh/uv/) installed on your computer.

## Running

With `uv`:

```bash
uv run main.py
```

With regular python:

```
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Usage

To start the MCP server, run the `main.py` script with the URL of the WSDL file you want to access.

```bash
uv run main.py <WSDL_URL>
```

For example, if you have a WSDL at `http://www.dneonline.com/calculator.asmx?wsdl`:

```bash
uv run main.py http://www.dneonline.com/calculator.asmx?wsdl
```

This tool has been tested with these random WSDL files I found on the internet:

* http://www.dneonline.com/calculator.asmx?wsdl
* http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso?WSDL

## Configure your agentic coding tool

Configure your MCP client (e.g., Gemini CLI, or an IDE extension) to run this script.

**Example generic MCP config:**

```json
{
  "mcpServers": {
    "soap-service": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/mcp2ws/pyproject.toml",
        "/path/to/mcp2ws/main.py",
        "http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso?WSDL"
      ]
    }
  }
}
```

## Example Session

In Gemini CLI, using the
<http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso?WSDL>
service:

```
> What is the capital city of France? Use the soap tool.

✦ I will find the ISO code for France and then use it to get the capital city.

╭────────────────────────────────────────────────────────────────────────╮
│ ✓  CountryISOCode (soap-service MCP Server) {"sCountryName":"France"}  │
│                                                                        │
│ FR                                                                     │
╰────────────────────────────────────────────────────────────────────────╯
✦ I will now retrieve the capital city of France using its ISO code.
╭────────────────────────────────────────────────────────────────────────╮
│ ✓  CapitalCity (soap-service MCP Server) {"sCountryISOCode":"FR"}      │
│                                                                        │
│ Paris                                                                  │
╰────────────────────────────────────────────────────────────────────────╯
✦ The capital city of France is Paris.
```

## TODO

* Expose `<documentation/>` tags from WSDL in the tool listing. I don't know how standard this is, but
  I've seen these tags in .ASMX WSDL files.
* Better support for mapping XML schema to JSON schema for input. Currently only primitive types are supported.
* Add tests.
* Run evals and optimize the how the tools are described in the MCP protocol.
* Implement support for more web service standards like
  [WS-*](https://en.wikipedia.org/wiki/List_of_web_service_specifications) and
  [UDDI](https://en.wikipedia.org/wiki/Web_Services_Discovery).
  This probably won't happen because this stops being a fun joke and starts being a job.
