---
name: ftpc-storage-write
description: Read-write access to ftpc storage backends (local, FTP/FTPS, SFTP, S3, Azure Data Lake, Azure Blob). Upload files, delete files, and create directories in addition to read operations.
allowed-tools: Read, Grep, Glob, Bash(bun:*)
---

# FTPC Storage (Read-Write)

Use the Bun/TypeScript ftpc implementation when a task needs to modify remote
storage. Confirm destructive actions with the user before deleting or replacing
remote data.

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

## CLI Operations

List before mutating so the target is clear:

```bash
bun run src/index.ts ls my-ftp /incoming
```

Download:

```bash
bun run src/index.ts get my-sftp /remote/report.csv ./report.csv
```

Upload:

```bash
bun run src/index.ts put my-s3 ./summary.csv /reports/summary.csv
```

Create a directory or prefix:

```bash
bun run src/index.ts mkdir my-azure /reports/2026
```

Delete a file after confirmation:

```bash
bun run src/index.ts rm my-blob /reports/old.csv
```

Use `--config PATH` before the command for a non-default config file:

```bash
bun run src/index.ts --config ./ftpc.toml put my-ftp ./file.txt /incoming/file.txt
```

## TypeScript API

```ts
import { Storage } from "./src/index.ts";

const store = Storage.connect(
  "sftp://user:password@sftp.example.com/home/user",
);

try {
  await store.upload("./local.csv", "incoming/local.csv", {
    onProgress: ({ bytes, total }) => {
      console.error(
        `uploaded ${bytes}${total === undefined ? "" : `/${total}`}`,
      );
    },
  });

  await store.mkdir("archive");
  await store.download("incoming/local.csv", "./roundtrip.csv");
  await store.delete("incoming/old.csv");
} finally {
  await store.close();
}
```

Named constructors are useful when credentials are supplied by the caller:

```ts
const ftp = Storage.ftp("ftp.example.com", {
  username: "user",
  password: "password",
  tls: true,
  basePath: "/incoming",
});

const lake = Storage.azure("account.dfs.core.windows.net", "filesystem", {
  accountKey: process.env.AZURE_STORAGE_ACCOUNT_KEY,
  basePath: "/reports",
});
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

## Safety Notes

Prefer listing the target path immediately before upload, delete, or directory
creation. Treat `rm` and `StorageSession.delete()` as destructive. For uploads,
check whether the destination path already exists when overwriting would matter.
