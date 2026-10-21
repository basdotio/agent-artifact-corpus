import { describe, it, expect } from '@jest/globals';
import { validatePath, validateSvnUrl } from '../common/utils';

describe('SVN URL Validation Tests', () => {
  describe('validateSvnUrl function', () => {
    it('should accept valid SVN URLs', () => {
      expect(validateSvnUrl('http://octopus/svnayg/repo/crm-boot')).toBe(true);
      expect(validateSvnUrl('https://svn.example.com/repo/trunk')).toBe(true);
      expect(validateSvnUrl('svn://server.example.com/repo')).toBe(true);
      expect(validateSvnUrl('file:///local/repo/path')).toBe(true);
    });

    it('should reject invalid URLs', () => {
      expect(validateSvnUrl('ftp://example.com/repo')).toBe(false);
      expect(validateSvnUrl('local/path/to/file')).toBe(false);
      expect(validateSvnUrl('C:\\Windows\\path')).toBe(false);
      expect(validateSvnUrl('')).toBe(false);
    });
  });

  describe('validatePath vs validateSvnUrl', () => {
    it('URLs should be rejected by validatePath but accepted by validateSvnUrl', () => {
      const testUrl = 'http://octopus/svnayg/repo/crm-boot';
      expect(validatePath(testUrl)).toBe(false); // Current behavior - path validation rejects URLs
      expect(validateSvnUrl(testUrl)).toBe(true); // URL validation accepts URLs
    });

    it('Local paths should be accepted by validatePath but rejected by validateSvnUrl', () => {
      const testPath = 'local/path/to/file';
      expect(validatePath(testPath)).toBe(true); // Path validation accepts local paths
      expect(validateSvnUrl(testPath)).toBe(false); // URL validation rejects local paths
    });

    it('Windows paths should be accepted by validatePath but rejected by validateSvnUrl', () => {
      const testPath = 'C:\\workspaces\\project';
      expect(validatePath(testPath)).toBe(true); // Path validation accepts Windows paths
      expect(validateSvnUrl(testPath)).toBe(false); // URL validation rejects Windows paths
    });
  });
});