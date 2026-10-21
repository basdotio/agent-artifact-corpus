# Applying the licences

Do this only after the owner approves the recommendation. Make it one commit
(or one pull request) so the change is reviewable as a unit, and run the
project's own checks before committing.

## Files

1. **`LICENSES/<SPDX-id>.txt`** for every licence used, full text, from the
   SPDX list (`https://raw.githubusercontent.com/spdx/license-list-data/main/text/<id>.txt`)
   or `reuse download <id>`. Only licences actually used; `reuse lint` reports
   unused ones.
2. **Root `LICENSE`**: the full text of the main licence (the part most people
   mean by "the project"), so GitHub's licence detection still works. Explain
   the split in the README, not in `LICENSE`.
3. **`REUSE.toml`**: one annotation per area, broadest first, plus `precedence
   = "override"` entries for third-party files inside an area:

   <!-- REUSE-IgnoreStart -->

   ```toml
   version = 1

   [[annotations]]
   path = "**"
   SPDX-FileCopyrightText = "2026 Owner Name"
   SPDX-License-Identifier = "AGPL-3.0-or-later"

   [[annotations]]
   path = ["packages/**"]
   SPDX-FileCopyrightText = "2026 Owner Name"
   SPDX-License-Identifier = "Apache-2.0"

   [[annotations]]
   path = "vendor/some-data.ts"
   precedence = "override"
   SPDX-FileCopyrightText = "Upstream Project contributors"
   SPDX-License-Identifier = "MPL-2.0"
   ```

   <!-- REUSE-IgnoreEnd -->

   Brand assets get a `LicenseRef-<Name>` id with a short text in
   `LICENSES/LicenseRef-<Name>.txt` saying all rights are reserved.
4. **SPDX headers** on every source file, using the comment style of the file
   type, after any shebang or doctype:

   <!-- REUSE-IgnoreStart -->

   ```
   // SPDX-FileCopyrightText: 2026 Owner Name
   // SPDX-License-Identifier: Apache-2.0
   ```

   <!-- REUSE-IgnoreEnd -->

   Generated files: change the generator so it writes the header, or the next
   regeneration drops it. For a generated file built from third-party data,
   the header names the upstream licence, not the project's.
5. **Manifest `license` fields** matching each part, including private
   packages, and in the lockfile root entry if the package manager records it.
   Edit only that line rather than regenerating the lockfile with a different
   tool version.
6. **`NOTICE`** at the root: the copyright line, the licence map in brief, and
   one entry per third-party component (name, URL, licence, where it is used).
   Published packages that bundle third-party material get their own `NOTICE`,
   listed in the manifest's published files.
7. **Licences inside built artifacts**: a store package, binary or bundle is a
   distribution of its own. Copy its licence and a third-party notices file
   into the build output from the build script, including full texts of
   bundled MIT/BSD/Apache dependencies. Check that a minifier or bundler keeps
   required notices; esbuild keeps comments starting `//!` or `/*!`.
8. **README "Licence" section**: a table of part → licence, one line on why,
   the copyright line, a link to `NOTICE`, and, if relevant, a sentence that
   releases before the change keep their earlier licence.
9. **`CONTRIBUTING.md`**: which licence applies to which directory, the header
   new files need, and the DCO or CLA process.
10. **`TRADEMARKS.md`** if the brand is reserved: what others may do (refer to
    the project, link to it) and what needs permission (forks under the name,
    implying endorsement).
11. **Hosted AGPL services**: a visible link to the source (for example in the
    footer), with the link text in the project's string bundle if it has one.

## Checks

- **`reuse lint`** must pass (`pipx run reuse lint`, or `pip install reuse`).
  Example headers in docs or tests are read as real declarations; wrap them in
  `REUSE-IgnoreStart` / `REUSE-IgnoreEnd` comments.
- **A project test** that each source file's header names the licence for its
  directory, that manifest fields match, and that `LICENSES/` has every text.
  `reuse lint` proves a licence exists, not that it is the right one.
- **CI**: a workflow running `reuse lint`, and a DCO check if the owner chose
  DCO. Exempt bots, and consider exempting the repository owner, who holds the
  copyright already. Some repositories block AI co-author sign-off trailers;
  check commit hooks before signing off on the owner's behalf.
- **The build**: build each shipped artifact and confirm the licence files are
  inside it.

## Report back

Tell the owner what changed per part, what passed, anything left undone (for
example store listings that only update on resubmission, or README freshness
markers you did not re-review), and that earlier releases keep their licence.
