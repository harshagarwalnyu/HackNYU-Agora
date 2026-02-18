import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn utility', () => {
  it('should merge class names correctly', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2')
  })

  it('should handle conditional classes', () => {
    expect(cn('class1', true && 'class2', false && 'class3')).toBe('class1 class2')
  })

  it('should merge tailwind classes correctly (override)', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2')
    expect(cn('px-2 py-1', 'p-4')).toBe('p-4')
  })

  it('should handle arrays of classes', () => {
    expect(cn(['class1', 'class2'])).toBe('class1 class2')
  })

  it('should handle objects with boolean values', () => {
    expect(cn({ 'class1': true, 'class2': false })).toBe('class1')
  })

  it('should handle mixed inputs', () => {
    expect(cn('class1', ['class2'], { 'class3': true })).toBe('class1 class2 class3')
  })

  it('should ignore undefined and null values', () => {
    expect(cn('class1', undefined, null)).toBe('class1')
  })

  it('should return empty string for no input', () => {
    expect(cn()).toBe('')
  })

  it('should handle complex tailwind merges', () => {
    // text-red-500 is overridden by text-blue-500
    // bg-black is not overridden
    expect(cn('text-red-500 bg-black', 'text-blue-500')).toBe('bg-black text-blue-500')
  })

  it('should handle nested arrays', () => {
    expect(cn(['class1', ['class2', 'class3']])).toBe('class1 class2 class3')
  })

  it('should normalize whitespace', () => {
    expect(cn('  class1  ', '  class2  ')).toBe('class1 class2')
  })

  it('should ignore falsy values including zero', () => {
    expect(cn('class1', 0, false, null, undefined, '')).toBe('class1')
  })

  it('should handle numbers greater than zero', () => {
    // Numbers are converted to strings by clsx and then merged.
    // 1 becomes '1', which is not a tailwind class but is preserved.
    expect(cn('class1', 1)).toBe('class1 1')
  })

  it('should handle specific Tailwind conflicts', () => {
    // p-4 (padding: 1rem) vs px-2 (padding-left/right: 0.5rem)
    // If p-4 comes last, it overrides everything.
    expect(cn('px-2 py-2', 'p-4')).toBe('p-4')

    // If px-2 comes last, it overrides horizontal padding of p-4
    expect(cn('p-4', 'px-2')).toBe('p-4 px-2')
  })
})
