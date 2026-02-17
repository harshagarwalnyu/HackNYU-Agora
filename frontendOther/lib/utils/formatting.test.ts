import { formatTimeAgo, truncateText, cleanTranscript } from './formatting';

describe('Formatting Utils', () => {
  describe('formatTimeAgo', () => {
    beforeAll(() => {
      jest.useFakeTimers();
      jest.setSystemTime(new Date('2024-01-01T12:00:00Z'));
    });

    afterAll(() => {
      jest.useRealTimers();
    });

    it('returns "just now" for dates less than 60 seconds ago', () => {
      const date = new Date('2024-01-01T11:59:30Z'); // 30 seconds ago
      expect(formatTimeAgo(date)).toBe('just now');
    });

    it('returns "xm ago" for dates less than 1 hour ago', () => {
      const date = new Date('2024-01-01T11:55:00Z'); // 5 minutes ago
      expect(formatTimeAgo(date)).toBe('5m ago');
    });

    it('returns "xh ago" for dates less than 24 hours ago', () => {
        const date = new Date('2024-01-01T10:00:00Z'); // 2 hours ago
        expect(formatTimeAgo(date)).toBe('2h ago');
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
  });
});
