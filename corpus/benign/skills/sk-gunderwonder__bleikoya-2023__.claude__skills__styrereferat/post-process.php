<?php
/**
 * Post-processing for imported styrereferat content.
 *
 * - Convert ALL-CAPS headings to Norwegian sentence case, preserving
 *   recognized proper nouns (Bleikøya, Vel, etc).
 * - Strip leading numbering from h2 headings (e.g. "1. Foo" → "Foo").
 */

/**
 * Proper nouns to re-capitalize after lowercasing.
 * Months and weekdays stay lowercase in Norwegian.
 */
function styrereferat_proper_nouns(): array {
	return [
		'Bleikøya', 'Bleikøyas',
		'Vel', 'Velhuset', 'Velforening',
		'Hovedøya', 'Lindøya', 'Nakholmen', 'Gressholmen', 'Rambergøya',
		'Oslo', 'Norge',
	];
}

/**
 * Normalize a heading string to Norwegian sentence case if it is all caps.
 * Leaves mixed-case headings untouched.
 */
function styrereferat_normalize_case(string $text): string {
	$plain = strip_tags($text);
	$letters = preg_replace('/[^\p{L}]/u', '', $plain);

	if ($letters === '' || mb_strtoupper($letters, 'UTF-8') !== $letters) {
		return $text;
	}

	$text = mb_strtolower($text, 'UTF-8');

	$text = preg_replace_callback(
		'/^([^\p{L}]*)(\p{L})/u',
		fn($m) => $m[1] . mb_strtoupper($m[2], 'UTF-8'),
		$text
	);

	foreach (styrereferat_proper_nouns() as $word) {
		$lower = mb_strtolower($word, 'UTF-8');
		$text = preg_replace(
			'/(?<!\p{L})' . preg_quote($lower, '/') . '(?!\p{L})/u',
			$word,
			$text
		);
	}

	return $text;
}

/**
 * Promote single-item ordered lists to h2.
 *
 * Google Docs auto-numbered agenda items render as `<ol><li>…</li></ol>`
 * blocks — one per item because paragraphs in between break the list.
 * These are really section headings.
 */
function styrereferat_promote_single_item_lists(string $html): string {
	// Match <ol> with optional attributes, and an optional wp:list block
	// comment that may surround it. Drop both the open/close markers and
	// the inner list-item markers so the result is a clean <h2>.
	return preg_replace_callback(
		'#(?:<!--\s*wp:list[^>]*-->\s*)?<ol\b[^>]*>\s*(?:<!--\s*wp:list-item\s*-->\s*)?<li\b[^>]*>((?:(?!</?li[\s>/]).)*)</li>\s*(?:<!--\s*/wp:list-item\s*-->\s*)?</ol>(?:\s*<!--\s*/wp:list\s*-->)?#is',
		fn($m) => '<!-- wp:heading --><h2 class="wp-block-heading">' . trim($m[1]) . '</h2><!-- /wp:heading -->',
		$html
	);
}

/**
 * Transform headings in HTML.
 */
function styrereferat_clean_headings(string $html): string {
	$html = styrereferat_promote_single_item_lists($html);

	return preg_replace_callback(
		'#<(h[1-6])(\b[^>]*)>(.+?)</\1>#is',
		function ($m) {
			$tag = $m[1];
			$attrs = $m[2];
			$inner = trim($m[3]);

			$inner = styrereferat_normalize_case($inner);

			if ($tag === 'h2') {
				$inner = preg_replace('/^\s*\d+(\.\d+)*[\.\)]?\s+/u', '', $inner);
			}

			return "<{$tag}{$attrs}>{$inner}</{$tag}>";
		},
		$html
	);
}

/**
 * Strip <u> wrappers inside <a> tags.
 *
 * Google Docs renders linked text as underlined and exports the underline
 * as a <u> wrapper inside the <a>. The theme already underlines links via
 * CSS, so the <u> is redundant and produces a double underline.
 */
function styrereferat_unwrap_link_underlines(string $html): string {
	return preg_replace_callback(
		'#<a([^>]*)>(.*?)</a>#is',
		function ($m) {
			$inner = preg_replace('#</?u\b[^>]*>#i', '', $m[2]);
			return '<a' . $m[1] . '>' . $inner . '</a>';
		},
		$html
	);
}
