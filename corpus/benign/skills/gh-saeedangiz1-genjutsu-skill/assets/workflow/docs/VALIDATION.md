> Historical upstream evidence for Sirio Berati's original release. This is not validation of the modified skill. See the [current release validation](../../../docs/VALIDATION.md).

# Package validation

Validated on 2026-10-06 in a newly created virtual environment installed from requirements.txt (Python 3.14.6, macOS ARM64):

- Eight isolated tests passed: mask fingerprint invalidation, duplicate-submission protection, self-contained Edit draft payload, result download/restoration dispatch, approved-draft HD payload, rejection of missing mask frames, and byte-identical original audio packet restoration, and dynamic Tmpfiles link extraction.
- Synthetic four-frame compositing test passed (depth foreground, original background, aligned output).
- FastAPI TestClient returned 200 for the UI, all three companion assets and API docs.
- Clean setup.sh installation, dependency imports, Rubber Band, missing-key failure, and configured-key checks passed. The share package remains credential-free.
- Source scanned for machine-specific user paths, old generation IDs, known credentials, and legacy parent-project references.

A live user-authorized end-to-end test completed successfully: Demucs, colored depth, SAM 3, rejected bad depth mask, RGB repair and all-frame visual review, Tmpfiles upload, Omni draft, polling/retrieval, audio restoration, approved HD completion, and browser download. The HD export is 1920×1080; all 189 original audio packets match byte-for-byte. A 0.292-second final-frame hold preserved the full source audio. The actual browser download matched the HD output SHA-256. A fresh dependency installation on other operating systems has not been tested. Clean-install testing caught and fixed an invalid Tmpfiles direct-link assumption and Enhancor’s required callback. The automatic cloudflared callback receiver returned HTTP 200; a file-route request returned 404. Catbox is a newly added adapter verified against its documented API, not a live upload. The unit suite mocks external calls; full-clip visual mask approval remains separate.


## Mesh client verification — October 6, 2026

- Fresh ZIP extraction and `setup-face-mesh.sh` succeeded on macOS ARM64 / Python 3.12.
- Both fast face mesh and depth + face mesh were run through the packaged preparation functions, using actual local tracking, encoding and Rubber Band pitch processing. Each tracked all 104 frames and embedded audio successfully.
- Previously generated Demucs stems and depth/SAM outputs were injected as fixtures for this client test; it did not repeat billed provider calls.
- Ten automated tests cover review invalidation, submission payloads, collection and other integration behavior.
- Fixed combined-mode RGB mask repair to reapply the mesh. Fast mode rejects SAM repair. Added `doctor.py --mesh` and depth/original dimension and frame-count checks.
- The UI exposes all three preparation choices. First-use model download was exercised.
- Mesh modes remain optimized for a single centered speaker. Other framing, multiple faces, other operating systems and every provider failure condition are not exhaustively validated. No claim of bug-free operation is made.

Hosting fallback checks: 13 automated tests now pass, including primary-host retry, fallback switching, disabled fallback, and success without fallback. Catbox behavior is mocked in these tests, not newly live-uploaded.
