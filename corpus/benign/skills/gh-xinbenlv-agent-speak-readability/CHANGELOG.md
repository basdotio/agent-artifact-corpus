# Changelog

This project follows semantic versioning. The version of the skill lives in
the `version` field of `SKILL.md`.

## 0.1.0 - 2026-09-21

The first release. The rules and the check work, and the interface may still
change.

### Added

- `SKILL.md`, the entry point. It holds nine cross-language rules, R1 to R9,
  and the ten-step pre-send check.
- R1, the master rule. R1 asks for every argument of an action: the actor, the
  action, the object, the instrument, the place and the result.
- `lang/zh/PRINCIPLES.md`, with Chinese rules Z1 to Z10 and five extra check
  steps. The rules cover the dropped subject, the 「让我……来……」 form, measure
  words, 「上述」 for backward reference, colloquial compression, tense markers
  and the length caps.
- `lang/en/PRINCIPLES.md`, with English rules E1 to E9 and six extra check
  steps. The rules cover ASD-STE100 and the English failure mode, which is the
  dropped object rather than the dropped subject.
- `lang/zh/ACCEPTANCE-CASES.md`, which keeps four hand-written corrections
  character for character. Those corrections are the acceptance standard.
- `lang/zh/NEGATIVE-SAMPLES.md`, with real failure samples from one session.
- `docs/suggested-claude-md-section.md`, a replacement for the language
  section of a global `CLAUDE.md`, in English and in Chinese.
- Apache License 2.0.

### Notes on the design

The skill states the requirement as a list of edits to perform before sending.
The skill does not state the requirement as a quality to aim at. Action
constraints survive a long session. Style constraints drift back to the
default voice of the model within one or two turns.
