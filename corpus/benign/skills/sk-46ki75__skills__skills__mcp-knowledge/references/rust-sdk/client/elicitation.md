# Client: elicitation (`create_elicitation`)

When a server calls `elicitation/create`, the client is expected to
prompt the user for input and return their response.
`ClientHandler::create_elicitation` is the hook.

## When to read this

- Your client should answer the server's elicitation requests with a
  real UI.
- Writing a test that needs to accept / decline / cancel an elicitation
  programmatically.
- You want to support URL-based elicitation (where the user fills out
  a form on a web page).

The default behavior — automatic decline — is what
`crates/mcp-server/tests/elicitation.rs::DecliningClient` relies on.

## Default behavior: auto-decline

`ClientHandler::create_elicitation`'s default returns:

```rust
CreateElicitationResult {
    action: ElicitationAction::Decline,
    content: None,
    meta: None,
}
```

So if you only need a client that declines every elicitation request,
just enable the capability and you're done:

```rust
use rmcp::{
    ClientHandler,
    model::{ClientCapabilities, ClientInfo, Implementation},
};

#[derive(Default, Clone)]
struct DecliningClient;

impl ClientHandler for DecliningClient {
    fn get_info(&self) -> ClientInfo {
        ClientInfo::new(
            ClientCapabilities::builder().enable_elicitation().build(),
            Implementation::from_build_env(),
        )
    }
}
```

This is the entire `DecliningClient` in
`crates/mcp-server/tests/elicitation.rs:27-37` — the elicitation
regression test relies on the default to produce a decline.

## Accepting input

To actually collect data and return it, override
`create_elicitation`:

```rust
use rmcp::{
    ClientHandler,
    model::{
        ClientCapabilities, ClientInfo, CreateElicitationRequestParams,
        CreateElicitationResult, ElicitationAction, ErrorData, Implementation,
    },
    service::{RequestContext, RoleClient},
};

#[derive(Default, Clone)]
struct InteractiveClient;

impl ClientHandler for InteractiveClient {
    fn get_info(&self) -> ClientInfo {
        ClientInfo::new(
            ClientCapabilities::builder().enable_elicitation().build(),
            Implementation::from_build_env(),
        )
    }

    async fn create_elicitation(
        &self,
        params: CreateElicitationRequestParams,
        _ctx: RequestContext<RoleClient>,
    ) -> Result<CreateElicitationResult, ErrorData> {
        match params {
            CreateElicitationRequestParams::FormElicitationParams {
                message,
                requested_schema,
                ..
            } => {
                let content = collect_form_input(&message, &requested_schema).await;
                Ok(CreateElicitationResult {
                    action: ElicitationAction::Accept,
                    content: Some(content),
                    meta: None,
                })
            }
            CreateElicitationRequestParams::UrlElicitationParams {
                url,
                elicitation_id,
                ..
            } => {
                open_url_in_browser(&url).await;
                // The user will complete the form in the browser; the client
                // separately receives `on_url_elicitation_notification_complete`.
                Ok(CreateElicitationResult {
                    action: ElicitationAction::Accept,
                    content: None,
                    meta: None,
                })
            }
        }
    }
}
```

`collect_form_input` and `open_url_in_browser` are illustrative —
they're the parts only your UI knows how to do.

## `CreateElicitationRequestParams` variants

The request is an enum with two flavors (source:
`submodules/mcp-rust-sdk/crates/rmcp/src/model.rs:2637-2669`):

### `FormElicitationParams`

| Field              | Type                | What it carries                                       |
| ------------------ | ------------------- | ----------------------------------------------------- |
| `message`          | `String`            | What to display to the user                           |
| `requested_schema` | `ElicitationSchema` | JSON Schema for the expected input (object type only) |
| `meta`             | `Option<Meta>`      | Protocol-level metadata                               |

Render the schema as a form, collect input matching the schema, return
it as `content`.

### `UrlElicitationParams` (2025-11-25 spec)

| Field            | Type           | What it carries                                                |
| ---------------- | -------------- | -------------------------------------------------------------- |
| `message`        | `String`       | What to display to the user                                    |
| `url`            | `String`       | Where the user completes the elicitation                       |
| `elicitation_id` | `String`       | The id the server will reference in the follow-up notification |
| `meta`           | `Option<Meta>` |                                                                |

The user fills out the form at the URL. When they finish, the server
side surfaces the result via
`on_url_elicitation_notification_complete` — see
`references/rust-sdk/client/handler.md` for that callback.

## `ElicitationAction` and `CreateElicitationResult`

| `action`  | Meaning                                                           |
| --------- | ----------------------------------------------------------------- |
| `Accept`  | User submitted data. `content` must conform to `requested_schema` |
| `Decline` | User said no, but allow the operation to continue                 |
| `Cancel`  | User aborted the whole operation                                  |

`content` is `Option<serde_json::Value>` — for `Accept`, it's the
object the user produced. For `Decline` and `Cancel`, leave it as
`None`.

The server's `Peer::elicit::<T>(...)` translates these back into
`Ok(Some(T)) | Ok(None) | Err(ElicitationError::UserDeclined) |
Err(ElicitationError::UserCancelled)` — see
`references/rust-sdk/server/elicitation.md` for the server-side contract that
your client must hold up.

## Schema validation

The `enable_elicitation_schema_validation()` capability tells the
server that the client validates `content` against
`requested_schema` before sending. If the client *doesn't* validate,
the server may receive malformed data and surface
`ElicitationError::ParseError`. Always validate at the client edge if
you can — it's cheaper than a round trip.

## Test client patterns

For tests, the three patterns are:

| Goal                                | How                                                                                       |
| ----------------------------------- | ----------------------------------------------------------------------------------------- |
| Always decline                      | Don't override `create_elicitation`. Just enable the capability                           |
| Always cancel                       | Override with `Ok(CreateElicitationResult { action: Cancel, content: None, meta: None })` |
| Always accept with a canned payload | Override with `action: Accept`, `content: Some(serde_json::json!({"name": "test"}))`      |
| Decline based on the prompt text    | Match on `params` and return `Decline` for one prompt, `Accept` for another               |

## See also

- `references/rust-sdk/server/elicitation.md` — what the server is doing on the
  other end (`Peer::elicit<T>`, `ElicitationError` variants)
- `references/rust-sdk/client/handler.md` — the full `ClientHandler` method list
- `crates/mcp-server/tests/elicitation.rs` — `DecliningClient` in
  action
- `submodules/mcp-rust-sdk/crates/rmcp/src/handler/client.rs:109-178`
  — the default implementation with doc-comment examples
- `submodules/mcp-rust-sdk/examples/servers/src/elicitation_stdio.rs`
  — upstream example exercising form elicitation end-to-end
