/**
 * Fullscreen toggle hook — manages display mode transitions.
 */
import { useCallback, useState, useEffect } from "react";
import { useMcpApp } from "./McpAppProvider";

export function useFullscreen() {
  const { app, hostContext } = useMcpApp();
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (hostContext?.displayMode === "fullscreen") {
      setIsFullscreen(true);
    }
  }, [hostContext?.displayMode]);

  const toggleFullscreen = useCallback(async () => {
    if (app) {
      const current = hostContext?.displayMode;
      await app.requestDisplayMode({
        mode: current === "fullscreen" ? "inline" : "fullscreen",
      });
      setIsFullscreen((prev) => !prev);
      return;
    }
    // Fallback for local dev
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {}
    setIsFullscreen((prev) => !prev);
  }, [app, hostContext]);

  return { isFullscreen, toggleFullscreen };
}
