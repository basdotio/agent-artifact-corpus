# upload-github-attachment

An agent skill that uploads a local image or file to GitHub user-attachments storage. It returns a URL for issue, pull request, discussion, or comment Markdown.

Use it to embed screenshots, videos, logs, or other evidence in GitHub content. The files do not go into a repository.

This skill comes from [moeru-ai/airi](https://github.com/moeru-ai/airi).

## Install

```bash
npx skills add moeru-ai/upload-github-attachment-skill
```

Add `-g` to install the skill for all projects.

## Requirements

- `gh` and `curl`.
- A `gh auth login` session, or `GH_TOKEN` or `GITHUB_TOKEN` in the environment.

## Usage

Ask the agent to upload a file for a GitHub issue or pull request. You can also run the script directly:

```bash
scripts/upload-github-attachment.sh --repo OWNER/REPO /absolute/path/to/image.png
```

The script prints only the `https://github.com/user-attachments/assets/...` URL.

GitHub does not document the upload endpoint. The endpoint can change without notice.

## License

[MIT](LICENSE)
