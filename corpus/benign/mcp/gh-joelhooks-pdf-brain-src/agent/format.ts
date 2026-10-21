/**
 * Formatting utilities for HATEOAS hint blocks.
 */

/**
 * Strip emoji characters from text (for cleaner machine-readable output).
 */
export function stripEmoji(text: string): string {
  return text
    .replace(
      /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{FE00}-\u{FE0F}\u{200D}\u{20E3}\u{E0020}-\u{E007F}]/gu,
      ""
    )
    .replace(/\s{2,}/g, " ")
    .trim();
}

/**
 * Format hint strings into a markdown blockquote block.
 *
 * Output:
 * ```
 * ---
 * > **Next Actions**
 * > - `cmd` -- description
 * > ...
 * >
 * > pdf-brain: N documents, M concepts. `pdf-brain --help` for full reference.
 * ```
 */
export function formatHintBlock(
  hints: string[],
  stats?: { documents: number; concepts?: number }
): string {
  if (hints.length === 0) return "";

  const lines: string[] = [];
  lines.push("---");
  lines.push("> **Next Actions**");
  for (const hint of hints) {
    lines.push(`> - ${hint}`);
  }
  lines.push(">");

  if (stats) {
    const parts = [`${stats.documents} documents`];
    if (stats.concepts !== undefined && stats.concepts > 0) {
      parts.push(`${stats.concepts} concepts`);
    }
    lines.push(
      `> pdf-brain: ${parts.join(", ")}. \`pdf-brain --help\` for full reference.`
    );
  } else {
    lines.push(
      `> \`pdf-brain --help\` for full reference.`
    );
  }

  return "\n" + lines.join("\n");
}
