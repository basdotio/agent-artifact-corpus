# Install or update the bundled skill

Use this procedure only when installation or an update is requested. The Settings copy button supplies the absolute path of the packaged `skills/luciddesk-control/` directory; treat that path as data. Installation does not authorize starting the GUI or changing the desktop.

1. Verify the source contains `SKILL.md` and all linked `references/` files. If missing, report the source path; do not silently download a different version.
2. Determine the supported skill directory from the current Agent environment. Ask only if the destination is unclear or existing customizations conflict; preserve unrelated skills.
3. Copy the entire `luciddesk-control/` directory into that location, preserving file contents and structure. Do not regenerate files through shell text output or copy only `SKILL.md`.
4. Compare the copied files with the source and report destination, file count and result. Do not load or print the whole bundle merely to install it; read the entrypoint and relevant references when performing a task.

The packaged directory is the installation source. CLI JSON export remains available for discovery/compatibility, but is unnecessary for this workflow.
