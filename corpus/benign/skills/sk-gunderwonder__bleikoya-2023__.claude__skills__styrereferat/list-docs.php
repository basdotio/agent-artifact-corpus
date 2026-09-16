<?php
/**
 * List recent Google Docs from the Shared Drive, optionally filtered to a folder.
 *
 * Usage:
 *   wp eval-file .claude/skills/styrereferat/list-docs.php [folder_name_or_id] [limit]
 *
 * If the first argument matches a Drive ID pattern (long alphanumeric +/-/_),
 * it is treated as a folder ID directly. Otherwise it is looked up by name.
 *
 * Output: TSV (id<tab>name<tab>modified) — one doc per line, newest first.
 */

use Google\Service\Drive;

$folder_name = $args[0] ?? null;
$limit = isset($args[1]) ? (int) $args[1] : 20;

require_once get_stylesheet_directory() . '/vendor/autoload.php';
require_once get_stylesheet_directory() . '/includes/google/sheets-export.php';

$client = get_google_client();
if (is_wp_error($client)) {
	echo "ERROR: " . $client->get_error_message() . "\n";
	exit(1);
}

$shared_drive_id = $_ENV['GOOGLE_SHARED_DRIVE_ID'] ?? getenv('GOOGLE_SHARED_DRIVE_ID') ?: '';
if (empty($shared_drive_id)) {
	echo "ERROR: GOOGLE_SHARED_DRIVE_ID not configured\n";
	exit(1);
}

$drive_service = new Drive($client);

$query = "mimeType = 'application/vnd.google-apps.document' and trashed = false";

if (!empty($folder_name)) {
	// If the arg looks like a Drive ID (long, no spaces, only alphanumeric/-/_),
	// use it directly. Otherwise resolve by name.
	if (preg_match('/^[a-zA-Z0-9_-]{20,}$/', $folder_name)) {
		$folder_id = $folder_name;
	} else {
		$folder_query = "name = '" . addslashes($folder_name) . "' and mimeType = 'application/vnd.google-apps.folder' and trashed = false";
		$folders = $drive_service->files->listFiles([
			'q'                         => $folder_query,
			'driveId'                   => $shared_drive_id,
			'corpora'                   => 'drive',
			'includeItemsFromAllDrives' => true,
			'supportsAllDrives'         => true,
			'fields'                    => 'files(id, name)',
		]);

		$found = $folders->getFiles();
		if (empty($found)) {
			echo "ERROR: folder '$folder_name' not found in Shared Drive\n";
			exit(1);
		}

		$folder_id = $found[0]->getId();
	}

	$query .= " and '$folder_id' in parents";
}

try {
	$results = $drive_service->files->listFiles([
		'q'                         => $query,
		'driveId'                   => $shared_drive_id,
		'corpora'                   => 'drive',
		'includeItemsFromAllDrives' => true,
		'supportsAllDrives'         => true,
		'orderBy'                   => 'modifiedTime desc',
		'pageSize'                  => $limit,
		'fields'                    => 'files(id, name, modifiedTime)',
	]);

	foreach ($results->getFiles() as $file) {
		echo $file->getId() . "\t" . $file->getName() . "\t" . $file->getModifiedTime() . "\n";
	}
} catch (Exception $e) {
	echo "ERROR: " . $e->getMessage() . "\n";
	exit(1);
}
