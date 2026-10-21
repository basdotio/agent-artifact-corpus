# Dot CUA read adapter

While the read call is pending, the SDK prints `request_ready` with the server's
run directory, request ID and workout ID. The parent verifies the user's scope,
loads the worker source printed by:

```sh
python -m garmin_agent_tools.browser worker-path
```

Using only the platform's documented CUA runtime and an already bound authorized
Garmin tab, invoke the declared function:

```js
await observeQueuedWorkout(requestReady.value, authorizedGarminTab, {
  privateRoot: publicMcpContext.value.browser_home
});
```

On its initial attempt, this function navigates to the authorized workout or uses
the documented `Tab.reload()` when already at that URL, then freshly reads selected
visible workout fields. Its selectors reflect
one observed Garmin page version; changed or unsupported UI remains unknown. Only
`browser_not_ready` allows another fresh read of the same request/page with
`navigate:false`. Stop on login, CAPTCHA, permission denial or wrong page. Do not
retry or route around an access block. After `observation_saved`, publish it without
changing the original identifiers:

```sh
python -m garmin_agent_tools.browser publish-read --run-dir RUN_DIR --request-id REQUEST_ID
```

The original MCP call then completes. Each call needs its own refreshed page observation and
request; old observations cannot be relabelled as fresh. Unsupported sport/targets
remain null. Browser reads do not establish API authentication or watch receipt.
