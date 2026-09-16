# Rails Guides Reference Mappings

**Purpose**: Maps topic names to official Rails Guides URLs

**Version**: 1.0.0 (supports Rails 6.1 - 8.0)

---

## Topic Mappings

### Getting Started
```yaml
getting_started:
  title: "Getting Started with Rails"
  url_path: "getting_started.html"
  version_support: "all"
  keywords: [tutorial, first app, setup, install]

initialization:
  title: "The Rails Initialization Process"
  url_path: "initialization.html"
  version_support: "all"
  keywords: [boot, startup, initialization]
```

### Active Record

```yaml
active_record_basics:
  title: "Active Record Basics"
  url_path: "active_record_basics.html"
  version_support: "all"
  keywords: [orm, models, database, CRUD]

active_record_migrations:
  title: "Active Record Migrations"
  url_path: "active_record_migrations.html"
  version_support: "all"
  keywords: [migrations, schema, database changes]

active_record_validations:
  title: "Active Record Validations"
  url_path: "active_record_validations.html"
  version_support: "all"
  keywords: [validation, validates, presence, format]

active_record_callbacks:
  title: "Active Record Callbacks"
  url_path: "active_record_callbacks.html"
  version_support: "all"
  keywords: [callbacks, before_save, after_create, lifecycle]

active_record_associations:
  title: "Active Record Associations"
  url_path: "association_basics.html"
  version_support: "all"
  keywords: [has_many, belongs_to, has_one, through, polymorphic]

active_record_querying:
  title: "Active Record Query Interface"
  url_path: "active_record_querying.html"
  version_support: "all"
  keywords: [query, where, joins, includes, eager loading]
```

### Action Controller

```yaml
action_controller_overview:
  title: "Action Controller Overview"
  url_path: "action_controller_overview.html"
  version_support: "all"
  keywords: [controllers, requests, responses, filters]

routing:
  title: "Rails Routing from the Outside In"
  url_path: "routing.html"
  version_support: "all"
  keywords: [routes, resources, namespace, scope, member, collection]
```

### Action View

```yaml
action_view_overview:
  title: "Action View Overview"
  url_path: "action_view_overview.html"
  version_support: "all"
  keywords: [views, templates, rendering, partials]

layouts_and_rendering:
  title: "Layouts and Rendering in Rails"
  url_path: "layouts_and_rendering.html"
  version_support: "all"
  keywords: [layouts, render, yield, content_for]

form_helpers:
  title: "Action View Form Helpers"
  url_path: "form_helpers.html"
  version_support: "all"
  keywords: [forms, form_with, form_for, input fields]
```

### Action Mailer

```yaml
action_mailer_basics:
  title: "Action Mailer Basics"
  url_path: "action_mailer_basics.html"
  version_support: "all"
  keywords: [email, mailer, deliver, smtp]
```

### Action Cable

```yaml
action_cable_overview:
  title: "Action Cable Overview"
  url_path: "action_cable_overview.html"
  version_support: "all"
  keywords: [websockets, channels, subscriptions, broadcasting]
```

### Active Job

```yaml
active_job_basics:
  title: "Active Job Basics"
  url_path: "active_job_basics.html"
  version_support: "all"
  keywords: [jobs, background, queues, sidekiq, delayed_job]
```

### Active Storage

```yaml
active_storage_overview:
  title: "Active Storage Overview"
  url_path: "active_storage_overview.html"
  version_support: "6.0+"
  keywords: [uploads, files, attachments, S3, cloud storage]
```

### Testing

```yaml
testing:
  title: "Testing Rails Applications"
  url_path: "testing.html"
  version_support: "all"
  keywords: [tests, minitest, rspec, fixtures, factories]
```

### Security

```yaml
security:
  title: "Securing Rails Applications"
  url_path: "security.html"
  version_support: "all"
  keywords: [security, CSRF, XSS, SQL injection, authentication]
```

### Debugging

```yaml
debugging_rails_applications:
  title: "Debugging Rails Applications"
  url_path: "debugging_rails_applications.html"
  version_support: "all"
  keywords: [debug, byebug, pry, logs, debugging]
```

### Configuration

```yaml
configuring:
  title: "Configuring Rails Applications"
  url_path: "configuring.html"
  version_support: "all"
  keywords: [config, environment, settings, credentials]

rails_application_templates:
  title: "Rails Application Templates"
  url_path: "rails_application_templates.html"
  version_support: "all"
  keywords: [templates, generators, app templates]
```

### Performance

```yaml
caching_with_rails:
  title: "Caching with Rails"
  url_path: "caching_with_rails.html"
  version_support: "all"
  keywords: [cache, caching, fragment cache, low-level cache]

asset_pipeline:
  title: "The Asset Pipeline"
  url_path: "asset_pipeline.html"
  version_support: "all"
  keywords: [assets, sprockets, javascript, css, images]
```

### Internationalization

```yaml
i18n:
  title: "Rails Internationalization (I18n) API"
  url_path: "i18n.html"
  version_support: "all"
  keywords: [i18n, translations, locales, internationalization]
```

### Action Mailbox

```yaml
action_mailbox_basics:
  title: "Action Mailbox Basics"
  url_path: "action_mailbox_basics.html"
  version_support: "6.0+"
  keywords: [incoming email, mailbox, inbound email]
```

### Action Text

```yaml
action_text_overview:
  title: "Action Text Overview"
  url_path: "action_text_overview.html"
  version_support: "6.0+"
  keywords: [rich text, trix, wysiwyg, text editor]
```

### Rails 7+ Specific

```yaml
autoloading_and_reloading_constants:
  title: "Autoloading and Reloading Constants"
  url_path: "autoloading_and_reloading_constants.html"
  version_support: "all"
  keywords: [autoload, zeitwerk, eager loading]

engines:
  title: "Getting Started with Engines"
  url_path: "engines.html"
  version_support: "all"
  keywords: [engines, plugins, mountable]

api_app:
  title: "Using Rails for API-only Applications"
  url_path: "api_app.html"
  version_support: "5.0+"
  keywords: [api, json, api-only, rest]
```

### Rails 8+ Specific

```yaml
solid_cache:
  title: "Solid Cache"
  url_path: "solid_cache.html"
  version_support: "8.0+"
  keywords: [solid cache, caching, database cache]

solid_queue:
  title: "Solid Queue"
  url_path: "solid_queue.html"
  version_support: "8.0+"
  keywords: [solid queue, jobs, background jobs]

solid_cable:
  title: "Solid Cable"
  url_path: "solid_cable.html"
  version_support: "8.0+"
  keywords: [solid cable, websockets, action cable]
```

---

## Version Support Legend

- `all` - Available in Rails 3.0+
- `5.0+` - Available from Rails 5.0 onwards
- `6.0+` - Available from Rails 6.0 onwards
- `7.0+` - Available from Rails 7.0 onwards
- `8.0+` - Available from Rails 8.0 onwards

## URL Construction

**Pattern**: `https://guides.rubyonrails.org/v{MAJOR.MINOR}/{url_path}`

**Examples**:
- Rails 7.1: `https://guides.rubyonrails.org/v7.1/routing.html`
- Rails 8.0: `https://guides.rubyonrails.org/v8.0/routing.html`
- Latest: `https://guides.rubyonrails.org/routing.html` (edge)

## Usage in rails-docs-search

```ruby
# Pseudocode for topic lookup
topic = "active_record_associations"
mapping = reference[topic]
version = detect_rails_version() # e.g., "7.1"
url = "https://guides.rubyonrails.org/v#{version}/#{mapping.url_path}"
content = WebFetch(url, prompt: "Extract information about associations")
```

## Maintenance

**Update frequency**: Quarterly or when new Rails version released

**Adding new topics**:
1. Check official Rails Guides index
2. Add mapping with all fields
3. Test URL accessibility
4. Update this file

**Version-specific topics**:
- Mark with `version_support`
- Skill should gracefully handle unavailable guides for older Rails versions
