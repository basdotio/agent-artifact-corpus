# Licence reference

General information, not legal advice. SPDX ids in backticks.

## Common licences

| Licence | Kind | Others may use it in closed products | Must share changes | Covers network use | Patent grant | Typical fit |
| --- | --- | --- | --- | --- | --- | --- |
| `MIT`, `ISC`, `BSD-2-Clause` | Permissive | Yes | No | No | No express grant | Small libraries; maximum adoption |
| `BSD-3-Clause` | Permissive | Yes | No | No | No express grant | As MIT, plus a no-endorsement clause |
| `Apache-2.0` | Permissive | Yes | No | No | Yes, with patent retaliation | Libraries, especially from companies; explicitly excludes trademarks (section 6) |
| `MPL-2.0` | Weak copyleft, per file | Yes | Changes to MPL files only | No | Yes | Apps or extensions that should stay open file by file; App Store friendly |
| `LGPL-3.0-or-later` | Weak copyleft, per library | Yes, if users can relink | Changes to the library | No | Yes | Libraries that must stay open but may be linked from closed code |
| `EPL-2.0` | Weak copyleft, per module | Yes | Changes to EPL modules | No | Yes | Java and Eclipse ecosystems |
| `GPL-3.0-or-later` | Strong copyleft | No: combined works must be GPL | Yes, when distributed | No | Yes | Distributed apps and tools that must stay open |
| `AGPL-3.0-or-later` | Strong copyleft, network | No | Yes, including when run as a service (section 13) | Yes | Yes | Hosted apps and services that must stay open |
| `CC0-1.0` | Public-domain dedication | Yes | No | n/a | Explicitly none | Data, examples, trivial config |
| `CC-BY-4.0` | Content, attribution | Yes | No | n/a | n/a | Docs, research, images |
| `CC-BY-SA-4.0` | Content, share-alike | Yes, with credit | Adaptations stay CC BY-SA | n/a | n/a | Docs, research, translations, interface copy |

`-only` variants (`GPL-3.0-only`) refuse later versions of the licence;
`-or-later` accepts them. Prefer `-or-later` unless the owner objects.

Creative Commons licences are not designed for software, and Creative Commons
itself recommends against using them for code. Use them for content only.

## Source-available (not open source)

These forbid some uses, so they do not meet the Open Source Definition.
Contributors and distributions may avoid them. Name this trade-off whenever you
suggest one.

| Licence | Restriction | Later becomes open |
| --- | --- | --- |
| `BUSL-1.1` (Business Source) | Production use limited by an "Additional Use Grant" the owner writes | Yes, to a named open licence at a change date (at most four years) |
| FSL (Functional Source License) | No competing commercial use | Yes, to Apache-2.0 or MIT after two years |
| `PolyForm-Noncommercial-1.0.0` | No commercial use | No |
| `PolyForm-Shield-1.0.0` | No use that competes with the licensor | No |

## Compatibility

"A into B" means code under A may be included in a work licensed as B.

| Combination | Allowed? |
| --- | --- |
| MIT, BSD, ISC into anything | Yes, keep their notices |
| Apache-2.0 into GPL-3.0, AGPL-3.0, LGPL-3.0 | Yes |
| Apache-2.0 into GPL-2.0-only | No |
| Apache-2.0 into MPL-2.0 | Yes |
| MPL-2.0 into GPL, LGPL, AGPL | Yes, unless the file says "Incompatible With Secondary Licenses" |
| MPL-2.0 into a permissive or closed work | Yes, but the MPL files stay MPL and their source must be available |
| LGPL into a closed work | Yes, by linking, if users can replace the LGPL part |
| GPL or AGPL into a permissive or closed work | No: the combined work must be GPL or AGPL |
| GPL-3.0 with AGPL-3.0 | Yes, each part keeps its licence (section 13 of each) |
| GPL-2.0-only with GPL-3.0 | No |
| CC-BY-SA-4.0 into GPL-3.0 | Yes, one way |
| Non-commercial or source-available into an open-source work | No |

## Distribution channels

| Channel | Watch for |
| --- | --- |
| Apple App Store, Mac App Store | GPL and AGPL are widely considered incompatible with Apple's terms when others hold copyright in the code (VLC was removed in 2011 over this). Prefer MPL-2.0 or permissive. |
| Google Play, browser extension stores | No licence restriction. Ship the licence and third-party notices inside the package. |
| npm, PyPI, crates.io | Set the manifest `license` field to the SPDX id; include `LICENSE` and `NOTICE` in the published files. |
| Hosted service | Only AGPL obliges source sharing for network use. AGPL also expects the service to offer its source to users, usually a link in the footer. |
| Container images | Every package inside the image ships under its own licence. |

## Relicensing

- The copyright holders can relicense future versions under any terms.
  Earlier releases keep the licence they shipped with; nothing revokes it.
- Code from outside contributors can only be relicensed with their consent,
  or under rights a CLA granted.
- Moving a file between parts with different licences relicenses that file;
  treat it as a licensing change, not a refactor.
