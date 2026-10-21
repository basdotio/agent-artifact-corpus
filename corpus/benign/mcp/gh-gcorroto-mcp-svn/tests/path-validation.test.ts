import { describe, it, expect } from '@jest/globals';
import { validatePath } from '../common/utils';

describe('Path Validation Tests', () => {
  describe('Windows Absolute Paths', () => {
    it('should accept Windows absolute paths with drive letters', () => {
      expect(validatePath('C:\\workspaces\\crm-boot')).toBe(true);
      expect(validatePath('D:\\project\\subfolder')).toBe(true);
      expect(validatePath('E:\\folder\\file.txt')).toBe(true);
      expect(validatePath('Z:\\deep\\nested\\folder\\structure')).toBe(true);
    });

    it('should accept Windows absolute paths with forward slashes', () => {
      expect(validatePath('C:/workspaces/crm-boot')).toBe(true);
      expect(validatePath('D:/project/subfolder')).toBe(true);
    });
  });

  describe('Unix Absolute Paths', () => {
    it('should accept Unix absolute paths', () => {
      expect(validatePath('/home/user/project')).toBe(true);
      expect(validatePath('/var/log/file.log')).toBe(true);
      expect(validatePath('/usr/local/bin')).toBe(true);
    });
  });

  describe('Relative Paths', () => {
    it('should accept relative paths', () => {
      expect(validatePath('project/file.txt')).toBe(true);
      expect(validatePath('../other/file.txt')).toBe(true);
      expect(validatePath('../../parent/folder')).toBe(true);
      expect(validatePath('simple-folder')).toBe(true);
    });
  });

  describe('Invalid Characters', () => {
    it('should reject paths with invalid characters', () => {
      expect(validatePath('file<name>.txt')).toBe(false);
      expect(validatePath('file>name.txt')).toBe(false);
      expect(validatePath('file"name.txt')).toBe(false);
      expect(validatePath('file|name.txt')).toBe(false);
      expect(validatePath('file?name.txt')).toBe(false);
      expect(validatePath('file*name.txt')).toBe(false);
    });

    it('should reject paths with colons in inappropriate places', () => {
      expect(validatePath('folder:name/file.txt')).toBe(false);
      expect(validatePath('file:name.txt')).toBe(false);
      expect(validatePath('C:\\folder:name\\file.txt')).toBe(false);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty and null inputs', () => {
      expect(validatePath('')).toBe(true); // Empty string might be valid
      expect(validatePath('.')).toBe(true); // Current directory
      expect(validatePath('..')).toBe(true); // Parent directory
    });

    it('should handle UNC paths', () => {
      expect(validatePath('\\\\server\\share\\file.txt')).toBe(true);
      expect(validatePath('//server/share/file.txt')).toBe(true);
    });
  });
});