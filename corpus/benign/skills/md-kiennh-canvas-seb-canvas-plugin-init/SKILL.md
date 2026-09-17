---
name: canvas-plugin-init
description: Initialize a new Canvas LMS plugin with GUI, API, Worker, and Course Navigation components.
---

# Canvas Plugin Initialization Skill

This skill provides a standardized way to initialize a new plugin in Canvas LMS. It creates a robust starting point with GUI settings, a backend API, a background worker, and a customizable Course Navigation page with permissions.

## Features
- **GUI (User Interface)**: Creates a `settings_partial` that displays a "Hello {{current_user}}" message and basic configuration fields.
- **API Backend**: Sets up a controller in `app/controllers/api/v1/` and registers custom routes.
- **Worker Job**: Implements a `Delayed::Job` compatible worker for background tasks.
- **Course Navigation**: Adds a sample page to the Course menu (sidebar) that shows "Hello {{username}}, welcome to {{coursename}}".
- **System Hooks (Canvas Extensions)**: Demonstrates how to hook into core Canvas logic using `Module#prepend` (example: `Quizzes::Quiz#generate_submission` to track quiz starts).
- **Granular Permissions**: Registers a custom permission (`view_<plugin_name>_sample_page`) that can be configured in the Course/Account "Permissions" settings.
- **Automatic Registration**: Updates `Gemfile.d/plugins.rb` to ensure the plugin is loaded by Canvas.

## Usage

### 1. Initialize a new plugin
Use the `init_plugin.sh` script to scaffold the plugin.

```bash
/bin/bash .agent/skills/canvas-plugin-init/scripts/init_plugin.sh <plugin_name_snake_case>
```

Example:
```bash
/bin/bash .agent/skills/canvas-plugin-init/scripts/init_plugin.sh hello_world
```

### 2. File Structure Created
- `gems/plugins/<name>/<name>.gemspec`: Gem specification.
- `gems/plugins/<name>/lib/<name>/engine.rb`: Rails Engine, Permission registration, and Course Navigation extension.
- `gems/plugins/<name>/app/views/plugins/_<name>_settings.html.erb`: Configuration GUI.
- `gems/plugins/<name>/app/controllers/api/v1/<name>_controller.rb`: API Backend.
- `gems/plugins/<name>/app/controllers/course_sample_controller.rb`: Course Navigation controller.
- `gems/plugins/<name>/app/views/<name>/course_sample/index.html.erb`: Course Navigation view.
- `gems/plugins/<name>/config/pre_routes.rb`: Custom routes.
- `gems/plugins/<name>/lib/<name>/worker.rb`: Background Worker.

### 3. Components Overview

#### Course Navigation Extensions
The skill uses `Course.prepend` to inject a custom tab into the `tabs_available` list. The tab only appears if the user has the registered permission for that course.

#### Permissions
Permissions are registered via `Permissions.register` in the engine's `to_prepare` block. They automatically appear in the Canvas Permissions UI under the name provided.

#### GUI
The settings partial is accessible via **Site Admin > Plugins > <Your Plugin Name>**.

## Requirements
- Canvas LMS environment.
- Sufficient permissions to create files in `gems/plugins/` and modify `Gemfile.d/plugins.rb`.

## Troubleshooting

### Missing partial plugins/_<plugin_name>_settings

**Error:**
```
ActionView::MissingTemplate in Plugins#show
Missing partial plugins/_<plugin_name>_settings
```

**Cause:**
This error occurs when the plugin is registered with a `settings_partial` in the engine.rb file, but the corresponding partial view file doesn't exist.

**Solution:**
Ensure the settings partial exists at the correct location:
```
gems/plugins/<plugin_name>/app/views/plugins/_<plugin_name>_settings.html.erb
```

The `init_plugin.sh` script automatically creates this file. If you're creating a plugin manually or the file is missing, create it with the following structure:

```erb
<div class="plugin_settings_<plugin_name>">
  <h3><%= t(:<plugin_name>_title, "<Plugin Name> Settings") %></h3>
  <p><%= t(:<plugin_name>_description, "Configure <plugin name> settings.") %></p>
</div>

<%= fields_for :settings do |f| %>
<table class="formtable">
  <tr>
    <td style="vertical-align: top;"><%= blabel :<plugin_name>, :enabled, :en => "Enable Plugin" %></td>
    <td>
      <%= f.check_box :enabled, :checked => Canvas::Plugin.value_to_boolean(settings[:enabled]) %>
    </td>
  </tr>
  <!-- Add additional settings fields here -->
</table>
<% end %>
```

**Key Points:**
- The partial filename must start with an underscore (`_`)
- The partial must be in the `app/views/plugins/` directory (not `app/views/<plugin_name>/`)
- The `settings_partial` value in engine.rb should match: `"plugins/<plugin_name>_settings"` (without underscore or .html.erb extension)
- Use `fields_for :settings` to ensure form fields are properly namespaced
