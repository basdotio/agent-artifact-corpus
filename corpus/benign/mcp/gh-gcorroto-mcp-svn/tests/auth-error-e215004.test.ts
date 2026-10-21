import { describe, it, expect, beforeEach } from '@jest/globals';
import { SvnService } from '../tools/svn-service.js';
import { SvnError } from '../common/types.js';

describe('E215004 Authentication Error Handling', () => {
  let svnService: SvnService;

  beforeEach(() => {
    svnService = new SvnService({
      workingDirectory: '/tmp/non-existent-svn-repo',
      timeout: 5000
    });
  });

  describe('categorizeError for E215004', () => {
    it('should detect E215004 error code and provide specific guidance', () => {
      const mockError = {
        message: 'svn: E215004: No more credentials or we tried too many times. Authentication failed',
        code: 1
      };

      // Use reflection to access private method for testing
      const service = svnService as any;
      const result = service.categorizeError(mockError, 'test command');

      expect(result.message).toContain('Too many failed authentication attempts');
      expect(result.suggestion).toContain('Clear the SVN credentials cache');
      expect(result.suggestion).toContain('SVN_USERNAME and SVN_PASSWORD');
    });

    it('should detect "No more credentials" text and provide specific guidance', () => {
      const mockError = {
        message: 'svn: Authentication failed: No more credentials available',
        code: 1
      };

      const service = svnService as any;
      const result = service.categorizeError(mockError, 'test command');

      expect(result.message).toContain('Too many failed authentication attempts');
      expect(result.suggestion).toContain('Clear the SVN credentials cache');
    });

    it('should detect "we tried too many times" text and provide specific guidance', () => {
      const mockError = {
        message: 'svn: Authentication failed: we tried too many times',
        code: 1
      };

      const service = svnService as any;
      const result = service.categorizeError(mockError, 'test command');

      expect(result.message).toContain('Too many failed authentication attempts');
      expect(result.suggestion).toContain('Clear the SVN credentials cache');
    });

    it('should still handle generic authentication errors', () => {
      const mockError = {
        message: 'svn: E170001: Authentication failed',
        code: 1
      };

      const service = svnService as any;
      const result = service.categorizeError(mockError, 'test command');

      expect(result.message).toContain('Authentication error');
      expect(result.suggestion).toContain('Verify your SVN credentials');
      expect(result.suggestion).not.toContain('Clear the SVN credentials cache');
    });
  });

  describe('clearCredentials function', () => {
    it('should provide clearCredentials method', () => {
      expect(typeof svnService.clearCredentials).toBe('function');
    });

    it('should return a promise when calling clearCredentials', async () => {
      const result = svnService.clearCredentials();
      expect(result).toBeInstanceOf(Promise);
      
      // Wait for the promise to resolve (it will likely fail in test environment)
      try {
        const response = await result;
        // If it succeeds, it should have the expected structure
        expect(response).toHaveProperty('success');
        expect(response).toHaveProperty('command');
      } catch (error) {
        // If it fails, that's expected in test environment
        expect(error).toBeDefined();
      }
    });
  });
});