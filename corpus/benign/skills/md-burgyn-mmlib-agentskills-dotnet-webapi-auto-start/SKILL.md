---
name: dotnet-webapi-auto-start
description: Automatically checks and starts .NET WebAPI service at the end of agent work. Use when agent finishes modifying a .NET WebAPI project - at the end of work, checks if the service is running based on launchSettings.json, if not, asks the user if they want to start it, and if yes, starts it using dotnet run with launch profile and opens browser to /scalar.
---

# .NET WebAPI Auto Start

## Overview

This skill automatically checks if a .NET WebAPI service is running after the agent completes work on a .NET WebAPI project. If the service is not running, it offers to start it and open the Scalar API documentation in the browser.

## When to Use

This skill activates automatically at the end of agent work when:
- The agent has been modifying a .NET WebAPI project
- The workspace contains a `.csproj` file with ASP.NET Core references
- The project has a `launchSettings.json` file (or `Properties/launchSettings.json`)

## Workflow

Follow these steps sequentially at the end of agent work:

### Step 1: Detect .NET WebAPI Project

1. Search for `.csproj` files in the workspace root
2. Read the `.csproj` file to verify it contains ASP.NET Core references:
   - Look for `Microsoft.AspNetCore.App` framework reference
   - Or `Microsoft.AspNetCore.App` package reference
   - Or `Microsoft.NET.Sdk.Web` SDK
3. If no WebAPI project is found, skip this workflow
4. Search for `launchSettings.json` in:
   - `Properties/launchSettings.json` (preferred location)
   - `launchSettings.json` (root directory)

### Step 2: Determine Launch Profile

1. Read and parse `launchSettings.json` as JSON
2. Extract the `profiles` object
3. Select a launch profile in this priority order:
   - Profile named `"http"` (if exists)
   - Profile named `"https"` (if exists)
   - First profile in the profiles object
4. Extract the base URL:
   - If `launchUrl` exists, use it as-is (it may already include a path)
   - Otherwise, extract the first URL from `applicationUrl` (split by semicolon if multiple URLs)
   - If `applicationUrl` contains multiple URLs separated by semicolons, prefer HTTP over HTTPS for faster startup
5. Construct the Scalar URL:
   - If `launchUrl` exists and doesn't end with `/scalar`, replace it with `/scalar`
   - If no `launchUrl`, append `/scalar` to the base URL from `applicationUrl`
   - Example: `http://localhost:5000` → `http://localhost:5000/scalar`

### Step 3: Check if Service is Running

1. Extract the port number from the base URL (from Step 2)
2. Try to check if the service is running using one of these methods:

   **Method A: HTTP Request (preferred)**
   - Use `curl -f --max-time 2 <base-url>` or similar HTTP request
   - If the request succeeds (exit code 0), the service is running
   - If it fails or times out, the service is not running

   **Method B: Port Check (fallback)**
   - On macOS/Linux: `lsof -i :<port>` or `netstat -an | grep :<port>`
   - On Windows: `netstat -an | findstr :<port>`
   - If port is in use, service may be running (but verify with HTTP request)

3. If service is running:
   - Inform the user: "The service is already running."
   - End workflow

### Step 4: Ask User

If the service is not running:

1. Use the `AskQuestion` tool with this question:
   - Question: "The service is not running. Would you like to start it and open Scalar documentation?"
   - Options: `["Yes", "No"]`

2. If user selects "No":
   - End workflow

### Step 5: Start Service

If user selects "Yes":

1. Determine the launch profile name (from Step 2)
2. Run the service in the background:
   ```bash
   dotnet run --launch-profile <profile-name>
   ```
   - Use `run_terminal_cmd` with `is_background: true`
   - Run from the directory containing the `.csproj` file

3. Wait for service startup:
   - Wait 3-5 seconds for the service to start
   - Optionally check if the service is responding (repeat Step 3 check)

4. Open browser to Scalar documentation:
   - Construct the full Scalar URL (from Step 2)
   - macOS: `open <scalar-url>`
   - Linux: `xdg-open <scalar-url>`
   - Windows: `start <scalar-url>`

5. Inform the user:
   - "Service started. Opening Scalar documentation in browser."

## Edge Cases

### No launchSettings.json Found

- Use default ports:
  - HTTP: `http://localhost:5000`
  - HTTPS: `https://localhost:5001` (if HTTPS is preferred)
- Use profile name `"http"` or `"https"` when running `dotnet run`
- If neither profile exists, run `dotnet run` without `--launch-profile`

### Multiple Launch Profiles

- Prefer `"http"` over `"https"` for faster startup (no certificate setup)
- If only HTTPS profiles exist, use the first HTTPS profile
- Extract the first URL from `applicationUrl` if multiple URLs are present

### Service Already Running

- If Step 3 detects the service is running, inform the user and end workflow
- Do not attempt to start another instance

### Startup Failure

- If `dotnet run` fails, inform the user about the error
- Do not attempt to open the browser if startup failed
- Show the error message from the command output

### No .csproj File Found

- Skip this workflow entirely
- Do not prompt the user

## Technical Notes

### launchSettings.json Structure

```json
{
  "profiles": {
    "http": {
      "commandName": "Project",
      "applicationUrl": "http://localhost:5000",
      "launchUrl": "swagger"
    },
    "https": {
      "commandName": "Project",
      "applicationUrl": "https://localhost:5001",
      "launchUrl": "swagger"
    }
  }
}
```

### Service Check Commands

**HTTP Request:**
```bash
curl -f --max-time 2 http://localhost:5000
```

**Port Check (macOS/Linux):**
```bash
lsof -i :5000
# or
netstat -an | grep :5000
```

**Port Check (Windows):**
```bash
netstat -an | findstr :5000
```

### Starting Service

```bash
# From project root directory
dotnet run --launch-profile http
```

### Opening Browser

**macOS:**
```bash
open http://localhost:5000/scalar
```

**Linux:**
```bash
xdg-open http://localhost:5000/scalar
```

**Windows:**
```bash
start http://localhost:5000/scalar
```
