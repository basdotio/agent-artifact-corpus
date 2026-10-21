/**
 * Incremental SSE `data:` reader. Feed it response chunks as they stream past;
 * it never holds more than the current partial line.
 */
export function sseTap(onData: (data: any) => void): (chunk: Buffer | string) => void {
  let buf = "";
  return (chunk) => {
    buf += typeof chunk === "string" ? chunk : chunk.toString("utf8");
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, "");
      buf = buf.slice(nl + 1);
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        onData(JSON.parse(payload));
      } catch {
        // partial or non-JSON payload: nothing to extract
      }
    }
  };
}

/** Run a whole SSE body through an adapter's event extractor. Used by tests. */
export function actualFromStream(text: string, pick: (data: any) => string | undefined): string | undefined {
  let found: string | undefined;
  const feed = sseTap((d) => {
    if (found === undefined) found = pick(d);
  });
  feed(text);
  return found;
}
