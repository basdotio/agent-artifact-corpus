# NDI Console document API

These examples target the public Console API at `https://console.nace.ai`. Request shapes and behavior were checked against the [public OpenAPI contract](https://console.nace.ai/openapi.json) and [Perception documentation](https://console.nace.ai/docs/perception/documents) on 2026-10-08. Check those sources when options change. Example names and values below are synthetic.

## Authentication and a first request

Read `DREX_API_KEY` from the environment in server-side code. Send it as a bearer header to the Console origin only. `GET /v1/models` checks the key without submitting a document job. Avoid logging headers or verbose HTTP traces.

For all five operations, send JSON to `POST /v1/documents/{operation}`. Use a UUID as the `Idempotency-Key`, store it before submission, and keep it unchanged when retrying the same body. `?wait_seconds=60` can wait for a result in the initial request, but may still return a queued/running job.

### Source choices

Use a public HTTPS document URL only when the user intended that document to be fetched:

```json
{"type":"url","url":"https://example.com/document.pdf","file_name":"document.pdf"}
```

`example.com` is a placeholder; replace it with the user's real public file URL. Private documents should be uploaded, not made public for this integration.

After upload, use identifiers returned for the user's own file:

```json
{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"}
```

For Extract, Split or Ground, a finished Parse can be reused:

```json
{"type":"parse_result","job_id":"PARSE_JOB_ID"}
```

Classify does not accept `parse_result`. Never manufacture IDs or borrow them from another account or example.

## Upload a local file

1. POST `/v1/documents/upload-grants` with the Console bearer header and JSON such as `{"path":"examples/hello-ndi.txt","total_size_bytes":123,"ttl_seconds":600}`. Compute the real byte count; `123` is illustrative.
2. Keep the response in memory: it contains `workspace_id`, `upload_url`, `token` and expiration metadata. Do not print or commit the token.
3. In a separate unauthenticated HTTP client, POST multipart form data to the returned HTTPS `upload_url`: a `file` part containing the bytes and a **required** `metadata` part with JSON `{"path":"examples/hello-ndi.txt","total_size_bytes":123}` and content type `application/json`. Send only the grant token in `X-Upload-Token`; do not attach the Console key.
4. Read `result.file.workspace_id` and `result.file.file_id` from the upload response. Use them as the `workspace_file` source.

For large files, follow the [resumable upload guide](https://console.nace.ai/docs/perception/uploads): create `/v1/documents/upload-sessions`, upload the returned part sizes to its session URL, and complete with a stable idempotency key. Do not improvise part numbering or resubmit an uncertain completion under a new key.

## Operation bodies

In these examples, replace `WORKSPACE_ID` and `FILE_ID` with the identifiers from the upload response, or use another supported source object above. Generate the request as a JSON object in code, not with shell string interpolation. Send only the operation the user requested.

### Parse

POST `/v1/documents/parse`

```json
{"source":{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"},"output":{"formats":["markdown","blocks"]}}
```

Read `result.document.markdown` and `result.document.blocks`. Preserve page/region information and check any disclosure that the inline content is bounded. Follow a provided full-content link when complete text is needed. See [Parse](https://console.nace.ai/docs/perception/parse).

### Extract

POST `/v1/documents/extract`

```json
{
  "source":{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"},
  "schema":{
    "type":"object",
    "properties":{
      "invoice_number":{"type":"string","description":"The printed invoice identifier."},
      "currency":{"type":"string","description":"The currency explicitly stated in the document."},
      "total":{"type":"number","description":"The final payable total, preserving its numeric scale."}
    },
    "required":["invoice_number","currency","total"]
  },
  "citations":{"enabled":true,"include_source_text":true}
}
```

Inspect `result.data` together with `result.fields`: each field has a JSON Pointer, status and citations. A missing field can be `null` with `not_found` even in a successful job; do not fabricate a replacement. A citation's source text still needs comparison with the original document. Use inline `schema` or a saved `schema_id`, not both. See [Extract](https://console.nace.ai/docs/perception/extract).

### Classify

POST `/v1/documents/classify`, with an original URL or uploaded file:

```json
{
  "source":{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"},
  "classes":[
    {"id":"invoice","label":"Invoice","description":"A request for payment listing goods or services and an amount due."},
    {"id":"receipt","label":"Receipt","description":"An acknowledgment that a payment was received."}
  ],
  "granularity":"document",
  "unknown_policy":"allow"
}
```

Inspect `result.units`, unknown flags and unread pages. The reported classification confidence is a share of read pages/sheets assigned to a class, not a calibrated probability. See [Classify](https://console.nace.ai/docs/perception/classify).

### Split

POST `/v1/documents/split`

```json
{
  "source":{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"},
  "classes":[
    {"id":"invoice","label":"Invoice","description":"A request for payment."},
    {"id":"receipt","label":"Receipt","description":"An acknowledgment of payment."}
  ],
  "unknown_policy":"include",
  "output":{"include_content":true,"materialize_files":false}
}
```

Inspect `result.segments`, inclusive page ranges and classifications. Keep unclassified segments visible. Request `materialize_files: true` only when the user needs separate downloadable files. See [Split](https://console.nace.ai/docs/perception/split).

### Ground

POST `/v1/documents/ground`

```json
{
  "source":{"type":"workspace_file","workspace_id":"WORKSPACE_ID","file_id":"FILE_ID"},
  "targets":[{"id":"invoice-id","text":"DEMO-1001"}],
  "options":{"max_matches":3,"include_previews":true}
}
```

Use the user's actual quote, or `DEMO-1001` for the synthetic sample. Inspect `result.targets`, target status, `matched_text`, `match_method` and location. A successful job can contain a `not_found` target. Locating a quote is not fact-checking it. See [Ground](https://console.nace.ai/docs/perception/ground).

## Polling and downloads

Save the returned `job_id`, then GET `/v1/documents/jobs/{job_id}` with the same Console key. Read `status`, not just the HTTP code. Poll until `succeeded`, `failed` or `cancelled`; preserve `error`, warnings and the ID when reporting a failure. An HTTP timeout leaves the remote job's status unknown; continue reading that job rather than submitting another.

Artifact paths come from the result. For a Console artifact link, authenticate to the Console, disable automatic redirects, and inspect its response. Download any HTTPS signed-storage redirect using a **new request with no bearer header**. Do not expose that signed URL in code, chat or public logs. A streamed artifact may return bytes directly. See [Jobs and results](https://console.nace.ai/docs/perception/jobs).

## Errors

| HTTP status | Next action |
| --- | --- |
| 401 | Correct the missing, expired or invalid key locally; stop submissions. |
| 402 | Explain the credit/payment condition and link the user to Console billing. |
| 409 | Restore the original body for that idempotency key; do not reuse a key for a different job. |
| 422 | Correct the request/source/schema based on the returned error. |
| 429 | Respect `Retry-After`; keep the original job/key and a bounded retry count. |
| 5xx or transport ambiguity | Preserve the request key and any known job ID; inspect existing status before retrying the same request. |

Report the HTTP status, error code and request ID without credentials or private document content. See [API errors](https://console.nace.ai/docs/perception/errors).
