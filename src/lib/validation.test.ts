import { describe, expect, it } from 'vitest';
import { validateCustomAlias, validateUrl } from './validation';

describe('validateUrl', () => {
  it('accepts a plain https URL', () => {
    expect(validateUrl('https://example.com/long/path')).toBeNull();
  });

  it('accepts a plain http URL', () => {
    expect(validateUrl('http://example.com')).toBeNull();
  });

  it('rejects a blank input', () => {
    expect(validateUrl('   ')).toBe('Enter a URL.');
  });

  it('rejects unparseable text', () => {
    expect(validateUrl('not a url')).toMatch(/valid URL/i);
  });

  it('rejects a non-http(s) scheme', () => {
    expect(validateUrl('ftp://example.com/file')).toMatch(/http or https/i);
  });

  it('rejects a filename-shaped URL', () => {
    expect(validateUrl('http://report.pdf')).toMatch(/filename/i);
  });
});

describe('validateCustomAlias', () => {
  it('treats blank as valid (optional)', () => {
    expect(validateCustomAlias('')).toBeNull();
    expect(validateCustomAlias('   ')).toBeNull();
  });

  it('accepts 6-12 alphanumeric characters', () => {
    expect(validateCustomAlias('mylink12')).toBeNull();
    expect(validateCustomAlias('abcdef')).toBeNull();
    expect(validateCustomAlias('a1b2c3d4e5f6')).toBeNull();
  });

  it('rejects fewer than 6 characters', () => {
    expect(validateCustomAlias('ab12')).toMatch(/6-12/);
  });

  it('rejects more than 12 characters', () => {
    expect(validateCustomAlias('a'.repeat(13))).toMatch(/6-12/);
  });

  it('rejects non-alphanumeric characters', () => {
    expect(validateCustomAlias('my-link1')).toMatch(/letters or numbers/);
  });
});
