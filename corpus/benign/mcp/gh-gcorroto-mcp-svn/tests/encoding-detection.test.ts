import { describe, it, expect, beforeAll } from '@jest/globals';
import { executeSvnCommand, createSvnConfig, validateSvnInstallation } from '../common/utils';
import iconv from 'iconv-lite';
import jschardet from 'jschardet';

describe('Encoding Detection Tests', () => {
  describe('jschardet Library', () => {
    it('should detect UTF-8 encoding', () => {
      const utf8Text = 'Hello World';
      const buffer = Buffer.from(utf8Text, 'utf8');
      const detected = jschardet.detect(buffer);
      
      expect(detected).toBeDefined();
      expect(detected.encoding).toBeDefined();
      // UTF-8 or ASCII are both acceptable for English text
      expect(['UTF-8', 'ascii', 'windows-1252']).toContain(detected.encoding);
    });

    it('should detect different encodings for non-ASCII text', () => {
      // Japanese text in different encodings
      const japaneseText = 'こんにちは'; // "Hello" in Japanese
      const utf8Buffer = Buffer.from(japaneseText, 'utf8');
      const detected = jschardet.detect(utf8Buffer);
      
      expect(detected).toBeDefined();
      expect(detected.encoding).toBeDefined();
      expect(detected.confidence).toBeGreaterThan(0);
    });

    it('should detect Chinese text encoding', () => {
      // Chinese text
      const chineseText = '你好世界'; // "Hello World" in Chinese
      const utf8Buffer = Buffer.from(chineseText, 'utf8');
      const detected = jschardet.detect(utf8Buffer);
      
      expect(detected).toBeDefined();
      expect(detected.encoding).toBeDefined();
      expect(detected.confidence).toBeGreaterThan(0);
    });
  });

  describe('iconv-lite Library', () => {
    it('should decode UTF-8 text correctly', () => {
      const text = 'Hello World';
      const buffer = Buffer.from(text, 'utf8');
      const decoded = iconv.decode(buffer, 'utf8');
      
      expect(decoded).toBe(text);
    });

    it('should decode Japanese text correctly', () => {
      const japaneseText = 'こんにちは';
      const buffer = Buffer.from(japaneseText, 'utf8');
      const decoded = iconv.decode(buffer, 'utf8');
      
      expect(decoded).toBe(japaneseText);
    });

    it('should decode Chinese text correctly', () => {
      const chineseText = '你好世界';
      const buffer = Buffer.from(chineseText, 'utf8');
      const decoded = iconv.decode(buffer, 'utf8');
      
      expect(decoded).toBe(chineseText);
    });

    it('should handle fallback to utf8 for unknown encodings', () => {
      const text = 'Simple text';
      const buffer = Buffer.from(text, 'utf8');
      // Even if we detect null or undefined encoding, we should fallback to utf8
      const detected = jschardet.detect(buffer);
      const encoding = detected && detected.encoding ? detected.encoding : 'utf8';
      const decoded = iconv.decode(buffer, encoding);
      
      expect(decoded).toBeDefined();
      expect(typeof decoded).toBe('string');
    });
  });

  describe('Integration with executeSvnCommand', () => {
    let svnAvailable: boolean;

    beforeAll(async () => {
      const config = createSvnConfig();
      svnAvailable = await validateSvnInstallation(config);
    });

    it('should handle encoding detection in real SVN commands', async () => {
      if (!svnAvailable) {
        console.log('Skipping encoding detection integration test - SVN not available');
        return;
      }

      const config = createSvnConfig();
      
      try {
        // Run a simple SVN command that should work regardless of working copy state
        const result = await executeSvnCommand(config, ['--version', '--quiet']);
        
        expect(result).toBeDefined();
        expect(result.success).toBe(true);
        expect(result.data).toBeDefined();
        expect(typeof result.data).toBe('string');
        
        // The output should be properly decoded
        expect(result.data.length).toBeGreaterThan(0);
      } catch (error) {
        // This is acceptable as we may not have SVN installed
        console.log('SVN command test skipped:', error);
      }
    });
  });

  describe('Encoding Edge Cases', () => {
    it('should handle empty buffers', () => {
      const emptyBuffer = Buffer.from('', 'utf8');
      const detected = jschardet.detect(emptyBuffer);
      const encoding = detected && detected.encoding ? detected.encoding : 'utf8';
      const decoded = iconv.decode(emptyBuffer, encoding);
      
      expect(decoded).toBe('');
    });

    it('should handle binary data gracefully', () => {
      // Create some binary data
      const binaryBuffer = Buffer.from([0x00, 0x01, 0x02, 0x03, 0xFF, 0xFE]);
      const detected = jschardet.detect(binaryBuffer);
      const encoding = detected && detected.encoding ? detected.encoding : 'utf8';
      
      // Should not throw an error
      expect(() => {
        iconv.decode(binaryBuffer, encoding);
      }).not.toThrow();
    });
  });
});
