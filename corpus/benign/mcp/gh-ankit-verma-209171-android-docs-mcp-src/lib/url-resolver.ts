/**
 * Resolves fully-qualified class names (FQCN) to developer.android.com URLs.
 *
 * Examples:
 *   android.app.Activity         → /reference/android/app/Activity
 *   androidx.compose.ui.Modifier → /reference/kotlin/androidx/compose/ui/Modifier
 *   java.lang.String             → /reference/java/lang/String
 */

const BASE_URL = "https://developer.android.com";

export type Language = "java" | "kotlin";

/**
 * Detect if a FQCN belongs to AndroidX (Jetpack) libraries.
 */
function isAndroidX(fqcn: string): boolean {
    return fqcn.startsWith("androidx.");
}

/**
 * Detect if a FQCN belongs to the Android platform SDK.
 */
function isPlatformApi(fqcn: string): boolean {
    return (
        fqcn.startsWith("android.") ||
        fqcn.startsWith("dalvik.") ||
        fqcn.startsWith("org.apache.") ||
        fqcn.startsWith("org.json.") ||
        fqcn.startsWith("org.xml.") ||
        fqcn.startsWith("org.xmlpull.") ||
        fqcn.startsWith("javax.")
    );
}

/**
 * Resolve a FQCN to its developer.android.com documentation URL.
 *
 * @param fqcn - Fully qualified class name (e.g., "android.app.Activity")
 * @param language - "java" or "kotlin". Defaults: kotlin for AndroidX, java for platform.
 * @returns Full URL to the documentation page
 */
export function resolveClassUrl(fqcn: string, language?: Language): string {
    // Convert dots to slashes for the URL path
    const pathSegments = fqcn.replace(/\./g, "/");

    // Determine default language based on package
    const lang = language ?? (isAndroidX(fqcn) ? "kotlin" : "java");

    if (lang === "kotlin") {
        return `${BASE_URL}/reference/kotlin/${pathSegments}`;
    }

    return `${BASE_URL}/reference/${pathSegments}`;
}

/**
 * Resolve a package name to its package summary URL.
 *
 * @param packageName - e.g., "android.app" or "androidx.compose.ui"
 * @param language - "java" or "kotlin"
 * @returns Full URL to the package summary page
 */
export function resolvePackageUrl(
    packageName: string,
    language?: Language,
): string {
    const pathSegments = packageName.replace(/\./g, "/");
    const lang = language ?? (isAndroidX(packageName) ? "kotlin" : "java");

    if (lang === "kotlin") {
        return `${BASE_URL}/reference/kotlin/${pathSegments}/package-summary`;
    }

    return `${BASE_URL}/reference/${pathSegments}/package-summary`;
}

/**
 * Get the URL for a package index listing page.
 *
 * @param type - "platform" for android.*, "androidx" for Jetpack libraries
 * @param language - "java" or "kotlin"
 */
export function getPackageIndexUrl(
    type: "platform" | "androidx" = "platform",
    language: Language = "java",
): string {
    if (type === "androidx") {
        return language === "kotlin"
            ? `${BASE_URL}/reference/kotlin/androidx/packages`
            : `${BASE_URL}/reference/androidx/packages`;
    }

    return language === "kotlin"
        ? `${BASE_URL}/reference/kotlin/packages`
        : `${BASE_URL}/reference/packages`;
}

/**
 * Get the URL for Jetpack library release notes.
 *
 * @param library - Library name, e.g., "compose", "navigation", "lifecycle"
 */
export function getReleaseNotesUrl(library: string): string {
    return `${BASE_URL}/jetpack/androidx/releases/${library.toLowerCase()}`;
}

/**
 * Build a search URL for Android developer docs.
 *
 * @param query - Search query string
 */
export function getSearchUrl(query: string): string {
    return `${BASE_URL}/s/results?q=${encodeURIComponent(query)}`;
}

/**
 * Check if a given string looks like a FQCN.
 */
export function isFqcn(input: string): boolean {
    return /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.[A-Z]\w*$/.test(input);
}
