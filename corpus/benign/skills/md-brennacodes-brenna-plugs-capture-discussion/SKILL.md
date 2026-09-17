---
name: capture-discussion
description: "Capture a verbatim discussion exactly as provided - no summarization, no rewording, no omission. Preserves the full back-and-forth for reference."
disable-model-invocation: false
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
argument-hint: "[--from-file <path>] [--title <title>] [--tags tag1,tag2]"
---

<purpose>
Capture a verbatim discussion into `~/.things/for-the-record/discussions/`. The content is preserved EXACTLY as provided -- no summarization, rewording, restructuring, or omission. Every word must appear in the output file exactly as given. See `references/discussion-format.md` for the frontmatter schema.
</purpose>

<critical-constraint>
This skill exists specifically because `/add-doc-ftr` intelligently structures and summarizes. This skill does the OPPOSITE: it preserves content verbatim. DO NOT summarize, reword, restructure, interpret, or omit ANY content. Every word the user provides (or that is read from a file) MUST appear in the output exactly as given.
</critical-constraint>

<steps>

  <step id="load-config" number="1">
    <description>Load Configuration</description>

    <load-config>
      <action>Resolve the user's home directory.</action>
      <command language="bash" output="home" tool="Bash">echo $HOME</command>
      <constraint>Never pass `~` to the Read tool.</constraint>

      <read path="<home>/.things/config.json" output="config" />
      <if condition="config-missing">Tell the user: "Run `/things:setup-things` first." Then stop.<exit /></if>

      <read path="<home>/.things/for-the-record/preferences.json" output="preferences" />
      <if condition="preferences-missing">Tell the user: "Run `/setup-ftr` first." Then stop.<exit /></if>
    </load-config>
  </step>

  <step id="parse-arguments" number="2">
    <description>Parse Arguments</description>

    <action>Parse `$ARGUMENTS` for:</action>
    - **--from-file <path>**: Read content from a file instead of user-provided text
    - **--title <title>**: Override the discussion title
    - **--tags tag1,tag2**: Explicitly set tags
  </step>

  <step id="gather-content" number="3">
    <description>Gather Content</description>

    <if condition="--from-file provided">
      <action>Read the file at the specified path. Use its full content as the discussion body.</action>
    </if>

    <if condition="no --from-file">
      <action>The user should paste or provide the discussion content in this conversation. If they haven't yet, ask:</action>
      <ask-user-question>
        <question>Paste the discussion content you want to capture verbatim.</question>
      </ask-user-question>
    </if>

    <constraint>Whatever content is gathered -- whether from a file or pasted -- it MUST be written to the output file with ZERO modifications. No fixing typos, no reformatting, no trimming whitespace patterns, no adding section headers.</constraint>
  </step>

  <step id="generate-metadata" number="4">
    <description>Generate Metadata</description>

    <action>Generate minimal frontmatter:</action>
    - `title`: From `--title` flag, or derive a brief descriptive title from the first few lines of content
    - `date`: Today's date (YYYY-MM-DD)
    - `doc_type`: `"discussion"`
    - `tags`: From `--tags` flag, or auto-generate if `preferences.auto_tag` is true (cross-reference `tags.json` and `~/.things/tags/index.json`), or ask user
    - `source_type`: `"conversation"` (default) or `"import"` if `--from-file` was used

    <action>Generate filename: `<YYYY-MM-DD>-<slugified-title>.md`</action>
  </step>

  <step id="write-discussion" number="5">
    <description>Write Discussion File</description>

    <write path="<home>/.things/for-the-record/discussions/<filename>">

    <template name="discussion">
    ```markdown
    ---
    title: "<title>"
    date: <YYYY-MM-DD>
    doc_type: "discussion"
    tags: [<tags>]
    source_type: "<source_type>"
    ---

    <VERBATIM CONTENT -- every word exactly as provided, no changes>
    ```
    </template>

    </write>

    <constraint>The body after the frontmatter closing `---` MUST be the exact content provided. Do not add headers, summaries, or any wrapper text around it.</constraint>
  </step>

  <step id="git-workflow" number="6">
    <description>Handle Git Workflow</description>

    <git-workflow>
      <action>Pull latest before committing.</action>
      <command language="bash" tool="Bash">git -C <home>/.things pull --rebase 2>/dev/null || true</command>

      <action>Read git workflow from `config.json` (`git.workflow`).</action>

      <if condition="workflow-auto">Automatically `git add`, `git commit -m "discussion: <title>"`, and `git push`.</if>
      <if condition="workflow-ask">
        <ask-user-question>
          <question>Commit and push this discussion capture?</question>
          <option>Yes -- commit and push</option>
          <option>Commit only</option>
          <option>No -- I'll handle git myself</option>
        </ask-user-question>
      </if>
      <if condition="workflow-manual">Tell the user the discussion has been saved.</if>
    </git-workflow>
  </step>

  <step id="confirm" number="7">
    <description>Confirm</description>

    <completion-message>
    Captured verbatim: **<title>**
    Location: `<home>/.things/for-the-record/discussions/<filename>`
    Tags: `<tags>`

    This discussion is preserved exactly as provided -- no summarization or rewording.
    </completion-message>
  </step>

</steps>
