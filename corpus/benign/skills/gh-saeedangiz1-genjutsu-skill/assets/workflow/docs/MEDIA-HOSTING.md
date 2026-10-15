# Media hosting

Enhancor must fetch direct HTTPS media. Replicate preprocessing uses Replicate's `/v1/files` upload API with your token. Enhancor references use the selected public host below. URLs and request bodies stay in each local run; do not share run folders with the clean project.

## Tmpfiles (default)

`MEDIA_HOST=tmpfiles`. No account key required. Adapter POSTs multipart `file` and `expire=21600` (six hours) to `https://tmpfiles.org/api/v1/upload`, reads the response download page and extracts its actual `/dl/…` link (including host-generated path components), then verifies that it returns nonempty non-HTML bytes. Current documented maximum is 100 MB. Reference: [Tmpfiles API](https://tmpfiles.org/api).

Temporary files can disappear before a long queue finishes. Re-upload only for a deliberate new submission, after checking whether the original request completed. Do not requeue blindly.

## Catbox

Set `MEDIA_HOST=catbox`. Optionally set your own `CATBOX_USERHASH` from your account. Multipart POST to `https://catbox.moe/user/api.php` with `reqtype=fileupload`, optional `userhash`, and `fileToUpload`. The response is a direct URL. Reference: [Catbox API](https://catbox.moe/tools.php).

Both hosts expose uploaded files via public URLs. Use them only for media you intend to share with these services. There is no silent host fallback. For private storage, replace `media_host.upload` with your own signed-URL uploader whose expiry covers the full generation queue. No storage credentials are included.


## Configured automatic fallback

`MEDIA_HOST` selects the primary (`tmpfiles` by default). `MEDIA_HOST_FALLBACKS=catbox` tries Catbox after two failed primary attempts. Set the fallback value to empty to prohibit switching. Both routes provide public URLs; Catbox is persistent. The uploader warns when switching hosts and checks the returned media URL. It never retries model generation. Failed or expired media must be freshly uploaded before a separately authorized generation retry.
