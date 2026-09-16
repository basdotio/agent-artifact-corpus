<?php
/**
 * Import a Google Doc as a WordPress draft post (styrereferat-flavored).
 *
 * Usage:
 *   wp eval-file .claude/skills/styrereferat/import.php <doc_url_or_id> [category_id]
 *
 * Output (parsed by skill):
 *   POST_ID: 1234
 *   TITLE: Referat fra Styremøte ...
 *   EDIT_URL: https://.../wp-admin/post.php?post=1234&action=edit
 */

$doc_url = $args[0] ?? null;
$category_id = isset($args[1]) ? (int) $args[1] : null;

if (empty($doc_url)) {
	echo "ERROR: doc URL/ID required\n";
	exit(1);
}

require_once get_stylesheet_directory() . '/vendor/autoload.php';
require_once get_stylesheet_directory() . '/includes/google/docs-import.php';
require_once __DIR__ . '/post-process.php';

$options = [];
if ($category_id) {
	$options['category_id'] = $category_id;
}

$result = import_google_doc_to_post($doc_url, $options);

if (is_wp_error($result)) {
	echo "ERROR: " . $result->get_error_message() . "\n";
	exit(1);
}

$post_id = $result['post_id'];

// Post-process: normalize ALL-CAPS Norwegian headings to sentence case,
// strip leading numbering from h2, and remove redundant <u> wrappers inside
// links (theme already underlines via CSS).
$post = get_post($post_id);
$cleaned = styrereferat_clean_headings($post->post_content);
$cleaned = styrereferat_unwrap_link_underlines($cleaned);

if ($cleaned !== $post->post_content) {
	wp_update_post([
		'ID'           => $post_id,
		'post_content' => $cleaned,
	]);
}

// Build edit URL manually — get_edit_post_link() returns empty in wp-cli context
// because there is no logged-in user to check capabilities against.
$edit_url = admin_url("post.php?post={$post_id}&action=edit");

echo "POST_ID: {$post_id}\n";
echo "TITLE: {$result['title']}\n";
echo "EDIT_URL: {$edit_url}\n";
