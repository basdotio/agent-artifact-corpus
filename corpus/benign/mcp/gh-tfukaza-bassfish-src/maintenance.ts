/** One scheduled operation at a time; a slow sweep cannot accumulate timer jobs. */
export function startMaintenance(
  step: () => Promise<void>,
  failed: (error: unknown) => void,
  report: (recovered: boolean) => void,
): () => void {
  let stopped = false;
  let backoff = 250;
  let deferred = false;
  let lastWarning = 0;
  let timer: NodeJS.Timeout;
  const run = async () => {
    let wait = 250;
    try {
      await step();
      if (deferred) report(true);
      deferred = false;
      backoff = 250;
    } catch (error) {
      if (stopped) return;
      if ((error as { code?: string }).code !== 'STORAGE_BUSY') {
        failed(error);
        return;
      }
      if (!deferred || Date.now() - lastWarning >= 60_000) {
        report(false);
        lastWarning = Date.now();
      }
      deferred = true;
      wait = backoff / 2 + (Math.random() * backoff) / 2;
      backoff = Math.min(5000, backoff * 2);
    }
    if (!stopped)
      timer = setTimeout(() => {
        void run();
      }, wait);
  };
  timer = setTimeout(() => {
    void run();
  }, 250);
  return () => {
    stopped = true;
    clearTimeout(timer);
  };
}
