import { describe, it, expect, beforeEach } from '@jest/globals';
import { SvnService } from '../tools/svn-service.js';

describe('Issue #3 - Error in svn_info with remote URLs', () => {
  let svnService: SvnService;

  beforeEach(() => {
    svnService = new SvnService();
  });

  it('should handle the exact URL from the issue without validation error', async () => {
    const remoteUrl = 'http://octopus/svnayg/repo/crm-boot';
    
    try {
      // This should not throw a validation error
      await svnService.getInfo(remoteUrl);
    } catch (error: any) {
      // The fix should prevent the "Invalid path" error
      expect(error.message).not.toContain('Invalid path: http://octopus/svnayg/repo/crm-boot');
      expect(error.message).not.toContain('Invalid path or URL:');
      
      // It might fail for other reasons (network, auth, etc.), but not validation
      console.log('Note: SVN command may fail due to network/auth, but validation passed');
    }
  });

  it('should accept various SVN URL formats', async () => {
    const urlFormats = [
      'http://octopus/svnayg/repo/crm-boot',
      'https://svn.example.com/repo/trunk',
      'svn://server.example.com/repo',
      'file:///local/repo/path'
    ];

    for (const url of urlFormats) {
      try {
        await svnService.getInfo(url);
      } catch (error: any) {
        // Should not be validation errors
        expect(error.message).not.toContain('Invalid path:');
        expect(error.message).not.toContain('Invalid path or URL:');
      }
    }
  });
});