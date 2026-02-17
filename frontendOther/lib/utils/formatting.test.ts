import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { formatTimeAgo, truncateText, cleanTranscript } from './formatting';

describe('Formatting Utils', () => {
  describe('formatTimeAgo', () => {
    beforeAll(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2024-01-01T12:00:00Z'));
    });

    afterAll(() => {
      vi.useRealTimers();
    });

    it('returns "just now" for dates less than 60 seconds ago', () => {
      const date = new Date('2024-01-01T11:59:30Z'); // 30 seconds ago
      expect(formatTimeAgo(date)).toBe('just now');
    });

    it('returns "xm ago" for dates less than 1 hour ago', () => {
      const date = new Date('2024-01-01T11:55:00Z'); // 5 minutes ago
      expect(formatTimeAgo(date)).toBe('5m ago');
    });

    it('returns "1m ago" for dates exactly 60 seconds ago', () => {
      const date = new Date('2024-01-01T11:59:00Z'); // 60 seconds ago
      expect(formatTimeAgo(date)).toBe('1m ago');
    });

    it('returns "59m ago" for dates exactly 3599 seconds ago', () => {
      const date = new Date('2024-01-01T11:00:01Z'); // 3599 seconds ago
      expect(formatTimeAgo(date)).toBe('59m ago');
    });

    it('returns "1h ago" for dates exactly 3600 seconds ago', () => {
      const date = new Date('2024-01-01T11:00:00Z'); // 3600 seconds ago
      expect(formatTimeAgo(date)).toBe('1h ago');
    });

    it('returns "xh ago" for dates less than 24 hours ago', () => {
        const date = new Date('2024-01-01T10:00:00Z'); // 2 hours ago
        expect(formatTimeAgo(date)).toBe('2h ago');
    });

    it('returns "23h ago" for dates exactly 86399 seconds ago', () => {
      const date = new Date('2023-12-31T12:00:01Z'); // 86399 seconds ago (23h 59m 59s ago)
      expect(formatTimeAgo(date)).toBe('23h ago');
    });

    it('returns formatted date for dates exactly 86400 seconds ago', () => {
      const date = new Date('2023-12-31T12:00:00Z'); // 86400 seconds ago (24 hours)
      expect(formatTimeAgo(date)).toBe(date.toLocaleDateString());
    });

    it('returns formatted date for dates older than 24 hours', () => {
        const date = new Date('2023-12-30T12:00:00Z'); // 2 days ago
        expect(formatTimeAgo(date)).toBe(date.toLocaleDateString());
    });

    it('handles future dates gracefully (treats as "just now")', () => {
         const date = new Date('2024-01-01T12:01:00Z'); // 1 minute in future
         expect(formatTimeAgo(date)).toBe('just now');
    });
  });

  describe('truncateText', () => {
    it('returns original text if shorter than maxLength', () => {
      expect(truncateText('Hello', 10)).toBe('Hello');
    });

    it('returns original text if equal to maxLength', () => {
      expect(truncateText('Hello', 5)).toBe('Hello');
    });

    it('truncates text and adds ellipsis if longer than maxLength', () => {
      expect(truncateText('Hello World', 5)).toBe('Hello...');
    });

    it('uses default maxLength of 100', () => {
        const longText = 'a'.repeat(101);
        expect(truncateText(longText)).toBe('a'.repeat(100) + '...');
        expect(truncateText('a'.repeat(100))).toBe('a'.repeat(100));
    });

    it('returns empty string if input is empty', () => {
      expect(truncateText('')).toBe('');
    });

    it('returns "..." if maxLength is 0', () => {
      expect(truncateText('Hello', 0)).toBe('...');
    });

    it('returns "..." if maxLength is negative', () => {
      expect(truncateText('Hello', -1)).toBe('...');
    });

    it('returns original text if maxLength is greater than text length', () => {
      expect(truncateText('Hello', 6)).toBe('Hello');
    });
  });

  describe('cleanTranscript', () => {
    it('trims whitespace', () => {
      expect(cleanTranscript('  hello  ')).toBe('hello');
    });

    it('replaces multiple spaces with single space', () => {
      expect(cleanTranscript('hello   world')).toBe('hello world');
    });

    it('removes special characters not allowed', () => {
      // @#$ are not in [^\w\s?.,'!-], so they should be removed
      expect(cleanTranscript('hello @#$ world!')).toBe('hello  world!');
    });

    it('preserves allowed special characters', () => {
        // Allowed: \w \s ? . , ' ! -
        const text = "Hello, world! It's-me? 123";
        expect(cleanTranscript(text)).toBe(text);
    });

    it('handles mixed case and cleanup', () => {
        const text = "  Hello   @World!  ";
        // 1. trim -> "Hello   @World!"
        // 2. replace spaces -> "Hello @World!"
        // 3. remove special chars -> "Hello World!"
        expect(cleanTranscript(text)).toBe('Hello World!');
    });

    it('returns empty string if input is empty', () => {
      expect(cleanTranscript('')).toBe('');
    });

    it('replaces newlines and tabs with space', () => {
      expect(cleanTranscript('Hello\nWorld\t!')).toBe('Hello World !');
    });

    it('returns empty string if input contains only invalid characters', () => {
      expect(cleanTranscript('@#$%^&*()')).toBe('');
    });
  });
});
