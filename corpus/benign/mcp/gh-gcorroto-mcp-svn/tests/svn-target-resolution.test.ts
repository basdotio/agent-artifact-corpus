import { describe, it, expect } from '@jest/globals';
import {
  resolveSvnTarget,
  combineRepoUrl,
  parseListOutput
} from '../common/utils.js';
import { SvnError } from '../common/types.js';

describe('SVN target resolution', () => {
  const config = {
    workingDirectory: '/tmp/wc',
    url: 'https://svn.example.com/repo'
  };

  it('passes through full URLs unchanged', () => {
    const url = 'https://other.host/project/trunk';
    expect(resolveSvnTarget(url, config)).toEqual({ value: url, kind: 'url' });
  });

  it('joins repo-relative paths with SVN_URL', () => {
    expect(resolveSvnTarget('/trunk/app.sql', config)).toEqual({
      value: 'https://svn.example.com/repo/trunk/app.sql',
      kind: 'url'
    });
  });

  it('normalizes local paths when no URL prefix applies', () => {
    const result = resolveSvnTarget('src/main.ts', config);
    expect(result.kind).toBe('path');
    expect(result.value).toContain('src');
  });

  it('rejects empty targets', () => {
    expect(() => resolveSvnTarget('', config)).toThrow(SvnError);
  });
});

describe('combineRepoUrl', () => {
  it('strips duplicate slashes', () => {
    expect(combineRepoUrl('https://svn.example.com/repo/', '/trunk/')).toBe(
      'https://svn.example.com/repo/trunk'
    );
  });
});

describe('parseListOutput', () => {
  it('parses simple listing lines', () => {
    const output = 'README.md\ntrunk/\n';
    expect(parseListOutput(output, false)).toEqual([
      { name: 'README.md', kind: 'file' },
      { name: 'trunk', kind: 'dir' }
    ]);
  });

  it('parses verbose listing lines', () => {
    const output = '   42 alice 1280 2024-01-15 10:00:00 +0000 README.md\n';
    const entries = parseListOutput(output, true);
    expect(entries).toHaveLength(1);
    expect(entries[0].name).toBe('README.md');
    expect(entries[0].revision).toBe(42);
    expect(entries[0].author).toBe('alice');
    expect(entries[0].size).toBe(1280);
  });
});
