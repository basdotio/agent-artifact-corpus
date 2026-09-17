---
name: beaver-builder
description: Use this skill when working with Beaver Builder page builder, custom Beaver Builder modules, Beaver Builder layouts, or any BB-specific PHP/JS/CSS development.
version: 1.0.0
---

# Beaver Builder Skill

## Overview

Beaver Builder is the primary page builder for all faithmade sites. Custom modules extend it via the `faithmade-modules` plugin.

## Custom Module Structure

```
faithmade-modules/modules/my-module/
  my-module.php          # Module class
  includes/
    frontend.php         # Frontend template
    frontend.css.php     # Dynamic CSS
    frontend.js.php      # Dynamic JS (optional)
  css/
    frontend.css         # Static CSS
  js/
    frontend.js          # Static JS
```

## Module Class Pattern

```php
class MyModule extends FLBuilderModule {
  public function __construct() {
    parent::__construct([
      'name'          => __('My Module', 'faithmade'),
      'description'   => __('Description here', 'faithmade'),
      'category'      => __('Faithmade', 'faithmade'),
      'dir'           => FM_MODULES_DIR . 'modules/my-module/',
      'url'           => FM_MODULES_URL . 'modules/my-module/',
      'icon'          => 'layout.svg',
    ]);
  }
}

FLBuilder::register_module('MyModule', [
  'general' => [
    'title'    => __('General', 'faithmade'),
    'sections' => [
      'main' => [
        'title'  => '',
        'fields' => [
          'my_field' => [
            'type'    => 'text',
            'label'   => __('Field Label', 'faithmade'),
            'default' => '',
          ],
        ],
      ],
    ],
  ],
]);
```

## Frontend Template

```php
// includes/frontend.php
<?php
$settings = $module->settings; // Access module settings
?>
<div class="my-module">
  <?php echo esc_html($settings->my_field); ?>
</div>
```

## Field Types

- `text` — single line text
- `textarea` — multi-line text
- `select` — dropdown
- `multiple-audios` / `multiple-photos` / `multiple-videos`
- `color` — color picker
- `dimension` — spacing/size
- `unit` — unit with px/em/% selector
- `link` — URL + target
- `photo` — image selector
- `icon` — icon picker
- `editor` — WYSIWYG
- `form` — nested field group

## Twig in Modules

Twig templates can be used via the Toolbox plugin's shortcode integration within frontend.php templates.

## Debugging

- Enable BB debug mode: add `define('FL_BUILDER_DEBUG', true);` to wp-config.php
- Clear BB cache: Dashboard → Settings → Beaver Builder → Tools → Clear Cache
- Module not showing: check `FLBuilder::register_module()` call and class name match
