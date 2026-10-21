# Security

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature if this repository offers
it in the Security tab. Availability must be checked before sending sensitive
details. If no private reporting route is available, open a minimal issue asking
for a reporting route without including the exploit, credentials or personal data.

Reports should identify the affected commit, the expected and observed behavior,
and a minimal reproduction using synthetic data. Never include credentials,
real account data, private files or machine-specific paths.

## Scope and maintenance

This is a portfolio project supplied under the MIT license. There is no support
response-time commitment or claim that older commits receive security fixes.
Review configuration and permissions before running it with your own data.
Model output and external service responses must be treated as untrusted input.

If a public disclosure exposes a credential, revoke or rotate it immediately.
Removing a file or making a repository private does not remove existing clones.

## Known limits of the file tools

These are limits of the current design, not vulnerabilities awaiting a fix. Take them into account before pointing the file tools at your own data.

- **Handle authorization is demonstrated for a narrow set of link types.** The check resolves the final path of the opened handle. It was tested against a file symlink, a directory symlink and a directory junction that point out of a root (all refused), and a race in which a directory inside a root was replaced by a junction to an outside folder after the early path check and put back before the final check; the read was still refused, because the final path of the already-open handle named the outside file. It was not tested against volume mount points, subst drives or remote SMB shares. Keep configured roots on ordinary local folders, and do not treat the boundary as covering every kind of reparse point.
- **File text can steer the model.** File and text content is placed into the prompt without a fence or escaping, so instructions written inside a file can influence a summary, a classification or an extracted value. The roots limit which files can be read; they do not make the content of those files trustworthy. Treat model output as untrusted, and verify anything you act on against the source.
- **The extraction check is a presence check.** `extract_json_file` nulls a string or number that does not occur, after normalization, as a substring of the source. A value that is present can still be wrong, in the wrong field, or matched inside a longer value, and dictionary keys, booleans and nulls are not checked. A nulled field is `None`, so the returned fields are not guaranteed to match the declared types; check `unverified_fields`.
- **Containment does not recognize secrets.** Any eligible file under a configured root can be read and its content can appear in tool output. Configure narrow roots that exclude credential stores, token files and keyrings.
- **Outbound requests.** Prompts, which include file content, are sent to the configured Ollama endpoint. Requests do not follow redirects, but the tools do not verify that the endpoint is local; review `LOCAL_LLM_OLLAMA_URL` before use.
