import { levenshteinDistance } from './utils';

describe('levenshteinDistance', () => {
  it('should return 0 for identical strings', () => {
    expect(levenshteinDistance('hello', 'hello')).toBe(0);
  });

  it('should return the correct distance for strings with different lengths', () => {
    expect(levenshteinDistance('hell', 'hello')).toBe(1);
    expect(levenshteinDistance('hello', 'hell')).toBe(1);
  });

  it('should return the correct distance for strings with substitutions', () => {
    expect(levenshteinDistance('hello', 'hallo')).toBe(1);
  });

  it('should return the correct distance for strings with multiple differences', () => {
    expect(levenshteinDistance('kitten', 'sitting')).toBe(3);
  });

  it('should return the length of the non-empty string when one string is empty', () => {
    expect(levenshteinDistance('', 'hello')).toBe(5);
    expect(levenshteinDistance('hello', '')).toBe(5);
  });

  it('should return 0 for two empty strings', () => {
    expect(levenshteinDistance('', '')).toBe(0);
  });
});
