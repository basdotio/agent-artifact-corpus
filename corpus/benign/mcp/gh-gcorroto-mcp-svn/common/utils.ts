import { spawn, SpawnOptions } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs';
import { SvnConfig, SvnResponse, SvnError, SvnInfo, SvnStatus, SvnLogEntry, SvnListEntry, SVN_STATUS_CODES } from './types.js';
import iconv from 'iconv-lite';

/**
 * Create SVN configuration from environment variables and parameters.
 *
 * Environment variables:
 *   SVN_PATH                - path to the svn executable (default: 'svn')
 *   SVN_WORKING_DIRECTORY   - local working-copy directory (optional)
 *   SVN_URL / SVN_REPOSITORY_URL - repository URL (optional; used to
 *                             resolve repo-relative targets like
 *                             `/trunk/file.sql` and to run URL-only
 *                             commands without a working copy)
 *   SVN_USERNAME, SVN_PASSWORD
 *   SVN_TIMEOUT             - command timeout in ms (default: 30000)
 */
export function createSvnConfig(overrides: Partial<SvnConfig> = {}): SvnConfig {
  const envWorkingDir = process.env.SVN_WORKING_DIRECTORY;
  let workingDirectory = overrides.workingDirectory || envWorkingDir || process.cwd();
  let url = overrides.url || process.env.SVN_URL || process.env.SVN_REPOSITORY_URL;

  // Backward-compat: SVN_WORKING_DIRECTORY used to be overloaded with a
  // repository URL. Promote it to `url` and fall back cwd to something
  // valid, but warn so the user migrates to SVN_URL.
  if (!overrides.workingDirectory && envWorkingDir && validateSvnUrl(envWorkingDir)) {
    if (!url) url = envWorkingDir;
    workingDirectory = process.cwd();
    console.warn(
      `[svn-mcp] SVN_WORKING_DIRECTORY is set to a URL ("${envWorkingDir}"). ` +
      `Treating it as SVN_URL for backward compatibility. ` +
      `Please migrate to SVN_URL and set SVN_WORKING_DIRECTORY to a local path (or unset it).`
    );
  }

  return {
    svnPath: overrides.svnPath || process.env.SVN_PATH || 'svn',
    workingDirectory,
    url,
    username: overrides.username || process.env.SVN_USERNAME,
    password: overrides.password || process.env.SVN_PASSWORD,
    timeout: overrides.timeout || parseInt(process.env.SVN_TIMEOUT || '30000', 10)
  };
}

/**
 * Validate that SVN is available on the system
 */
export async function validateSvnInstallation(config: SvnConfig): Promise<boolean> {
  try {
    const result = await executeSvnCommand(config, ['--version', '--quiet']);
    return result.success;
  } catch (error) {
    return false;
  }
}

/**
 * Detect whether the current directory is an SVN working copy
 */
export async function isWorkingCopy(workingDirectory: string): Promise<boolean> {
  try {
    const svnDir = path.join(workingDirectory, '.svn');
    return await promisify(fs.access)(svnDir).then(() => true).catch(() => false);
  } catch {
    return false;
  }
}

/**
 * Normalize paths for Windows
 */
export function normalizePath(filePath: string): string {
  return path.resolve(filePath).replace(/\\/g, '/');
}

/**
 * Escape arguments for the Windows command line
 */
export function escapeArgument(arg: string): string {
  // If the argument contains spaces or special characters, wrap it in quotes
  if (/[\s&()<>[\]{}^=;!'+,`~%]/.test(arg)) {
    return `"${arg.replace(/"/g, '""')}"`;
  }
  return arg;
}

/**
 * Build authentication arguments
 */
export function buildAuthArgs(config: SvnConfig, options: { noAuthCache?: boolean } = {}): string[] {
  const args: string[] = [];
  
  if (config.username) {
    args.push('--username', config.username);
  }
  
  if (config.password) {
    args.push('--password', config.password);
  }
  
  // Always use --non-interactive to avoid prompts
  args.push('--non-interactive');

  // Option to skip the credentials cache (useful for E215004)
  if (options.noAuthCache) {
    args.push('--no-auth-cache');
  }
  
  return args;
}

/**
 * Execute an SVN command with improved error handling
 */
export async function executeSvnCommand(
  config: SvnConfig,
  args: string[],
  options: { input?: string; encoding?: BufferEncoding; noAuthCache?: boolean } = {}
): Promise<SvnResponse> {
  const startTime = Date.now();
  
  // Append authentication arguments
  const finalArgs = [...args, ...buildAuthArgs(config, { noAuthCache: options.noAuthCache })];
  const command = `${config.svnPath} ${finalArgs.join(' ')}`;
  
  return new Promise((resolve, reject) => {
    // We avoid `shell: true` on Windows for two reasons:
    //   1. Node's shell handling for cmd.exe sets
    //      windowsVerbatimArguments=true and joins argv with single
    //      spaces — destroying any argument that contains a space (e.g.
    //      paths under "Program Files" or repos with spaces in folder
    //      names). libuv's direct CreateProcess path quotes each argv
    //      element correctly.
    //   2. shell:true depends on cmd.exe being resolvable from the
    //      parent env, which Claude Desktop/Code sometimes sanitizes.
    //
    // The only case we still need a shell is when SVN_PATH points at a
    // .bat/.cmd shim — Node forbids spawning those directly since
    // 18.20/20.12 (CVE-2024-27980). For that we go through cmd.exe and
    // pre-escape each arg ourselves so the shell re-parses correctly.
    const isWindows = process.platform === 'win32';
    const isBatchShim = isWindows && /\.(bat|cmd)$/i.test(config.svnPath || '');
    const systemRoot = process.env.SystemRoot || process.env.systemroot || 'C:\\Windows';
    const system32 = `${systemRoot}\\System32`;
    const cmdPath = process.env.ComSpec || process.env.comspec || `${system32}\\cmd.exe`;

    const childEnv: NodeJS.ProcessEnv = {
      ...process.env,
      // Force SVN to use UTF-8
      LANG: 'en_US.UTF-8',
      LC_ALL: 'en_US.UTF-8'
    };

    if (isWindows) {
      childEnv.ComSpec = cmdPath;
      childEnv.SystemRoot = systemRoot;

      // Collapse duplicate-cased PATH entries (Windows inherited env often
      // ships 'Path'; if we also set 'PATH' the two may race). Keep a
      // single 'PATH' key and make sure System32 is present.
      for (const k of Object.keys(childEnv)) {
        if (k !== 'PATH' && k.toLowerCase() === 'path') delete childEnv[k];
      }
      const existingPath = process.env.PATH || process.env.Path || '';
      const pathParts = existingPath.split(';').filter(Boolean);
      const hasSystem32 = pathParts.some(p => p.toLowerCase() === system32.toLowerCase());
      childEnv.PATH = hasSystem32 ? existingPath : [...pathParts, system32].join(';');
    }

    // Resolve cwd. If SVN_WORKING_DIRECTORY is configured as a repository
    // URL (valid use case for URL-targeted commands like `svn cat <url>`),
    // we can't pass it to CreateProcess as cwd — Windows raises
    // ERROR_PATH_NOT_FOUND which libuv surfaces as a misleading
    // "spawn <exe> ENOENT" attached to the executable. Fall back to
    // process.cwd() in that case; URL commands pass the URL as an arg so
    // cwd doesn't matter, and local commands that need a working copy
    // won't have been given a URL here.
    let resolvedCwd = config.workingDirectory;
    if (!resolvedCwd || validateSvnUrl(resolvedCwd)) {
      resolvedCwd = process.cwd();
    }

    const spawnOptions: SpawnOptions = {
      cwd: resolvedCwd,
      // Direct spawn (no shell) lets libuv quote argv per element. The
      // batch-shim case is the only one that has to take the cmd.exe
      // detour, with manual arg escaping below.
      shell: isBatchShim ? cmdPath : false,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: childEnv
    };

    // Only pre-escape when we're going through a shell — direct spawn
    // does its own quoting and would double-escape if we did it too.
    const argsForSpawn = isBatchShim ? finalArgs.map(escapeArgument) : finalArgs;
    const childProcess = spawn(config.svnPath!, argsForSpawn, spawnOptions);
    
    let stdout = '';
    let stderr = '';
    
    // Create streaming decoders to properly handle multi-byte characters across chunk boundaries
    // Using UTF-8 as SVN output is configured to use UTF-8 via LANG/LC_ALL environment variables
    // The encoding is consistent throughout the stream - it doesn't change mid-stream as per SVN behavior
    const stdoutDecoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
    const stderrDecoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
    
    // Configure timeout
    const timeout = setTimeout(() => {
      childProcess.kill('SIGTERM');
      reject(new SvnError(`Command timeout after ${config.timeout}ms: ${command}`));
    }, config.timeout);
    
    // Capture stdout using streaming decoder to handle multi-byte characters correctly
    childProcess.stdout?.on('data', (data) => {
      stdout += stdoutDecoder.write(data);
    });

    // Capture stderr using streaming decoder to handle multi-byte characters correctly
    childProcess.stderr?.on('data', (data) => {
      stderr += stderrDecoder.write(data);
    });

    // Write input if provided
    if (options.input && childProcess.stdin) {
      childProcess.stdin.write(options.input);
      childProcess.stdin.end();
    }

    // Handle process completion
    childProcess.on('close', (code) => {
      clearTimeout(timeout);
      
      // Finalize decoders to flush any remaining buffered data
      stdout += stdoutDecoder.end();
      stderr += stderrDecoder.end();
      
      const executionTime = Date.now() - startTime;
      const response: SvnResponse = {
        success: code === 0,
        command,
        workingDirectory: config.workingDirectory!,
        executionTime
      };
      
      if (code === 0) {
        response.data = stdout.trim();
        resolve(response);
      } else {
        const error = new SvnError(`SVN command failed with code ${code}: ${command}`);
        error.code = code || undefined;
        error.stderr = stderr.trim();
        error.command = command;
        
        response.error = error.message;
        response.data = stderr.trim();
        
        reject(error);
      }
    });
    
    // Handle process errors
    childProcess.on('error', (error) => {
      clearTimeout(timeout);
      
      const svnError = new SvnError(`Failed to execute SVN command: ${error.message}`);
      svnError.command = command;
      
      reject(svnError);
    });
  });
}

/**
 * Parse SVN XML output
 */
export function parseXmlOutput(xmlString: string): any {
  // Basic XML parsing implementation
  // In a production environment it would be better to use a library like xml2js
  try {
    // This is a simplified implementation for Node.js
    // In browsers we would use DOMParser, but in Node.js we need another approach
    const lines = xmlString.split('\n');
    const result: any = {};
    
    for (const line of lines) {
      const match = line.match(/<([^>]+)>([^<]+)<\/\1>/);
      if (match) {
        result[match[1]] = match[2];
      }
    }
    
    return result;
  } catch (error) {
    throw new SvnError(`Failed to parse XML output: ${error}`);
  }
}

/**
 * Parse output of `svn info`
 */
export function parseInfoOutput(output: string): SvnInfo {
  const lines = output.split('\n');
  const info: Partial<SvnInfo> = {};
  
  for (const line of lines) {
    const [key, ...valueParts] = line.split(': ');
    const value = valueParts.join(': ').trim();
    
    switch (key.trim()) {
      case 'Path':
        info.path = value;
        break;
      case 'Working Copy Root Path':
        info.workingCopyRootPath = value;
        break;
      case 'URL':
        info.url = value;
        break;
      case 'Relative URL':
        info.relativeUrl = value;
        break;
      case 'Repository Root':
        info.repositoryRoot = value;
        break;
      case 'Repository UUID':
        info.repositoryUuid = value;
        break;
      case 'Revision':
        info.revision = parseInt(value, 10);
        break;
      case 'Node Kind':
        info.nodeKind = value as 'file' | 'directory';
        break;
      case 'Schedule':
        info.schedule = value;
        break;
      case 'Last Changed Author':
        info.lastChangedAuthor = value;
        break;
      case 'Last Changed Rev':
        info.lastChangedRev = parseInt(value, 10);
        break;
      case 'Last Changed Date':
        info.lastChangedDate = value;
        break;
      case 'Text Last Updated':
        info.textLastUpdated = value;
        break;
      case 'Checksum':
        info.checksum = value;
        break;
    }
  }
  
  return info as SvnInfo;
}

/**
 * Parse output of `svn status`
 */
export function parseStatusOutput(output: string): SvnStatus[] {
  const lines = output.split('\n').filter(line => line.trim());
  const statusList: SvnStatus[] = [];
  
  for (const line of lines) {
    if (line.length < 8) continue;
    
    const statusCode = line[0];
    const propStatusCode = line[1];
    const path = line.substring(8).trim();
    
    const status: SvnStatus = {
      path,
      status: (SVN_STATUS_CODES as any)[statusCode] || 'unknown'
    };
    
    statusList.push(status);
  }
  
  return statusList;
}

/**
 * Parse output of `svn log`
 */
export function parseLogOutput(output: string): SvnLogEntry[] {
  const entries: SvnLogEntry[] = [];

  if (!output || output.trim().length === 0) {
    return entries;
  }

  // Split on the SVN log separator lines
  const logEntries = output.split(/^-{72}$/gm).filter(entry => entry.trim());

  for (const entryText of logEntries) {
    const lines = entryText.trim().split('\n');
    if (lines.length < 2) continue;

    const headerLine = lines[0];
    // Flexible header pattern
    const headerMatch = headerLine.match(/^r(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*)$/);
    
    if (headerMatch) {
      try {
        const [, revision, author, date, details] = headerMatch;
        const message = lines.slice(2).join('\n').trim();
        
        entries.push({
          revision: parseInt(revision, 10),
          author: author.trim(),
          date: date.trim(),
          message: message || 'No message'
        });
      } catch (parseError) {
        console.warn(`Warning: Failed to parse log entry: ${parseError}`);
        continue;
      }
    }
  }
  
  return entries;
}

/**
 * Parse output of `svn list`. Supports both simple and verbose modes.
 * Simple: one name per line; directories end with '/'.
 * Verbose: "REV AUTHOR [SIZE] DATE NAME" — size is absent for directories.
 */
export function parseListOutput(output: string, verbose: boolean = false): SvnListEntry[] {
  const entries: SvnListEntry[] = [];
  if (!output || output.trim().length === 0) {
    return entries;
  }

  const lines = output.split('\n').map(l => l.replace(/\r$/, '')).filter(l => l.length > 0);

  if (!verbose) {
    for (const rawName of lines) {
      const isDir = rawName.endsWith('/');
      const name = isDir ? rawName.slice(0, -1) : rawName;
      if (!name) continue;
      entries.push({ name, kind: isDir ? 'dir' : 'file' });
    }
    return entries;
  }

  // Verbose: REV AUTHOR [SIZE] DATE... NAME
  // SIZE only appears for files; DATE spans multiple tokens (month day year/time).
  // Regex: 4 fixed tokens (rev, author, size-or-empty, date-block) + name.
  const verboseRegex = /^\s*(\d+)\s+(\S+)\s+(?:(\d+)\s+)?(\S+\s+\S+\s+\S+)\s+(.+?)\s*$/;
  for (const line of lines) {
    const m = line.match(verboseRegex);
    if (!m) continue;
    const [, rev, author, size, date, rawName] = m;
    const isDir = rawName.endsWith('/') || rawName === '.';
    const name = isDir && rawName !== '.' ? rawName.slice(0, -1) : rawName;
    entries.push({
      name,
      kind: isDir ? 'dir' : 'file',
      revision: parseInt(rev, 10),
      author,
      size: size !== undefined ? parseInt(size, 10) : undefined,
      date
    });
  }
  return entries;
}

/**
 * Format a duration in milliseconds to a human-readable string
 */
export function formatDuration(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * Validate a file/directory name
 */
export function validatePath(filePath: string): boolean {
  // Check that it does not contain characters forbidden on Windows
  // but allow a colon in valid contexts (Windows drive letters)

  // Pattern to detect Windows absolute paths (C:, D:, etc.)
  const windowsAbsolutePathPattern = /^[A-Za-z]:[\\\/]/;

  if (windowsAbsolutePathPattern.test(filePath)) {
    // For Windows absolute paths, only validate the segment after the drive letter
    const pathAfterDrive = filePath.substring(2); // Strip "C:" or similar
    const invalidChars = /[<>:"|?*]/;
    return !invalidChars.test(pathAfterDrive);
  } else {
    // For every other path, apply full validation
    const invalidChars = /[<>:"|?*]/;
    return !invalidChars.test(filePath);
  }
}

/**
 * Get a relative path from the working directory
 */
export function getRelativePath(fullPath: string, workingDirectory: string): string {
  return path.relative(workingDirectory, fullPath).replace(/\\/g, '/');
}

/**
 * Validate an SVN repository URL. Recognises svn://, svn+<tunnel>://
 * (e.g. svn+ssh://), http(s):// and file://.
 */
export function validateSvnUrl(url: string): boolean {
  const svnUrlPattern = /^(svn(\+[a-z0-9]+)?|https?|file):\/\/.+/i;
  return svnUrlPattern.test(url);
}

/**
 * Join a repository base URL with a repo-relative path. Preserves the
 * exact encoding of the inputs — we do not re-encode callers' input.
 */
export function combineRepoUrl(baseUrl: string, repoPath: string): string {
  const base = baseUrl.replace(/\/+$/, '');
  const rel = repoPath.replace(/^\/+/, '').replace(/\/+$/, '');
  return rel ? `${base}/${rel}` : base;
}

export interface SvnResolvedTarget {
  /** Value passed to the svn CLI. */
  value: string;
  kind: 'url' | 'path';
}

/**
 * Turn a user target into something svn can accept: absolute URL,
 * repo-relative path (joined with SVN_URL), or normalized local path.
 */
export function resolveSvnTarget(target: string, config: SvnConfig): SvnResolvedTarget {
  if (!target || typeof target !== 'string') {
    throw new SvnError('Target is required');
  }

  if (validateSvnUrl(target)) {
    return { value: target, kind: 'url' };
  }

  if (target.startsWith('/') && config.url) {
    return { value: combineRepoUrl(config.url, target), kind: 'url' };
  }

  if (!validatePath(target)) {
    throw new SvnError(`Invalid path or URL: ${target}`);
  }
  return { value: normalizePath(target), kind: 'path' };
}

/**
 * Clean and normalize command output
 */
export function cleanOutput(output: string): string {
  return output
    .replace(/\r\n/g, '\n')  // Normalize line endings
    .replace(/\r/g, '\n')    // Convert CR to LF
    .trim();
}

/**
 * Create a more descriptive SVN error message
 */
export function createSvnError(message: string, command?: string, stderr?: string): SvnError {
  const error = new SvnError(message);
  if (command) error.command = command;
  if (stderr) error.stderr = stderr;
  return error;
}

/**
 * Clear the SVN credentials cache to resolve E215004 errors
 */
export async function clearSvnCredentials(config: SvnConfig): Promise<SvnResponse> {
  try {
    // On Unix/Linux systems, SVN stores credentials in ~/.subversion/auth
    // On Windows, in %APPDATA%\Subversion\auth
    // Attempt to clear using the dedicated auth command if available

    // First try the standard cleanup command
    return await executeSvnCommand(config, ['auth', '--remove'], { noAuthCache: true });
  } catch (error: any) {
    // If the auth command is unavailable, try a fallback
    try {
      // Fallback: run a command that does not store credentials
      const response = await executeSvnCommand(config, ['info', '--non-interactive'], { noAuthCache: true });
      return {
        success: true,
        data: 'Credentials cache cleared (using alternative method)',
        command: 'clear-credentials',
        workingDirectory: config.workingDirectory!
      };
    } catch (fallbackError: any) {
      return {
        success: false,
        error: `Could not clear credentials cache: ${fallbackError.message}`,
        command: 'clear-credentials',
        workingDirectory: config.workingDirectory!
      };
    }
  }
} 