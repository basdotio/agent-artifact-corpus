export interface VersionCheckResult {
  hasUpdate: boolean;
  currentVersion: string;
  latestVersion: string;
  updateCommand: string;
}

export const CURRENT_VERSION = "1.0.0";
const PACKAGE_NAME = "@tusharjain-19/deploy-mcp";

export async function checkForUpdates(): Promise<VersionCheckResult> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`https://registry.npmjs.org/${PACKAGE_NAME}/latest`, {
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      return {
        hasUpdate: false,
        currentVersion: CURRENT_VERSION,
        latestVersion: CURRENT_VERSION,
        updateCommand: `npx ${PACKAGE_NAME}@latest setup`
      };
    }

    const data = await response.json();
    const latestVersion = data.version || CURRENT_VERSION;

    const hasUpdate = isNewerVersion(CURRENT_VERSION, latestVersion);

    return {
      hasUpdate,
      currentVersion: CURRENT_VERSION,
      latestVersion,
      updateCommand: `npm install -g ${PACKAGE_NAME}@latest`
    };
  } catch (error) {
    return {
      hasUpdate: false,
      currentVersion: CURRENT_VERSION,
      latestVersion: CURRENT_VERSION,
      updateCommand: `npx ${PACKAGE_NAME}@latest setup`
    };
  }
}

function isNewerVersion(current: string, latest: string): boolean {
  const cParts = current.split('.').map(Number);
  const lParts = latest.split('.').map(Number);

  for (let i = 0; i < 3; i++) {
    const c = cParts[i] || 0;
    const l = lParts[i] || 0;
    if (l > c) return true;
    if (l < c) return false;
  }
  return false;
}
