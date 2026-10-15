# Nextra Development: Error & Solution Log

This document serves as a persistent accumulator for issues encountered during development and their corresponding solutions.

### 1. Rhino Object Deletion Key Not Working
*   **Error**: After generating an object using the LLM via the nextra.rhino plugin, pressing the `Delete` key on the keyboard did nothing. The user had to click another tab or the main viewport first.
*   **Root Cause**: The Eto `WebView` panel retained keyboard focus after generation. Since Rhino's main window didn't have focus, it ignored keyboard shortcuts like `Delete`.
*   **Solution**: Updated the frontend `script.js` to automatically restore focus to Rhino upon completion of geometry generation (`document.title = 'nextra-focus|';`).

### 2. External URLs Opening Delayed
*   **Error**: Clicking external links (e.g., Create Account) in the plugin UI didn't open the browser immediately. It would only pop up after the user clicked another tab or interacted with Rhino.
*   **Root Cause**: In `NextraPanel.cs`, the `System.Diagnostics.Process.Start()` call was being executed directly inside the WebView's synchronous `DocumentTitleChanged` event. This deadlocked the WebView's internal event pump because it was waiting for the OS to flush the message queue, which only happened when the user clicked the Rhino viewport.
*   **Solution**: Wrapped the external URL opening and focus logic inside `Eto.Forms.Application.Instance.AsyncInvoke(() => { ... })`. This queues the action to run on the main UI thread immediately *after* the WebView finishes its internal click event, preventing the freeze.

### 3. Token Multiplier and UI Display
*   **Error**: The UI was showing caching tokens alongside regular tokens, which was visually cluttered. Additionally, token metrics should only be visible when Developer Mode is active.
*   **Root Cause**: The token display logic in `script.js` was unconditionally rendering all token metadata passed from the backend.
*   **Solution**: In the frontend `script.js`, we wrapped the token display logic in an `if (isDeveloperMode)` check and stripped the cache token HTML, leaving only the clean total token count.

### 4. Token Deduction "Never Reaching 0" 
*   **Error**: Users observed that sometimes when their remaining tokens were less than the cost of a generation, the tokens wouldn't be deducted, leaving them stranded with a small token balance that never reached `0`.
*   **Root Cause**: If an API attempts to deduct an amount greater than the user's available balance, the strict Supabase RPC constraint (`IF get_available_tokens < p_amount THEN RETURN FALSE`) rejects the entire transaction to prevent negative balances.
*   **Solution**: In the Next.js web backend (`nextra.web/src/app/api/plugin/verify/route.js`), the deduction calculation utilizes `Math.min(tokens, cost)`. If a user generates a prompt costing 1500 tokens but only has 1000 left, the backend caps the deduction request at exactly 1000 tokens. This safely drains their balance to exactly `0` without triggering the database rejection.

### 5. Login "Expecting Value" JSON Error
*   **Error**: The Grasshopper plugin login popup displayed `Validation Failed: Server error: Expecting value: line 1 column 1 (char 0)`.
*   **Root Cause**: The Python backend was hitting a custom Next.js deployment URL but missing the required Next.js `basePath` (`/nextra.rhino.gh`). Because the URL was incomplete, the Next.js server returned a 404 HTML error page instead of JSON. The Python backend attempted to parse this HTML as JSON (`resp.json()`), which crashed with a decoding error.
*   **Solution**: Updated `next_web_url` in `backend_config.json` to explicitly include the `/nextra.rhino.gh` base path, and redeployed the python backend.

### 6. External URLs Hidden Behind Plugin Popup
*   **Error**: Clicking an external URL in the login popup opened the browser, but it appeared to only show up *after* the user closed the popup.
*   **Root Cause**: The `NextraMainWindow` form had `Topmost = true` enabled. This forced the popup to remain above all OS windows, including the newly spawned web browser. The browser opened successfully but was hidden behind the popup.
*   **Solution**: Removed `Topmost = true` from `NextraMainWindow.cs`. Since the window's `Owner` is explicitly set to Rhino's MainWindow, it will still natively stay above Grasshopper/Rhino without aggressively blocking standalone applications like Chrome.

### 7. Grasshopper UI Hanging on External Links and Deletions
*   **Error**: Similar to the Rhino panel issue, clicking external URLs or attempting to delete objects after generating them in Grasshopper caused the UI to hang until a separate tab or viewport was clicked.
*   **Root Cause**: While `NextraPanel.cs` was fixed previously using `AsyncInvoke`, the exact same deadlock existed in `NextraMainWindow.cs` (the Grasshopper popup). It was using a background `Task.Run` for `Process.Start`, which starved the OS message pump needed by the browser shell, freezing the WebView's event handler.
*   **Solution**: Applied `Eto.Forms.Application.Instance.AsyncInvoke` within `NextraMainWindow.cs` for the `nextra-external|` and `nextra-focus|` events, matching the Rhino fix.

### 8. Tokens Showing 0 and Failing to Deduct
*   **Error**: The user had manually granted themselves 10,000 tokens via the Supabase database, yet the UI displayed a balance of `0`, and generation requests were either rejected or ran without deducting tokens.
*   **Root Cause**: When adding tokens manually through the Supabase Dashboard, the user left the `expires_at` column `NULL`. The SQL functions `get_available_tokens` and `deduct_tokens` strictly filtered for `expires_at > now()`. Since `NULL > now()` evaluates to `NULL` (falsy in SQL), those token grants were completely ignored by the database.
*   **Solution**: Updated `setup_all_database.sql` to explicitly support non-expiring tokens by changing the filter to `(expires_at IS NULL OR expires_at > now())` and sorting by `expires_at ASC NULLS LAST`.

### 9. Skills Generation Token Multiplier Ignored
*   **Error**: When running a generation in the "Skills" tab, the `Pro` or `Thinking` mode token multipliers were not being applied, leading to undercharging for premium model usage.
*   **Root Cause**: In `agent.py`, the token deduction logic inside `run_skills_generation` mistakenly passed the raw token count directly to `verify_and_deduct_tokens`. It skipped the `math.ceil(raw_tokens * multiplier)` step that was correctly implemented in the standard chat generation loop.
*   **Solution**: Updated `agent.py`'s skills generation block to fetch the active `model_mode`, apply the correct multiplier from `get_model_config`, and pass the `final_cost` to the deduction logic.

### 10. Grasshopper UI Hanging on Initial Open (Blank Screen)
*   **Error**: When launching the `nextra.gh` UI by clicking the canvas widget, the popup window appeared completely blank and Grasshopper froze until the user clicked another tab or viewport to force a UI refresh.
*   **Root Cause**: The widget's `ToggleUI()` method (which instantiated and showed the `NextraMainWindow`) was being called synchronously directly inside the Grasshopper Canvas `MouseDown` event handler. This created a deadlock where Grasshopper paused its WinForms message pump waiting for the UI to open, but the Eto WebView required the message pump to initialize its browser engine.
*   **Solution**: In `NextraAssemblyPriority.cs`, wrapped the `widget.ToggleUI()` call inside `Eto.Forms.Application.Instance.AsyncInvoke(() => { ... })`. This allows the `MouseDown` event to finish and release the message pump *before* the WebView initializes.

### 11. Tokens Never Deducting (Cloud Deployment Gap)
*   **Error**: Even after fixing the token deduction logic in `route.js` (Item 4) and the Supabase triggers (Item 8), tokens were still not being deducted in production.
*   **Root Cause**: The fix for the `Math.min(tokens, cost)` cap was implemented in the local codebase for `nextra.web`, but the Next.js web application was never re-deployed to Google Cloud Run. The Grasshopper/Rhino plugins were still communicating with the outdated production endpoint.
*   **Solution**: Ran `gcloud run deploy nextra-web` to sync the local `nextra.web` backend fixes to the live production server.

### 12. WebView COM Re-Entrancy Deadlock (UI Still Hanging / Delete Key Not Working)
*   **Error**: Despite applying `AsyncInvoke` and `Task.Run` in the C# plugin code (Item 2 & 7), the Rhino/Grasshopper WebView still hung when opening external links or triggering focus changes. This caused the `Delete` key to fail after generation, because the `nextra-focus|` event was getting swallowed by the thread lock, preventing keyboard focus from returning to Rhino. The UI would only refresh after the user explicitly clicked another tab.
*   **Root Cause**: Inside the C# `DocumentTitleChanged` event handler, we were executing `_webView.ExecuteScript("document.title = '...';")` to reset the title flag. Calling `ExecuteScript` against the WebView2 COM interface *while* it is actively processing a Javascript-initiated COM event triggers a thread re-entrancy deadlock. The WebView effectively freezes itself until the OS forces a UI thread pump.
*   **Solution**: Completely removed `ExecuteScript` calls from `NextraPanel.cs` and `NextraMainWindow.cs`. Instead, shifted the responsibility to the frontend: `script.js` now uses `setTimeout(() => { document.title = '...'; }, 50);` to silently reset its own title shortly after triggering the C# hook. This allows the `nextra-focus|` command to cleanly execute and instantly transfer keyboard focus back to Rhino/Grasshopper, making the `Delete` key work flawlessly immediately after generation!


### 13. Token Deduction Silently Bypassed for Non-BYOK Users
*   **Error**: Tokens were not being deducted for users utilizing the default server API keys, despite all Cloud deployments and database patches being applied.
*   **Root Cause**: In `agent.py`, the token deduction block checked `if resolved_key and not resolved_key.startswith("AIza"):`. Since `resolved_key` is ALWAYS a valid Gemini API key (even when falling back to the server config), it always started with `"AIza"`, causing the script to skip the token deduction block permanently.
*   **Solution**: Changed the check in `agent.py` to `if api_key and not api_key.startswith("AIza"):`. Now it correctly checks the *user's inputted key* (which is their Nextra password, not an `AIza` string) to determine if they are using Bring-Your-Own-Key.

### 14. "Stop" Button and "New Chat" Ignored by LLM Task Loop
*   **Error**: Clicking the Stop button or New Chat button would visually reset the frontend UI, but the backend would continue generating. If the LLM request took a long time (e.g., analyzing a large `investigate_geometry` result), the backend would eventually send a `"Still working..."` status message 15 seconds later, which would unexpectedly re-disable the user's input box in the frontend.
*   **Root Cause**: While `/stop` correctly set `cancel_flag = True`, the `while not task.done():` polling loop around `chat_session.send_message(parts)` inside `agent.py` did not check the `cancel_flag`. The loop waited unconditionally for the LLM to finish, locking up backend resources and eventually triggering a status blast to the UI.
*   **Solution**: Updated the `asyncio.wait` loop inside `run_generation` and `run_skills_generation` to yield every `2.0` seconds and explicitly check `if cancel_flag: task.cancel()`. Now, pressing Stop instantly severs the connection to the Gemini API and kills the backend task cleanly!

### 15. Disconnected WebSocket Permanently Freezes Frontend (No Error Message)
*   **Error**: If the backend connection dropped gracefully or the cloud instance scaled down while the UI was "Analyzing result...", the frontend UI would permanently hang. The text box remained disabled forever, the typing indicator kept spinning, and no error message was shown in the chat, even though the status dot turned red indicating "Disconnected".
*   **Root Cause**: The frontend `ws.onclose` event handler was indiscriminately disabling the input box (`messageInput.disabled = true;`) without checking if a generation was actively running. Unlike `ws.onerror`, it completely forgot to clear the `typingIndicator` or print a warning message.
*   **Solution**: Updated `ws.onclose` and `skillsWs.onclose` in `script.js` to detect if the typing indicator is visible. If it is, the script clears the spinner, prints a system message (`⚠️ Connection lost while generating...`), and automatically re-enables the text input so the user isn't permanently locked out of the UI!