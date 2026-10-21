/**
 * Shared notification hook — provides transient message state for widgets.
 * Renders as an inline MessageBar (not Toast, which gets clipped in iframes).
 */
import { useState, useCallback } from "react";

export interface Notification {
  message: string;
  intent: "success" | "error";
}

export function useNotification(durationMs = 4000) {
  const [notification, setNotification] = useState<Notification | null>(null);

  const showNotification = useCallback(
    (message: string, intent: "success" | "error") => {
      setNotification({ message, intent });
      setTimeout(() => setNotification(null), durationMs);
    },
    [durationMs],
  );

  return { notification, showNotification } as const;
}
