# Example Plugin Documentation (With Issues)

This example demonstrates common documentation issues that the WordPress Documentation Review Skill will catch.

## Installing the Plugin

We recommend installing the plugin from the WordPress repository. You guys can easily install it by following these steps:

1. Click on **plugins** in the left sidebar
2. Click **add new**
3. Search for the plugin name
4. The plugin will be installed when you click the install button
5. After installation, please click **activate**

Note: You must have administrator access to install plugins.

## Using the Master Branch

If you're a developer, you might want to use the master branch from our github repository. The whitelist of approved contributors can push directly to master.

```bash
$ git clone https://github.com/example/plugin.git
$ cd plugin
$ git checkout master
```

## Configuration

To configure the plugin settings, go to **settings** > **plugin settings** on the right side of your dashboard.

### API Settings

You'll need to enter your API key in the apiKey field. To get your API key:

- Go to the provider website
- Login to your account
- Click "Generate API Key"
- Copy the key

Then paste YOUR_API_KEY into the field:

```php
define( 'API_KEY', 'YOUR_API_KEY' );
```

### Advanced Options

The plugin has many advanced options that are crazy useful! You can enable these features:

- Caching (This will improve performance)
- Logging (useful for debugging)
- Auto-updates (the plugin will update automatically)

## Troubleshooting

**Problem**: The plugin is not working

Solution: Make sure you activated it correctly

**Problem**: API errors

Solution: Check your key

## Code Example

Here's how to use the main function:

```php
function process_data() {
  $data = get_data();
  // process the data
  return $data;
}
```

## Support

If you need help, click here to visit our support forum: https://example.com/support

For more info, see our website.

## Screenshots

![Dashboard](screenshot.png)

## Notes

- This plugin is awesome!
- It's better than all the other plugins
- In the future, we will add many new features
- The disabled users might have trouble with some features
- This was built by the guys at Example Corp

## Changelog

### 1.0
- Initial release
