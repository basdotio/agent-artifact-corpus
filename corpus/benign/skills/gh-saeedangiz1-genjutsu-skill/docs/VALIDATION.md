# Validation — v0.1.0

Written by GPT. Local release checks performed on 2026-10-10, Windows x64, Python 3.13.3. The underlying workflow derives from upstream commit `40fd6615c2b7d940d4d7060e82de522292eefe99`; that historical upstream run is separate from these checks.

## Observed offline results

**86 tests passed in the final combined run, zero failures/errors/skips.** The unified runner blocks outbound network connections and uses synthetic local media and mocked provider responses. The Windows ASGI suite required a run outside the desktop sandbox; the initial sandboxed pass stalled on the local UI event loop and was stopped. No remote inference or provider uploads were performed in either run.

| Area | Observed behavior |
| --- | --- |
| Source preflight | Missing/silent audio, undecodable references, clips over 30 seconds, unsupported MP4 packet copying and missing local prerequisites stop before hosted work |
| Preparation identity | Source/recipe changes reject stale partial-job reuse; cached audio/depth/masks are checked against saved hashes |
| Billed stage recovery | Demucs, depth and SAM reuse persisted accepted IDs; ambiguous intents stop before another POST |
| Review | All modes bind source, exact prepared video and working audio; edits invalidate approval; corrupt review is never accepted |
| Submission | Draft payloads use reviewed input without rebuilding; prompt/reference identities bind content rather than paths; unchanged accepted requests reuse IDs |
| Concurrency | Actual Windows cross-process advisory lock and crash-release checks; concurrent submits/collectors perform one mocked operation |
| HD | Current configured callback is used for new HD; accepted HD remains resumable after callback rotation; source-copy mutation blocks queueing |
| Collection | Crash points around download/export renames recover conservatively; restoration failure keeps existing downloads; changed source/output is preserved and rejected |
| Audio/composite | Synthetic H.264/AAC exports retain original compressed audio packets byte-for-byte; depth foreground/source background composite is verified |
| Installer | Paths containing spaces, idempotence, explicit managed updates, secret/run preservation, unsafe paths, symbolic links, nested targets and unmanaged collisions |
| CLI | Argument passing without shell interpolation, caller-relative paths, missing-runtime guidance, saved same-job recipe and preparation statuses |
| Local UI | ASGI health/page/icons return successful responses; invalid reference fails before submission; manual import preserves an existing export |

Upstream tests were retained and their mocked fixtures updated for stronger review/input contracts. The additional tests exercise observable behavior, including actual file locks, real local decoding/encoding and saved-state crash paths. They do not check wording as a substitute for behavior.

All three Bash launch/setup scripts passed Git Bash `bash -n` syntax checks. They were not run to install a WSL/macOS/Linux environment or download the optional mesh model. The separate mesh setup is designed for exact Python 3.12 and official model acquisition.

Additional review led to local Host/Origin guards, early video-reference duration checks and a free-threaded-Python readiness gate; their focused regressions passed in the final combined release run.

An independent skill trial installed a temporary copy, validated actual local H.264/AAC media and PNG/video reference decoding, rejected a missing-audio source, and confirmed the installed command/discovery guidance. Runtime imports passed with regular CPython. Actual readiness was blocked by missing Rubber Band, optional mesh worker/model and callback/account configuration. Compatible five-second source/video-reference pairing passed; incompatible two-second pairing stopped before processing. Actual free-threaded Python now fails readiness cleanly before native imports. No remote accounts were exercised.

## Reproduce

Create an isolated Python 3.12+ environment, install `assets/workflow/requirements.txt`, then from the repository root run:

```bash
python scripts/check.py
python scripts/run_tests.py
```

The first command checks public resources, Python syntax and local links without loading the runtime. The second runs both test suites with outbound connections disabled. `--scratch PATH` chooses the fixture directory; `--report PATH` saves measured JSON results. For existing isolated dependencies, `--dependencies PATH` loads them without installing globally.

Main top-level packages are exactly pinned by upstream. Transitive dependency resolution is not locked for every target OS, so a fresh installation may resolve newer compatible dependencies. [GitHub Actions run 38072157410](https://github.com/SaeedAngiz1/Genjutsu-Skill/actions/runs/38072157410) passed package validation and all 86 offline tests on both Windows and Ubuntu with Python 3.13, zero failures/errors/skips, on 2026-10-10. That run tested code commit `bfc3d8bab8cb3b9c5bb8a91c19f3d2fe4a1036ed`; the follow-up documentation commit records this evidence without changing runtime code. This CI does not install the complete video runtime or exercise hosted inference.

## Remaining acceptance

No user keys, credits or source/reference pair were used for a live run. Actual Replicate/Enhancor account access, current provider schemas/balance/prices, public-host fetches, callback reachability, paid draft/HD completion, real facial tracking and complete generated visual/audio quality remain unverified for this fork. Full runtime setup on WSL2/macOS/Linux is also unverified in this release. The native Windows installer and local media/test code were exercised; this does not establish native Windows launch support.

The skill packages an executable workflow and explicit recovery/quality contracts. It cannot guarantee every generated identity, mask, frame or provider response. Live testing must use the user's own authorized budget and actual full-clip inspection. Claude/Codex discovery and model behavior require checking in the user's configured agent environment; offline frontmatter validation is a narrower check.

## Publication scope

The public package contains original diagrams/UI icons, attributed MIT source/docs, install helpers and tests. It excludes credentials, environments, model weights, private runs, signed URLs, tutorial footage/captions, upstream examples and proprietary TEIN assets. See [THIRD-PARTY.md](../THIRD-PARTY.md).
