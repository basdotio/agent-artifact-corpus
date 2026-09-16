# Example Plugin Documentation (Corrected)

This example demonstrates proper WordPress documentation following the official style guide.

## Installing the plugin

You can install the plugin from the WordPress repository. To install:

1. Select **Plugins** in the left sidebar.
2. Select **Add New**.
3. Search for the plugin name.
4. Select **Install Now**.
5. After installation completes, select **Activate**.

**Note**: You need administrator access to install plugins.

## Using the main branch

If you're a developer, you can use the main branch from the GitHub repository. The allowlist of approved contributors can push directly to main.

```bash
$ git clone https://github.com/example/plugin.git
$ cd plugin
$ git checkout main
```

## Configuration

To configure the plugin settings, go to **Settings** > **Plugin Settings**.

### API settings

You need to enter your API key in the **API Key** field. To get your API key:

1. Go to the provider website.
2. Log in to your account.
3. Select **Generate API Key**.
4. Copy the key.

Then add your API key to your configuration:

```php
define( 'API_KEY', *`API_KEY`* );
```

Replace *`API_KEY`* with your actual API key from the provider.

### Advanced options

The plugin provides several advanced features:

- **Caching**: Improves performance by storing frequently accessed data
- **Logging**: Records events for troubleshooting
- **Auto-updates**: Keeps the plugin current automatically

## Troubleshooting

### Plugin not working

If the plugin doesn't work after activation:

1. Verify the plugin activated successfully in **Plugins**.
2. Check for PHP error messages in debug logs.
3. Ensure your WordPress version meets the minimum requirements.

### API errors

If you receive API errors:

1. Verify your API key is correct.
2. Check that your API key has appropriate permissions.
3. Ensure your server can connect to the API endpoint.

## Code example

The following example shows how to use the `process_data()` function:

```php
function process_data() {
    $data = get_data();
    // Process the retrieved data
    return $data;
}
```

## Support

For support questions, visit the [support forum](https://example.com/support).

For additional information, see the [plugin website](https://example.com).

## Screenshots

![Plugin dashboard showing main settings](screenshot.png)

## Notes

- The plugin integrates with popular caching solutions
- Compatible with WordPress 6.0 and higher
- Regular updates maintain security and compatibility

## Changelog

### Version 1.0
- Initial release
