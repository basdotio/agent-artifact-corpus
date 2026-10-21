import { BassfishError } from '../domain.js';
export const tursoVersion = '0.7.2';
/** Bun implements getReport(), but no runtime guarantees it; a missing report is not musl. */
function glibcVersionRuntime(): string | undefined {
  try {
    return (
      process.report?.getReport() as { header?: { glibcVersionRuntime?: string } } | undefined
    )?.header?.glibcVersionRuntime;
  } catch {
    return undefined;
  }
}
export function requireSupportedPlatform(
  platform: string = process.platform,
  arch: string = process.arch,
  glibc = glibcVersionRuntime(),
): void {
  if (platform === 'darwin' && arch === 'arm64') return;
  if (platform === 'linux' && ['arm64', 'x64'].includes(arch) && glibc) return;
  throw new BassfishError(
    'UNSUPPORTED_PLATFORM',
    'Bassfish supports Apple Silicon macOS and glibc Linux on arm64 or x64. This release has no Intel Mac, musl Linux, or Windows build.',
  );
}
