import { describe, it, expect } from '@jest/globals';
import iconv from 'iconv-lite';

describe('Multi-byte Character Encoding Tests', () => {
  describe('Chunk boundary handling', () => {
    it('should correctly handle multi-byte UTF-8 characters split across chunks', () => {
      // Test string with multi-byte characters
      const testString = 'Hello こんにちは 世界 🌍';
      const fullBuffer = Buffer.from(testString, 'utf8');
      
      // Simulate splitting at an arbitrary position that might split a multi-byte char
      // Japanese character こ is 3 bytes in UTF-8: E3 81 93
      const splitPoint = 9; // This will split the first Japanese character
      const chunk1 = fullBuffer.slice(0, splitPoint);
      const chunk2 = fullBuffer.slice(splitPoint);
      
      // Using iconv-lite streaming decoder (correct approach)
      const decoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
      const decoded1 = decoder.write(chunk1);
      const decoded2 = decoder.write(chunk2);
      const decodedFinal = decoder.end();
      const streamResult = decoded1 + decoded2 + decodedFinal;
      
      // Should reconstruct the original string correctly
      expect(streamResult).toBe(testString);
    });

    it('should handle Shift-JIS multi-byte characters across chunks', () => {
      // Test string with Japanese characters
      const testString = 'こんにちは';
      const fullBuffer = iconv.encode(testString, 'shift_jis');
      
      // Split at a position that breaks a multi-byte character
      const splitPoint = 3;
      const chunk1 = fullBuffer.slice(0, splitPoint);
      const chunk2 = fullBuffer.slice(splitPoint);
      
      // Using streaming decoder
      const decoder = iconv.getDecoder('shift_jis', { stripBOM: false, addBOM: false });
      const decoded1 = decoder.write(chunk1);
      const decoded2 = decoder.write(chunk2);
      const decodedFinal = decoder.end();
      const streamResult = decoded1 + decoded2 + decodedFinal;
      
      // Should reconstruct the original string correctly
      expect(streamResult).toBe(testString);
    });

    it('should handle emoji and other 4-byte UTF-8 sequences', () => {
      const testString = 'Test 🌍🎉🚀 emoji';
      const fullBuffer = Buffer.from(testString, 'utf8');
      
      // Split in the middle of emoji region
      const splitPoint = 8; // This will likely split an emoji
      const chunk1 = fullBuffer.slice(0, splitPoint);
      const chunk2 = fullBuffer.slice(splitPoint);
      
      // Using streaming decoder
      const decoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
      const decoded1 = decoder.write(chunk1);
      const decoded2 = decoder.write(chunk2);
      const decodedFinal = decoder.end();
      const streamResult = decoded1 + decoded2 + decodedFinal;
      
      expect(streamResult).toBe(testString);
    });

    it('should demonstrate the problem with per-chunk detection (old buggy approach)', () => {
      const testString = 'Test こんにちは';
      const fullBuffer = Buffer.from(testString, 'utf8');
      
      // Split at a position that breaks a multi-byte character
      const splitPoint = 7; // This splits the Japanese character
      const chunk1 = fullBuffer.slice(0, splitPoint);
      const chunk2 = fullBuffer.slice(splitPoint);
      
      // Simulating the previous buggy approach: detect and decode each chunk independently
      // Note: jschardet is not imported here to keep test isolated
      // The old implementation did: jschardet.detect(chunk) then iconv.decode(chunk, detected)
      // which failed when multi-byte chars were split
      
      const wrongDecode1 = iconv.decode(chunk1, 'utf8');
      const wrongDecode2 = iconv.decode(chunk2, 'utf8');
      const wrongResult = wrongDecode1 + wrongDecode2;
      
      // This will NOT match the original due to replacement characters for invalid sequences
      expect(wrongResult).not.toBe(testString);
      expect(wrongResult).toContain('\ufffd'); // Contains replacement character
    });
  });

  describe('iconv-lite streaming decoder capabilities', () => {
    it('should buffer incomplete sequences and decode when complete', () => {
      const testString = '日本語';
      const fullBuffer = Buffer.from(testString, 'utf8');
      
      // Send one byte at a time to stress-test the streaming decoder
      const decoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
      let result = '';
      
      for (let i = 0; i < fullBuffer.length; i++) {
        result += decoder.write(fullBuffer.slice(i, i + 1));
      }
      result += decoder.end();
      
      expect(result).toBe(testString);
    });

    it('should work with mixed ASCII and multi-byte content', () => {
      const testString = 'ASCII text 日本語 more ASCII 中文';
      const fullBuffer = Buffer.from(testString, 'utf8');
      
      // Split at various positions
      const splits = [5, 15, 25];
      let lastPos = 0;
      const decoder = iconv.getDecoder('utf8', { stripBOM: false, addBOM: false });
      let result = '';
      
      for (const split of splits) {
        result += decoder.write(fullBuffer.slice(lastPos, split));
        lastPos = split;
      }
      result += decoder.write(fullBuffer.slice(lastPos));
      result += decoder.end();
      
      expect(result).toBe(testString);
    });
  });
});
