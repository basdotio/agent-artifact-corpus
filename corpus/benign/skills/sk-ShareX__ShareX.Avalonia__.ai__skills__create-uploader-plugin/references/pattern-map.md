# Pattern Map

Use the closest existing plugin instead of inventing a new pattern.

## Minimal Manual Config

Use when the service only needs a token, API key, or a few simple settings.

- `src/desktop/plugins/Bitly.Plugin/`
- `src/desktop/plugins/Pastebin.Plugin/`

Good reference points:

- simple config model
- lightweight provider
- basic Avalonia settings view

## Browser Login Or OAuth

Use when the service has browser/device auth, callback flows, or refresh tokens.

- `src/desktop/plugins/Dropbox.Plugin/`
- `src/desktop/plugins/Nextcloud.Plugin/`

Good reference points:

- secret-store usage
- browser launch/login workflow
- config viewmodel state transitions
- staged setup UX after authentication

## File Storage Destination

Use when the destination uploads files/blobs and may also expose public links.

- `src/desktop/plugins/AmazonS3.Plugin/`
- `src/desktop/plugins/Nextcloud.Plugin/`
- `src/desktop/plugins/Ftp.Plugin/`

Good reference points:

- file uploader implementation
- public/share URL generation
- upload path handling
- native capability discovery vs generic compatibility endpoints

## Explorer-Capable Provider

Use when the service can list, download, delete, or create remote folders.

- `src/desktop/plugins/AmazonS3.Plugin/AmazonS3Provider.cs`
- `src/desktop/plugins/Dropbox.Plugin/DropboxProvider.cs`
- `src/desktop/plugins/Nextcloud.Plugin/NextcloudProvider.cs`

Implement `IUploaderExplorer` only if the service genuinely supports browsing.

## Secret Migration

Use when you are moving old plaintext config into `ISecretStore`.

- `src/desktop/plugins/AmazonS3.Plugin/AmazonS3Provider.cs`
- `src/desktop/plugins/Imgur.Plugin/ImgurProvider.cs`

Implement `IInstanceSecretMigrator` when importing legacy settings or upgrading an older plugin shape.

## Native API Replacement

Use when the old code works through a compatibility path but the service has a richer first-party API.

- `docs/proposals/xip/XIP0048-nextcloud-native-plugin-design.md`
- `src/desktop/plugins/Nextcloud.Plugin/`

Good reference points:

- replacing a legacy compatibility uploader with a dedicated plugin
- evaluating native auth and capability endpoints
- mapping a richer staged UI to the provider workflow
