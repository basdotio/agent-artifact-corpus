# WP-CLI Commands Reference

## Core Commands

### WordPress Core Management

#### Download WordPress
```bash
wp core download
wp core download --version=6.4
wp core download --path=/custom/path
```

#### Install WordPress
```bash
wp core install --url=example.com --title="Site Title" --admin_user=admin --admin_password=password --admin_email=admin@example.com
```

#### Update WordPress
```bash
wp core update
wp core update --version=6.5
wp core check-update
```

#### Database Operations
```bash
wp db create
wp db drop
wp db export backup.sql
wp db import backup.sql
wp db reset --yes
```

### Plugin Management

#### List Plugins
```bash
wp plugin list
wp plugin list --status=active
wp plugin list --format=json
```

#### Install Plugins
```bash
wp plugin install akismet
wp plugin install akismet --activate
wp plugin install https://example.com/plugin.zip
wp plugin install akismet --version=5.0
```

#### Activate/Deactivate Plugins
```bash
wp plugin activate akismet
wp plugin activate --all
wp plugin deactivate akismet
wp plugin deactivate --all
```

#### Update Plugins
```bash
wp plugin update akismet
wp plugin update --all
```

#### Delete Plugins
```bash
wp plugin delete akismet
wp plugin uninstall akismet --deactivate
```

### Theme Management

#### List Themes
```bash
wp theme list
wp theme list --status=active
```

#### Install Themes
```bash
wp theme install twentytwentyfour
wp theme install twentytwentyfour --activate
wp theme install https://example.com/theme.zip
```

#### Activate Themes
```bash
wp theme activate twentytwentyfour
```

#### Update Themes
```bash
wp theme update twentytwentyfour
wp theme update --all
```

### User Management

#### List Users
```bash
wp user list
wp user list --role=administrator
wp user list --format=json
```

#### Create Users
```bash
wp user create bob bob@example.com --role=author
wp user create alice alice@example.com --role=editor --user_pass=password
```

#### Update Users
```bash
wp user update 1 --user_pass=newpassword
wp user update bob --display_name="Bob Smith"
```

#### Delete Users
```bash
wp user delete bob --reassign=1
```

### Post Management

#### List Posts
```bash
wp post list
wp post list --post_type=page
wp post list --post_status=draft
```

#### Create Posts
```bash
wp post create --post_type=post --post_title="New Post" --post_status=publish
wp post create --post_type=page --post_title="About Us" --post_status=publish
```

#### Update Posts
```bash
wp post update 123 --post_status=publish
wp post update 123 --post_title="Updated Title"
```

#### Delete Posts
```bash
wp post delete 123
wp post delete $(wp post list --post_status=draft --format=ids)
```

### Site Options

#### Get Options
```bash
wp option get blogname
wp option get siteurl
```

#### Set Options
```bash
wp option update blogname "My New Site Name"
wp option update blogdescription "Just another WordPress site"
```

#### Add Options
```bash
wp option add custom_option "value"
```

#### Delete Options
```bash
wp option delete custom_option
```

### Search and Replace

#### Basic Search-Replace
```bash
wp search-replace 'http://oldsite.com' 'https://newsite.com'
wp search-replace 'old text' 'new text' --dry-run
```

#### Targeted Search-Replace
```bash
wp search-replace 'old' 'new' wp_posts
wp search-replace 'old' 'new' wp_posts wp_postmeta
```

### Cache Operations

#### Clear Cache
```bash
wp cache flush
wp transient delete --all
wp rewrite flush
```

### Media Management

#### Regenerate Thumbnails
```bash
wp media regenerate
wp media regenerate 123
wp media regenerate --yes
```

#### Import Media
```bash
wp media import image.jpg
wp media import image.jpg --post_id=123
```

### Multisite Commands

#### Create Site
```bash
wp site create --slug=newsite --title="New Site"
```

#### List Sites
```bash
wp site list
```

#### Super Admin Management
```bash
wp super-admin add username
wp super-admin remove username
```

## Common Workflows

### Fresh Install
```bash
# Download WordPress
wp core download

# Create config
wp config create --dbname=wpdb --dbuser=root --dbpass=password

# Create database
wp db create

# Install WordPress
wp core install --url=localhost --title="My Site" --admin_user=admin --admin_email=admin@example.com
```

### Site Migration
```bash
# Export database
wp db export backup.sql

# Search and replace URLs (dry run first)
wp search-replace 'http://oldsite.com' 'https://newsite.com' --dry-run

# Actually do it
wp search-replace 'http://oldsite.com' 'https://newsite.com'

# Clear cache
wp cache flush
```

### Bulk Plugin Management
```bash
# Update all plugins
wp plugin update --all

# Activate all plugins
wp plugin activate --all

# Deactivate all plugins
wp plugin deactivate --all
```

### Content Cleanup
```bash
# Delete all drafts
wp post delete $(wp post list --post_status=draft --format=ids)

# Delete all spam comments
wp comment delete $(wp comment list --status=spam --format=ids)

# Delete unused tags
wp term list post_tag --count=0 --format=ids | xargs -d ' ' -I % wp term delete post_tag %
```

## Output Formats

WP-CLI supports multiple output formats:

```bash
wp plugin list --format=table   # Default
wp plugin list --format=json    # JSON output
wp plugin list --format=csv     # CSV output
wp plugin list --format=yaml    # YAML output
wp plugin list --format=ids     # Space-separated IDs
wp plugin list --format=count   # Count only
```

## Global Parameters

These work with all commands:

- `--path=<path>` - Path to WordPress installation
- `--url=<url>` - URL for multisite subsites
- `--user=<id|login>` - Run as specific user
- `--skip-plugins` - Skip loading plugins
- `--skip-themes` - Skip loading themes
- `--quiet` - Suppress output
- `--debug` - Show debugging output
- `--prompt` - Prompt for values
- `--allow-root` - Allow root user (use carefully)

## Common Patterns

### Conditional Operations
```bash
# Install plugin if not already installed
wp plugin is-installed woocommerce || wp plugin install woocommerce --activate
```

### Loops and Batch Operations
```bash
# Loop through all sites in multisite
wp site list --field=url | xargs -I % wp --url=% plugin update --all
```

### JSON Processing
```bash
# Get specific field from JSON output
wp plugin list --format=json | jq '.[] | select(.status=="active") | .name'
```

### Error Handling
```bash
# Continue on error
wp plugin update --all || echo "Some plugins failed to update"
```

## Debugging Commands

```bash
# Check configuration
wp --info

# Debug mode
wp --debug plugin list

# Get PHP version
wp cli info

# Test database connection
wp db check
```
