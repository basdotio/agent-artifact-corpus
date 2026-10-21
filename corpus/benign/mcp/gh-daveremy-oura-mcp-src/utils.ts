export function formatLocalDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function today(): string {
  return formatLocalDate(new Date());
}

/**
 * The calendar day after `date` (both `YYYY-MM-DD`).
 *
 * Pure UTC arithmetic on purpose: parsing a bare `YYYY-MM-DD` yields UTC
 * midnight, so reading it back with local getters can shift the day for
 * anyone west of UTC. Used to build the exclusive upper bound in
 * {@link OuraClient.requestDay}.
 */
export function nextDay(date: string): string {
  const [y, m, d] = date.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + 1));
  return `${t.getUTCFullYear()}-${String(t.getUTCMonth() + 1).padStart(2, "0")}-${String(
    t.getUTCDate()
  ).padStart(2, "0")}`;
}
