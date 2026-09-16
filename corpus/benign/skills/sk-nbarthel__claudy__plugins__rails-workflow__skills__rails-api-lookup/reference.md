# Rails API Reference Mappings

**Purpose**: Maps Rails classes/modules to API documentation URLs

**Version**: 1.0.0 (supports Rails 6.1 - 8.0)

---

## Active Record Classes

### Core Classes

```yaml
ActiveRecord::Base:
  url_path: "ActiveRecord/Base.html"
  description: "Base class for all models"
  common_methods:
    save: "method-i-save"
    save!: "method-i-save-21"
    update: "method-i-update"
    update!: "method-i-update-21"
    destroy: "method-i-destroy"
    destroy!: "method-i-destroy-21"
    reload: "method-i-reload"
    persisted?: "method-i-persisted-3F"
    new_record?: "method-i-new_record-3F"

ActiveRecord::Relation:
  url_path: "ActiveRecord/Relation.html"
  description: "Query result collection"
  common_methods:
    to_a: "method-i-to_a"
    each: "method-i-each"
    map: "method-i-map"
    pluck: "method-i-pluck"
    ids: "method-i-ids"
```

### Query Interface

```yaml
ActiveRecord::QueryMethods:
  url_path: "ActiveRecord/QueryMethods.html"
  description: "Query building methods"
  common_methods:
    where: "method-i-where"
    not: "method-i-not"
    order: "method-i-order"
    limit: "method-i-limit"
    offset: "method-i-offset"
    joins: "method-i-joins"
    left_joins: "method-i-left_joins"
    includes: "method-i-includes"
    eager_load: "method-i-eager_load"
    preload: "method-i-preload"
    references: "method-i-references"
    group: "method-i-group"
    having: "method-i-having"
    distinct: "method-i-distinct"
    select: "method-i-select"
    reorder: "method-i-reorder"
    reverse_order: "method-i-reverse_order"
```

### Associations

```yaml
ActiveRecord::Associations::ClassMethods:
  url_path: "ActiveRecord/Associations/ClassMethods.html"
  description: "Association declarations"
  common_methods:
    belongs_to: "method-i-belongs_to"
    has_one: "method-i-has_one"
    has_many: "method-i-has_many"
    has_and_belongs_to_many: "method-i-has_and_belongs_to_many"
    has_one_attached: "method-i-has_one_attached"
    has_many_attached: "method-i-has_many_attached"
```

### Validations

```yaml
ActiveModel::Validations::ClassMethods:
  url_path: "ActiveModel/Validations/ClassMethods.html"
  description: "Validation declarations"
  common_methods:
    validates: "method-i-validates"
    validates_each: "method-i-validates_each"
    validates_with: "method-i-validates_with"
    validate: "method-i-validate"

ActiveModel::Validations::HelperMethods:
  url_path: "ActiveModel/Validations/HelperMethods.html"
  description: "Built-in validators"
  common_methods:
    validates_presence_of: "method-i-validates_presence_of"
    validates_absence_of: "method-i-validates_absence_of"
    validates_length_of: "method-i-validates_length_of"
    validates_size_of: "method-i-validates_size_of"
    validates_numericality_of: "method-i-validates_numericality_of"
    validates_inclusion_of: "method-i-validates_inclusion_of"
    validates_exclusion_of: "method-i-validates_exclusion_of"
    validates_format_of: "method-i-validates_format_of"
    validates_uniqueness_of: "method-i-validates_uniqueness_of"
```

### Callbacks

```yaml
ActiveRecord::Callbacks:
  url_path: "ActiveRecord/Callbacks.html"
  description: "Model lifecycle callbacks"
  common_methods:
    after_initialize: "method-i-after_initialize"
    after_find: "method-i-after_find"
    before_validation: "method-i-before_validation"
    after_validation: "method-i-after_validation"
    before_save: "method-i-before_save"
    around_save: "method-i-around_save"
    after_save: "method-i-after_save"
    before_create: "method-i-before_create"
    around_create: "method-i-around_create"
    after_create: "method-i-after_create"
    before_update: "method-i-before_update"
    around_update: "method-i-around_update"
    after_update: "method-i-after_update"
    before_destroy: "method-i-before_destroy"
    around_destroy: "method-i-around_destroy"
    after_destroy: "method-i-after_destroy"
    after_commit: "method-i-after_commit"
    after_rollback: "method-i-after_rollback"
```

### Migrations

```yaml
ActiveRecord::Migration:
  url_path: "ActiveRecord/Migration.html"
  description: "Database migration base class"
  common_methods:
    change: "method-i-change"
    up: "method-i-up"
    down: "method-i-down"
    reversible: "method-i-reversible"

ActiveRecord::ConnectionAdapters::SchemaStatements:
  url_path: "ActiveRecord/ConnectionAdapters/SchemaStatements.html"
  description: "Schema manipulation methods"
  common_methods:
    create_table: "method-i-create_table"
    drop_table: "method-i-drop_table"
    rename_table: "method-i-rename_table"
    add_column: "method-i-add_column"
    remove_column: "method-i-remove_column"
    rename_column: "method-i-rename_column"
    change_column: "method-i-change_column"
    add_index: "method-i-add_index"
    remove_index: "method-i-remove_index"
    add_foreign_key: "method-i-add_foreign_key"
    remove_foreign_key: "method-i-remove_foreign_key"
    add_reference: "method-i-add_reference"
    remove_reference: "method-i-remove_reference"
```

---

## Action Controller Classes

### Core Classes

```yaml
ActionController::Base:
  url_path: "ActionController/Base.html"
  description: "Base controller class"
  common_methods:
    render: "method-i-render"
    redirect_to: "method-i-redirect_to"
    head: "method-i-head"

ActionController::API:
  url_path: "ActionController/API.html"
  description: "API-only controller base"
  version_support: "5.0+"

ActionController::Metal:
  url_path: "ActionController/Metal.html"
  description: "Minimal controller implementation"
```

### Controller Features

```yaml
ActionController::StrongParameters:
  url_path: "ActionController/StrongParameters.html"
  description: "Parameter filtering"
  common_methods:
    params: "method-i-params"
    permit: "method-i-permit"
    require: "method-i-require"

ActionController::Helpers:
  url_path: "ActionController/Helpers.html"
  description: "Helper method declarations"
  common_methods:
    helper_method: "method-i-helper_method"

ActionController::Cookies:
  url_path: "ActionController/Cookies.html"
  description: "Cookie handling"
  common_methods:
    cookies: "method-i-cookies"

ActionController::Flash:
  url_path: "ActionController/Flash.html"
  description: "Flash message handling"
  common_methods:
    flash: "method-i-flash"
```

---

## Action View Classes

### Core Classes

```yaml
ActionView::Base:
  url_path: "ActionView/Base.html"
  description: "View rendering base class"

ActionView::Helpers:
  url_path: "ActionView/Helpers.html"
  description: "View helper modules"
```

### View Helpers

```yaml
ActionView::Helpers::FormHelper:
  url_path: "ActionView/Helpers/FormHelper.html"
  description: "Form building helpers"
  common_methods:
    form_with: "method-i-form_with"
    form_for: "method-i-form_for"
    text_field: "method-i-text_field"
    text_area: "method-i-text_area"
    select: "method-i-select"
    check_box: "method-i-check_box"
    radio_button: "method-i-radio_button"

ActionView::Helpers::UrlHelper:
  url_path: "ActionView/Helpers/UrlHelper.html"
  description: "URL generation helpers"
  common_methods:
    link_to: "method-i-link_to"
    button_to: "method-i-button_to"
    url_for: "method-i-url_for"

ActionView::Helpers::TagHelper:
  url_path: "ActionView/Helpers/TagHelper.html"
  description: "HTML tag helpers"
  common_methods:
    content_tag: "method-i-content_tag"
    tag: "method-i-tag"

ActionView::Helpers::AssetTagHelper:
  url_path: "ActionView/Helpers/AssetTagHelper.html"
  description: "Asset inclusion helpers"
  common_methods:
    javascript_include_tag: "method-i-javascript_include_tag"
    stylesheet_link_tag: "method-i-stylesheet_link_tag"
    image_tag: "method-i-image_tag"
```

---

## Active Support Classes

### Core Extensions

```yaml
ActiveSupport::Concern:
  url_path: "ActiveSupport/Concern.html"
  description: "Module mixin pattern"
  common_methods:
    included: "method-i-included"
    class_methods: "method-i-class_methods"

ActiveSupport::Callbacks:
  url_path: "ActiveSupport/Callbacks.html"
  description: "Callback framework"
  common_methods:
    define_callbacks: "method-i-define_callbacks"
    set_callback: "method-i-set_callback"
    skip_callback: "method-i-skip_callback"
    run_callbacks: "method-i-run_callbacks"
```

### Time & Date

```yaml
ActiveSupport::TimeWithZone:
  url_path: "ActiveSupport/TimeWithZone.html"
  description: "Timezone-aware time"
  common_methods:
    in_time_zone: "method-i-in_time_zone"
    utc: "method-i-utc"
    local: "method-i-local"

ActiveSupport::Duration:
  url_path: "ActiveSupport/Duration.html"
  description: "Time duration"
  common_methods:
    ago: "method-i-ago"
    since: "method-i-since"
    from_now: "method-i-from_now"
```

---

## Action Mailer Classes

```yaml
ActionMailer::Base:
  url_path: "ActionMailer/Base.html"
  description: "Mailer base class"
  common_methods:
    mail: "method-i-mail"
    deliver_now: "method-i-deliver_now"
    deliver_later: "method-i-deliver_later"
```

---

## Action Cable Classes

```yaml
ActionCable::Channel::Base:
  url_path: "ActionCable/Channel/Base.html"
  description: "Cable channel base class"
  common_methods:
    stream_from: "method-i-stream_from"
    stream_for: "method-i-stream_for"
    transmit: "method-i-transmit"

ActionCable::Connection::Base:
  url_path: "ActionCable/Connection/Base.html"
  description: "Cable connection base class"
```

---

## Active Job Classes

```yaml
ActiveJob::Base:
  url_path: "ActiveJob/Base.html"
  description: "Background job base class"
  common_methods:
    perform_later: "method-i-perform_later"
    perform_now: "method-i-perform_now"
    set: "method-i-set"
```

---

## Active Storage Classes

```yaml
ActiveStorage::Attached::One:
  url_path: "ActiveStorage/Attached/One.html"
  description: "Single file attachment"
  version_support: "5.2+"
  common_methods:
    attach: "method-i-attach"
    attached?: "method-i-attached-3F"
    purge: "method-i-purge"

ActiveStorage::Attached::Many:
  url_path: "ActiveStorage/Attached/Many.html"
  description: "Multiple file attachments"
  version_support: "5.2+"
  common_methods:
    attach: "method-i-attach"
    attached?: "method-i-attached-3F"
    purge: "method-i-purge"
```

---

## URL Construction

**Pattern**: `https://api.rubyonrails.org/v{MAJOR.MINOR}/{url_path}#{method_anchor}`

**Examples**:

**Class page**:
```
https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html
```

**Instance method**:
```
https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html#method-i-save
```

**Class method**:
```
https://api.rubyonrails.org/v7.1/ActiveRecord/Base.html#method-c-create
```

**Special characters in anchor**:
- `?` → `-3F`
- `!` → `-21`
- `=` → `-3D`

**Examples**:
- `persisted?` → `#method-i-persisted-3F`
- `save!` → `#method-i-save-21`
- `==` → `#method-i--3D-3D`

---

## Usage in rails-api-lookup

```ruby
# Pseudocode for API lookup
class_name = "ActiveRecord::Base"
method_name = "save"
mapping = reference[class_name]
version = detect_rails_version() # e.g., "7.1"
anchor = mapping.common_methods[method_name] # e.g., "method-i-save"
url = "https://api.rubyonrails.org/v#{version}/#{mapping.url_path}##{anchor}"
content = WebFetch(url, prompt: "Extract method signature and documentation")
```

---

## Maintenance

**Update frequency**: Quarterly or when new Rails version released

**Adding new APIs**:
1. Check official Rails API docs index
2. Add mapping with url_path and common_methods
3. Test URL accessibility
4. Update this file

**Version-specific APIs**:
- Mark with `version_support`
- Skill should gracefully handle unavailable APIs for older Rails versions
