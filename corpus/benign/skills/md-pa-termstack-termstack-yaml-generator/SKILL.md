---
name: termstack-yaml-generator
description: This skill should be used when the user wants to create a TermStack TUI configuration, generate a YAML file for browsing APIs, create a terminal dashboard, or build a config-driven terminal UI. Use this when users mention TermStack, TUI configuration, API browser, terminal dashboard, or want to create YAML configs for data visualization in the terminal.
version: 2.0.0
---

# TermStack YAML Configuration Generator

This skill helps generate TermStack YAML configuration files for creating terminal user interfaces (TUIs) that browse APIs, display data in tables, stream logs, and navigate between pages.

## What is TermStack?

TermStack is a config-driven Terminal User Interface (TUI) framework. You define pages, data sources, views, and actions in YAML - no coding required. It supports:

- **HTTP API calls** with query parameters and headers
- **CLI command execution** with arguments
- **Script execution** for custom data processing
- **Stream adapters** for real-time data (logs, websocket)
- **Table views** with sortable, styled columns
- **Text/YAML views** for detailed data
- **Logs views** with filtering and search
- **Multi-page navigation** with context passing
- **Conditional navigation** based on data values
- **Actions** triggered by keyboard shortcuts
- **Multiple data sources** with merge capabilities
- **Column transforms** with Tera templates
- **Validation rules** for data integrity

## YAML Configuration Structure

```yaml
version: v1

app:
  name: "App Name"
  description: "App description"
  theme: "default"

globals:
  api_base: "https://api.example.com"
  # Variables accessible in all templates as {{ variable_name }}

start: page_name  # First page to show

pages:
  page_name:
    title: "Page Title"
    data:
      adapter: http  # or "cli", "script", "stream"
      url: "{{ api_base }}/endpoint"
      method: GET
      params:
        key: "value"
      headers:
        Accept: "application/json"
      items: "$.data[*]"  # JSONPath to extract array items
    view:
      type: table  # or "text", "logs"
      columns:
        - path: "$.field"
          display: "Column Name"
          width: 20
          style:
            - default: true
              color: cyan
    next:
      page: detail_page
      context:
        item_id: "$.id"
    actions:
      - key: "ctrl+d"
        name: "Details"
        page: "detail_page"
        context:
          item_id: "$.id"
```

## Key Concepts

### 1. Data Adapters

**IMPORTANT: Choosing the Right Field**
- Use `adapter: cli|http|script` for **single-fetch** or **periodic refresh** data sources
- Use `type: stream` for **real-time streaming** data sources (continuous output)

#### HTTP Adapter
```yaml
data:
  adapter: http
  url: "{{ api_base }}/users"
  method: GET  # GET, POST, PUT, DELETE, PATCH
  params:
    limit: 10
    status: "active"
  headers:
    Authorization: "Bearer {{ token }}"
    Accept: "application/json"
  items: "$.data[*]"  # JSONPath for array extraction
  timeout: "30s"  # Supports: s, m, h (e.g., "5m", "1h")
  refresh_interval: "5m"  # Auto-refresh data
```

#### CLI Adapter
```yaml
data:
  adapter: cli
  command: "kubectl"
  args: ["get", "pods", "-n", "{{ namespace }}", "-o", "json"]
  items: "$.items[*]"
  timeout: "10s"
  refresh_interval: "30s"
```

#### Script Adapter
Execute external scripts for custom data processing:
```yaml
data:
  adapter: script
  path: "./scripts/process_data.sh"
  args: ["--env", "{{ environment }}"]
  items: "$[*]"
  timeout: "1m"
```

#### Stream Adapter
For real-time streaming data (logs, command output):
```yaml
data:
  type: stream  # Use "type" (not "adapter") for streaming
  command: "kubectl"
  args: ["logs", "-f", "pod-name", "-n", "namespace"]
  buffer_size: 1000  # Max lines to keep in buffer (default: 100)
  buffer_time: "5m"  # Time window for buffering (optional)
  follow: true  # Auto-scroll to new lines (default: true)
  timeout: "30s"  # Optional timeout
```

**Important:** Stream data sources use `type: stream` (not `adapter: stream`). The command output is streamed in real-time to the terminal.

### 2. View Types

#### Table View
Display data in columns with sorting and styling:
```yaml
view:
  type: table
  columns:
    - path: "$.name"
      display: "Name"
      width: 30
      style:
        - default: true
          color: cyan
          bold: true
    - path: "$.status"
      display: "Status"
      width: 15
      style:
        - condition: "{{ value == 'active' }}"
          color: green
        - condition: "{{ value == 'inactive' }}"
          color: red
        - default: true
          color: gray
    - path: "$.created_at"
      display: "Age"
      width: 15
      transform: "{{ value | timeago }}"  # Tera filter
      style:
        - default: true
          color: yellow
    - path: "$.size"
      display: "Size"
      width: 12
      transform: "{{ value | filesizeformat }}"  # Format bytes
      style:
        - default: true
          color: blue
```

#### Text View
Display single objects as formatted text:
```yaml
view:
  type: text
  syntax: yaml  # or json, xml, toml, etc.
```

#### Logs View
Display streaming logs:
```yaml
view:
  type: logs
  follow: true              # Auto-scroll to new lines (default: true)
  wrap: true                # Wrap long lines (default: false)
  show_line_numbers: true   # Show line numbers (default: false)
  show_timestamps: false    # Show timestamps (default: false)
```

**Note:** Log filtering is defined in the schema but not yet fully implemented in the current version. Use the basic logs view shown above.

### 3. Navigation

#### Simple Navigation (Enter key)
```yaml
next:
  page: detail_page
  context:
    item_id: "$.id"
    item_name: "$.name"
```

#### Conditional Navigation
Navigate to different pages based on data values:
```yaml
next:
  - condition: "{{ row.type == 'folder' }}"
    page: folder_view
    context:
      folder_id: "$.id"
  - condition: "{{ row.type == 'file' }}"
    page: file_view
    context:
      file_id: "$.id"
  - default: true
    page: default_view
```

### 4. Actions

Actions are triggered via the Shift+A menu or direct Ctrl+key shortcuts:

```yaml
actions:
  # Execute command
  - key: "ctrl+d"
    name: "Delete"
    description: "Delete this item"
    confirm: "Are you sure you want to delete {{ name }}?"
    command: "curl"
    args: ["-X", "DELETE", "{{ api_base }}/items/{{ id }}"]
    refresh: true

  # Navigate to page
  - key: "ctrl+v"
    name: "View Details"
    page: "detail_page"
    context:
      item_id: "$.id"

  # Open in external app
  - key: "ctrl+o"
    name: "Open in Browser"
    command: "open"
    args: ["{{ html_url }}"]

  # Builtin action (yaml_view is useful as a custom action)
  - key: "ctrl+y"
    name: "YAML View"
    builtin: yaml_view
```

### 5. Multiple Data Sources

Combine data from multiple sources:

```yaml
data:
  sources:
    - name: users
      adapter: http
      url: "{{ api_base }}/users"
      items: "$.data[*]"
      
    - name: stats
      adapter: http
      url: "{{ api_base }}/stats"
      items: "$.data[*]"
      optional: true  # Don't fail if this source fails
      
  merge: true  # Merge all sources into single dataset

# Access in columns
view:
  type: table
  columns:
    - path: "$.name"
      display: "User"
      source: users  # From specific source
    - path: "$.count"
      display: "Stats"
      source: stats
```

### 6. Context Variables and Navigation

**CRITICAL: There are TWO different syntaxes for context depending on navigation type!**

#### A. Next Navigation (Enter key) - Uses JSONPath

```yaml
# Source page - next navigation ONLY accepts JSONPath syntax
next:
  page: detail
  context:
    user_id: "$.id"              # ✅ JSONPath - extracts from selected row
    user_name: "$.attributes.name"  # ✅ JSONPath

# Target page - access as template variables
detail:
  title: "User: {{ user_name }}"  # Template variable
  data:
    url: "{{ api_base }}/users/{{ user_id }}"
```

#### B. Action Navigation (Shift+A menu / Ctrl+key) - Uses Templates

```yaml
# Source page - action context ACCEPTS template expressions
actions:
  - key: "ctrl+d"
    page: detail
    context:
      user_id: "{{ id }}"                    # ✅ Template - from current row
      user_name: "{{ attributes.name }}"     # ✅ Template
      combined: "{{ namespace }}/{{ name }}"  # ✅ Template expressions work!
```

#### C. Variable Scoping and Access

**Variables available in templates ({{ }}):**

1. **Global variables** - From `globals` section
   ```yaml
   globals:
     api_base: "https://api.example.com"
   # Use: {{ api_base }}
   ```

2. **Current row fields** - Flattened to top level
   ```yaml
   # If row is: {"metadata": {"name": "pod-1"}, "status": "Running"}
   # Access: {{ metadata.name }} or {{ status }}
   ```

3. **Previous page data** - Stored by page name
   ```yaml
   # After selecting from "namespaces" page, entire row stored as "namespaces"
   # Access: {{ namespaces.metadata.name }}
   ```

4. **Context variables** - From navigation context
   ```yaml
   # If context passed: pod_name: "$.metadata.name"
   # Access: {{ pod_name }}
   ```

5. **Special variables**
   - `{{ row }}` - The entire current row object
   - `{{ value }}` - Current value (in transforms/conditions)
   - `{{ env.VAR_NAME }}` - Environment variables

**Variable Resolution Priority (high to low):**
1. Current row fields (flattened)
2. Page contexts (from previous navigations)
3. Global variables
4. Environment variables

#### D. Common Patterns

**Pattern 1: Multi-level Navigation**
```yaml
# Page 1: namespaces
next:
  page: pods
  context:
    namespace: "$.metadata.name"  # Extract and store

# Page 2: pods (has access to {{ namespace }})
title: "Pods in {{ namespace }}"
data:
  command: "kubectl"
  args: ["get", "pods", "-n", "{{ namespace }}"]

# Navigate to logs
actions:
  - key: "ctrl+l"
    page: pod_logs
    context:
      pod_name: "{{ metadata.name }}"      # Template - from current pod
      namespace: "{{ namespace }}"         # Template - from stored context

# Page 3: pod_logs (has access to both)
title: "Logs: {{ pod_name }}"
data:
  type: stream
  command: "kubectl"
  args: ["logs", "-f", "{{ pod_name }}", "-n", "{{ namespace }}"]
```

**Pattern 2: Accessing Previous Page Data**
```yaml
# Entire selected row from "users" page is stored as "users"
title: "Details - {{ users.attributes.name }}"

# OR use extracted context variable
title: "Details - {{ user_name }}"
```

**Pattern 3: Current Row Access**
```yaml
# In table view, current row fields are available directly
columns:
  - path: "$.status"
    style:
      - condition: "{{ status == 'active' }}"  # Access current row's status field
        color: green
```

#### E. Key Rules Summary

| Location | Syntax | Example |
|----------|--------|---------|
| **next.context values** | JSONPath only | `pod_name: "$.metadata.name"` |
| **action.context values** | Templates | `pod_name: "{{ metadata.name }}"` |
| **Page titles** | Templates | `title: "{{ namespace }}"` |
| **Data commands/URLs** | Templates | `args: ["-n", "{{ namespace }}"]` |
| **Transforms** | Templates | `transform: "{{ value \| timeago }}"` |
| **Conditions** | Templates | `condition: "{{ value > 5 }}"` |

### 7. Styling

Available colors: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `gray`

Style modifiers: `bold`, `dim`

```yaml
style:
  - condition: "{{ value > 100 }}"
    color: green
    bold: true
  - condition: "{{ value < 0 }}"
    color: red
  - default: true
    color: white
```

### 8. Column Transforms

Use Tera templates to transform column values:

```yaml
columns:
  - path: "$.created_at"
    display: "Age"
    transform: "{{ value | timeago }}"  # "2 hours ago"
    
  - path: "$.bytes"
    display: "Size"
    transform: "{{ value | filesizeformat }}"  # "1.5 MB"
    
  - path: "$.status"
    display: "Status"
    transform: "{{ value | upper }}"  # ACTIVE
    
  - path: "$.price"
    display: "Price"
    transform: "${{ value | round(precision=2) }}"  # $19.99
    
  - path: "$.tags"
    display: "Tags"
    transform: "{{ value | join(sep=', ') }}"  # tag1, tag2
```

Available Tera filters:
- `timeago` - Convert timestamp to relative time
- `filesizeformat` - Format bytes to human-readable size
- `upper`, `lower`, `capitalize` - Case conversion
- `round` - Round numbers
- `join` - Join arrays
- `status_color` - Color code status values

### 9. Validation Rules

Add validation to ensure data integrity:

```yaml
validation:
  rules:
    - field: "$.email"
      type: email
      message: "Invalid email format"
      
    - field: "$.age"
      type: range
      min: 0
      max: 120
      message: "Age must be between 0 and 120"
      
    - field: "$.username"
      type: regex
      pattern: "^[a-zA-Z0-9_]+$"
      message: "Username can only contain letters, numbers, and underscores"
      
    - field: "$.status"
      type: enum
      values: ["active", "inactive", "pending"]
      message: "Status must be active, inactive, or pending"
```

### 10. JSONPath Reference

Common patterns:
- `$[*]` - All items in root array
- `$.data[*]` - All items in `data` array
- `$.items[*]` - All items in `items` array
- `$.attributes.name` - Nested field access
- `$.data` - Single object (for detail views)
- `$..name` - Recursive descent (all `name` fields)
- `$[0]` - First item
- `$[-1]` - Last item
- `$[?(@.status == 'active')]` - Filter items

## Complete Examples

### Example 1: Dog API Browser

```yaml
version: v1

app:
  name: "Dog Breeds Browser"
  description: "Explore dog breeds and facts"
  theme: "default"

globals:
  api_base: "https://dogapi.dog/api/v2"

start: breeds

pages:
  breeds:
    title: "Dog Breeds"
    data:
      adapter: http
      url: "{{ api_base }}/breeds"
      method: GET
      headers:
        Accept: "application/json"
      items: "$.data[*]"
    view:
      type: table
      columns:
        - path: "$.attributes.name"
          display: "Breed"
          width: 30
          style:
            - default: true
              color: cyan
              bold: true
        - path: "$.attributes.life.min"
          display: "Min Life"
          width: 10
          style:
            - default: true
              color: green
        - path: "$.attributes.life.max"
          display: "Max Life"
          width: 10
          style:
            - default: true
              color: green
        - path: "$.attributes.hypoallergenic"
          display: "Hypo"
          width: 6
          style:
            - condition: "{{ value == 'true' }}"
              color: yellow
              bold: true
            - default: true
              color: gray
    next:
      page: breed_detail
      context:
        breed_id: "$.id"
        breed_name: "$.attributes.name"
    actions:
      - key: "ctrl+f"
        name: "View Facts"
        page: "facts"

  breed_detail:
    title: "{{ breed_name }}"
    data:
      adapter: http
      url: "{{ api_base }}/breeds/{{ breed_id }}"
      method: GET
      headers:
        Accept: "application/json"
      items: "$.data"
    view:
      type: table
      columns:
        - path: "$.attributes.name"
          display: "Name"
          width: 30
        - path: "$.attributes.description"
          display: "Description"
          width: 80

  facts:
    title: "Dog Facts"
    data:
      adapter: http
      url: "{{ api_base }}/facts"
      method: GET
      headers:
        Accept: "application/json"
      items: "$.data[*]"
    view:
      type: table
      columns:
        - path: "$.attributes.body"
          display: "Fact"
          width: 100
          style:
            - default: true
              color: yellow
```

### Example 2: Kubernetes Dashboard with Logs

```yaml
version: v1

app:
  name: "Kubernetes Dashboard"
  description: "Browse pods and view logs"
  theme: "default"

globals:
  namespace: "default"

start: pods

pages:
  pods:
    title: "Pods in {{ namespace }}"
    data:
      adapter: cli
      command: "kubectl"
      args: ["get", "pods", "-n", "{{ namespace }}", "-o", "json"]
      items: "$.items[*]"
      refresh_interval: "10s"
    view:
      type: table
      columns:
        - path: "$.metadata.name"
          display: "Name"
          width: 40
          style:
            - default: true
              color: cyan
        - path: "$.status.phase"
          display: "Status"
          width: 15
          style:
            - condition: "{{ value == 'Running' }}"
              color: green
            - condition: "{{ value == 'Pending' }}"
              color: yellow
            - condition: "{{ value == 'Failed' }}"
              color: red
            - default: true
              color: white
        - path: "$.metadata.creationTimestamp"
          display: "Age"
          width: 15
          transform: "{{ value | timeago }}"
    next:
      page: pod_detail
      context:
        pod_name: "$.metadata.name"       # JSONPath for next navigation
        pod_namespace: "$.metadata.namespace"
    actions:
      - key: "ctrl+l"
        name: "View Logs"
        page: "pod_logs"
        context:
          pod_name: "{{ metadata.name }}"  # Templates for action navigation
          pod_namespace: "{{ metadata.namespace }}"

  pod_detail:
    title: "Pod: {{ pod_name }}"
    data:
      adapter: cli
      command: "kubectl"
      args: ["get", "pod", "{{ pod_name }}", "-n", "{{ pod_namespace }}", "-o", "json"]
      items: "$.data"
    view:
      type: text
      syntax: yaml

  pod_logs:
    title: "Logs: {{ pod_name }}"
    data:
      type: stream
      command: "kubectl"
      args: ["logs", "-f", "{{ pod_name }}", "-n", "{{ pod_namespace }}"]
      buffer_size: 1000
      follow: true
    view:
      type: logs
      follow: true
      wrap: true
      show_line_numbers: true
```

### Example 3: File Browser with Conditional Navigation

```yaml
version: v1

app:
  name: "File Browser"
  description: "Browse files and directories"
  theme: "default"

globals:
  base_path: "/Users/user/projects"

start: directory

pages:
  directory:
    title: "{{ current_path | default(value=base_path) }}"
    data:
      adapter: cli
      command: "ls"
      args: ["-la", "{{ current_path | default(value=base_path) }}"]
      items: "$[*]"
    view:
      type: table
      columns:
        - path: "$.name"
          display: "Name"
          width: 40
          style:
            - condition: "{{ row.type == 'dir' }}"
              color: blue
              bold: true
            - default: true
              color: white
        - path: "$.size"
          display: "Size"
          width: 12
          transform: "{{ value | filesizeformat }}"
        - path: "$.modified"
          display: "Modified"
          width: 20
          transform: "{{ value | timeago }}"
    next:
      - condition: "{{ row.type == 'dir' }}"
        page: directory
        context:
          current_path: "$.path"
      - condition: "{{ row.type == 'file' }}"
        page: file_content
        context:
          file_path: "$.path"
      - default: true
        page: directory

  file_content:
    title: "{{ file_path }}"
    data:
      adapter: cli
      command: "cat"
      args: ["{{ file_path }}"]
    view:
      type: text
      syntax: auto  # Auto-detect from file extension
```

### Example 4: REST API with Multiple Data Sources

```yaml
version: v1

app:
  name: "User Dashboard"
  description: "View users with stats"
  theme: "default"

globals:
  api_base: "https://api.example.com"

start: users

pages:
  users:
    title: "Users with Activity"
    data:
      sources:
        - name: users
          adapter: http
          url: "{{ api_base }}/users"
          items: "$.data[*]"
          
        - name: activity
          adapter: http
          url: "{{ api_base }}/activity"
          items: "$.data[*]"
          optional: true
          
      merge: true
    view:
      type: table
      columns:
        - path: "$.name"
          display: "User"
          width: 30
          source: users
          style:
            - default: true
              color: cyan
              
        - path: "$.email"
          display: "Email"
          width: 35
          source: users
          
        - path: "$.last_login"
          display: "Last Login"
          width: 20
          source: activity
          transform: "{{ value | timeago }}"
          style:
            - default: true
              color: yellow
```

## Generation Guidelines

When generating a TermStack YAML:

1. **Understand the data source** - API endpoints, CLI commands, or scripts
2. **Define globals** - API base URL and common variables
3. **Create the start page** - Usually a list/table view
4. **Add detail pages** - For viewing individual items
5. **Set up navigation** - Use `next` for Enter key, `actions` for shortcuts
6. **Add styling** - Color code important fields
7. **Use correct context** - Pass IDs/names via context, access directly by key name
8. **Choose the right data source type** - Use `adapter: http|cli|script` for single/periodic fetches, `type: stream` for real-time streaming
9. **Select appropriate view** - Table for lists, Text for details, Logs for streaming
10. **Add transforms** - Use Tera filters for formatting (timeago, filesizeformat)
11. **Implement validation** - Add rules for data integrity
12. **Use conditional navigation** - Route to different pages based on data type

## Common Patterns

### REST API Browser
```
List Page (table) → Detail Page (table/text) → Related Items (table)
```

### File Browser
```
Directory (table) → Subdirectory (table) → File Content (text)
Use conditional navigation for files vs directories
```

### Kubernetes Dashboard
```
Namespaces → Pods → Pod Details → Logs (streaming)
```

### Log Viewer
```
Services (table) → Logs (logs view with filters)
Use stream adapter with follow mode
```

### Multi-Source Dashboard
```
Users (merged from users + stats) → User Detail → User Activity
```

## Timeout Formats

All timeout fields support these formats:
- Seconds: `"30s"`, `"5s"`
- Minutes: `"5m"`, `"30m"`
- Hours: `"1h"`, `"2h"`
- Combined: `"1h30m"`, `"2m30s"`

## Running TermStack

```bash
termstack examples/your-config.yaml
```

**Installation:** If you don't have `termstack` installed, download it with:

```bash
# macOS Apple Silicon
curl -fsSL https://github.com/pa/termstack/releases/latest/download/termstack-macos-arm64.tar.gz \
  | tar -xz \
  && chmod +x termstack \
  && sudo mv termstack /usr/local/bin/termstack

# macOS Intel
curl -fsSL https://github.com/pa/termstack/releases/latest/download/termstack-macos-amd64.tar.gz \
  | tar -xz \
  && chmod +x termstack \
  && sudo mv termstack /usr/local/bin/termstack

# Linux x86_64
curl -fsSL https://github.com/pa/termstack/releases/latest/download/termstack-linux-amd64.tar.gz \
  | tar -xz \
  && chmod +x termstack \
  && sudo mv termstack /usr/local/bin/termstack
```

## Navigation Keys

- `Enter` - Navigate to next page (defined by `next`)
- `Esc` - Go back
- `Shift+A` - Open action menu
- `j`/`k` or arrows - Move up/down
- `g` - Go to top
- `G` - Go to bottom
- `/` - Search (use `%Column Name% term` for column-specific search)
- `q` - Quit
- `r` - Refresh data
- `f` - Toggle filter (in logs view)

## Tips for Best Results

1. **Always specify `items` JSONPath** - This tells TermStack where to find the array
2. **Use descriptive context variable names** - Makes templates easier to understand
3. **Add timeouts** - Prevent hanging on slow APIs or commands
4. **Use refresh_interval for dashboards** - Keep data current
5. **Add confirmation for destructive actions** - Use `confirm` field
6. **Style based on data values** - Use conditional styles for status, severity, etc.
7. **Use transforms for readability** - Format timestamps, file sizes, etc.
8. **Test JSONPath expressions** - Use online tools to verify paths
9. **Add optional flag to non-critical data sources** - Prevents failures
10. **Use builtin actions** - Leverage built-in functionality (help, search, refresh)

## Troubleshooting Common Issues

### Issue: "Command exited with status: 1" in Stream

**Cause:** Template variables in stream command are not being resolved correctly.

**Solution:**
```yaml
# ❌ WRONG - Using global variable that may not be in scope
data:
  type: stream
  command: "kubectl"
  args: ["logs", "-f", "{{ pod_name }}", "-n", "{{ namespace }}"]

# ✅ CORRECT - Pass namespace explicitly in context
actions:
  - key: "ctrl+l"
    page: pod_logs
    context:
      pod_name: "{{ metadata.name }}"
      pod_namespace: "{{ metadata.namespace }}"

# Then in pod_logs page:
data:
  type: stream
  args: ["logs", "-f", "{{ pod_name }}", "-n", "{{ pod_namespace }}"]
```

### Issue: Variables Not Available in Next Page

**Cause:** Using wrong syntax in context (templates in next.context or JSONPath in action.context).

**Solution:**
```yaml
# ❌ WRONG - Template in next.context
next:
  context:
    name: "{{ metadata.name }}"  # Won't work!

# ✅ CORRECT - JSONPath in next.context
next:
  context:
    name: "$.metadata.name"

# ❌ WRONG - JSONPath in action.context
actions:
  - key: "ctrl+d"
    context:
      name: "$.metadata.name"  # Won't work!

# ✅ CORRECT - Template in action.context
actions:
  - key: "ctrl+d"
    context:
      name: "{{ metadata.name }}"
```

### Issue: Can't Access Previous Page Data

**Cause:** Not understanding how page data is stored.

**Solution:**
```yaml
# After navigating from "namespaces" page, entire selected row is stored
# Access it using the page name as prefix:
title: "Pods in {{ namespaces.metadata.name }}"

# OR extract specific fields in context:
# In namespaces page:
next:
  page: pods
  context:
    namespace: "$.metadata.name"  # Extract and store

# In pods page:
title: "Pods in {{ namespace }}"  # Use extracted value
```

### Issue: Template Variables Empty/Undefined

**Cause:** Variable not in scope or wrong variable name.

**Debug steps:**
1. Check if variable is passed in context
2. Verify context syntax matches navigation type (next vs action)
3. Use page name prefix for previous page data: `{{ pagename.field }}`
4. Check variable resolution priority (current row > page contexts > globals)

**Example:**
```yaml
# If you're getting empty {{ pod_name }}:

# Check 1: Was it passed in context?
actions:
  - key: "ctrl+l"
    context:
      pod_name: "{{ metadata.name }}"  # ✅ Passed

# Check 2: Is it being used in the right page?
pod_logs:
  title: "{{ pod_name }}"  # ✅ Should work if context passed

# Check 3: Try using source page prefix
pod_logs:
  title: "{{ pods.metadata.name }}"  # Alternative if context not working
```

### Issue: JSONPath Not Extracting Data

**Cause:** Wrong JSONPath expression or data structure.

**Solution:**
```yaml
# Test your JSONPath on actual data first
# If data is: {"metadata": {"name": "my-pod"}}

# ✅ CORRECT
context:
  name: "$.metadata.name"  # Extracts "my-pod"

# ❌ WRONG
context:
  name: "$.name"  # Won't find it (name is nested)
  name: "metadata.name"  # Missing $ prefix
```

### Best Practices for Context

1. **Always pass namespace with pod data:**
   ```yaml
   context:
     pod_name: "{{ metadata.name }}"
     pod_namespace: "{{ metadata.namespace }}"
   ```

2. **Use consistent variable names across pages:**
   ```yaml
   # Good pattern:
   namespaces → namespace
   pods → pod_name, pod_namespace
   deployments → deployment_name
   ```

3. **Extract data early in navigation chain:**
   ```yaml
   # In first page, extract what you'll need later
   next:
     context:
       namespace: "$.metadata.name"
       cluster: "$.metadata.clusterName"
   ```

4. **Use descriptive context keys:**
   ```yaml
   # ✅ GOOD
   context:
     pod_name: "{{ metadata.name }}"
     pod_namespace: "{{ metadata.namespace }}"
   
   # ❌ BAD
   context:
     name: "{{ metadata.name }}"  # Too generic
     ns: "{{ metadata.namespace }}"  # Unclear abbreviation
   ```
