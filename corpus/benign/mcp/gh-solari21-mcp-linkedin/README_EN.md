# 🚀 MCP LinkedIn: Professional Model Context Protocol (MCP) Server

<p align="left">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg?logo=python&logoColor=white" alt="Python" height="20"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP%20SDK-FastMCP-8A2BE2.svg" alt="MCP SDK" height="20"></a>
  <a href="https://playwright.dev/"><img src="https://img.shields.io/badge/engine-Playwright-2EAD33.svg?logo=playwright&logoColor=white" alt="Playwright" height="20"></a>
  <a href="https://github.com/solari21/mcp-linkedin/releases"><img src="https://img.shields.io/github/v/release/solari21/mcp-linkedin?logo=github&color=blue" alt="GitHub Release" height="20"></a>
  <a href="https://github.com/users/solari21/projects/2"><img src="https://img.shields.io/badge/Roadmap-Projects%20V2-orange?logo=github" alt="Roadmap Projects V2" height="20"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" height="20"></a>
  <a href="https://github.com/solari21/mcp-linkedin/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" height="20"></a>
  <a href="https://m8ven.ai/mcp/solari21-mcp-linkedin-1ary7v?s=readme"><img src="https://m8ven.ai/badge/mcp/solari21-mcp-linkedin-1ary7v" alt="M8ven Score" height="20"></a>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Espa%C3%B1ol-Switch-blue?style=for-the-badge&logo=googletranslate&logoColor=white" alt="Cambiar a Español" /></a>
  &nbsp;&nbsp;
  <a href="README_EN.md"><img src="https://img.shields.io/badge/English-Active-orange?style=for-the-badge&logo=readme&logoColor=white" alt="Active English Version" /></a>
</p>

**MCP LinkedIn** is a high-performance open-source server built on top of the **Model Context Protocol (MCP)**, **FastMCP**, and **Playwright**. It enables AI assistants (Claude Desktop, Gemini, Antigravity, Cursor, Cline) to interact with LinkedIn in a supervised, respectful manner engineered for professional productivity.

Unlike opaque automation scripts, **MCP LinkedIn** adheres to a strict **Human-in-the-Loop (HITL)** philosophy featuring mandatory two-phase safeguards (`confirm=True`) for destructive or sensitive operations, human cadence emulation, and an interactive Plan B that resolves security challenges without focus-stealing or intrusive windows.

> [!TIP]
> **Complete Operational Manual**: For in-depth command usage, recommended prompts, architecture breakdowns, and weekly workflows across all 32 tools, explore the **[Operational Usage Guide (GUIA_USO.md)](./GUIA_USO.md)**.

---

## 🌟 Why MCP LinkedIn? (Competitive Comparison)

Several experimental LinkedIn MCP implementations exist across the open-source ecosystem. The following table highlights the engineering differences and production reliability advantages:

| Feature / Capability | `stickerdaniel/linkedin-mcp` | `eliasbiondo/linkedin-mcp` | 🚀 **MCP LinkedIn (This Project)** |
|---|:---:|:---:|:---:|
| **Available Tools** | 4 | 5 | **32 full-featured tools** |
| **Rich Media Publishing (Images)** | ❌ Text only | ❌ Unavailable | ✅ **Native HD upload (`expect_file_chooser`)** |
| **Automatic First Comment** | ❌ No | ❌ No | ✅ **Automated injection for organic reach** |
| **Full 3-Dots Menu Control** | ❌ No | ❌ No | ✅ **Feature, Save, Embed `<iframe>`, Edit, Delete** |
| **Human-in-the-Loop Safeguards** | ❌ Blind | ❌ Blind | ✅ **Mandatory two-phase confirmation (`confirm=True`)** |
| **Challenge Resilience (2FA/CAPTCHA)** | ❌ Hang / Crash | ❌ Hang / Crash | ✅ **Interactive Plan B without focus stealing (`schtasks /IT`)** |
| **Cookie Sanitization (Anti-HTTP 999)** | ❌ No | ❌ No | ✅ **Domain normalization & `li_at` deduplication** |
| **Real-Time 360° Search** | ⚠️ Partial | ⚠️ Partial | ✅ **People, Jobs with full specs, and Companies** |
| **Inbox & Chronological Threads** | ⚠️ Basic | ❌ No | ✅ **Direct inbox reading, thread history & supervised reply** |
| **Human Cadence Emulation** | ❌ Instantaneous | ❌ Instantaneous | ✅ **Gaussian randomized jitter (1.5s - 3.0s)** |
| **Local Anti-AI Engine & Heuristics** | ❌ No | ❌ No | ✅ **3-Pass Humanizer & 5-Check AI Detection Panel** |
| **Calibrated Copywriting Strategy** | ❌ No | ❌ No | ✅ **21 Hook formulas, 9 comment archetypes, 4:5 carousels** |

---

## 🏛️ System Architecture (Modular 5-Layer Model)

Unlike the sequential lifecycle of publishing, the architecture of **MCP LinkedIn** is a decoupled 5-layer system cleanly separating client interfaces, control orchestration, heuristic intelligence engines, cookie state persistence, and browser automation:

<p align="center">
  <img src="assets/infografia_mcp_linkedin.png?v=1.1.0" alt="FastMCP LinkedIn Server Architecture v1.1.0" width="850">
</p>

---

## 🔄 End-to-End Operational Flow (Lifecycle Lifecycle)

The following flowchart outlines the complete operational sequence and lifecycle of a post, coordinating all **32 tools** from initial ideation through post-publication monitoring:

<p align="center">
  <img src="assets/diagrama_flujo_mcp_linkedin.png?v=1.1.0" alt="MCP LinkedIn End-to-End Operational Flowchart" width="850">
</p>

---

## 🛠️ Complete Tools Catalog (32 Tools)

### A. Publishing and Content Distribution
* `linkedin_create_post`: Publishes professional posts with formatting, hashtags, optional high-definition image upload, automatic first-comment injection with external links, and optional `clean_previous_tests=True` parameter for pre-flight deduplication and purging of orphaned test posts.
* `linkedin_add_comment`: Adds structured comments featuring native multiline formatting (`<p>` blocks in Tiptap/ProseMirror without collapse), strict semantic author verification (`verify_author`), and topic checks (`verify_topic`) preventing cross-posting on unintended threads.
* `linkedin_get_recent_posts`: Retrieves recent posts from the authenticated profile alongside impression counts and engagement metrics.
* `linkedin_check_session`: Diagnostics tool checking active session validity, cookie health, and connectivity.
* `linkedin_renew_session_interactive`: Launches an assisted, non-invasive window to solve 2FA or reCAPTCHA challenges and re-sync session state.

### B. Post Management (3-Dots Menu)
* `linkedin_toggle_feature_post`: Pins or unpins a post in the profile's "Featured" section.
* `linkedin_toggle_save_post`: Adds or removes a post from saved items.
* `linkedin_get_post_embed_code`: Generates the HTML `<iframe>` snippet to embed posts on external websites.
* `linkedin_get_post_link`: Resolves and sanitizes canonical direct post links, stripping tracking parameters.
* `linkedin_edit_post`: Opens LinkedIn's native edit modal and updates text on an existing post.
* `linkedin_delete_post`: Permanently removes a post (mandatory `confirm=True` safeguard prevents accidental deletion).
* `linkedin_get_comment_settings_url`: Retrieves comment privacy configuration guidelines.

### C. Search & Professional Prospecting
* `linkedin_search_people`: Searches professionals filtered by keywords, title, company, or geographic location.
* `linkedin_search_jobs`: Queries active job listings with location and workplace type filters (remote/hybrid/on-site).
* `linkedin_search_companies`: Locates companies and institutions by industry sector or name.

### D. Inbox & Supervised Messaging
* `linkedin_get_inbox_messages`: Reads recent inbox threads (`/messaging/`) including unread indicators.
* `linkedin_get_conversation_thread`: Extracts full chronological chat history for a contact or conversation ID.
* `linkedin_send_message`: Drafts and delivers direct messages with two-phase human validation (`confirm=True`).

### E. Market Intelligence, Profiles & Feed
* `linkedin_get_profile_details`: Structured profile scraping (About, Experience, Education, Skills, and Featured items).
* `linkedin_get_feed_posts`: Gathers top feed updates alongside reaction and comment statistics.
* `linkedin_get_job_details`: In-depth breakdown of job postings (key requirements, full description, and workplace conditions).
* `linkedin_get_company_details`: Institutional corporate profile data (industry, headcount, headquarters, and specialties).

### F. Editorial Intelligence, Copywriting & Anti-AI Heuristics (Jakeschincariol Benchmark)
* `linkedin_humanize`: 3-pass text cleaner removing invisible characters (zero-width, BOMs), normalizing non-standard typography (em-dashes to commas, smart quotes), and replacing 113+ corporate slop buzzwords while protecting URLs.
* `linkedin_detect_ai`: 5-check evaluation panel (Burstiness, Specificity, Slop Density, Fingerprint, Voice) delivering a PASS/REVIEW/FLAGGED verdict with a 0-100 human score without external API costs.
* `linkedin_hook_score`: Hook calibrator benchmarking against 21 proven formulas (`hooks.json`) validating mobile ($\le$ 140 chars) and desktop ($\le$ 210 chars) fold visibility before "see more".
* `linkedin_score_profile`: 12-criterion objective audit (100 total points) scoring own or third-party profiles with a *Fix-First* priority action plan.
* `linkedin_generate_comment`: High-value comment generator based on 9 professional archetypes (data point, edge case, receipt, constructive disagreement) eliminating shallow comments ("Great post!").
* `linkedin_triage_inbox`: Automated inbox classification into LEAD, RECRUITER, PEER, ASK, and SPAM (detecting outreach bots and cold sequences with Calendly links).
* `linkedin_triage_replies`: 5-tier reply triage under personal posts prioritizing responses to maximize first-hour dwell time.
* `linkedin_carousel_planner`: Slide-by-slide architecture for vertical PDF carousels (1080x1350 px, 4:5 aspect ratio) with $<25$ words per slide and ready-to-print HTML/CSS templates.
* `linkedin_repurpose_content`: Deconstructs long-form content (videos, transcripts, articles) into claims, numbers, stories, and mechanisms to build a weekly 4-post calendar.
* `linkedin_dm_sequence`: 4-stage prospecting sequence with invite notes strictly $\le 200$ characters and 2 spaced follow-ups.

---

## 📦 Installation & Setup

### Prerequisites
* **Python 3.10 or higher**
* **Brave Browser** (recommended for native bot evasion) or **Google Chrome / Chromium**

### Option 1: Quick Install via Assisted Installer
Clone the repository and run the automated installer for your operating system:

**On Windows:**
```cmd
git clone https://github.com/solari21/mcp-linkedin.git
cd mcp-linkedin
install.bat
```

**On Linux / macOS:**
```bash
git clone https://github.com/solari21/mcp-linkedin.git
cd mcp-linkedin
chmod +x install.sh
./install.sh
```

### Option 2: Manual Installation via Pip or Pre-built Wheel
```bash
# Editable mode for development:
pip install -e .

# Or direct install of pre-built release wheel:
pip install dist/mcp_linkedin-1.0.0-py3-none-any.whl

# Install Playwright browser drivers:
playwright install chromium
```

---

## ⚙️ Configuration & Authentication

Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```

### Supported Authentication Methods

1. **Step-Zero CDP Architecture (Default & Recommended - Zero-Login & Zero Friction)**:
   * **Passive Hot-Sync**: The server attaches passively to the user's running browser (Brave Browser or Chrome on port `9222`) via Chrome DevTools Protocol (`Storage.getCookies`) using direct WebSockets.
   * **Zero Passwords & Zero Captchas**: Extracts pre-authenticated cookies (`li_at`, `JSESSIONID`) in under 50 ms without requiring plaintext credentials or triggering reCAPTCHA challenges.
   * **Inviolable User Session (Anti-Revocation)**: By avoiding automated login forms in subprocesses, LinkedIn's multi-session revocation policy is never triggered. The user is **never logged out** of their primary desktop browser.
   * **Zero Focus Stealing**: 100% silent background operation without competing windows.

2. **Supervised Interactive Plan B (`linkedin_renew_session_interactive`)**:
   * Explicitly callable via MCP tool whenever an isolated challenge (2FA/reCAPTCHA) demands manual intervention on Windows (`schtasks /IT` with `SW_SHOWNOACTIVATE`).
   * **Popup Loop Eradication**: The server **NEVER** opens windows automatically or in endless loops on network errors or HTTP 429/999 codes. If session cookies are invalid and CDP is inactive, it raises a clean `PermissionError` for the user to decide when to intervene.

3. **Environment Variables (`.env`) (CI/CD / Headless Servers)**:
   ```env
   LINKEDIN_EMAIL="your_email@example.com"
   LINKEDIN_PASSWORD="your_secure_password"
   ```

4. **Persistent Storage & Cookie Hardening**:
   * Cookies are normalized to `.linkedin.com` under strict Playwright schemas, with expiration extended to 1 year (`expires = now + 365 days`) and atomic backups (`.bak`) in:
   ```env
   LINKEDIN_STORAGE_STATE_FILE="./config/linkedin_storage_state.json"
   ```

> [!WARNING]
> ### 🛡️ Critical Session Resilience Guidelines (Lessons from Production)
> 1. **No Concurrent Headless Subprocesses**: If your main browser (Brave) has an active LinkedIn session, **DO NOT** launch separate headless Playwright instances (`browser.launch()`). LinkedIn flags fingerprint collisions and simultaneous TLS channels on the same account, instantly revoking the `li_at` token and forcing your browser to the "Welcome back" login screen. Always leverage direct WebSocket CDP connections to your active tab.
> 2. **No Automated `/login` Forms**: Submitting credentials into web forms immediately flags automated bot behavior and produces reCAPTCHA challenges. Authentication in this server relies exclusively on passive session tokens (`li_at`) captured without friction.
> 3. **Lightweight WebSocket CDP Connection (<10ms)**: Standard `connect_over_cdp` can freeze for up to 180 seconds indexing extensions and workers. This server dispatches direct JSON-RPC messages over the `webSocketDebuggerUrl` targeting the specific tab, ensuring sub-10ms latency and zero freezing.

---

## 🔌 MCP Client Integration

### 1. Claude Desktop
Add the following snippet to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "mcp-linkedin",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

### 2. Antigravity / Cursor / Cline
In your MCP server configuration file (`mcp_config.json`):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "python",
      "args": [
        "-m",
        "linkedin_server"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

---

## 🔄 Continuous Integration & Distribution (CI/CD)

The repository provides automated GitHub Actions workflows ensuring stability, syntax health, and effortless releases:

* **CI - Build & Lint Verification (`ci.yml`)**: Validates Python syntax, AST integrity, and clean package building across a matrix of Python 3.10, 3.11, and 3.12 on both Ubuntu and Windows for every `push` and `pull_request`.
* **Build & Release Package Distribution (`publish_package.yml`)**: Upon official GitHub Release publication or manual dispatch, automatically builds Wheel (`.whl`) and source tarball (`.tar.gz`) distributions, validates metadata with `twine check`, and attaches compiled binary assets via `softprops/action-gh-release@v2`.

---

## 🛡️ Human-in-the-Loop Philosophy & Platform Respect

> [!NOTE]
> **Ethical Purpose & Platform Respect Statement:**  
> This MCP server **is not designed for bulk scraping, aggressive cold prospecting, or bypassing LinkedIn security mechanisms**. On the contrary, it is founded upon strict principles of **minimal intrusion, personal single-user productivity, and respectful platform cadence**. We believe AI integration with professional networks must provide real value to users without degrading community experience or compromising service stability.

### Technical Safeguards
1. **Two-Phase Confirmation (`confirm=True`)**: Operations modifying account state (such as deleting a post or sending direct messages) require explicit user confirmation. If an LLM calls the tool without this parameter, the system **refuses execution** and returns a structured confirmation prompt, eliminating hallucinations.
2. **Human Cadence & Anti-Throttling**: Incorporates Gaussian random jitter (1.5s to 3.0s) between requests to maintain natural interaction pacing without burdening server infrastructure.
3. **Continuous Supervision**: The AI functions strictly as a personal assistant under the direct, conscious oversight of its operator.

---

## ⚖️ Legal Disclaimer

> [!IMPORTANT]
> This project is developed strictly for **educational research into the Model Context Protocol (MCP) and supervised personal productivity assistance**.
> 
> * **No Affiliation**: This software is not affiliated, endorsed, sponsored, or certified in any way by LinkedIn Corporation or Microsoft Corporation.
> * **Terms Compliance**: The end user retains sole and exclusive responsibility for ensuring their usage complies with LinkedIn's Terms of Service and Professional Community Policies.
> * **Ethical Usage**: This software actively rejects spam, bulk harvesting, and unsupervised automation. The author disclaims all liability for any improper or non-compliant use.

---

## 🗺️ Roadmap & Project Board

Current status and upcoming milestones (also tracked on the interactive Kanban board at [**GitHub Projects #2 - MCP LinkedIn Roadmap**](https://github.com/users/solari21/projects/2)):

### ✅ Implemented (v1.0.0)
- [x] **Official Launch Post**: Published live on LinkedIn with technical infographic and verified first comment ([View on LinkedIn](https://www.linkedin.com/feed/update/urn:li:share:7512122634080374784/)).
- [x] **FastMCP 2.2+ Architecture**: 22 strictly typed tools with runtime schema introspection.
- [x] **Rich Media Publishing**: Support for HD image uploads with `expect_file_chooser()` and automatic first-comment injection via Tiptap.
- [x] **Supervised Comments with Native Paragraphs & Anti-Cross-Posting**: `linkedin_add_comment` tool with strict author verification (`verify_author`), topic checks (`verify_topic`), and multiline paragraph injection without line-break collapse.
- [x] **Full 3-Dots Menu Control**: Feature in profile, save items, extract `<iframe>` snippets, copy canonical links, edit text, and delete posts.
- [x] **Human-in-the-Loop Safeguards**: Mandatory two-phase confirmation (`confirm=True`) on sensitive or destructive operations.
- [x] **Interactive Plan B Without Focus Loss**: Challenge detection (2FA, reCAPTCHA) and assisted projection via Windows `schtasks /IT`.
- [x] **Cookie Sanitization (Anti-HTTP 999)**: Domain normalization, quote unescaping in `JSESSIONID`, and strict deduplication of `li_at`.
- [x] **360° Real-Time Intelligence & Search**: Search engines for people, job listings with full specs, and corporate company records.
- [x] **Inbox & Conversation History**: Recent inbox query, chronological chat threads, and supervised message delivery.

### ✅ Implemented (v1.1.0 - Editorial Intelligence & Anti-AI Heuristics)
- [x] **Anti-AI Engine & Heuristic Cleaning**: Full integration of `linkedin_humanize` (3-pass cleaning: 17 invisible chars, typography, and 113+ bilingual corporate slop phrases) and `linkedin_detect_ai` (5-check panel with PASS/REVIEW/FLAGGED verdict).
- [x] **Copywriting & Hook Calibration**: `linkedin_hook_score` with 21 high-impact formulas and visual cutoff limits for mobile (140 chars) and desktop (210 chars).
- [x] **100-Point Profile Audit**: `linkedin_score_profile` with 12 objective criteria and a prioritized *Fix-First* action plan.
- [x] **High-Value Comment Generator**: `linkedin_generate_comment` featuring 9 professional archetypes eliminating empty remarks.
- [x] **Inbox & Reply Triage**: `linkedin_triage_inbox` (5 categories and Calendly anti-spam detection) and `linkedin_triage_replies` (thread prioritization in the first hour).
- [x] **PDF Carousels & Content Repurposing**: `linkedin_carousel_planner` (vertical 4:5 ratio slides with HTML/CSS templates) and `linkedin_repurpose_content` (breakdown into 4 weekly posts).
- [x] **Direct Messaging Prospecting**: `linkedin_dm_sequence` (4-stage outreach sequence with invite notes $\le 200$ chars and spaced follow-ups).
- [x] **Official Distribution & CI/CD Auto-Release**: Official releases on [GitHub Releases](https://github.com/solari21/mcp-linkedin/releases) with pre-compiled Wheel (`.whl`) and tarball (`.tar.gz`) binaries, automated CI on push to `main`, and cross-sync with [Projects V2 #2 (Roadmap)](https://github.com/users/solari21/projects/2).

### 🛡️ Production Engineering Lessons & DOM Selectors in 2026
1. **Phantom Inputs on `/login`**: LinkedIn injects hidden fields in the DOM for autofill and WebAuthn with 0 dimensions (`visible: false`). Forcing the `:visible` pseudo-selector (`input[type="email"]:visible`, `input[type="password"]:visible`) prevents Playwright `TimeoutError`.
2. **SSO vs. Form Button Collisions**: The "Sign in with Microsoft" button contains the string "Sign in". Submissions must be dispatched via `Enter` on the password input (`press("Enter")`) or strict role matching (`name="Sign in", exact=True`).
3. **Post-Publishing Modal Dialogs**: After post creation, LinkedIn spawns a floating `<dialog data-testid="dialog">` intercepting mouse clicks. A proactive `Escape` key or native JavaScript dispatch (`evaluate('b => b.click()')`) is required.
4. **Tiptap / ProseMirror Editor**: The comment textarea ignores `.fill()`; it requires focused click interaction (`.click()`), typed cadence (`keyboard.type`), and `Shift+Enter` line-breaks to prevent premature submission.
5. **Strict Cookie Domain Normalization (`.linkedin.com`)**: Constraining `li_at` to `.www.linkedin.com` caused Chromium to drop the cookie on apex domain queries (`linkedin.com/feed/`) and internal APIs, triggering HTTP 302 redirects to `/login` and HTTP 429 rate limits. All cookies are normalized canonically to `.linkedin.com`.
6. **Zero Invasive Windows (Popup Loop Elimination)**: Automatic triggers of `trigger_interactive_session_renewal` in `ensure_authenticated()` were removed. If a session is unavailable, a clean exception is raised rather than repeatedly spawning external physical windows.
7. **Guaranteed 1-Year Persistence & Passive CDP Capture**: Hot extraction of the `li_at` cookie from the active Brave session (port 9222) via direct WebSockets (`Storage.getCookies` / `Network.getCookies`), with forced 365-day expiration extension and atomic `.bak` backup protection.
8. **No Concurrent Headless Subprocesses & Token Revocation**: Running a headless Playwright subprocess (`browser.launch()`) with shared cookies while Brave maintains an active session causes LinkedIn's backend to detect footprint/TLS mismatches, immediately revoking `li_at`. The solution implemented in `linkedin_cdp.py` dispatches CDP calls directly to the existing Brave tab (`/devtools/page/<id>`), guaranteeing zero focus theft and zero session revocation.
9. **Pre-Flight Deduplication & Orphan Test Post Purging**: Before publishing production posts, the agent inspects recent posts (`linkedin_get_recent_posts`) to detect and purge (`linkedin_delete_post(confirm=True)`) orphaned tests or duplicates.
10. **Disambiguation of Comment Buttons in Tiptap**: In LinkedIn's DOM tree, the "Comment" button exists in two places (the bottom action bar toggle and the primary comment box submit trigger). Explicitly targeting the primary submit button after `Shift+Enter` input and verifying DOM appearance is mandatory.
11. **Multiline Paragraphs in Tiptap / ProseMirror (`Input.insertText` vs `Shift+Enter`)**: Tiptap collapses raw keyboard line breaks (`Shift+Enter` or single `<br>`) into a single continuous paragraph on submit. To create genuine `<p>...</p>` paragraph separation, multiline text must be inserted via `Input.insertText` (or `page.keyboard.insert_text()`).
12. **Author Verification & Anti-Cross-Posting**: Commenting or interacting by blindly extracting URLs from open tabs without validating the author is prohibited. Strict semantic validation (`verify_author`, `verify_topic`) ensures interactions only occur on the user's legitimate posts.
13. **Navigation Inviolability & Silent Background Operation**: Stealing focus via `$w.AppActivate` or bringing tabs to the foreground is prohibited. Remote CDP interactions in Brave must execute silently over WebSockets without disrupting active work.
14. **First-Person Singular Identity Governance**: Communications, posts, or comments authored on behalf of the project creator must strictly use the first-person singular ("my MCP server", "I continue improving"), eliminating royal plurals ("we created", "we improved").

### 📋 Upcoming Features (Backlog)
- [ ] **Interactive Polls**: Creation and monitoring of LinkedIn poll votes.
- [ ] **Native Scheduled Publishing**: Deferred post scheduling for future dates and times.
- [ ] **Automated PDF Carousel Upload**: Direct presentation file uploading into LinkedIn's document modal.
- [ ] **Analytics Exporter**: Structured export of impressions, clicks, and reactions into SQLite and CSV formats.

---

## 🎖️ Open Source Credits & Acknowledgements

This project builds upon and honors the contributions of the open-source community:

* **[Jesús Moronta](https://github.com/solari21)**: Overall FastMCP architecture, engineering integration, passive Brave CDP automation with zero focus theft, Tiptap multiline injection, 32-tool suite, and ongoing development.
* **[Jake Schincariol](https://github.com/Jakeschincariol)** ([opusjake.ai](https://opusjake.ai)): Creator of the **[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)** repository and benchmark, from which the anti-AI heuristic engines (`humanize` and `detect`), 21 hook formulas (`hooks.json`), 100-point profile rubric (`rubric.json`), vertical 4:5 PDF carousel guidelines, and inbox/reply triage rules were adapted and integrated.
* **[@Daniel Sticker (stickerdaniel)](https://github.com/stickerdaniel/linkedin-mcp-server)**: For early messaging concepts and initial MCP LinkedIn exploration.
* **[@Elias Biondo (eliasbiondo)](https://github.com/eliasbiondo/linkedin-mcp-server)**: For foundational ideas on modular profile data extraction.
* **[FastMCP](https://github.com/jlowin/fastmcp)**: For providing the most ergonomic and rapid Python framework for building MCP servers.
* **[Playwright](https://playwright.dev/)**: For delivering the most robust and modern web automation engine in the ecosystem.

---

## 📄 License

Distributed under the **MIT** License. See [LICENSE](./LICENSE) for full details.
