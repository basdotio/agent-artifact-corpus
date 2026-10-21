import { existsSync, writeFileSync, readFileSync, mkdirSync } from 'fs';
import { join, basename } from 'path';
import { createHash } from 'crypto';
import config from '../config.js';

interface RepoConfig {
  url: string;
  localPath?: string;
  lastAccessed: number;
  type: 'local' | 'remote' | 'cached';
  branch?: string;
}

export class RepositoryConfigManager {
  private configDir: string;

  constructor() {
    this.configDir = config.REPO_CONFIG_DIR;
    if (!existsSync(this.configDir)) {
      mkdirSync(this.configDir, { recursive: true });
    }
  }

  private getConfigPath(repoUrl: string): string {
    const hash = createHash('md5').update(repoUrl).digest('hex');
    return join(this.configDir, `${hash}.json`);
  }

  private sanitizeLocalPath(repoUrl: string): string | null {
    if (repoUrl.startsWith('file://')) {
      const localPath = repoUrl.replace('file://', '');
      return existsSync(localPath) ? localPath : null;
    }
    return null;
  }

  getRepositoryPath(repoUrl: string, branch?: string): { path: string; config: RepoConfig } {
    const localPath = this.sanitizeLocalPath(repoUrl);
    
    if (localPath) {
      const repoConfig: RepoConfig = {
        url: repoUrl,
        localPath,
        lastAccessed: Date.now(),
        type: 'local',
        branch
      };
      
      this.saveConfig(repoUrl, repoConfig);
      return { path: localPath, config: repoConfig };
    }

    const configPath = this.getConfigPath(repoUrl);
    let repoConfig: RepoConfig;

    if (existsSync(configPath)) {
      try {
        repoConfig = JSON.parse(readFileSync(configPath, 'utf8'));
        repoConfig.lastAccessed = Date.now();
      } catch {
        repoConfig = this.createRemoteConfig(repoUrl, branch);
      }
    } else {
      repoConfig = this.createRemoteConfig(repoUrl, branch);
    }

    this.saveConfig(repoUrl, repoConfig);
    return { path: repoConfig.localPath || '', config: repoConfig };
  }

  private createRemoteConfig(repoUrl: string, branch?: string): RepoConfig {
    const repoName = basename(repoUrl.replace('.git', ''));
    const cacheDir = join(this.configDir, 'cache');
    
    if (!existsSync(cacheDir)) {
      mkdirSync(cacheDir, { recursive: true });
    }

    return {
      url: repoUrl,
      localPath: join(cacheDir, repoName),
      lastAccessed: Date.now(),
      type: 'remote',
      branch
    };
  }

  private saveConfig(repoUrl: string, config: RepoConfig): void {
    const configPath = this.getConfigPath(repoUrl);
    writeFileSync(configPath, JSON.stringify(config, null, 2));
  }

  isLocalRepository(repoUrl: string): boolean {
    return repoUrl.startsWith('file://');
  }

  needsCloning(repoUrl: string): boolean {
    if (this.isLocalRepository(repoUrl)) {
      return false;
    }
    
    const { config } = this.getRepositoryPath(repoUrl);
    return !config.localPath || !existsSync(config.localPath);
  }

  getRepoType(repoUrl: string): 'local' | 'remote' {
    return this.isLocalRepository(repoUrl) ? 'local' : 'remote';
  }
}

export const repoConfigManager = new RepositoryConfigManager();
