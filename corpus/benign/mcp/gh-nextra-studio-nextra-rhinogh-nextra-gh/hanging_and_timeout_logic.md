---
title: hanging_and_timeout_logic
category: else
---

# Hanging and Timeout Prevention Logic

This document summarizes the architectural mechanisms implemented to prevent the Nextra Cloud Backend, the Google LLM API, and the local Rhino/Grasshopper client from hanging indefinitely during heavy script execution, buggy SDKs, or network instability.

## 1. The 180-Second Architecture
- **Gemini LLM Client (`genai.Client`)**: The Gemini client is explicitly configured with `http_options={'timeout': 180000}` (180 seconds in milliseconds). However, due to a known bug in the `google-genai` Python SDK where it occasionally passes `timeout=None` to the underlying HTTP client, this native setting cannot be fully trusted.
- **Manual LLM Thread Timeouts (`asyncio` wrapper)**: To completely bypass the SDK bug and prevent the LLM thread from endlessly returning `"Still working..."`, the synchronous `chat_session.send_message` call is isolated in a background thread using `asyncio.to_thread`. The main WebSocket loop actively monitors it via a `while not task.done()` loop that strictly checks `time.time()`. If 180 seconds pass without a response, the task is forcefully cancelled, throwing a manual application-level exception.
- **Local Worker Primitive (`send_worker_primitive`)**: When the cloud server sends a command (like `plugin-execute`) to the Grasshopper/Rhino plugin via WebSockets, it waits for the result using `asyncio.wait_for(future, timeout=180.0)`. If a generated script triggers an infinite loop or a massive operation that locks the local UI thread for more than 3 minutes, the cloud server automatically aborts the wait.

## 2. Graceful Error Fallbacks (The 4 Edge Cases)
If the local worker disconnects, times out, or the LLM crashes, throwing raw system errors confuses the LLM and creates a bad User Experience. The system now categorizes and gracefully catches all 4 failure states:

**State A: Raw Code Errors (Fails Fast)**
If the AI writes a script with a typo or an IndexError, it fails instantly locally. The C# worker catches the raw error text and sends it back. The LLM receives this raw error, realizes its mistake, and automatically tries again. 

**State B: System Disconnect (The Local Worker Dropped)**
If the local WebSocket genuinely drops (e.g., Rhino crashes, or a C# component triggers an infinite loop freezing the UI thread), the cloud server catches it and returns a secret flag: `SYSTEM_DISCONNECT`. The main backend loop intercepts this flag, bypasses the LLM, and gracefully returns a formatted Assistant message (e.g., `⚠️ **Connection Interrupted**...`) to the UI, allowing the user to seamlessly try again when the worker reconnects.

**State C: The 180s Timeout (The AI Script is Stuck)**
If the script hits the 180-second limit, the local software hasn't crashed; it is stuck in an infinite while loop or a massive geometric calculation, freezing the local thread. The cloud server catches `asyncio.TimeoutError` and explicitly returns the following string back to the LLM context:
> `"ERROR: Execution timed out after 180 seconds. You likely created an infinite loop or an overly heavy calculation. Do not apologize. Rewrite the script to be more efficient or add a safe-exit counter to your while loops."`

This ensures the LLM understands exactly what happened and guides it to rewrite the script more efficiently without getting stuck in a loop.

**State D: LLM API Timeout or Crash (The "Stop Answering" Edge Case)**
If the Google API SDK itself hangs indefinitely (bypassing the native timeout bug) or throws an unexpected 500 network exception, the system prevents the UI from endlessly spinning. Here is exactly how State D resolves:
1. **Thread Isolation**: The LLM API call runs inside an `asyncio.to_thread` task so it doesn't block the WebSocket connection.
2. **Time Tracking**: A `while` loop checks the task status every 15 seconds. If `time.time() - start_t > 180`, the backend executes `task.cancel()` and raises a manual `Exception`.
3. **Graceful UI Fallback**: The global `except Exception as e:` block intercepts this crash. Instead of sending a raw system `"type": "error"`, it formats the error into an `"type": "assistant"` JSON payload. 
4. **Frontend Resolution**: The Nextra frontend (`script.js`) receives the assistant message, hides the typing indicator, unlocks the text box, and renders the error as if the AI cleanly apologized (e.g., `⚠️ **Connection lost or AI error occurred**...`). This guarantees the UI never gets permanently stuck.

## 3. Asynchronous "Still Working..." Heartbeat
When the local software executes a heavy script, the main UI thread is blocked, meaning it cannot process new interactions. To prevent the user from thinking the system crashed, we wrap the `route_tool` execution in an asyncio task inside the websocket routers (`chat_websocket` and `skills_websocket`).

While waiting for the task to complete, a background `while` loop runs and sends this payload to the frontend every 15 seconds:
```json
{
  "type": "status",
  "content": "Still working..."
}
```
This heartbeat accomplishes two things:
1. It updates the frontend UI so the user knows the AI is still processing.
2. It generates network traffic that keeps the Cloud Run load balancer from dropping the frontend WebSocket due to inactivity.

## 4. 15-Minute Inactivity Auto-Shutdown
To optimize cloud resources and prevent runaway costs, the cloud backend runs a background monitor that automatically shuts down the server (exiting with code `0` to trigger a Cloud Run scale-to-zero) after **15 minutes** (900 seconds) of total inactivity.

To ensure the server does not shut down while a user actively has the Nextra panel open:
- The frontend client sends a `{ "type": "ping" }` message over the WebSocket every **20 seconds**.
- Receipt of any message (including this ping) updates the backend's `last_activity_time` tracker, resetting the inactivity countdown.

## 5. Local Worker Keep-Alive and Reconnect Loop
The C# local worker (`WorkerClient.cs` / `PluginWebSocketService.cs`) is designed with robust network resilience:
- **30-Second Ping Loop**: A background thread sends `{ "action": "ping" }` to the cloud backend every 30 seconds to keep the intermediate proxies and load balancers from closing the connection.
- **5-Second Reconnect Loop**: If the worker loses connection or fails to connect on startup, it enters a non-blocking `while` loop, waiting 5 seconds before attempting to connect again.
- **Thread-Isolated Receive Loop**: WebSocket reads run completely separated from the local main UI thread, ensuring incoming requests are queued and processed sequentially without blocking the network layer.
