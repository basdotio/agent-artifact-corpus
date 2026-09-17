---
name: update-homebrew-tap
description: Updates the homebrew tap for the project.
---

When updating the homebrew tap, always include:

1. Check `.seed.yaml` to see what projects are available and what their URLs are.

    The `seed.yaml` file is a seed for generating the Homebrew tap. It contains the following information:
    - `tap_repository` is the repository of the Homebrew tap.
    - `tap_repository.url` is the repository URL of the Homebrew tap.
    - `tap_repository.license` is the license of the Homebrew tap.
    - `target_projects` is a list of projects to be installed.
    - `target_projects.name` is the name of the project.
    - `target_projects.url` is the repository URL of the project.

2. Do the following for each project in `target_projects`:
    1. Check `README.md` via GitHub website to see what commands are provided by the project and what prerequisites are required.
    2. Check GitHub Releases page for each project to see which name and version are available in the project.
    3. Check `checksums.txt` in GitHub Releases for each project to see SHA256 checksums for the archives.
    4. Implement formulae for the project. Formulae should satisfy all of the following conditions:
        1. The formulae must be named `(?<project_name>[a-z0-9-]+).rb` and located in the top level of the tap directory.
        2. The formulae must install all of the commands provided by the project.
        3. The formulae must fetch the archive to install the commands from the project's GitHub Releases page. All projects are hosted on public GitHub repositories.
        4. The formulae must test by running the first command in the README for the project with `-v`.
        5. If prerequisites are noted in the README for the project, the formulae must print the prerequisites as caveats.
3. Create or update the `README.md` of the tap repository. `README.md` should be formatted as follows:

    ```markdown
    Homebrew Tap
    ============

    This is a homebrew tap for the following projects:

    | Project | Description | Version | Commands |
    |---------|-------------|---------|----------|
    | [example-tool-1](https://github.com/Kuniwak/example-tool-1.md) | A tool for example-tool-1 | 1.0.0 |  `example-foo`, `example-bar` |
    | [example-tool-2](https://github.com/Kuniwak/example-tool-2.md) | A tool for example-tool-2 | 2.0.0 |  `example-baz`, `example-qux` |
    | ... | ... | ... | ... |
    ```