/**
 * Tunnel-client profile generator.
 *
 * Emits the verified v0.0.11 profile YAML (config_version: 1) with the
 * control-plane, health and MCP sections. Secrets are always file: references
 * — never literal values. Proxy is intentionally NOT baked into the YAML:
 * Phase 0 verified the explicit `--http-proxy` run flag, which the process
 * runtime passes as a structured argv element instead.
 */
import { mkdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

export interface ProfileInput {
  controlPlaneBaseUrl: string;
  tunnelId: string;
  runtimeApiKeyRef: string;
  mcpAuthorizationRef: string;
  bridgeUrl: string;
  /** e.g. 127.0.0.1:0 (ephemeral loopback port). */
  healthListenAddr: string;
  healthUrlFile: string;
  logFile: string;
  logLevel: string;
}

function yamlScalar(value: string | number | boolean): string {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return String(value);
  return (
    '"' +
    value
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/\n/g, '\\n')
      .replace(/\r/g, '\\r') +
    '"'
  );
}

/** Build the profile YAML text for a validated input. */
export function buildProfileYaml(input: ProfileInput): string {
  const lines: string[] = [];
  lines.push('config_version: 1');
  lines.push('control_plane:');
  lines.push('  base_url: ' + yamlScalar(input.controlPlaneBaseUrl));
  lines.push('  tunnel_id: ' + yamlScalar(input.tunnelId));
  lines.push('  api_key: ' + yamlScalar(input.runtimeApiKeyRef));
  lines.push('health:');
  lines.push('  listen_addr: ' + yamlScalar(input.healthListenAddr));
  lines.push('  url_file: ' + yamlScalar(input.healthUrlFile));
  lines.push('admin_ui:');
  lines.push('  open_browser: false');
  lines.push('log:');
  lines.push('  level: ' + yamlScalar(input.logLevel));
  lines.push('  format: json');
  lines.push('  file: ' + yamlScalar(input.logFile));
  lines.push('mcp:');
  lines.push('  server_urls:');
  lines.push('    - channel: main');
  lines.push('      url: ' + yamlScalar(input.bridgeUrl));
  lines.push('  extra_headers:');
  lines.push('    Authorization: ' + yamlScalar(input.mcpAuthorizationRef));
  return lines.join('\n') + '\n';
}

export class ProfileGenerator {
  private readonly profilesDir: string;

  constructor(profilesDir: string) {
    this.profilesDir = profilesDir;
  }

  get directory(): string {
    return this.profilesDir;
  }

  profilePath(profileName: string): string {
    return join(this.profilesDir, profileName.replace(/[^A-Za-z0-9._-]/g, '_') + '.yaml');
  }

  /** Write the profile atomically (temp + rename) and return its path. */
  write(profileName: string, input: ProfileInput): string {
    const dir = this.profilesDir;
    mkdirSync(dir, { recursive: true });
    const target = this.profilePath(profileName);
    const tmp = join(dir, `${profileName}.${process.pid}.tmp`);
    writeFileSync(tmp, buildProfileYaml(input), 'utf8');
    try {
      renameSync(tmp, target);
    } catch (error) {
      rmSync(tmp, { force: true });
      throw error;
    }
    return target;
  }
}
