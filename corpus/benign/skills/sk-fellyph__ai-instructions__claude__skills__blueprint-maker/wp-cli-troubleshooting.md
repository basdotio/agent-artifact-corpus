# WP-CLI Common Issues and Troubleshooting

## Database Connection Issues

### Error: Can't connect to the database

**Possible causes:**

1. **Using MAMP but WP-CLI is not using MAMP PHP binary**
   - Check which PHP WP-CLI uses: `wp --info`
   - Specify alternate PHP binary if needed

2. **WordPress multisite install**
   - Use `--url` parameter to specify site URL
   - Example: `wp --url=example.com/site2 plugin list`

3. **Incorrect database credentials in wp-config.php**
   - Verify DB_NAME, DB_USER, DB_PASSWORD, DB_HOST
   - Test connection: `wp db check`

### Database Connection Error with WP-CLI on Mounted Sites

**Problem:** WP-CLI commands fail with database connection error in WordPress Playground.

**Solution:** Explicitly install SQLite integration plugin:
```json
{
  "plugins": ["sqlite-database-integration"]
}
```

## PHP Configuration Issues

### Running wp --info produces HTML output

If you see HTML instead of proper output, Phar support is disabled.

**Solution:** Whitelist Phar in php.ini:
```ini
suhosin.executor.include.whitelist = phar
```

### PHP Fatal error: Cannot redeclare wp_unregister_GLOBALS()

**Cause:** Modified wp-config.php beyond what WP-CLI supports.

**Solution:** Ensure this line remains in wp-config.php:
```php
require_once(ABSPATH . 'wp-settings.php');
```

This line must be matched by regex when WP-CLI runs.

### PHP Fatal error: Call to undefined function

**Cause:** wp-config.php calls WordPress functions before WordPress loads.

**Solution:** Move WordPress function calls to a mu-plugin instead of wp-config.php.

## Memory Issues

### PHP Fatal error: Allowed memory size exhausted

**Problem:** Running out of memory, especially with `wp package install`.

**Permanent fix:** Edit php.ini:
```bash
# Find your php.ini
php -i | grep php.ini

# Increase memory_limit
memory_limit = 512M
```

**Temporary fix:**
```bash
php -d memory_limit=512M "$(which wp)" package install <package-name>
```

**Additional steps if still failing:**
1. Restart PHP
2. Check for additional php.ini files:
```bash
php -i | grep additional
```

## Permission Issues

### Error: YIKES! It looks like you're running this as root

**Problem:** Running WP-CLI as root is dangerous.

**Solution:** Always run WP-CLI as a regular user, never as root. If you must run as root (not recommended), use `--allow-root` flag.

## Configuration Issues

### PHP notice: Undefined index on $_SERVER superglobal

**Cause:** $_SERVER is not populated in CLI context.

**Solution:** Check if keys exist before accessing:
```php
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
}
```

For HTTP_HOST in wp-config.php:
```php
if (defined('WP_CLI') && WP_CLI && !isset($_SERVER['HTTP_HOST'])) {
    $_SERVER['HTTP_HOST'] = 'example.com';
}
```

### PHP notice: Use of undefined constant STDOUT

**Cause:** Not running via PHP CLI.

**Solution:** Verify you're using PHP CLI, not PHP-CGI or PHP-FPM.

### Can't find wp-content directory / use of $_SERVER['document_root']

**Cause:** $_SERVER['document_root'] unavailable in CLI.

**Solution:** Use `dirname(__FILE__)` instead:
```php
// Bad
$path = $_SERVER['document_root'] . '/wp-content';

// Good
$path = dirname(__FILE__) . '/wp-content';
```

## Character Encoding Issues

### Cannot create post with Latin characters on Windows

**Problem:** UTF-8 in PHP arguments doesn't work on Windows for PHP <= 7.0.

**Solution for PHP <= 7.0:** Use `--prompt` option:
```bash
echo "Perícias Contábeis" | wp post create --post_type=page --post_status=publish --prompt=post_title
```

**Solution for PHP >= 7.1:** Works natively, no workaround needed.

## Network and Installation Issues

### The installation hangs

**Cause:** Cannot connect to GitHub for resources.

**Solution:** Ensure outbound connections allowed on:
- SSL (port 443)
- Git (port 9418)

### W3 Total Cache Error: some files appear missing

**Cause:** W3 Total Cache object caching interferes.

**Solution:** Disable object caching or remove `wp-content/object-cache.php`.

## Global Parameters Conflicts

### Conflict between global parameters and command arguments

**Problem:** Global parameters like `--url` conflict with command arguments.

**Example:**
```bash
# This fails - --url is interpreted as global parameter
wp widget add rss sidebar-1 1 --url="http://example.com/feed/"
```

**Solution:** Use WP_CLI_STRICT_ARGS_MODE:
```bash
WP_CLI_STRICT_ARGS_MODE=1 wp --url=wp.dev/site2 widget add rss sidebar-1 1 --url="http://wp-cli.org/feed/"
```

Arguments before command = global, arguments after = local.

## URL Redirects

### Warning: Some code is trying to do a URL redirect

**Cause:** Plugin/theme restricts wp-admin access.

**Solution:** Pass user parameter:
```bash
wp --user=admin plugin list
```

## Debugging Issues

### Xdebug Issues

#### PHP Fatal error: Maximum function nesting level reached

**Cause:** Xdebug nesting level limit.

**Solutions:**

1. **Temporarily disable Xdebug:**
```bash
XDEBUG_MODE=off wp <command>
```

2. **Increase nesting level in php.ini:**
```ini
xdebug.max_nesting_level = 512
```

3. **One-time increase:**
```bash
php -d xdebug.max_nesting_level=512 wp <command>
```

4. **Permanently disable Xdebug** (if not debugging)

#### Error: Xdebug has detected a possible infinite loop

**Solution:** Same as above - disable Xdebug or increase nesting level.

## WordPress Version Compatibility

### The automated updater doesn't work for versions before 3.4

**Cause:** `wp core update` designed for WordPress 3.4+.

**Solution 1 (Fully automated):**
```bash
# Download latest WordPress
wp core download --force

# Update database
wp core update-db

# Download again to ensure clean state
wp core download --force
```

**Solution 2 (Semi-automated):**
```bash
# Download files
wp core download --force

# Navigate to /wp-admin/ and run database upgrade manually
```

## Best Practices to Avoid Issues

### 1. Always Check Environment
```bash
wp --info
```

### 2. Use Path Parameter
```bash
wp --path=/var/www/html plugin list
```

### 3. Test Before Production
```bash
# Use --dry-run when available
wp search-replace 'old' 'new' --dry-run
```

### 4. Keep Backups
```bash
# Always backup before major operations
wp db export backup-$(date +%Y%m%d).sql
```

### 5. Use Correct User Context
```bash
# Run as web server user
sudo -u www-data wp plugin list
```

### 6. Check Logs
```bash
# Enable debug mode
wp --debug plugin list

# Check error logs
tail -f /var/log/php/error.log
```

## WordPress Playground Specific Issues

### WP-CLI Commands Not Working in Playground

**Solution:** Ensure `wp-cli` library is loaded:
```json
{
  "extraLibraries": ["wp-cli"]
}
```

### SQLite Integration Required

**Problem:** WP-CLI database commands fail.

**Solution:** Install SQLite integration:
```json
{
  "plugins": ["sqlite-database-integration"]
}
```

### File Paths in Playground

**Remember:** All paths must be absolute starting with `/wordpress/`:
- Plugins: `/wordpress/wp-content/plugins/`
- Themes: `/wordpress/wp-content/themes/`
- Uploads: `/wordpress/wp-content/uploads/`

## Getting Help

### Check WP-CLI Info
```bash
wp cli info
```

### Check WordPress Environment
```bash
wp cli check-update
wp core version
wp plugin list
```

### Enable Debug Mode
```bash
wp --debug <command>
```

### Get Command Help
```bash
wp help <command>
wp help plugin install
```

### Test Database Connection
```bash
wp db check
```

## Quick Diagnostic Commands

```bash
# Full system check
wp --info
wp cli info
wp core version
wp db check
wp config get

# Plugin diagnostics
wp plugin list --status=active
wp plugin verify-checksums --all

# Theme diagnostics
wp theme list
wp theme status

# Database diagnostics
wp db size
wp db tables

# User diagnostics
wp user list --role=administrator
```
