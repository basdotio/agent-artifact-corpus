# Client: roots (`list_roots`)

When a server calls `roots/list`, the client returns the
filesystem/workspace roots it has exposed (IDE open folders, sandbox
paths, etc.). `ClientHandler::list_roots` is the hook.

## When to read this

- Writing an IDE-integrated client that exposes open folders.
- Building a sandboxed client that wants to scope server access to
  specific directories.
- Implementing live updates so the server is notified when the user
  opens or closes a folder.

The default behavior — empty list — is fine for clients that don't
have a filesystem concept (chat UIs, headless scripts).

## Default behavior: empty list

`ClientHandler::list_roots`'s default returns `ListRootsResult::default()`
— an empty `roots: Vec<Root>`. A server calling `peer.list_roots()`
will get the empty list back without an error.

If you don't even want the *capability* advertised, leave it off in
`ClientCapabilities`; the server's `Peer::list_roots()` call then
fails with a capability-not-supported error, which the server-side
tool can handle gracefully.

## Returning real roots

```rust
use rmcp::{
    ClientHandler,
    model::{
        ClientCapabilities, ClientInfo, ErrorData, Implementation,
        ListRootsResult, RawRoot, Root,
    },
    service::{RequestContext, RoleClient},
};

#[derive(Clone)]
struct WorkspaceClient {
    roots: Vec<Root>,
}

impl ClientHandler for WorkspaceClient {
    fn get_info(&self) -> ClientInfo {
        ClientInfo::new(
            ClientCapabilities::builder()
                .enable_roots()
                .enable_roots_list_changed()
                .build(),
            Implementation::from_build_env(),
        )
    }

    async fn list_roots(
        &self,
        _ctx: RequestContext<RoleClient>,
    ) -> Result<ListRootsResult, ErrorData> {
        Ok(ListRootsResult {
            roots: self.roots.clone(),
            meta: None,
        })
    }
}

fn build_root(uri: &str, name: Option<&str>) -> Root {
    let raw = match name {
        Some(n) => RawRoot::new(uri).with_name(n),
        None => RawRoot::new(uri),
    };
    raw.no_annotation()
}
```

## `Root` shape

A `Root` is `Annotated<RawRoot>`. The two fields on `RawRoot`:

| Field  | Type             | Meaning                                                                   |
| ------ | ---------------- | ------------------------------------------------------------------------- |
| `uri`  | `String`         | The root URI. Use `file:///absolute/path` for filesystem locations        |
| `name` | `Option<String>` | Display label. If unset, server-side code typically falls back to the URI |

URIs should be **absolute** and **normalized**. Servers may compare
URIs as strings; trailing slashes and `..` segments will cause
mismatches.

## Capability flavors

| Capability                     | Meaning                                                          |
| ------------------------------ | ---------------------------------------------------------------- |
| `.enable_roots()`              | Client supports `roots/list`                                     |
| `.enable_roots_list_changed()` | Client will additionally send `roots/list_changed` notifications |

If your client mutates its roots at runtime (user opens / closes a
folder), enable list-changed and emit notifications via
`client_service.peer().notify_roots_list_changed().await?` whenever the
list shifts. Servers can subscribe by overriding
`ServerHandler::on_roots_list_changed`.

## Static vs dynamic

Two common shapes:

| Pattern                               | When                                                                        |
| ------------------------------------- | --------------------------------------------------------------------------- |
| Static `Vec<Root>` fixed at startup   | Headless scripts, sandboxes with a single workspace                         |
| Dynamic, fetched from an IDE callback | VS Code / IntelliJ-style clients where roots change as folders open / close |

For the dynamic case, store the list behind an `Arc<Mutex<...>>` so
`list_roots` can read it without async blocking, and update from the
IDE's filesystem-watch callbacks.

## Permission and consent

Like sampling, roots disclose information that the user might not want
to share. UI clients should:

- Show the user which roots are exposed (and to which server).
- Default to **no roots** for untrusted servers.
- Allow per-server overrides.

`rmcp` doesn't enforce any of this — it's policy.

## See also

- `references/rust-sdk/server/roots.md` — the server side that calls
  `list_roots`
- `references/rust-sdk/client/handler.md` — the full `ClientHandler` method list
  including `on_resource_*` notifications (analogous live updates)
- `submodules/mcp-rust-sdk/crates/rmcp/src/handler/client.rs:102-107`
  — default implementation of `list_roots`
