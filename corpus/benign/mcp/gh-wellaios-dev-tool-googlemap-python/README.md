# WELLAIOS GeoLocator Tool Server (Standalone)

This repository features a standalone server demonstration for the WELLAIOS GeoLocator tool.
This tool leverages the Google Places API to find locations based on specific text queries, providing powerful geographical search capabilities to your AI agents.

## Getting Started

Follow these steps to set up and run your WELLAIOS GeoLocator server:

1. **Get a Google Places API Key**

   You'll need an API key from Google Cloud Platform with access to the Google Places API. Visit the [Google Cloud Console](https://console.cloud.google.com/) to obtain your key and enable the necessary APIs.

   For detailed, step-by-step instructions on how to get an API key and enable the Places API, please refer to the official Google Cloud documentation on [authentication](https://developers.google.com/maps/documentation/places/web-service/get-api-key).

2. **Install Python and Required Packages**

   Make sure you have Python installed on your system (Python 3.12+ is recommended).
   Then, navigate to your project directory in the terminal and install the necessary Python packages using `pip`:

   ```
   pip install -r requirements.txt
   ```

3. **Configure the Server**

   Create a file named `.env` in the root directory of your project (the same directory as `main.py`). Add the following content, replacing the placeholder values with your actual tokens and API key:

   ```
   AUTH_TOKEN=your_wellaios_auth_token_here
   Goog_Api_Key=your_google_places_api_key_here
   ```

   - `AUTH_TOKEN`: This is the bearer token used for authenticating clients with your tool server (e.g., from WELLAIOS).
   - `Goog_Api_Key`: This is your Google Places API key.

4. **Test Your Tool Server**

   You can test your running tool server

   - **MCP Inspector**:
     For basic testing and inspecting the tool's functionality, you can use the [MCP inspector](https://github.com/modelcontextprotocol/inspector).

     **Note**: The MCP Inspector currently does not support multi-user scenarios. Therefore, you won't be able to test the multi-user specific features using this tool alone.

   - **WELLAIOS Engine**:
     The best way to thoroughly test the multi-user capabilities and the full integration is by connecting your tool server to the WELLAIOS engine itself.
     Refer to the WELLAIOS documentation for instructions on how to connect external tool servers.

## Guide to connect to MCP Inspector

### Transport Type

Select `Streamble HTTP`

### URL

Enter the MCP path under your server's location.
For example, if your server is running locally on port 30000, the URL would be:

`http://localhost:30000/mcp`

### Authentication

Use `Bearer Token` as the authentication method.
Then, use the exact token you've set in your `.env` file.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file.
