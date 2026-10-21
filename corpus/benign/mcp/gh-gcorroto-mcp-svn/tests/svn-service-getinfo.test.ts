import { describe, it, expect } from '@jest/globals';
import { SvnService } from '../tools/svn-service';

describe('SvnService getInfo method', () => {
  let svnService: SvnService;

  beforeEach(() => {
    svnService = new SvnService();
  });

  describe('Path validation behavior', () => {
    it('should accept remote URLs after fix', async () => {
      const remoteUrl = 'http://octopus/svnayg/repo/crm-boot';
      
      try {
        await svnService.getInfo(remoteUrl);
      } catch (error: any) {
        // If it fails, it should not be due to path validation
        expect(error.message).not.toContain('Invalid path:');
        expect(error.message).not.toContain('Invalid path or URL:');
        // It might fail for other reasons like network issues or SVN not available
      }
    });

    it('should accept local paths', async () => {
      const localPath = 'local/path/to/file';
      
      // This should not throw a validation error (though it might fail for other reasons like SVN not available)
      try {
        await svnService.getInfo(localPath);
      } catch (error: any) {
        // If it fails, it should not be due to path validation
        expect(error.message).not.toContain('Invalid path:');
      }
    });

    it('should work without path parameter', async () => {
      // This should not throw a validation error
      try {
        await svnService.getInfo();
      } catch (error: any) {
        // If it fails, it should not be due to path validation
        expect(error.message).not.toContain('Invalid path:');
      }
    });

    it('should reject invalid inputs that are neither valid paths nor URLs', async () => {
      const invalidInput = 'file<with>invalid:chars*';
      
      await expect(svnService.getInfo(invalidInput)).rejects.toThrow('Invalid path or URL: file<with>invalid:chars*');
    });
  });
});