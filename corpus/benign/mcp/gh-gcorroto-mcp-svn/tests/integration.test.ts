import { describe, it, expect, beforeAll } from '@jest/globals';
import { SvnService } from '../tools/svn-service';
import { createSvnConfig, validateSvnInstallation } from '../common/utils';

describe('SVN MCP Integration Tests', () => {
  let svnService: SvnService;
  let svnAvailable: boolean;

  beforeAll(async () => {
    const config = createSvnConfig();
    svnService = new SvnService(config);
    svnAvailable = await validateSvnInstallation(config);
  });

  describe('SVN Installation', () => {
    it('should detect if SVN is available', async () => {
      // This test does not fail when SVN is unavailable, it only reports the status
      console.log(`SVN Available: ${svnAvailable}`);
      expect(typeof svnAvailable).toBe('boolean');
    });
  });

  describe('Health Check', () => {
    it('should perform health check without errors', async () => {
      const result = await svnService.healthCheck();
      
      expect(result).toBeDefined();
      expect(result.workingDirectory).toBeDefined();
      expect(typeof result.success).toBe('boolean');
      
      // The command is 'health-check' when SVN is available or 'svn --version' when it is not
      expect(['health-check', 'svn --version']).toContain(result.command);
      
      if (result.success && result.data) {
        expect(typeof result.data.svnAvailable).toBe('boolean');
        if (result.data.svnAvailable) {
          expect(result.data.version).toBeDefined();
          expect(typeof result.data.workingCopyValid).toBe('boolean');
          expect(typeof result.data.repositoryAccessible).toBe('boolean');
        }
      }
    });
  });

  describe('Configuration', () => {
    it('should create default SVN configuration', () => {
      const config = createSvnConfig();
      
      expect(config).toBeDefined();
      expect(config.svnPath).toBeDefined();
      expect(config.workingDirectory).toBeDefined();
      expect(config.timeout).toBeGreaterThan(0);
    });

    it('should create SVN configuration with overrides', () => {
      const overrides = {
        svnPath: 'custom-svn',
        workingDirectory: '/custom/path',
        timeout: 5000
      };
      
      const config = createSvnConfig(overrides);
      
      expect(config.svnPath).toBe(overrides.svnPath);
      expect(config.workingDirectory).toBe(overrides.workingDirectory);
      expect(config.timeout).toBe(overrides.timeout);
    });
  });

  describe('SVN Service', () => {
    it('should create SVN service instance', () => {
      expect(svnService).toBeDefined();
      expect(svnService).toBeInstanceOf(SvnService);
    });
  });

  // Only run tests that require SVN when it is available
  describe('SVN Commands (requires SVN installation)', () => {
    beforeAll(() => {
      if (!svnAvailable) {
        console.warn('SVN not available, skipping SVN command tests');
      }
    });

    it('should handle SVN info gracefully when not in working copy', async () => {
      if (!svnAvailable) {
        console.log('Skipping SVN info test - SVN not available');
        return;
      }

      try {
        await svnService.getInfo();
        // If we got here, we are inside a valid working copy
        expect(true).toBe(true);
      } catch (error: any) {
        // It is expected to fail when we are not inside a working copy
        expect(error.message).toContain('Failed to get SVN info');
      }
    });

    it('should handle SVN status gracefully when not in working copy', async () => {
      if (!svnAvailable) {
        console.log('Skipping SVN status test - SVN not available');
        return;
      }

      try {
        await svnService.getStatus();
        // If we got here, we are inside a valid working copy
        expect(true).toBe(true);
      } catch (error: any) {
        // It is expected to fail when we are not inside a working copy
        expect(error.message).toContain('Failed to get SVN status');
      }
    });
  });
}); 