---
name: ftpc-storage
description: Read files from ftpc storage backends (local, FTP/FTPS, SFTP, S3, Azure Data Lake, Azure Blob). List directories, download files, and inspect metadata without modifying remote state.
allowed-tools: Read, Grep, Glob, Bash(bun:*)
---

# FTPC Storage (Read-Only)

Use the Bun/TypeScript ftpc implementation to inspect remote storage without
making remote changes. Run commands from the repository root unless the caller
has installed or built `ftpc` elsewhere.

## Supported Connections

| Backend         | URL format                                             | Example                                            |
| --------------- | ------------------------------------------------------ | -------------------------------------------------- |
| Local           | `file:///path` or `/path`                              | `file:///tmp/data`                                 |
| FTP             | `ftp://[user:pass@]host[:port]/path`                   | `ftp://ftp.example.com/pub`                        |
| FTPS            | `ftps://[user:pass@]host[:port]/path`                  | `ftps://secure.example.com`                        |
| SFTP            | `sftp://[user:pass@]host[:port]/path`                  | `sftp://user@host/home/user`                       |
| S3              | `s3://bucket/path`                                     | `s3://my-bucket/reports`                           |
| Azure Data Lake | `azure://account.dfs.core.windows.net/filesystem/path` | `azure://acct.dfs.core.windows.net/fs/base`        |
| Azure Blob      | `blob://account.blob.core.windows.net/container/path`  | `blob://acct.blob.core.windows.net/container/base` |

Configured remote names from `~/.ftpcconf.toml` or `--config PATH` can be used
wherever a URL is accepted.

## CLI Reads

List configured remotes:

```bash
bun run src/index.ts remotes
```

List a directory:

```bash
bun run src/index.ts ls my-s3 /reports
bun run src/index.ts ls s3://my-bucket/reports
```

Download a file:

```bash
bun run src/index.ts get my-sftp /remote/report.csv ./report.csv
```

Use `--config PATH` before the command when a non-default config file is needed:

```bash
bun run src/index.ts --config ./ftpc.toml ls my-azure /incoming
```

## TypeScript API

```ts
import { Storage } from "./src/index.ts";

const store = Storage.connect(
  "blob://account.blob.core.windows.net/container/reports",
);

try {
  const entries = await store.list();
  for (const entry of entries) {
    console.log({
      path: entry.path,
      name: entry.name,
      type: entry.type,
      size: entry.size,
      modifiedTime: entry.modifiedTime,
    });
  }

  await store.download("daily.csv", "./daily.csv", {
    onProgress: ({ bytes, total }) => {
      console.error(
        `downloaded ${bytes}${total === undefined ? "" : `/${total}`}`,
      );
    },
  });
} finally {
  await store.close();
}
```

## Config Shape

```toml
[local]
type = "local"

[my-ftp]
type = "ftp"
url = "ftp.example.com"
username = "user"
password = "password"
tls = true

[my-sftp]
type = "sftp"
url = "sftp.example.com"
username = "user"
password = "password"
# key_filename = "~/.ssh/id_rsa"

[my-s3]
type = "s3"
url = "s3://my-bucket/prefix"
region_name = "us-east-1"
endpoint_url = "https://s3.amazonaws.com"
aws_access_key_id = "ACCESS_KEY"
aws_secret_access_key = "SECRET_KEY"

[my-azure]
type = "azure"
url = "account.dfs.core.windows.net"
filesystem = "filesystem"
connection_string = "DefaultEndpointsProtocol=https;AccountName=..."

[my-blob]
type = "blob"
url = "account.blob.core.windows.net"
container = "container"
account_key = "ACCOUNT_KEY"
```

## Read-Only Boundaries

Prefer `remotes`, `ls`, `get`, `Storage.connect().list()`, and
`Storage.connect().download()` in this skill. Do not call `put`, `rm`, `mkdir`,
`upload`, or `delete`; use the `ftpc-storage-write` skill when remote mutation
is required.
