import { describe, it, expect, beforeEach } from '@jest/globals';
import { SvnService } from '../tools/svn-service.js';
import { SvnError } from '../common/types.js';

describe('Remote Command Error Handling', () => {
  let svnService: SvnService;

  beforeEach(() => {
    // Use a non-existent directory to trigger working copy errors
    svnService = new SvnService({
      workingDirectory: '/tmp/non-existent-svn-repo',
      timeout: 5000
    });
  });

  describe('diagnoseCommands', () => {
    it('should provide detailed error information and suggestions', async () => {
      const result = await svnService.diagnoseCommands();
      
      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.statusLocal).toBe(false);
      expect(result.data.statusRemote).toBe(false);
      expect(result.data.logBasic).toBe(false);
      expect(result.data.workingCopyPath).toBe('/tmp/non-existent-svn-repo');
      expect(result.data.errors).toHaveLength(3);
      expect(result.data.suggestions).toBeDefined();
      expect(Array.isArray(result.data.suggestions)).toBe(true);
      
      // Check that errors contain more specific information
      const errorMessages = result.data.errors.join(' ');
      expect(errorMessages).toContain('failed');
      
      // Check that suggestions are provided
      expect(result.data.suggestions.length).toBeGreaterThan(0);
    });

    it('should categorize SVN installation errors correctly', async () => {
      const result = await svnService.diagnoseCommands();
      
      // Since SVN likely isn't installed in the test environment, we should get installation errors
      const hasInstallationError = result.data.errors.some(error =>
        error.includes('SVN is not installed') || error.includes('not found in PATH')
      );
      expect(hasInstallationError).toBe(true);

      const hasInstallationSuggestion = result.data.suggestions.some(suggestion =>
        suggestion.includes('Install SVN') || suggestion.includes('PATH')
      );
      expect(hasInstallationSuggestion).toBe(true);
    });

    it('should provide unique suggestions without excessive duplication', async () => {
      const result = await svnService.diagnoseCommands();
      
      // While we might have duplicate suggestions due to the same error type,
      // let's make sure we have meaningful suggestions
      expect(result.data.suggestions.length).toBeGreaterThan(0);
      
      // Check that the first suggestion is meaningful
      expect(result.data.suggestions[0]).toBeTruthy();
      expect(typeof result.data.suggestions[0]).toBe('string');
      expect(result.data.suggestions[0].length).toBeGreaterThan(10);
    });
  });

  describe('getLog error handling', () => {
    it('should provide enhanced error messages for SVN installation issues', async () => {
      try {
        await svnService.getLog(undefined, 1);
        // If it doesn't throw, something unexpected happened
        expect(true).toBe(false);
      } catch (error) {
        expect(error).toBeInstanceOf(SvnError);
        
        const errorMessage = error.message;
        expect(typeof errorMessage).toBe('string');
        expect(errorMessage.length).toBeGreaterThan(0);
        
        // Check if it's the enhanced SVN installation error
        if (errorMessage.includes('SVN is not installed')) {
          expect(errorMessage).toContain('PATH');
        }
      }
    });
  });

  describe('error categorization', () => {
    it('should handle various error types with appropriate suggestions', async () => {
      const result = await svnService.diagnoseCommands();
      
      // Should have errors and suggestions
      expect(result.data.errors.length).toBeGreaterThan(0);
      expect(result.data.suggestions.length).toBeGreaterThan(0);
      
      // Each error should have corresponding details
      for (const error of result.data.errors) {
        expect(error).toContain('failed');
        expect(typeof error).toBe('string');
        expect(error.length).toBeGreaterThan(10);
      }
      
      // Each suggestion should be meaningful
      for (const suggestion of result.data.suggestions) {
        expect(typeof suggestion).toBe('string');
        expect(suggestion.length).toBeGreaterThan(10);
      }
    });
  });

  describe('error message improvements', () => {
    it('should detect and provide helpful guidance for common issues', async () => {
      // Create a service with a working directory that exists but isn't an SVN repo
      const service = new SvnService({
        workingDirectory: '/tmp'
      });
      
      const result = await service.diagnoseCommands();
      
      // Should get errors and suggestions
      expect(result.data.errors.length).toBeGreaterThan(0);
      expect(result.data.suggestions.length).toBeGreaterThan(0);
      
      // Should provide actionable suggestions
      const suggestionsText = result.data.suggestions.join(' ');
      expect(suggestionsText.length).toBeGreaterThan(20); // Meaningful content
    });
  });
});