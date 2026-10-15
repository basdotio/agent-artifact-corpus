## MCP Auth Demo

This mini project shows how to switch between:

1. Public OpenAI API (standard `sk-` key)
2. Azure OpenAI with a resource key
3. Azure OpenAI with Azure Active Directory (DefaultAzureCredential)

### Environment Variables

Create a `.env` (not committed) with one of the following modes:

Public OpenAI:
```
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4o-mini
```

Azure (key mode):
```
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
OPENAI_API_KEY=<azure-resource-key>
OPENAI_MODEL=<deployment-name>
AZURE_OPENAI_API_VERSION=2024-02-01
```

Azure (AAD token mode):
```
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
OPENAI_MODEL=<deployment-name>
AZURE_OPENAI_API_VERSION=2024-02-01
# No OPENAI_API_KEY present
```
Then authenticate with `az login`, or rely on Managed Identity / VS Code signed-in account.

### Running

```
uv run python main.py
```

### Diagnostics

If authentication fails, run:
```
uv run python diagnose_auth.py
```
This prints a summary of detected mode and performs a lightweight request.

### Common Issues

1. 401 invalid_api_key when using Azure key but hitting `api.openai.com`:
	- Set `AZURE_OPENAI_ENDPOINT`.
2. Non `sk-` key treated as public:
	- Provide Azure endpoint so Azure mode is selected.
3. Deployment not found / 404:
	- Ensure `OPENAI_MODEL` equals your deployment name (case-sensitive).
4. AAD token failure:
	- Confirm `az account show` works and that your identity has a Cognitive Services role.

### Security

Do not commit `.env`. Rotate keys periodically. For production prefer AAD token flow over static keys.

